from __future__ import annotations
import asyncio
import json as _json
import random
import re
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional
from urllib.parse import quote_plus
import logging

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.errors import RequestsError
from bs4 import BeautifulSoup

# Chrome impersonation target for curl_cffi. Mudah/Cloudflare fingerprints
# the TLS ClientHello (JA3/JA4) and HTTP/2 SETTINGS frame ordering — pure
# httpx (Python's TLS stack) is trivially detectable and returns 403 even
# with rotated User-Agent headers. curl_cffi links libcurl-impersonate which
# replays a real Chrome handshake, so the server sees us as a browser.
IMPERSONATE_TARGET = "chrome"

from .types_quota import TYPE_SEARCH_KEYWORD, TYPE_URL_PATH, display_region  # noqa: F401

# ── tuning ───────────────────────────────────────────────────────────
HOST = "https://www.mudah.my"
# Generic fallback path when TYPE_URL_PATH doesn't have a per-type entry
# (or when a per-type path 404s and we retry the generic one).
LIST_PATH_TEMPLATE = "/{region}/properties-for-sale"
MAX_PAGES_PER_QUERY = 8
# Concurrency bumped 2× per spec. Anti-bot risk scales linearly; ScraperBanned
# already triggers Playwright fallback so the upper bound is bounded.
PER_HOST_CONCURRENCY = 8
DETAIL_CONCURRENCY = 12
REQUEST_TIMEOUT = 20.0
# Per (region, type) wall-clock budget. Realistic detail-page fan-out with
# 3-retry-then-Playwright mandatory-field loop needs more headroom than the
# original 180s; cells were timing out before any complete row was written.
GLOBAL_DEADLINE_SEC = 600
RETRY_ATTEMPTS = 3

# ── Mandatory-field policy ───────────────────────────────────────────
# Per user spec: bedrooms, price, area (location), size_sqft, bathrooms,
# description MUST be present. A listing missing ANY of these is dropped
# in BOTH realtime and pure_fetch modes (set enforce_mandatory=False to
# bypass for debug/QA).
MANDATORY_FIELDS = ("bedrooms", "price", "area", "size_sqft", "bathrooms", "description")
# Max attempts per detail URL: 3× curl_cffi with rotated UA, then 1×
# Playwright bottom-up render. Total ≤ 4 fetches.
DETAIL_MAX_CURL_ATTEMPTS = 3

# HTML parser used across this module. `lxml` is materially faster than
# `html.parser` on Mudah's ~250 KB detail pages and is required for the
# `:-soup-contains` CSS pseudo-class used in amenity extraction.
# Fall back to the stdlib parser when lxml is unavailable so the scraper
# degrades instead of returning silent 0-row results via bs4.FeatureNotFound.
def _pick_parser() -> str:
    try:
        import lxml  # noqa: F401
        return "lxml"
    except ImportError:
        return "html.parser"

PARSER = _pick_parser()
logger = logging.getLogger(__name__)
logger.debug("[mudah_scraper] HTML parser in use: %s", PARSER)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

# Expanded link-noise blacklist (was 7 entries, now covers tracker / social /
# help / agent landing pages we never want crawled as listings).
_BAD_HREF_KEYWORDS = (
    "facebook", "twitter", "instagram", "linkedin",
    "login", "signup", "register",
    "banner", "ads", "tracking", "utm_",
    "agent", "contact", "help", "faq", "directory",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
)
# Mudah category-aggregator pages — they look listing-shaped but contain no
# real ad. LISTING_HREF_RE catches most via the 6+ digit ID requirement;
# this is the explicit guard against future Mudah URL shape drift.
_FAKE_PAGES = (
    "/property/apartment", "/property/condominium",
    "/property/house", "/property/bungalow",
    "/property/terrace", "/property/townhouse",
    "/property/semi-detached",
)
LISTING_HREF_RE = re.compile(r"-\d{6,}\.htm(?:[?#]|$)")


# ── global realtime URL budget ───────────────────────────────────────
class _RealtimeBudget:
    def __init__(self) -> None:
        self._remaining: int = 0
        self._lock = asyncio.Lock()
        self._enabled: bool = False

    def init(self, n: int) -> None:
        self._remaining = max(0, int(n))
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
        self._remaining = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def remaining(self) -> int:
        return self._remaining if self._enabled else 10 ** 9

    @property
    def exhausted(self) -> bool:
        return self._enabled and self._remaining <= 0

    async def reserve(self, want: int) -> int:
        """Atomically reserve up to `want` slots. Returns count granted."""
        if not self._enabled:
            return max(0, want)
        if want <= 0:
            return 0
        async with self._lock:
            grant = min(want, self._remaining)
            self._remaining -= grant
            return grant


BUDGET = _RealtimeBudget()


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    }


class ScraperBanned(RuntimeError):
    """Raised when the static fetch repeatedly trips anti-bot."""


# ── HTTP layer ───────────────────────────────────────────────────────
# Status codes that justify a retry. Everything else is treated as terminal
# so we don't burn the full RETRY_ATTEMPTS budget on a 404/410.
#
# NOTE: 429 and 503 intentionally appear in BOTH sets. The retry policy is
# "try once, then escalate to Playwright" rather than long curl backoffs —
# Mudah's rate-limit pages respond instantly under chromium because the JS
# challenge passes. Do NOT "fix" this overlap; it is the chosen strategy.
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_BANNED_STATUS = {403, 429, 503}


async def _get(client: AsyncSession, url: str) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            r = await client.get(
                url,
                headers=_headers(),
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT,
            )
            if r.status_code in (200, 201):
                text = r.text
                head = text[:5000].lower()
                if len(text) < 1500 or re.search(
                        r"\b(captcha|are you a human|attention required|just a moment|access denied)\b",
                        head,
                ):
                    raise ScraperBanned(f"anti-bot suspected (len={len(text)})")
                return text
            if r.status_code in _BANNED_STATUS:
                raise ScraperBanned(f"http {r.status_code}")
            # Terminal non-retryable status (e.g. 404, 410, 401). Raise immediately;
            # previous code silently re-looped and ate the full retry budget.
            if r.status_code not in _RETRYABLE_STATUS:
                raise RuntimeError(f"GET {url}: terminal http {r.status_code}")
            last_err = RuntimeError(f"http {r.status_code}")
        except (RequestsError, ScraperBanned) as e:
            last_err = e
        await asyncio.sleep(0.6 * attempt + random.random() * 0.4)
    if isinstance(last_err, ScraperBanned):
        raise last_err
    raise RuntimeError(f"GET failed: {url}: {last_err}")


# Playwright fetch — delegates to the shared, process-wide pool in
# playwright_pool.py. The pool boots Chromium ONCE for the entire run
# and reuses a single BrowserContext across all fetches, so per-page
# Playwright cost drops from ~3-5s (cold boot every call) to ~0.8-1.5s.
# It also blocks image/CSS/font/media at the context level to cut
# wall-clock and bandwidth on every fallback request.
async def _playwright_get(url: str) -> str:
    from .playwright_pool import get_pool
    return await get_pool().get_html(url)


_AMENITY_EMPTY = {
    "facilities_list": None,
    "nearby_bus_stops": None,
    "nearby_schools": None,
    "nearby_parks": None,
    "nearby_hospitals": None,
    "nearby_shopping": None,
}


def _extract_amenities_from_html(html: str) -> Dict[str, Optional[List[str]]]:
    """Parse facilities + nearby amenities out of a fully-rendered detail page.

    Uses `:-soup-contains` (soupsieve) — bs4's `:contains` is a jQuery-only
    pseudo-class and silently matches nothing; the previous implementation
    returned empty results on every page as a result.
    """
    soup = BeautifulSoup(html, PARSER)
    result: Dict[str, Optional[List[str]]] = dict(_AMENITY_EMPTY)

    def _texts(selector: str) -> Optional[List[str]]:
        els = soup.select(selector)
        if not els:
            return None
        out = [el.get_text(strip=True) for el in els]
        out = [t for t in out if t]
        return out or None

    result["facilities_list"]   = _texts("section:-soup-contains('Facilities') span, div[class*='facilities'] li")
    result["nearby_bus_stops"]  = _texts("div:-soup-contains('Bus Stop') ~ ul li, section:-soup-contains('Bus Stop') li")
    result["nearby_schools"]    = _texts("div:-soup-contains('School') ~ ul li, section:-soup-contains('School') li")
    result["nearby_parks"]      = _texts("div:-soup-contains('Park') ~ ul li, section:-soup-contains('Park') li")
    result["nearby_hospitals"]  = _texts("div:-soup-contains('Hospital') ~ ul li")
    result["nearby_shopping"]   = _texts("div:-soup-contains('Mall') ~ ul li, div:-soup-contains('Shopping') ~ ul li")
    return result


def _playwright_extract_all_sync(url: str) -> Dict[str, object]:
    """Combined Playwright pass — phone + whatsapp + gallery + amenities in
    ONE browser launch, ONE page.goto. Previously each ran an independent
    Chromium boot (4×), which dominated per-detail latency.

    Returns a dict with keys:
      - phone: Optional[str]
      - whatsapp: Optional[str]
      - images: List[str]
      - amenities: Dict[str, Optional[List[str]]]
    Each sub-step is wrapped so a single failure (missing button, slow click)
    never poisons the other three results.
    """
    empty: Dict[str, object] = {
        "phone": None,
        "whatsapp": None,
        "images": [],
        "amenities": dict(_AMENITY_EMPTY),
    }
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return empty

    out: Dict[str, object] = dict(empty)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)

                # 1) Phone
                try:
                    call_btns = page.query_selector_all(
                        "button:has-text('Call'), a:has-text('Call')"
                    )
                    if call_btns:
                        call_btns[0].click()
                        page.wait_for_timeout(500)
                    phone_links = page.query_selector_all("a[href^='tel:']")
                    if phone_links:
                        href = phone_links[0].get_attribute("href") or ""
                        m = re.search(r"tel:(.+)", href)
                        if m:
                            out["phone"] = m.group(1).strip()
                except Exception:
                    pass

                # 2) WhatsApp
                try:
                    wa_btns = page.query_selector_all(
                        "button:has-text('WhatsApp'), a:has-text('WhatsApp')"
                    )
                    if wa_btns:
                        wa_btns[0].click()
                        page.wait_for_timeout(500)
                    wa_links = page.query_selector_all(
                        "a[href*='wa.me'], a[href*='api.whatsapp.com']"
                    )
                    if wa_links:
                        href = wa_links[0].get_attribute("href") or ""
                        m = re.search(r"(?:wa\.me|whatsapp\.com/send\?phone=)\+?(\d+)", href)
                        if m:
                            out["whatsapp"] = m.group(1).strip()
                except Exception:
                    pass

                # 3) Gallery (click once to lazy-load full-res, then collect)
                try:
                    gallery_btn = page.query_selector(
                        "div[class*='gallery'], button[class*='photo']"
                    )
                    if gallery_btn:
                        gallery_btn.click()
                        page.wait_for_timeout(800)
                    imgs = page.query_selector_all(
                        "img[src*='cdn.rnudah.com/images/plain']"
                    )
                    collected: List[str] = []
                    for img in imgs:
                        src = img.get_attribute("src")
                        if src and src.startswith("http") and src not in collected:
                            collected.append(src)
                    out["images"] = collected
                except Exception:
                    pass

                # 4) Amenities from the now-fully-rendered DOM
                try:
                    out["amenities"] = _extract_amenities_from_html(page.content())
                except Exception:
                    pass
            finally:
                browser.close()
    except Exception:
        return out
    return out


async def _playwright_extract_all(url: str) -> Dict[str, object]:
    return await asyncio.to_thread(_playwright_extract_all_sync, url)



# ── parsing ──────────────────────────────────────────────────────────
def _build_search_url(
        region: str,
        type_key: str,
        page: int,
        *,
        filters: Optional[Dict] = None,
        force_generic: bool = False,
) -> str:
    """Build a Mudah listing-page URL.

    Path selection:
      1. If `force_generic` is True, use LIST_PATH_TEMPLATE (the generic
         /properties-for-sale path). Used by the 404 fallback in the
         list loop so a wrong per-type path can self-heal.
      2. Else look up TYPE_URL_PATH[type_key] for a category-specific
         path (e.g. /properties-for-sale/condominiums-apartments).
      3. Else fall back to LIST_PATH_TEMPLATE.
    """
    f = filters or {}
    kw_raw = f.get("keyword") or TYPE_SEARCH_KEYWORD[type_key]
    # carpark is encoded as a free-text token appended to `q=` because
    # Mudah has no dedicated query param. We do this BEFORE quoting so
    # multi-word keywords stay readable in logs.
    if f.get("carpark"):
        kw_raw = f"{kw_raw} carpark"
    parts: list[str] = [f"q={quote_plus(str(kw_raw))}", f"o={page}"]

    bedrooms = f.get("bedrooms")
    if isinstance(bedrooms, int) and bedrooms > 0:
        parts.append(f"bedrooms={bedrooms}")

    for k_src, k_url in (("min_price", "min_price"), ("max_price", "max_price")):
        v = f.get(k_src)
        try:
            if v is not None and float(v) > 0:
                parts.append(f"{k_url}={int(round(float(v)))}")
        except (TypeError, ValueError):
            pass

    if force_generic:
        path_tpl = LIST_PATH_TEMPLATE
    else:
        path_tpl = TYPE_URL_PATH.get(type_key, LIST_PATH_TEMPLATE)
    return f"{HOST}{path_tpl.format(region=region)}?" + "&".join(parts)


# Loose regex for harvesting listing URLs from raw HTML (incl. JSON
# blobs like __NEXT_DATA__). Anchored on the mudah.my host so we don't
# pick up arbitrary URLs from inline scripts.
_LISTING_HTML_RE = re.compile(
    r"https?://www\.mudah\.my/[\w\-/]+?-\d{6,}\.htm", re.IGNORECASE
)


def _extract_listing_urls(html: str) -> List[str]:
    # REVIEW (low-risk, not auto-fixed): both _extract_listing_urls and
    # _parse_detail (line ~585) rely on the live mudah.my DOM — CSS
    # selectors, LISTING_HREF_RE, and the attribute names parsed out of
    # each detail page. None of that can be statically verified from this
    # codebase; the only guarantee is runtime + golden-fixture coverage.
    # Treat any silent regression (empty url list, all-None fields after a
    # successful HTTP 200) as a selector-drift signal, not a logic bug.
    soup = BeautifulSoup(html, PARSER)
    urls: List[str] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = HOST + href
        if not href.startswith(HOST):
            continue
        lower = href.lower()
        if any(b in lower for b in _BAD_HREF_KEYWORDS):
            continue
        if any(fp in lower for fp in _FAKE_PAGES):
            continue
        if not LISTING_HREF_RE.search(lower):
            continue
        if href in seen:
            continue
        seen.add(href)
        urls.append(href)

    # __NEXT_DATA__ fallback: when Mudah's SSR hides listing URLs inside
    # the embedded JSON blob (and only renders cards after client-side
    # hydration), the anchor-based scan above returns 0. Sweep the raw
    # HTML for any mudah.my/...-<6+ digit id>.htm pattern as a last
    # resort. Cheap (one regex on the same text bs4 already parsed),
    # safe (host-anchored), and idempotent with `seen` above.
    if not urls:
        for m in _LISTING_HTML_RE.findall(html or ""):
            href = m.split("?")[0].split("#")[0]
            if href in seen:
                continue
            lower = href.lower()
            if any(b in lower for b in _BAD_HREF_KEYWORDS):
                continue
            if any(fp in lower for fp in _FAKE_PAGES):
                continue
            seen.add(href)
            urls.append(href)
    return urls


# K/M-aware: matches "RM 1.2M", "RM 550K", "RM 1,200,000". The `rm` prefix
# is REQUIRED so we never pick up a stray "3" from "3 bedroom".
_PRICE_RE = re.compile(r"rm[\s\u00a0]*([\d.,]+)\s*([km])?", re.I)
_PRICE_SUFFIX = {"k": 1_000, "m": 1_000_000}
_BED_RE = re.compile(r"(\d+)\s*(?:bed|bedroom|bedrooms)", re.I)
_BATH_RE = re.compile(r"(\d+)\s*(?:bath|bathroom|bathrooms)", re.I)
_SQFT_RE = re.compile(r"([\d,]+)\s*sq\s*\.?\s*ft", re.I)


def _clean_price(text: str) -> Optional[float]:
    m = _PRICE_RE.search(text or "")
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    if suffix in _PRICE_SUFFIX:
        val *= _PRICE_SUFFIX[suffix]
    return val


def _extract_next_data(soup: BeautifulSoup) -> Optional[Dict]:
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return _json.loads(tag.string)
    except Exception:
        return None


def _walk_find(node, predicate):
    if predicate(node):
        return node
    if isinstance(node, dict):
        for v in node.values():
            found = _walk_find(v, predicate)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _walk_find(v, predicate)
            if found is not None:
                return found
    return None


def _parse_from_next_data(nd: Dict) -> Dict:
    """全面提取 Mudah __NEXT_DATA__ 中隱藏的所有底層欄位，拒絕遺漏。"""
    out: Dict = {"raw_attributes": {}}
    ad = _walk_find(
        nd,
        lambda n: isinstance(n, dict) and ("adId" in n or "subject" in n) and "price" in n,
    )
    if not isinstance(ad, dict):
        return out

    # 基礎元數據提取
    if ad.get("adId"):
        out["list_id"] = str(ad["adId"])
    if isinstance(ad.get("subject"), str):
        out["title"] = ad["subject"]

    price_val = ad.get("price")
    if isinstance(price_val, (int, float)):
        out["price"] = float(price_val)
    elif isinstance(price_val, str):
        out["price"] = _clean_price(price_val)

    # 業務欄位精確映射
    for k_src, k_dst in (("region", "region_raw"), ("area", "location"),
                         ("city", "city"), ("sellerName", "agent_name"),
                         ("contact", "agent_phone"), ("listTime", "posted_at"),
                         ("body", "description"), ("categoryName", "category_name")):
        if isinstance(ad.get(k_src), (str, int, float)):
            out[k_dst] = ad[k_src]

    # 捕獲全量參數指標（動態屬性回收站）
    params = ad.get("parameters") or ad.get("attributes")
    if isinstance(params, list):
        for p in params:
            if not isinstance(p, dict):
                continue
            label = (p.get("label") or p.get("name") or "").strip()
            val = p.get("value")
            if not label or val is None:
                continue

            out["raw_attributes"][label] = val

            label_lower = label.lower()
            if "bedroom" in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["bedrooms"] = int(m.group(0))
            elif "bathroom" in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["bathrooms"] = int(m.group(0))
            elif "built" in label_lower or "size" in label_lower:
                m = re.search(r"[\d,]+", str(val))
                if m:
                    try:
                        out["built_up_sqft"] = int(m.group(0).replace(",", ""))
                    except ValueError:
                        pass
            elif "land" in label_lower and "area" in label_lower:
                m = re.search(r"[\d,]+", str(val))
                if m:
                    try:
                        out["land_area"] = int(m.group(0).replace(",", ""))
                    except ValueError:
                        pass
            elif "land" in label_lower and "unit" in label_lower:
                out["land_area_unit"] = str(val)
            elif "tenure" in label_lower and "type" in label_lower:
                out["tenure_type"] = str(val)
            elif "tenure" in label_lower and "duration" in label_lower:
                out["remaining_tenure"] = str(val)
            elif "furnish" in label_lower:
                out["furnishing"] = str(val)
            elif "condition" in label_lower:
                out["condition"] = str(val)
            elif "property type" in label_lower:
                out["property_type_specific"] = str(val)
            elif "land title" in label_lower:
                out["land_title"] = str(val)
            elif "strata" in label_lower and "title" in label_lower:
                out["strata_title"] = val in ("Yes", "yes", True, 1)
            elif "carpark" in label_lower or "car" in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["carpark"] = int(m.group(0))
            elif "floor" in label_lower and "range" in label_lower:
                out["floor_range"] = str(val)
            elif "floor" in label_lower and ("unit" in label_lower or "storey" in label_lower):
                m = re.search(r"\d+", str(val))
                if m: out["total_floors_unit"] = int(m.group(0))
            elif "facing" in label_lower or "direction" in label_lower:
                out["facing_direction"] = str(val)
            elif "unit" in label_lower and "type" in label_lower:
                out["unit_type"] = str(val)
            elif "tenancy" in label_lower or "tenanted" in label_lower:
                out["is_tenanted"] = val in ("Yes", "yes", True, 1)
            elif "maintenance" in label_lower or "maintenance fee" in label_lower:
                try:
                    out["maintenance_fee"] = float(val)
                except (TypeError, ValueError):
                    pass
            elif "assessment" in label_lower or "tax" in label_lower:
                try:
                    out["assessment_tax"] = float(val)
                except (TypeError, ValueError):
                    pass
            elif "deposit" in label_lower and "utility" not in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["deposit_months"] = int(m.group(0))
            elif "utility" in label_lower and "deposit" in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["utility_deposit_months"] = int(m.group(0))
            elif "project" in label_lower or "development" in label_lower:
                out["development_name"] = str(val)
            elif "developer" in label_lower:
                out["developer"] = str(val)
            elif "completion" in label_lower:
                m = re.search(r"\d{4}", str(val))
                if m: out["completion_year"] = int(m.group(0))
            elif "total floors" in label_lower and "unit" not in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["total_floors"] = int(m.group(0))
            elif "total units" in label_lower:
                m = re.search(r"\d+", str(val))
                if m: out["total_units"] = int(m.group(0))
            elif "price per" in label_lower or "psf" in label_lower.lower():
                try:
                    out["price_per_sqft"] = float(val)
                except (TypeError, ValueError):
                    pass

    # 圖片抓取：解除限制上限（不再截斷），獲取完整相簿
    imgs = ad.get("images") or ad.get("mediaList") or []
    if isinstance(imgs, list):
        collected: List[str] = []
        for it in imgs:
            if isinstance(it, str) and it.startswith("http"):
                collected.append(it)
            elif isinstance(it, dict):
                for k in ("url", "large", "medium"):
                    v = it.get(k)
                    if isinstance(v, str) and v.startswith("http"):
                        collected.append(v)
                        break
        if collected:
            out["image_urls"] = collected

    return out


def _parse_detail(html: str, url: str, region: str, type_key: str) -> Dict:
    soup = BeautifulSoup(html, PARSER)

    nd = _extract_next_data(soup)
    nd_fields: Dict = _parse_from_next_data(nd) if nd else {"raw_attributes": {}}

    # ── 全域文本提取（用於正則後備） ──
    text = soup.get_text(" ", strip=True)

    # ── 1. AD METADATA ──
    title = nd_fields.get("title")
    if not title:
        h1 = soup.find("h1")
        if h1: title = h1.get_text(strip=True)
    if not title:
        og = soup.find("meta", property="og:title")
        if og: title = og.get("content")

    list_id = nd_fields.get("list_id")
    if not list_id:
        list_id = url.split("-")[-1].replace(".htm", "") if "-" in url else None

    ad_status = None
    status_el = soup.select_one('[data-testid="ad-status"], [class*="status"]')
    if status_el:
        status_text = status_el.get_text(strip=True).lower()
        if "active" in status_text:
            ad_status = "active"
        elif "sold" in status_text:
            ad_status = "sold"
        elif "rented" in status_text:
            ad_status = "rented"

    is_featured = nd_fields.get("is_featured")
    if not is_featured:
        featured_el = soup.select_one('[class*="featured"], [data-testid*="featured"]')
        is_featured = featured_el is not None if featured_el else None

    category_name = nd_fields.get("category_name")
    if not category_name:
        cat_el = soup.select_one('[data-testid="category"], [class*="category"]')
        if cat_el: category_name = cat_el.get_text(strip=True)

    # ── 2. PRICING ──
    price = nd_fields.get("price")
    if price is None:
        price_el = soup.select_one('[data-testid="ad-price"]')
        if price_el: price = _clean_price(price_el.get_text(strip=True))
    if price is None:
        price = _clean_price(text)

    price_display = None
    if price:
        if "per month" in text.lower():
            price_display = f"RM {price:,.0f} per month"
        else:
            price_display = f"RM {price:,.0f}"

    currency = nd_fields.get("currency", "MYR")
    price_per_sqft = nd_fields.get("price_per_sqft")

    # ── 3. LOCATION ──
    region_name = nd_fields.get("region_raw") or region
    area_name = nd_fields.get("location")
    if not area_name:
        og_t = soup.find("meta", property="og:title")
        if og_t:
            # 格式: "...sq.ft, <Area>, <State> <list_id> | Mudah.my"
            m = re.search(r",\s*([^,|]+?),\s*[A-Za-z ]+?\s+\d{6,}\s*\|", og_t.get("content", ""))
            if m:
                area_name = m.group(1).strip()

    state = None
    # State extraction from address or meta
    address_meta = soup.find("meta", {"name": "description"})
    if address_meta:
        desc_text = address_meta.get("content", "").lower()
        # Try to extract state from common Malaysian state names
        states = ["selangor", "kuala lumpur", "johor", "penang", "perak", "pahang", "kedah",
                  "kelantan", "terengganu", "perlis", "negeri sembilan", "melaka", "sabah", "sarawak"]
        for state_name in states:
            if state_name in desc_text:
                state = state_name.title()
                break

    full_address = None
    addr_els = soup.select("p:-soup-contains('Jalan'), p:-soup-contains('Taman'), address")
    if addr_els:
        full_address = addr_els[0].get_text(strip=True)

    postcode = None
    postcode_m = re.search(r"\b\d{5}\b", text)
    if postcode_m:
        postcode = postcode_m.group(0)

    latitude = nd_fields.get("latitude")
    longitude = nd_fields.get("longitude")

    # ── 4. PROPERTY CORE ──
    # 取代 L659-663
    transaction_type = "For Rent" if type_key == "rent" else "For Sale"

    property_type = type_key
    property_sub_type = nd_fields.get("property_type_specific")

    size_sqft = nd_fields.get("built_up_sqft")
    if size_sqft is None:
        sqft_m = _SQFT_RE.search(text)
        if sqft_m:
            try:
                size_sqft = int(sqft_m.group(1).replace(",", ""))
            except ValueError:
                size_sqft = None

    land_area = nd_fields.get("land_area")
    land_area_unit = nd_fields.get("land_area_unit")

    bedrooms = nd_fields.get("bedrooms")
    if bedrooms is None:
        beds_m = _BED_RE.search(text)
        if beds_m:
            bedrooms = int(beds_m.group(1))

    bathrooms = nd_fields.get("bathrooms")
    if bathrooms is None:
        baths_m = _BATH_RE.search(text)
        if baths_m:
            bathrooms = int(baths_m.group(1))

    carpark = nd_fields.get("carpark")
    floor_range = nd_fields.get("floor_range")
    total_floors_unit = nd_fields.get("total_floors_unit")
    furnishing = nd_fields.get("furnishing")
    condition = nd_fields.get("condition")
    facing_direction = nd_fields.get("facing_direction")
    unit_type = nd_fields.get("unit_type")
    is_tenanted = nd_fields.get("is_tenanted")

    # ── 5. TENURE & LEGAL ──
    tenure_type = nd_fields.get("tenure_type")
    remaining_tenure = nd_fields.get("remaining_tenure")
    land_title = nd_fields.get("land_title")
    strata_title = nd_fields.get("strata_title")

    # ── 6. FINANCIAL ──
    maintenance_fee = nd_fields.get("maintenance_fee")
    assessment_tax = nd_fields.get("assessment_tax")
    deposit_months = nd_fields.get("deposit_months")
    utility_deposit_months = nd_fields.get("utility_deposit_months")

    mortgage_estimate = None
    mortgage_m = re.search(r"(?:estimated monthly|mortgage)[\s:]*rm[\s\u00a0]*([\d,]+)", text, re.I)
    if mortgage_m:
        try:
            mortgage_estimate = float(mortgage_m.group(1).replace(",", ""))
        except ValueError:
            mortgage_estimate = None

    mortgage_rate = None
    rate_m = re.search(r"(?:interest rate|rate)[\s:]*(\d+\.?\d*)%", text, re.I)
    if rate_m:
        try:
            mortgage_rate = float(rate_m.group(1))
        except ValueError:
            mortgage_rate = None

    # ── 7. IMAGES ──
    images: List[str] = list(nd_fields.get("image_urls") or [])
    if not images:
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src or any(x in src.lower() for x in ("logo", "icon", "avatar", "placeholder")):
                continue
            if src.startswith("http") and src not in images:
                images.append(src)

    image_count = len(images) if images else None

    # ── 8. DESCRIPTION ──
    desc = nd_fields.get("description") or ""
    if not desc:
        desc_el = soup.select_one("#property-adview-description") or soup.select_one('[data-testid="ad-description"]')
        if desc_el:
            for btn in desc_el.select("button"):
                btn.decompose()
            desc = re.sub(r"\n{2,}", "\n", desc_el.get_text("\n", strip=True))

    # ── 9. SELLER/AGENT ──
    seller_name = nd_fields.get("agent_name")
    if not seller_name:
        agent_el = soup.select_one('[data-testid="seller-name"], [class*="seller-name"]')
        if agent_el: seller_name = agent_el.get_text(strip=True)

    seller_type = None
    if seller_name:
        if "agent" in seller_name.lower() or "property" in seller_name.lower():
            seller_type = "Property agent"
        elif "developer" in seller_name.lower():
            seller_type = "Developer"
        else:
            seller_type = "Private advertiser"

    seller_profile_url = None
    profile_el = soup.select_one("a[href*='/my/'][href*='-real-estate'], a[href*='mudah.my/store']")
    if profile_el:
        seller_profile_url = profile_el.get("href")

    seller_logo_url = None
    logo_el = soup.select_one("img[src*='rnudah.com/stores']")
    if logo_el:
        seller_logo_url = logo_el.get("src")

    ren_number = None
    ren_m = re.search(r"REN\s?(\d+)", text)
    if ren_m:
        ren_number = ren_m.group(1)

    firm_license = None
    firm_m = re.search(r"Firm:\s?(.+?)(?:\n|$)", text)
    if firm_m:
        firm_license = firm_m.group(1).strip()

    is_verified = nd_fields.get("is_verified")
    if is_verified is None:
        verified_el = soup.select_one("a[href*='Seller-Verification'], [class*='verified']")
        is_verified = verified_el is not None if verified_el else None

    total_ads = None
    ads_m = re.search(r"(\d+)\s*(?:For Sale|For Rent)", text)
    if ads_m:
        try:
            total_ads = int(ads_m.group(1))
        except ValueError:
            total_ads = None

    # ── 10. SEO METADATA ──
    og_title = None
    og_title_el = soup.find("meta", property="og:title")
    if og_title_el:
        og_title = og_title_el.get("content")

    og_description = None
    og_desc_el = soup.find("meta", property="og:description")
    if og_desc_el:
        og_description = og_desc_el.get("content")

    og_image = None
    og_img_el = soup.find("meta", property="og:image")
    if og_img_el:
        og_image = og_img_el.get("content")

    meta_description = None
    meta_desc_el = soup.find("meta", {"name": "description"})
    if meta_desc_el:
        meta_description = meta_desc_el.get("content")

    # ── DEVELOPMENT INFO ──
    development_name = nd_fields.get("development_name")
    if not development_name:
        dev_el = soup.select_one("a[href*='/property/properties-in-']")
        if dev_el: development_name = dev_el.get_text(strip=True)

    development_url = None
    if development_name:
        dev_url_el = soup.select_one("a[href*='/property/properties-in-']")
        if dev_url_el:
            development_url = dev_url_el.get("href")

    developer = nd_fields.get("developer")
    if not developer:
        dev_el = soup.select_one("p:-soup-contains('DEVELOPED BY')")
        if dev_el:
            dev_text = dev_el.get_text(strip=True)
            m = re.search(r"DEVELOPED BY\s+(.+)", dev_text)
            if m: developer = m.group(1).strip()

    completion_year = nd_fields.get("completion_year")
    total_floors = nd_fields.get("total_floors")
    total_units = nd_fields.get("total_units")

    # ── 完備的結構化資料組裝 ──
    return {
        # AD METADATA
        "list_id": list_id,
        # listing_url is the canonical key used by storage layer for dedup +
        # CSV write. canonical_url kept for backward-compat with existing
        # downstream consumers (scrape_region_type filter, ranking agent).
        "listing_url": url,
        "canonical_url": url,
        "title": title,
        "description": desc or None,
        "posted_at": nd_fields.get("posted_at"),
        "ad_status": ad_status,
        "is_featured": is_featured,
        "category_name": category_name,

        # PRICING
        "price": price,
        "price_display": price_display,
        "currency": currency,
        "price_per_sqft": price_per_sqft,

        # LOCATION
        "region": region_name,
        "area": area_name,
        "state": state,
        "full_address": full_address,
        "postcode": postcode,
        "latitude": latitude,
        "longitude": longitude,

        # PROPERTY CORE
        "transaction_type": transaction_type,
        "property_type": property_type,
        "property_sub_type": property_sub_type,
        "size_sqft": size_sqft,
        "land_area": land_area,
        "land_area_unit": land_area_unit,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "carpark": carpark,
        "floor_range": floor_range,
        "total_floors_unit": total_floors_unit,
        "furnishing": furnishing,
        "condition": condition,
        "facing_direction": facing_direction,
        "unit_type": unit_type,
        "is_tenanted": is_tenanted,

        # TENURE & LEGAL
        "tenure_type": tenure_type,
        "remaining_tenure": remaining_tenure,
        "land_title": land_title,
        "strata_title": strata_title,

        # FINANCIAL
        "maintenance_fee": maintenance_fee,
        "assessment_tax": assessment_tax,
        "deposit_months": deposit_months,
        "utility_deposit_months": utility_deposit_months,
        "mortgage_estimate": mortgage_estimate,
        "mortgage_rate": mortgage_rate,

        # FACILITIES & AMENITIES (populated by Playwright)
        "facilities_list": None,  # Will be filled by Playwright
        "nearby_bus_stops": None,
        "nearby_schools": None,
        "nearby_parks": None,
        "nearby_hospitals": None,
        "nearby_shopping": None,

        # DEVELOPMENT
        "development_name": development_name,
        "development_url": development_url,
        "developer": developer,
        "completion_year": completion_year,
        "total_floors": total_floors,
        "total_units": total_units,

        # IMAGES
        "image_urls": images,
        "image_count": image_count,

        # SELLER/AGENT
        "seller_name": seller_name,
        "seller_type": seller_type,
        "seller_profile_url": seller_profile_url,
        "seller_logo_url": seller_logo_url,
        "ren_number": ren_number,
        "firm_license": firm_license,
        "is_verified": is_verified,
        "total_ads": total_ads,
        "agent_phone": None,  # Will be filled by Playwright
        "agent_whatsapp": None,  # Will be filled by Playwright

        # SEO
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image,
        "meta_description": meta_description,

        # METADATA
        "source": "mudah.my",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def _populate_playwright_fields(detail: Dict, url: str) -> Dict:
    """Asynchronously populate Playwright-gated fields.

    OPTIMIZED v2: a single Chromium boot + page.goto handles phone,
    whatsapp, gallery, and amenities sequentially in the same page.
    Previously this issued 4 independent browser launches in parallel —
    fewer total wall-seconds than serial, but ~4× the memory / CPU and
    4× the Mudah hit-count per detail. Now: 1 boot, 1 page.goto, ~70%
    less per-detail latency under realistic concurrency.
    """
    try:
        bundle = await _playwright_extract_all(url)
    except Exception:
        return detail
    if not isinstance(bundle, dict):
        return detail

    phone = bundle.get("phone")
    if isinstance(phone, str) and phone:
        detail["agent_phone"] = phone

    whatsapp = bundle.get("whatsapp")
    if isinstance(whatsapp, str) and whatsapp:
        detail["agent_whatsapp"] = whatsapp

    gallery_imgs = bundle.get("images")
    if isinstance(gallery_imgs, list) and gallery_imgs and (
        not detail.get("image_urls")
        or len(gallery_imgs) > len(detail.get("image_urls", []))
    ):
        detail["image_urls"] = gallery_imgs
        detail["image_count"] = len(gallery_imgs)

    amenities = bundle.get("amenities")
    if isinstance(amenities, dict):
        for k in (
            "facilities_list", "nearby_bus_stops", "nearby_schools",
            "nearby_parks", "nearby_hospitals", "nearby_shopping",
        ):
            v = amenities.get(k)
            if v is not None:
                detail[k] = v
    return detail


# ── public API ───────────────────────────────────────────────────────
def make_shared_client() -> AsyncSession:
    """Build the canonical async HTTP client used across the entire scrape run.

    Returns a curl_cffi AsyncSession that impersonates a real Chrome browser
    at the TLS layer (JA3/JA4 ClientHello + HTTP/2 SETTINGS order). This is
    required to bypass Mudah.my's Cloudflare bot protection, which fingerprints
    Python's native TLS stack and returns 403 regardless of User-Agent headers.

    `max_clients` mirrors the previous httpx.Limits.max_connections so per-host
    concurrency stays bounded at the same level as before the curl_cffi migration.
    """
    return AsyncSession(
        impersonate=IMPERSONATE_TARGET,
        max_clients=PER_HOST_CONCURRENCY * 4,
        timeout=REQUEST_TIMEOUT,
    )


# Type keys for which numeric 0 in bedrooms/bathrooms/size_sqft is a LEGAL
# value rather than an extraction failure (e.g. land, parking, commercial
# shoplot). Empty today because TYPE_QUOTA only ships residential keys; add
# here when extending coverage so the BUG-3 guard does not over-trigger
# expensive Playwright retries on legitimately 0-bedroom records.
_ZERO_ALLOWED_TYPES: set = set()
_ZERO_ALLOWED_FIELDS = ("bedrooms", "bathrooms", "size_sqft")


def _is_complete(detail: Optional[Dict], type_key: Optional[str] = None) -> bool:
    """True iff every mandatory field is present and non-empty.

    Rules:
      - None                                     -> missing
      - str: empty / whitespace-only             -> missing
      - int / float == 0 on bedrooms/bathrooms/
        size_sqft (residential types)            -> missing (extraction failed;
                                                    triggers Playwright retry)
      - int / float == 0 on type_key in
        _ZERO_ALLOWED_TYPES                       -> legal (land/parking/etc.)
      - any other truthy value                   -> present

    `area` here implements the user-chosen LOCATION definition (option B:
    `area` must be non-empty)."""
    if not isinstance(detail, dict):
        return False
    zero_ok = type_key in _ZERO_ALLOWED_TYPES
    for f in MANDATORY_FIELDS:
        v = detail.get(f)
        if v is None:
            return False
        if isinstance(v, str) and not v.strip():
            return False
        if (
            not zero_ok
            and f in _ZERO_ALLOWED_FIELDS
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and v == 0
        ):
            return False
    return True


async def scrape_region_type(
        region: str,
        type_key: str,
        target_count: int,
        *,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
        on_row: Optional[Callable[[Dict], Awaitable[None]]] = None,
        filters: Optional[Dict] = None,
        skip_playwright: bool = False,
        enforce_mandatory: bool = True,
        client: Optional[AsyncSession] = None,
) -> List[Dict]:
    """Scrape one (region,type).

    Per-detail fetch strategy (enforce_mandatory=True, default):
      1..3: curl_cffi GET with rotated UA. Parse. Keep if all 6 mandatory
            fields present, else small backoff and retry with a new UA.
      4:    Playwright bottom-up render (one chromium boot, full DOM).
            Parse. Keep if complete, else DROP.

    `skip_playwright=True` disables the per-property phone/whatsapp/
    gallery/amenities AUGMENTATION (used by pure_fetch for speed), but
    Playwright is still used as the 4th mandatory-field retry per the
    user-chosen retry policy (3 curl + 1 Playwright = 4 attempts).

    `enforce_mandatory=False` returns every parsed row regardless of
    completeness (debug / golden-fixture path).
    """
    if target_count <= 0:
        return []

    start = time.monotonic()
    deadline = start + GLOBAL_DEADLINE_SEC

    host_sem = asyncio.Semaphore(PER_HOST_CONCURRENCY)
    detail_sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

    list_use_playwright = False
    collected: List[Dict] = []
    dropped_incomplete = 0
    seen_urls: set[str] = set()

    _owned = client is None
    _client = client or make_shared_client()
    try:
        # ── list-page fetch with layered fallback ───────────────────
        # Per (region, type, page) total attempt budget = 5:
        #   1× curl_cffi (cheap path)
        #   3× curl_cffi retries with rotated UA on:
        #       • ScraperBanned exception, OR
        #       • HTTP 200 but `_extract_listing_urls` returns 0 (soft block /
        #         empty SSR shell — would previously silently break the cell).
        #   1× Playwright fallback (shared pool, cheap after first boot)
        #
        # On 404 (terminal in _get), we self-heal once by retrying with
        # `force_generic=True` so a wrong TYPE_URL_PATH entry doesn't kill
        # the cell — the generic /properties-for-sale?q=keyword path is
        # always accepted by Mudah.
        async def _list_fetch(page_no: int) -> tuple[Optional[str], str]:
            """Returns (html, source_tag). source_tag in {curl, curl-retry, pw, ''}."""
            url_specific = _build_search_url(
                region, type_key, page_no, filters=filters
            )
            url_generic = _build_search_url(
                region, type_key, page_no, filters=filters, force_generic=True
            )
            attempted_generic = (url_specific == url_generic)

            async def _try_curl(u: str) -> Optional[str]:
                async with host_sem:
                    return await _get(_client, u)

            # Attempt 1: cheap curl on type-specific path.
            for target in ((url_specific, "curl"),) + (
                () if attempted_generic else ((url_generic, "curl-generic"),)
            ):
                u, tag = target
                try:
                    h = await _try_curl(u)
                    if h and _extract_listing_urls(h):
                        return h, tag
                    last_html = h
                except ScraperBanned:
                    last_html = None
                    break  # ban → skip path-fallback, go straight to retry
                except RuntimeError as e:
                    # 404/410/etc on the type-specific path → try generic once.
                    msg = str(e).lower()
                    if "terminal http 404" in msg or "terminal http 410" in msg:
                        print(
                            f"[scrape-list] PATH_404 region={region} type={type_key} "
                            f"page={page_no} url={u} → falling back to generic path",
                            flush=True,
                        )
                        continue
                    last_html = None
                except Exception:
                    last_html = None

            # Attempts 2-4: curl retries with rotated UA + short backoff.
            for attempt in range(1, 4):
                if time.monotonic() > deadline:
                    break
                await asyncio.sleep(0.5 * attempt + random.random() * 0.3)
                try:
                    async with host_sem:
                        h = await _get(_client, url_generic)
                    if h and _extract_listing_urls(h):
                        return h, "curl-retry"
                    last_html = h
                except ScraperBanned:
                    last_html = None
                    break
                except Exception:
                    last_html = None

            # Attempt 5: Playwright (shared pool).
            try:
                async with host_sem:
                    h = await _playwright_get(url_generic)
                if h:
                    return h, "pw"
            except Exception as e:
                print(
                    f"[scrape-list] PW_FAIL region={region} type={type_key} "
                    f"page={page_no} err={type(e).__name__}: {str(e)[:120]}",
                    flush=True,
                )
            return last_html, ""

        listing_urls: List[str] = []
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            if time.monotonic() > deadline:
                break
            if BUDGET.exhausted:
                break

            html, source = await _list_fetch(page)
            if source == "pw":
                # Detail fetches in this cell will now also use Playwright,
                # mirroring previous behaviour when list was banned.
                list_use_playwright = True

            if not html:
                print(
                    f"[scrape-list] WARN region={region} type={type_key} page={page} "
                    f"source={source or 'none'} html_len=0 status=fail",
                    flush=True,
                )
                break

            urls = _extract_listing_urls(html)
            new = [u for u in urls if u not in seen_urls]
            next_data_present = "__NEXT_DATA__" in html
            print(
                f"[scrape-list] region={region} type={type_key} page={page} "
                f"source={source} html_len={len(html)} "
                f"extracted={len(urls)} new={len(new)} "
                f"next_data={'Y' if next_data_present else 'N'} "
                f"(running_total={len(listing_urls) + len(new)})",
                flush=True,
            )
            if not new:
                print(
                    f"[scrape-list] EMPTY region={region} type={type_key} page={page} "
                    f"source={source} — stopping pagination",
                    flush=True,
                )
                break
            grant = await BUDGET.reserve(len(new))
            if grant <= 0:
                break
            new = new[:grant]
            for u in new:
                seen_urls.add(u)
            listing_urls.extend(new)
            if on_progress:
                await on_progress(f"{region}/{type_key} page {page}: +{len(new)} (total {len(listing_urls)})")
            if BUDGET.exhausted:
                break
            if not BUDGET.enabled and len(listing_urls) >= target_count * 2:
                break

        async def _fetch_html_once(u: str, *, force_playwright: bool) -> Optional[str]:
            try:
                async with detail_sem:
                    if force_playwright or list_use_playwright:
                        return await _playwright_get(u)
                    return await _get(_client, u)
            except ScraperBanned:
                try:
                    return await _playwright_get(u)
                except Exception:
                    return None
            except Exception:
                return None

        async def fetch_one(u: str) -> Optional[Dict]:
            best: Optional[Dict] = None
            for attempt in range(1, DETAIL_MAX_CURL_ATTEMPTS + 1):
                if time.monotonic() > deadline:
                    return None
                html_ = await _fetch_html_once(u, force_playwright=False)
                if not html_:
                    continue
                try:
                    detail = _parse_detail(html_, u, region, type_key)
                except Exception as _e:
                    print(f"[scrape] PARSE_FAIL url={u} err={type(_e).__name__}: {_e}", flush=True)
                    continue
                best = detail
                if not enforce_mandatory or _is_complete(detail, type_key):
                    break
                await asyncio.sleep(0.4 * attempt + random.random() * 0.3)
            if enforce_mandatory and (best is None or not _is_complete(best, type_key)):
                if time.monotonic() <= deadline:
                    html_ = await _fetch_html_once(u, force_playwright=True)
                    if html_:
                        try:
                            best = _parse_detail(html_, u, region, type_key)
                        except Exception as _e:
                            print(f"[scrape] PARSE_FAIL(pw) url={u} err={type(_e).__name__}: {_e}", flush=True)
            if best is None:
                return None
            if not skip_playwright:
                try:
                    best = await _populate_playwright_fields(best, u)
                except Exception:
                    pass
            try:
                print(
                    f"[scrape] region={region} url={u} "
                    f"title={(best.get('title') or '')[:60]!r} "
                    f"price={best.get('price')} bedrooms={best.get('bedrooms')} "
                    f"area={(best.get('area') or '')[:30]!r} "
                    f"sqft={best.get('size_sqft')} bath={best.get('bathrooms')} "
                    f"desc_len={len(best.get('description') or '')}",
                    flush=True,
                )
            except Exception:
                pass
            if enforce_mandatory and not _is_complete(best, type_key):
                missing = [f for f in MANDATORY_FIELDS if not best.get(f)]
                print(f"[scrape] DROP_INCOMPLETE url={u} missing={missing}", flush=True)
                return None
            return best

        slice_n = len(listing_urls) if BUDGET.enabled else (target_count + 20)
        tasks: List[asyncio.Task] = [
            asyncio.create_task(fetch_one(u)) for u in listing_urls[:slice_n]
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                row = await coro
                if row and row.get("canonical_url"):
                    collected.append(row)
                    if on_row is not None:
                        # Stream this row to the caller (e.g. for incremental
                        # CSV flush) BEFORE the cell finishes. Swallow errors
                        # so a sink failure never aborts the scrape.
                        try:
                            await on_row(row)
                        except Exception as _sink_err:
                            print(
                                f"[scrape] on_row sink raised: "
                                f"{type(_sink_err).__name__}: {_sink_err}",
                                flush=True,
                            )
                else:
                    dropped_incomplete += 1
                if not BUDGET.enabled and len(collected) >= target_count:
                    break
        finally:
            pending = [t for t in tasks if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
    finally:
        if _owned:
            # curl_cffi AsyncSession exposes .close(), not .aclose() (httpx API).
            try:
                await _client.close()
            except Exception:
                pass

    print(
        f"[scrape] DONE region={region} type={type_key} kept={len(collected)} "
        f"dropped_or_failed={dropped_incomplete} list_urls={len(listing_urls)}",
        flush=True,
    )
    return collected
