"""
scraper/playwright_pool.py
──────────────────────────
Shared, process-wide Playwright pool. One Chromium boot per run, one
BrowserContext reused across all fetches, new Page per request.

Why this module exists
======================
The previous `_playwright_get_sync` in mudah_scraper.py called
`with sync_playwright(): browser = p.chromium.launch(); ...` on EVERY
call. Each Chromium cold-start is 2-5 seconds — with N fallback pages
per run that's the dominant cost. This pool amortises one ~2s startup
across the entire run so per-page Playwright cost drops to ~0.8-1.5s.

Optimisations vs Hackathon-67's playwright_client.py
====================================================
- No auto-scroll on list pages (pagination via ?o=N already covers it).
- No `wait_for_timeout(2500)` style sleeps (pure waste of wall clock).
- Block CSS / image / font / media / stylesheet via route() — Mudah's
  listing anchors are in HTML/__NEXT_DATA__ and don't need any of these.
  Cuts bytes ~80% and reduces render time another ~30%.
- Single shared UA across the context (no per-page rotation): keeps the
  TLS+H2 fingerprint stable so the server doesn't bucket us into a
  "suspicious mixed-UA" risk score.

Usage
=====
    from .playwright_pool import get_pool, shutdown_pool
    html = await get_pool().get_html("https://...")
    ...
    await shutdown_pool()   # call in finally of the run orchestrator
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Block these resource types — list pages don't need them.
_BLOCKED_TYPES = {"image", "stylesheet", "font", "media"}

# Default UA: stable, modern Chrome.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Cap concurrent pages opened against the same browser.
# Bumped 4 → 6: pure_fetch runs up to 24 cells in parallel
# (4 regions × 6 types) and a 4-slot queue starved goto() so badly
# that the 20s timeout fired before navigation even committed.
_MAX_CONCURRENT_PAGES = 6
# One retry on goto failure with a short backoff. The previous code
# returned "" on the first timeout, which is what produced the wave
# of `[playwright_pool] goto fail ... Timeout 20000ms exceeded.`
# lines and the resulting `kept=0` cells.
_GOTO_RETRIES = 1
_GOTO_RETRY_BACKOFF_SEC = 1.5


class PlaywrightPool:
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._context = None
        self._sem = asyncio.Semaphore(_MAX_CONCURRENT_PAGES)
        self._start_lock = asyncio.Lock()

    async def _ensure_started(self) -> None:
        if self._context is not None:
            return
        async with self._start_lock:
            if self._context is not None:
                return
            try:
                from playwright.async_api import async_playwright
            except ImportError as e:
                raise RuntimeError(
                    "Playwright not installed. `pip install playwright && "
                    "playwright install chromium`"
                ) from e
            logger.info("[playwright_pool] starting shared Chromium")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=_DEFAULT_UA,
                viewport={"width": 1366, "height": 768},
                java_script_enabled=True,
            )
            # Resource blocker installed once at context level.
            async def _route(route, request):
                if request.resource_type in _BLOCKED_TYPES:
                    await route.abort()
                else:
                    await route.continue_()
            await self._context.route("**/*", _route)

    async def get_html(
            self,
            url: str,
            *,
            goto_timeout_ms: int = 45000,
            anchor_wait_ms: int = 5000,
            capture_listing_urls: bool = False,
    ) -> str:
        """Fetch URL with the shared browser. Returns HTML or "" on failure.

        Strategy:
          - goto with wait_until="domcontentloaded" (don't wait for all images).
          - try wait_for_selector("a[href*='.htm']") up to anchor_wait_ms;
            on timeout, return whatever HTML is in the DOM right now
            (let the caller's __NEXT_DATA__ regex pick up URLs from JSON).
        """
        await self._ensure_started()
        async with self._sem:
            page = await self._context.new_page()
            # Network-response capture for dynamically-injected listing URLs
            # that __NEXT_DATA__ does not expose. Listener MUST be attached
            # BEFORE goto() to avoid missing early XHR/fetch responses.
            captured: list[str] = []
            if capture_listing_urls:
                import re as _re
                _LRE = _re.compile(
                    r"https?://www\.mudah\.my/[\w\-/]+?-\d{6,}\.htm",
                    _re.IGNORECASE,
                )
                def _on_response(resp) -> None:
                    try:
                        u = resp.url
                        if "mudah.my" in u and ".htm" in u:
                            for m in _LRE.findall(u):
                                captured.append(m)
                    except Exception:
                        pass
                page.on("response", _on_response)
            try:
                last_err: Optional[Exception] = None
                for attempt in range(_GOTO_RETRIES + 1):
                    try:
                        await page.goto(url, wait_until="domcontentloaded",
                                        timeout=goto_timeout_ms)
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        if attempt < _GOTO_RETRIES:
                            await asyncio.sleep(_GOTO_RETRY_BACKOFF_SEC * (attempt + 1))
                            continue
                if last_err is not None:
                    logger.warning("[playwright_pool] goto fail %s: %s",
                                   url, str(last_err)[:120])
                    return ""
                try:
                    await page.wait_for_selector(
                        "a[href*='.htm']", timeout=anchor_wait_ms
                    )
                except Exception:
                    # Soft timeout — fall through and return current DOM.
                    pass
                try:
                    html = await page.content()
                except Exception as e:
                    logger.warning("[playwright_pool] content fail %s: %s",
                                   url, str(e)[:120])
                    return ""
                if capture_listing_urls and captured:
                    # Append unique captured URLs as a comment block so the
                    # downstream _LISTING_HTML_RE sweep picks them up. We use
                    # an HTML comment to avoid corrupting BeautifulSoup parsing.
                    uniq = list(dict.fromkeys(captured))
                    logger.info("[playwright_pool] captured %d listing URLs via network",
                                len(uniq))
                    html += "\n<!-- network-captured: " + " ".join(uniq) + " -->\n"
                return html
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

    async def shutdown(self) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("[playwright_pool] shutdown complete")


_INSTANCE: Optional[PlaywrightPool] = None


def get_pool() -> PlaywrightPool:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PlaywrightPool()
    return _INSTANCE


async def shutdown_pool() -> None:
    global _INSTANCE
    if _INSTANCE is not None:
        await _INSTANCE.shutdown()
        _INSTANCE = None
