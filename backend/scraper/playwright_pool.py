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
_MAX_CONCURRENT_PAGES = 4


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
            goto_timeout_ms: int = 20000,
            anchor_wait_ms: int = 5000,
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
            try:
                try:
                    await page.goto(url, wait_until="domcontentloaded",
                                    timeout=goto_timeout_ms)
                except Exception as e:
                    logger.warning("[playwright_pool] goto fail %s: %s",
                                   url, str(e)[:120])
                    return ""
                try:
                    await page.wait_for_selector(
                        "a[href*='.htm']", timeout=anchor_wait_ms
                    )
                except Exception:
                    # Soft timeout — fall through and return current DOM.
                    pass
                try:
                    return await page.content()
                except Exception as e:
                    logger.warning("[playwright_pool] content fail %s: %s",
                                   url, str(e)[:120])
                    return ""
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
