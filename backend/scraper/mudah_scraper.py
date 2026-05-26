from __future__ import annotations
import asyncio
import json as _json
import random
import re
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from .types_quota import TYPE_SEARCH_KEYWORD, display_region  # noqa: F401

# ── tuning ───────────────────────────────────────────────────────────
HOST = "https://www.mudah.my"
LIST_PATH_TEMPLATE = "/{region}/properties-for-sale"
MAX_PAGES_PER_QUERY = 8
PER_HOST_CONCURRENCY = 4
DETAIL_CONCURRENCY = 6
REQUEST_TIMEOUT = 20.0
GLOBAL_DEADLINE_SEC = 180
RETRY_ATTEMPTS = 3

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

LISTING_HREF_RE = re.compile(r"-\d{6,}\.htm(?:[?#]|$)")


# ── global realtime URL budget ───────────────────────────────────────
# Realtime mode hard-caps the number of *listing URLs* collected across
# all regions/types in one search. Once the cap is hit, scraping stops
# and control returns to the ranking pipeline.
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
        return self._remaining if self._enabled else 10**9

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
async def _get(client: httpx.AsyncClient, url: str) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            r = await client.get(url, headers=_headers(), follow_redirects=True, timeout=REQUEST_TIMEOUT)
            if r.status_code in (200, 201):
                text = r.text
                if len(text) < 800 or "captcha" in text.lower() or "are you a human" in text.lower():
                    raise ScraperBanned(f"anti-bot suspected (len={len(text)})")
                return text
            if r.status_code in (403, 429, 503):
                raise ScraperBanned(f"http {r.status_code}")
            last_err = RuntimeError(f"http {r.status_code}")
        except (httpx.TransportError, ScraperBanned) as e:
            last_err = e
        await asyncio.sleep(0.6 * attempt + random.random() * 0.4)
    if isinstance(last_err, ScraperBanned):
        raise last_err
    raise RuntimeError(f"GET failed: {url}: {last_err}")


def _playwright_get_sync(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError(f"Playwright unavailable: {e}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            return page.content()
        finally:
            browser.close()


async def _playwright_get(url: str) -> str:
    return await asyncio.to_thread(_playwright_get_sync, url)


# ── parsing ──────────────────────────────────────────────────────────
def _build_search_url(region: str, type_key: str, page: int) -> str:
    kw = quote_plus(TYPE_SEARCH_KEYWORD[type_key])
    return f"{HOST}{LIST_PATH_TEMPLATE.format(region=region)}?q={kw}&o={page}"


def _extract_listing_urls(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    seen = set()
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = HOST + href
        if not href.startswith(HOST):
            continue
        lower = href.lower()
        if any(b in lower for b in ("facebook", "twitter", "login", "signup", ".svg", ".png", ".jpg")):
            continue
        if not LISTING_HREF_RE.search(lower):
            continue
        if href in seen:
            continue
        seen.add(href)
        urls.append(href)
    return urls


_PRICE_RE = re.compile(r"rm[\s\u00a0]*([\d.,]+)", re.I)
_BED_RE   = re.compile(r"(\d+)\s*(?:bed|bedroom|bedrooms)", re.I)
_BATH_RE  = re.compile(r"(\d+)\s*(?:bath|bathroom|bathrooms)", re.I)
_SQFT_RE  = re.compile(r"([\d,]+)\s*sq\s*\.?\s*ft", re.I)


def _clean_price(text: str) -> Optional[float]:
    m = _PRICE_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


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
            
            # 將完整的 Key-Value 保留，杜絕任何新欄位遺漏
            out["raw_attributes"][label] = val
            
            # 針對結構化數據進行精確轉換
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
                    try: out["built_up_sqft"] = int(m.group(0).replace(",", ""))
                    except ValueError: pass
            elif "land" in label_lower:
                m = re.search(r"[\d,]+", str(val))
                if m:
                    try: out["land_sqft"] = int(m.group(0).replace(",", ""))
                    except ValueError: pass
            elif "tenure" in label_lower:
                out["tenure"] = str(val)
            elif "furnish" in label_lower:
                out["furnishing"] = str(val)
            elif "property type" in label_lower:
                out["property_type_specific"] = str(val)
            elif "title" in label_lower:
                out["land_title"] = str(val)

    # 圖片抓取：解除限制上限（不再截斷 [:8]），獲取完整相簿
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
    soup = BeautifulSoup(html, "html.parser")

    nd = _extract_next_data(soup)
    nd_fields: Dict = _parse_from_next_data(nd) if nd else {"raw_attributes": {}}

    # ── DOM Fallbacks (當 NEXT_DATA 被防護干擾時的後備機制) ──
    title = nd_fields.get("title")
    if not title:
        h1 = soup.find("h1")
        if h1: title = h1.get_text(strip=True)
    if not title:
        og = soup.find("meta", property="og:title")
        if og: title = og.get("content")

    text = soup.get_text(" ", strip=True)

    price = nd_fields.get("price")
    if price is None:
        price_el = soup.select_one('[data-testid="ad-price"]')
        if price_el: price = _clean_price(price_el.get_text(strip=True))
    if price is None:
        price = _clean_price(text)

    beds_m = _BED_RE.search(text)
    baths_m = _BATH_RE.search(text)
    sqft_m = _SQFT_RE.search(text)

    images: List[str] = list(nd_fields.get("image_urls") or [])
    if not images:
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src or any(x in src.lower() for x in ("logo", "icon", "avatar", "placeholder")):
                continue
            if src.startswith("http") and src not in images:
                images.append(src)

    desc = nd_fields.get("description") or ""
    if not desc:
        desc_el = soup.select_one("#property-adview-description") or soup.select_one('[data-testid="ad-description"]')
        if desc_el:
            for btn in desc_el.select("button"):
                btn.decompose()
            desc = re.sub(r"\n{2,}", "\n", desc_el.get_text("\n", strip=True))

    loc_area = nd_fields.get("location")
    if not loc_area:
        meta_kw = soup.find("meta", {"name": "keywords"})
        if meta_kw:
            loc_area = (meta_kw.get("content") or "").split(",")[0].strip() or None

    agent_name = nd_fields.get("agent_name")
    if not agent_name:
        agent_el = soup.select_one('[data-testid="seller-name"], [class*="seller-name"]')
        if agent_el: agent_name = agent_el.get_text(strip=True)

    agent_phone = nd_fields.get("agent_phone")
    if not agent_phone:
        phone_match = re.search(r"\+?60\s*\d[\d\s-]{6,}", text)
        if phone_match: agent_phone = phone_match.group(0).strip()

    # ── 完備的結構化資料組裝 ──
    return {
        "listing_url": url,
        "list_id": nd_fields.get("list_id") or (url.split("-")[-1].replace(".htm", "") if "-" in url else None),
        "source": "mudah.my",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "price": price,
        "currency": "MYR",
        "property_type": type_key,
        "category_name": nd_fields.get("category_name"),
        "region": region,
        "location_area": loc_area,
        "city": nd_fields.get("city") or loc_area,
        
        # 房屋物理特徵
        "bedrooms": nd_fields.get("bedrooms") if nd_fields.get("bedrooms") is not None
                    else (int(beds_m.group(1)) if beds_m else None),
        "bathrooms": nd_fields.get("bathrooms") if nd_fields.get("bathrooms") is not None
                    else (int(baths_m.group(1)) if baths_m else None),
        "built_up_sqft": nd_fields.get("built_up_sqft") if nd_fields.get("built_up_sqft") is not None
                    else (int(sqft_m.group(1).replace(",", "")) if sqft_m else None),
        "land_sqft": nd_fields.get("land_sqft"),
        
        # 房屋產權與配置
        "tenure": nd_fields.get("tenure"),
        "furnishing": nd_fields.get("furnishing"),
        "land_title": nd_fields.get("land_title"),
        "property_type_specific": nd_fields.get("property_type_specific"),
        
        # 發布者資訊
        "agent_name": agent_name,
        "agent_phone": agent_phone,
        "posted_at": nd_fields.get("posted_at"),
        "description": desc or None,
        "image_urls": images,
        
        # 【重要】動態屬性池：若頁面出現設施、周邊或全新自定義標籤，皆會被封裝在此處
        "raw_attributes": nd_fields.get("raw_attributes", {})
    }


# ── public API ───────────────────────────────────────────────────────
async def scrape_region_type(
    region: str,
    type_key: str,
    target_count: int,
    *,
    on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
) -> List[Dict]:
    if target_count <= 0:
        return []

    start = time.monotonic()
    deadline = start + GLOBAL_DEADLINE_SEC

    host_sem = asyncio.Semaphore(PER_HOST_CONCURRENCY)
    detail_sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

    use_playwright = False
    collected: List[Dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(http2=False) as client:
        listing_urls: List[str] = []
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            if time.monotonic() > deadline:
                break
            if BUDGET.exhausted:
                break
            url = _build_search_url(region, type_key, page)
            html: Optional[str] = None
            try:
                async with host_sem:
                    html = await _get(client, url)
            except ScraperBanned:
                use_playwright = True
                try:
                    html = await _playwright_get(url)
                except Exception:
                    break
            except Exception:
                continue
            if not html:
                continue
            urls = _extract_listing_urls(html)
            new = [u for u in urls if u not in seen_urls]
            if not new:
                break
            # Reserve against the global realtime URL budget.
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

        async def fetch_one(u: str) -> Optional[Dict]:
            if time.monotonic() > deadline:
                return None
            try:
                async with detail_sem:
                    if use_playwright:
                        html_ = await _playwright_get(u)
                    else:
                        html_ = await _get(client, u)
            except ScraperBanned:
                try:
                    html_ = await _playwright_get(u)
                except Exception:
                    return None
            except Exception:
                return None
            try:
                return _parse_detail(html_, u, region, type_key)
            except Exception:
                return None

        # In realtime-budget mode, fetch details for ALL reserved URLs
        # (count was already capped by BUDGET.reserve). Otherwise keep
        # the original target_count + 20 over-fetch slack.
        slice_n = len(listing_urls) if BUDGET.enabled else (target_count + 20)
        tasks: List[asyncio.Task] = [
            asyncio.create_task(fetch_one(u)) for u in listing_urls[:slice_n]
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                row = await coro
                if row and row.get("listing_url"):
                    collected.append(row)
                if not BUDGET.enabled and len(collected) >= target_count:
                    break
        finally:
            pending = [t for t in tasks if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

    return collected