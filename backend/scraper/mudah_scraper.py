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


def _playwright_click_reveal_phone(url: str) -> Optional[str]:
    """Click 'Call' button to reveal phone number."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)

                # Click 'Call' button
                call_btns = page.query_selector_all("button:has-text('Call'), a:has-text('Call')")
                if call_btns:
                    call_btns[0].click()
                    page.wait_for_timeout(600)

                # Extract phone href
                phone_links = page.query_selector_all("a[href^='tel:']")
                if phone_links:
                    href = phone_links[0].get_attribute("href")
                    if href:
                        m = re.search(r"tel:(.+)", href)
                        if m:
                            return m.group(1).strip()
                return None
            finally:
                browser.close()
    except Exception:
        return None


async def _playwright_click_reveal_phone_async(url: str) -> Optional[str]:
    return await asyncio.to_thread(_playwright_click_reveal_phone, url)


def _playwright_click_reveal_whatsapp(url: str) -> Optional[str]:
    """Click 'WhatsApp' button to reveal WhatsApp number."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)

                # Click 'WhatsApp' button
                wa_btns = page.query_selector_all("button:has-text('WhatsApp'), a:has-text('WhatsApp')")
                if wa_btns:
                    wa_btns[0].click()
                    page.wait_for_timeout(600)

                # Extract WhatsApp link
                wa_links = page.query_selector_all("a[href*='wa.me'], a[href*='api.whatsapp.com']")
                if wa_links:
                    href = wa_links[0].get_attribute("href")
                    if href:
                        m = re.search(r"(?:wa\.me|whatsapp\.com/send\?phone=)\+?(\d+)", href)
                        if m:
                            return m.group(1).strip()
                return None
            finally:
                browser.close()
    except Exception:
        return None


async def _playwright_click_reveal_whatsapp_async(url: str) -> Optional[str]:
    return await asyncio.to_thread(_playwright_click_reveal_whatsapp, url)


def _playwright_click_gallery_images(url: str) -> List[str]:
    """Click gallery to load all full-res image URLs."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)

                # Click gallery container or thumbnails to load full-res
                gallery_btn = page.query_selector("div[class*='gallery'], button[class*='photo']")
                if gallery_btn:
                    gallery_btn.click()
                    page.wait_for_timeout(1000)

                # Collect all full-res image URLs
                img_selectors = page.query_selector_all("img[src*='cdn.rnudah.com/images/plain']")
                collected = []
                for img in img_selectors:
                    src = img.get_attribute("src")
                    if src and src.startswith("http") and src not in collected:
                        collected.append(src)

                return collected if collected else []
            finally:
                browser.close()
    except Exception:
        return []


async def _playwright_click_gallery_images_async(url: str) -> List[str]:
    return await asyncio.to_thread(_playwright_click_gallery_images, url)


def _playwright_extract_amenities(url: str) -> Dict[str, List[str]]:
    """Extract facilities and nearby amenities via DOM crawling."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {
            "facilities_list": None,
            "nearby_bus_stops": None,
            "nearby_schools": None,
            "nearby_parks": None,
            "nearby_hospitals": None,
            "nearby_shopping": None,
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                result = {
                    "facilities_list": None,
                    "nearby_bus_stops": None,
                    "nearby_schools": None,
                    "nearby_parks": None,
                    "nearby_hospitals": None,
                    "nearby_shopping": None,
                }

                # Extract facilities
                fac_els = soup.select("section:contains('Facilities') span, div[class*='facilities'] li")
                if fac_els:
                    facilities = [el.get_text(strip=True) for el in fac_els]
                    result["facilities_list"] = facilities if facilities else None

                # Extract bus stops
                bus_els = soup.select("div:contains('Bus Stop') ~ ul li, section:contains('Bus Stop') li")
                if bus_els:
                    buses = [el.get_text(strip=True) for el in bus_els]
                    result["nearby_bus_stops"] = buses if buses else None

                # Extract schools
                school_els = soup.select("div:contains('School') ~ ul li, section:contains('School') li")
                if school_els:
                    schools = [el.get_text(strip=True) for el in school_els]
                    result["nearby_schools"] = schools if schools else None

                # Extract parks
                park_els = soup.select("div:contains('Park') ~ ul li, section:contains('Park') li")
                if park_els:
                    parks = [el.get_text(strip=True) for el in park_els]
                    result["nearby_parks"] = parks if parks else None

                # Extract hospitals
                hosp_els = soup.select("div:contains('Hospital') ~ ul li")
                if hosp_els:
                    hospitals = [el.get_text(strip=True) for el in hosp_els]
                    result["nearby_hospitals"] = hospitals if hospitals else None

                # Extract shopping
                shop_els = soup.select("div:contains('Mall') ~ ul li, div:contains('Shopping') ~ ul li")
                if shop_els:
                    shopping = [el.get_text(strip=True) for el in shop_els]
                    result["nearby_shopping"] = shopping if shopping else None

                return result
            finally:
                browser.close()
    except Exception:
        return {
            "facilities_list": None,
            "nearby_bus_stops": None,
            "nearby_schools": None,
            "nearby_parks": None,
            "nearby_hospitals": None,
            "nearby_shopping": None,
        }


async def _playwright_extract_amenities_async(url: str) -> Dict[str, List[str]]:
    return await asyncio.to_thread(_playwright_extract_amenities, url)


# ── parsing ──────────────────────────────────────────────────────────
def _build_search_url(
        region: str,
        type_key: str,
        page: int,
        *,
        filters: Optional[Dict] = None,
) -> str:
    f = filters or {}
    kw_raw = f.get("keyword") or TYPE_SEARCH_KEYWORD[type_key]
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

    return f"{HOST}{LIST_PATH_TEMPLATE.format(region=region)}?" + "&".join(parts)


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
_BED_RE = re.compile(r"(\d+)\s*(?:bed|bedroom|bedrooms)", re.I)
_BATH_RE = re.compile(r"(\d+)\s*(?:bath|bathroom|bathrooms)", re.I)
_SQFT_RE = re.compile(r"([\d,]+)\s*sq\s*\.?\s*ft", re.I)


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
    soup = BeautifulSoup(html, "html.parser")

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
        meta_kw = soup.find("meta", {"name": "keywords"})
        if meta_kw:
            area_name = (meta_kw.get("content") or "").split(",")[0].strip() or None

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
    addr_els = soup.select("p:contains('Jalan'), p:contains('Taman'), address")
    if addr_els:
        full_address = addr_els[0].get_text(strip=True)

    postcode = None
    postcode_m = re.search(r"\b\d{5}\b", text)
    if postcode_m:
        postcode = postcode_m.group(0)

    latitude = nd_fields.get("latitude")
    longitude = nd_fields.get("longitude")

    # ── 4. PROPERTY CORE ──
    transaction_type = None
    if "rent" in text.lower() or type_key == "rent":
        transaction_type = "For Rent"
    else:
        transaction_type = "For Sale"

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
        dev_el = soup.select_one("p:contains('DEVELOPED BY')")
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
    """Asynchronously populate Playwright-gated fields."""
    try:
        # Get agent phone
        phone = await _playwright_click_reveal_phone_async(url)
        if phone:
            detail["agent_phone"] = phone
    except Exception:
        pass

    try:
        # Get agent WhatsApp
        whatsapp = await _playwright_click_reveal_whatsapp_async(url)
        if whatsapp:
            detail["agent_whatsapp"] = whatsapp
    except Exception:
        pass

    try:
        # Get full-res gallery images
        gallery_imgs = await _playwright_click_gallery_images_async(url)
        if gallery_imgs and (not detail.get("image_urls") or len(gallery_imgs) > len(detail.get("image_urls", []))):
            detail["image_urls"] = gallery_imgs
            detail["image_count"] = len(gallery_imgs)
    except Exception:
        pass

    try:
        # Get amenities
        amenities = await _playwright_extract_amenities_async(url)
        if amenities:
            detail["facilities_list"] = amenities.get("facilities_list")
            detail["nearby_bus_stops"] = amenities.get("nearby_bus_stops")
            detail["nearby_schools"] = amenities.get("nearby_schools")
            detail["nearby_parks"] = amenities.get("nearby_parks")
            detail["nearby_hospitals"] = amenities.get("nearby_hospitals")
            detail["nearby_shopping"] = amenities.get("nearby_shopping")
    except Exception:
        pass

    return detail


# ── public API ───────────────────────────────────────────────────────
async def scrape_region_type(
        region: str,
        type_key: str,
        target_count: int,
        *,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
        filters: Optional[Dict] = None,
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
            url = _build_search_url(region, type_key, page, filters=filters)
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
                detail = _parse_detail(html_, u, region, type_key)
                # Populate Playwright-gated fields
                detail = await _populate_playwright_fields(detail, u)
                return detail
            except Exception:
                return None

        slice_n = len(listing_urls) if BUDGET.enabled else (target_count + 20)
        tasks: List[asyncio.Task] = [
            asyncio.create_task(fetch_one(u)) for u in listing_urls[:slice_n]
        ]
        try:
            for coro in asyncio.as_completed(tasks):
                row = await coro
                if row and row.get("canonical_url"):
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