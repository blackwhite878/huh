# wsdfc_scraper_fix_v1

Fixes phase-3 Mudah scraper returning 0 rows / `extracted=0 new=0` across
most (region, type) cells.

## Root causes (compared against m-11117593-glitch/Hackathon-67)

1. **list-page loop only fell back to Playwright on `ScraperBanned`.**
   HTTP 200 with an empty Next.js shell (0 anchors matched) was treated
   as success, leading to immediate `break` on the cell.
2. **`_extract_listing_urls` only scanned `<a href>` anchors.** Mudah's
   SSR'd shell often hides listing URLs inside the `__NEXT_DATA__` JSON
   blob, so the anchor scan returned 0 even on a healthy page.
3. **Playwright fallback booted a brand-new Chromium per call** (~3-5s
   each). At fallback rates of dozens of pages per run this dominated
   wall time and made fallback effectively unusable.
4. **`LIST_PATH_TEMPLATE` was hard-coded to `/properties-for-sale`** for
   every `type_key`, relying on `?q=keyword` as the only filter. The
   generic page returns sparser SSR content than category-specific paths.

## Changes

| File | Change |
|------|--------|
| `backend/scraper/playwright_pool.py` (NEW) | Process-wide singleton `PlaywrightPool` — one Chromium boot, shared `BrowserContext`, per-page `new_page()`. Blocks image/CSS/font/media at route level. Caps concurrent pages at 4. |
| `backend/scraper/mudah_scraper.py` | Replaced per-call `_playwright_get_sync` with pool-backed `_playwright_get`. Added `__NEXT_DATA__` regex fallback in `_extract_listing_urls`. Rewrote list-page loop with 5-attempt budget: curl → 3× curl retry on 200+0urls or ban → 1× Playwright. Added `force_generic` to `_build_search_url` plus 404→generic self-heal. Replaced terse `[scrape] list` print with structured `[scrape-list]` WARN including `source`, `html_len`, `next_data` flag. |
| `backend/scraper/types_quota.py` | Added `TYPE_URL_PATH` dict mapping each type_key to a category-specific Mudah path. |
| `backend/scraper/pure_fetch_realtime.py` | `run_pure_fetch_realtime` `finally` block now calls `shutdown_pool()` so the shared Chromium is torn down after each run. |

## How to apply

```bash
cd <huh repo root>
git apply wsdfc_scraper_fix_v1.patch
# (one-time, if not already done)
pip install playwright
playwright install chromium
```

## How to calibrate `TYPE_URL_PATH`

The default paths are reasonable guesses based on Mudah's public
taxonomy. The list loop self-heals 404s by retrying with the generic
path, so a wrong entry will not crash the cell — you'll see:

```
[scrape-list] PATH_404 region=johor type=condo page=1 url=... → falling back to generic path
```

To permanently fix, edit `backend/scraper/types_quota.py` `TYPE_URL_PATH`
to point at the real path you find by browsing Mudah manually.

## How to roll back

```bash
git apply -R wsdfc_scraper_fix_v1.patch
```

No schema, storage, or CSV layout changes — rollback is safe at any time.

## Expected effect

| Metric | Before | After |
|---|---|---|
| Cells returning 0 rows | ~50%+ from log | <10% expected |
| Chromium boots per run | N (one per fallback call) | 1 |
| Avg Playwright fallback latency | ~3-5s | ~0.8-1.5s |
| List-page silent breaks (0 anchors, HTTP 200) | yes | retried with rotated UA + PW fallback |
