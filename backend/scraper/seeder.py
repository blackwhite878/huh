"""
Seeder & realtime fetch orchestrator.

Functions:
- ensure_region(region): if longterm CSV already at MAX_PER_REGION → skip.
  Otherwise top up per-type using cross-type back-fill policy (A).
  Returns dict {type_key: count_now, "total": N, "skipped": bool}.

- fetch_realtime_into_tempo(session_id, regions): scrape live, write to tempo
  JSON keyed by region+session_id, plus append-only into long-term CSV.
  Persists partial results: every successful per-type scrape is appended to
  both stores BEFORE moving on, so a later failure does not lose earlier work.

- load_demo_into_tempo(session_id, regions): copy from long-term CSV into the
  same tempo JSON shape (no network).

- run_with_retry_then_demo(coro_factory, retries=3): runs the supplied async
  coroutine; on three consecutive failures it switches to demo and sets the
  global `forced_demo` flag.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional

from . import storage
from .types_quota import (
    MAX_PER_REGION, MY_REGIONS, TYPE_QUOTA,
)
from .mudah_scraper import scrape_region_type

logger = logging.getLogger(__name__)

# Per-region type concurrency: how many (type) scrapes for a single region we
# run in parallel. Each scrape_region_type call already has its own per-host
# semaphore, so this is an outer fan-out cap.
REGION_TYPE_CONCURRENCY = 3


# ── global degradation flag (module-level singleton) ──────────────────
class _Flags:
    forced_demo: bool = False
    last_error: Optional[str] = None

FLAGS = _Flags()


def reset_flags() -> None:
    FLAGS.forced_demo = False
    FLAGS.last_error = None


# ── long-term seeder ──────────────────────────────────────────────────
async def ensure_region(region: str) -> Dict:
    """Top up a region's long-term CSV to MAX_PER_REGION. Skip if already full."""
    existing = storage.load_longterm(region)
    if len(existing) >= MAX_PER_REGION:
        return {"region": region, "skipped": True, "total": len(existing)}

    by_type_now: Dict[str, int] = {t: 0 for t in TYPE_QUOTA}
    for r in existing:
        t = r.get("property_type")
        if t in by_type_now:
            by_type_now[t] += 1

    # Pass 1: hit each type's nominal quota.
    for type_key, quota in TYPE_QUOTA.items():
        deficit = quota - by_type_now[type_key]
        if deficit <= 0:
            continue
        try:
            rows = await scrape_region_type(region, type_key, deficit)
        except Exception as e:
            logger.warning("[seed] %s/%s scrape raised: %r", region, type_key, e)
            rows = []
        written = storage.append_longterm(region, rows)
        by_type_now[type_key] += written
        logger.info("[seed] %s/%s scraped=%d written=%d", region, type_key, len(rows), written)

    # Pass 2: cross-type back-fill if total still under MAX_PER_REGION.
    total_now = sum(by_type_now.values())
    if total_now < MAX_PER_REGION:
        remaining = MAX_PER_REGION - total_now
        for type_key in sorted(TYPE_QUOTA, key=lambda k: -TYPE_QUOTA[k]):
            if remaining <= 0:
                break
            try:
                rows = await scrape_region_type(region, type_key, remaining)
            except Exception as e:
                logger.warning("[seed-backfill] %s/%s raised: %r", region, type_key, e)
                rows = []
            written = storage.append_longterm(region, rows)
            by_type_now[type_key] += written
            remaining -= written

    return {
        "region": region,
        "skipped": False,
        "total": sum(by_type_now.values()),
        "by_type": by_type_now,
    }


async def ensure_all_regions(regions: Optional[List[str]] = None) -> List[Dict]:
    regions = regions or MY_REGIONS
    results = []
    for r in regions:
        try:
            results.append(await ensure_region(r))
        except Exception as e:  # pragma: no cover
            logger.exception("ensure_region(%s) failed", r)
            results.append({"region": r, "error": str(e)})
    return results


# ── demo / realtime → tempo ───────────────────────────────────────────
def load_demo_into_tempo(session_id: str, regions: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for region in regions:
        rows = storage.load_longterm(region)
        storage.write_tempo(region, session_id, rows)
        counts[region] = len(rows)
    return counts


async def _scrape_one_type_persist(region: str, session_id: str, type_key: str, quota: int) -> int:
    """Scrape one type, persist into long-term CSV AND session tempo. Returns rows scraped."""
    try:
        rows = await scrape_region_type(region, type_key, quota)
    except Exception as e:
        logger.warning("[realtime] %s/%s scrape raised: %r", region, type_key, e)
        return 0
    if not rows:
        return 0
    storage.append_longterm(region, rows)
    storage.append_tempo(region, session_id, rows)
    return len(rows)


async def fetch_realtime_into_tempo(session_id: str, regions: List[str]) -> Dict[str, int]:
    """
    Scrape each region live. Types within a region run concurrently (bounded
    by REGION_TYPE_CONCURRENCY). After each region we re-snapshot tempo from
    the union of (just-scraped rows ∪ pre-existing long-term CSV) so the
    ranking agent always sees the freshest data even on partial failure.
    """
    counts: Dict[str, int] = {}
    for region in regions:
        # Initialise tempo with whatever long-term data already exists so a
        # total scrape failure still produces a usable file.
        pre = storage.load_longterm(region)
        storage.write_tempo(region, session_id, pre)

        if storage.longterm_count(region) >= MAX_PER_REGION:
            counts[region] = len(pre)
            continue

        sem = asyncio.Semaphore(REGION_TYPE_CONCURRENCY)

        async def _bounded(t: str, q: int) -> int:
            async with sem:
                return await _scrape_one_type_persist(region, session_id, t, q)

        results = await asyncio.gather(
            *[_bounded(t, q) for t, q in TYPE_QUOTA.items()],
            return_exceptions=True,
        )
        total_new = sum(r for r in results if isinstance(r, int))

        # Re-snapshot tempo to the freshest union (CSV is authoritative).
        rows = storage.load_longterm(region)
        storage.write_tempo(region, session_id, rows)
        counts[region] = len(rows)
        logger.info("[realtime] %s: +%d new, total=%d", region, total_new, len(rows))

    return counts


# ── retry orchestrator ────────────────────────────────────────────────
async def run_with_retry_then_demo(
    realtime_coro: Callable[[], Awaitable[Dict[str, int]]],
    demo_coro:     Callable[[], Dict[str, int]],
    *,
    retries: int = 3,
) -> Dict[str, int]:
    """
    Tries realtime up to `retries` times. On three consecutive failures, falls
    back to demo and sets FLAGS.forced_demo = True so the frontend can show a
    popup via /api/v1/system_status.

    A realtime attempt that returns an empty dict OR a dict whose values are
    all zero is treated as a failed attempt — otherwise a silently-banned
    scrape would be reported as success and the frontend would never know.
    """
    last_err: Optional[str] = None
    for attempt in range(1, retries + 1):
        try:
            res = await realtime_coro()
            if res and any(v > 0 for v in res.values()):
                return res
            last_err = f"attempt {attempt}: empty result {res!r}"
            logger.warning("[scraper] realtime empty %s", last_err)
        except Exception as e:
            last_err = f"attempt {attempt}: {e!r}"
            logger.warning("[scraper] realtime failed %s", last_err)
        await asyncio.sleep(1.0 * attempt)
    FLAGS.forced_demo = True
    FLAGS.last_error = last_err
    logger.error("[scraper] forced DEMO after %d retries: %s", retries, last_err)
    return demo_coro()
