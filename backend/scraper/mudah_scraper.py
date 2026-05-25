"""
Lean async Mudah.my scraper.

Design goals:
- Primary path: httpx + BeautifulSoup4 (fast, no browser).
- Fallback path: Playwright (JS-rendered fall-through) — used only when the
  static fetch yields too few links or the response looks like an anti-bot
  challenge.
- Polite by default: per-host semaphore, randomised jitter, rotating UA.
- No infinite loops: hard caps on pages and per-call deadlines.

Public coroutine:
    async def scrape_region_type(region, type_key, target_count, *, on_progress=None) -> list[dict]

Returns rows matching storage.CSV_FIELDS.
"""
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
# NOTE: Mudah uses path-based region routing, e.g.
#   https://www.mudah.my/selangor/properties-for-sale?q=condo&o=2
# The previous form `/malaysia/properties-for-sale?location=<region>` returns
# 404 / empty pages and was the root cause of "scraper saves no data".
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

# Mudah detail URLs end in `-<digits>.htm`. The previous regex also matched
# `/property/properties-in-...` listing-index pages which are NOT details and
# produced garbage parses. Tightened to detail pages only.
LISTING_HREF_RE = re.compile(r"-\d{6,}\.htm(?:[?#]|$)")


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
    except Exception as e:  # pragma: no cover
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
    # region is the canonical slug ("selangor", "kuala-lumpur", "negeri-sembilan").
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
    """
    Mudah is a Next.js app. The reliable ground-truth payload lives in
    <script id="__NEXT_DATA__" type="application/json">{...}</script>.
    Falls back silently if absent (older A/B variants or anti-bot stub).
    """
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return _json.loads(tag.string)
    except Exception:
        return None


def _walk_find(node, predicate):
    """Depth-first search a nested JSON tree for the first node matching predicate."""
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
    """Best-effort extraction from Mudah's __NEXT_DATA__. Returns partial dict."""
    out: Dict = {}
    ad = _walk_find(
        nd,
        lambda n: isinstance(n, dict) and ("adId" in n or "subject" in n) and "price" in n,
    )
    if not isinstance(ad, dict):
        return out

    if isinstance(ad.get("subject"), str):
        out["title"] = ad["subject"]

    price_val = ad.get("price")
    if isinstance(price_val, (int, float)):
        out["price"] = float(price_val)
    elif isinstance(price_val, str):
        out["price"] = _clean_price(price_val)

    for k_src, k_dst in (("region", "region_raw"), ("area", "location_area"),
                         ("city", "city"), ("sellerName", "agent_name"),
                         ("contact", "agent_phone"), ("listTime", "posted_at"),
                         ("body", "description")):
        if isinstance(ad.get(k_src), (str, int, float)):
            out[k_dst] = ad[k_src]

    params = ad.get("parameters") or ad.get("attributes")
    if isinstance(params, list):
        for p in params:
            if not isinstance(p, dict):
                continue
            label = (p.get("label") or p.get("name") or "").lower()
            val = p.get("value")
            if not label or val is None:
                continue
            if "bedroom" in label:
                m = re.search(r"\d+", str(val))
                if m:
                    out["bedrooms"] = int(m.group(0))
            elif "bathroom" in label:
                m = re.search(r"\d+", str(val))
                if m:
                    out["bathrooms"] = int(m.group(0))
            elif "built" in label or "size" in label:
                m = re.search(r"[\d,]+", str(val))
                if m:
                    try:
                        out["built_up_sqft"] = int(m.group(0).replace(",", ""))
                    except ValueError:
                        pass
            elif "land" in label:
                m = re.search(r"[\d,]+", str(val))
                if m:
                    try:
                        out["land_sqft"] = int(m.group(0).replace(",", ""))
                    except ValueError:
                        pass
            elif "tenure" in label:
                out["tenure"] = str(val)
            elif "furnish" in label:
                out["furnishing"] = str(val)

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
                        collected.append(v); break
        if collected:
            out["image_urls"] = collected[:8]
    return out


def _parse_detail(html: str, url: str, region: str, type_key: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    # Prefer the structured __NEXT_DATA__ payload; degrade to DOM scraping.
    nd = _extract_next_data(soup)
    nd_fields: Dict = _parse_from_next_data(nd) if nd else {}

    title = nd_fields.get("title")
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    if not title:
        og = soup.find("meta", property="og:title")
        if og:
            title = og.get("content")

    text = soup.get_text(" ", strip=True)

    price = nd_fields.get("price")
    if price is None:
        price_el = soup.select_one('[data-testid="ad-price"]')
        if price_el:
            price = _clean_price(price_el.get_text(strip=True))
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
            if src.startswith("http"):
                images.append(src)

    desc = nd_fields.get("description") or ""
    if not desc:
        desc_el = soup.select_one("#property-adview-description") or soup.select_one('[data-testid="ad-description"]')
        if desc_el:
            for btn in desc_el.select("button"):
                btn.decompose()
            desc = re.sub(r"\n{2,}", "\n", desc_el.get_text("\n", strip=True))

    loc_area = nd_fields.get("location_area")
    if not loc_area:
        meta_kw = soup.find("meta", {"name": "keywords"})
        if meta_kw:
            loc_area = (meta_kw.get("content") or "").split(",")[0].strip() or None

    agent_name = nd_fields.get("agent_name")
    if not agent_name:
        agent_el = soup.select_one('[data-testid="seller-name"], [class*="seller-name"]')
        if agent_el:
            agent_name = agent_el.get_text(strip=True)

    agent_phone = nd_fields.get("agent_phone")
    if not agent_phone:
        phone_match = re.search(r"\+?60\s*\d[\d\s-]{6,}", text)
        if phone_match:
            agent_phone = phone_match.group(0).strip()

    return {
        "listing_url": url,
        "source": "mudah.my",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "price": price,
        "currency": "MYR",
        "property_type": type_key,
        "region": region,
        "location_area": loc_area,
        "city": nd_fields.get("city") or loc_area,
        "bedrooms": nd_fields.get("bedrooms") if nd_fields.get("bedrooms") is not None
                    else (int(beds_m.group(1)) if beds_m else None),
        "bathrooms": nd_fields.get("bathrooms") if nd_fields.get("bathrooms") is not None
                    else (int(baths_m.group(1)) if baths_m else None),
        "built_up_sqft": nd_fields.get("built_up_sqft") if nd_fields.get("built_up_sqft") is not None
                    else (int(sqft_m.group(1).replace(",", "")) if sqft_m else None),
        "land_sqft": nd_fields.get("land_sqft"),
        "tenure": nd_fields.get("tenure"),
        "furnishing": nd_fields.get("furnishing"),
        "agent_name": agent_name,
        "agent_phone": agent_phone,
        "posted_at": nd_fields.get("posted_at"),
        "description": desc or None,
        "image_urls": images[:8],
    }


# ── public API ───────────────────────────────────────────────────────
async def scrape_region_type(
    region: str,
    type_key: str,
    target_count: int,
    *,
    on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
) -> List[Dict]:
    """Scrape Mudah.my for one (region,type) up to target_count listings."""
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
            for u in new:
                seen_urls.add(u)
            listing_urls.extend(new)
            if on_progress:
                await on_progress(f"{region}/{type_key} page {page}: +{len(new)} (total {len(listing_urls)})")
            if len(listing_urls) >= target_count * 2:
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

        tasks: List[asyncio.Task] = [
            asyncio.create_task(fetch_one(u)) for u in listing_urls[: target_count + 20]
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                row = await coro
                if row and row.get("listing_url"):
                    collected.append(row)
                if len(collected) >= target_count:
                    break
        finally:
            pending = [t for t in tasks if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

    return collected
