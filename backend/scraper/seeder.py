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

from curl_cffi.requests import AsyncSession

from . import storage
from .query_variants import generate_query_variants
from .types_quota import (
    MAX_PER_REGION, MY_REGIONS, TYPE_QUOTA,
)
from .mudah_scraper import (
    scrape_region_type,
    make_shared_client,
    BUDGET as _URL_BUDGET,
)

# Realtime mode hard cap: stop scraping once this many listing URLs have
# been collected (across all regions/types) and hand off to ranking.
REALTIME_URL_CAP = 100
# Floor below which we trigger progressive variant relaxation
# (drop carpark → drop bedrooms → widen price ±20%). Set to 0 to disable.
MIN_REALTIME_PER_REGION = 10

logger = logging.getLogger(__name__)

# Per-region type concurrency: how many (type) scrapes for a single region we
# run in parallel. Each scrape_region_type call already has its own per-host
# semaphore, so this is an outer fan-out cap.
# v3: 3 → 6 (2× per concurrency-bump spec).
REGION_TYPE_CONCURRENCY = 6


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


async def _scrape_one_type_persist(
    region: str,
    session_id: str,
    type_key: str,
    quota: int,
    *,
    filters: Optional[Dict] = None,
    client: Optional[AsyncSession] = None,
) -> int:
    """Scrape one type for REALTIME mode. Persists rows into the per-session
    tempo JSON ONLY.

    Per user spec: realtime mode MUST NOT write to the long-term CSV — the
    long-term store is owned exclusively by pure_fetch (bulk refresh) and
    by the legacy `ensure_region` seeder. Realtime is brief-driven and may
    carry filters that would pollute the long-term store with non-canonical
    rows.

    `client` is the shared HTTP client owned by the caller (reused across
    every (region, type) scrape so connection pool + TLS session survive
    the whole run).
    """
    try:
        rows = await scrape_region_type(
            region, type_key, quota, filters=filters, client=client,
        )
    except Exception as e:
        logger.warning("[realtime] %s/%s scrape raised: %r", region, type_key, e)
        return 0
    if not rows:
        return 0
    # Tempo only — long-term CSV is OFF-LIMITS for realtime mode.
    storage.append_tempo(region, session_id, rows)
    return len(rows)


async def fetch_realtime_into_tempo(
    session_id: str,
    regions: List[str],
    *,
    live_filter: Optional[Dict] = None,
) -> Dict[str, int]:
    """
    Scrape each region live. Types within a region run concurrently (bounded
    by REGION_TYPE_CONCURRENCY). After each region we re-snapshot tempo from
    the union of (just-scraped rows ∪ pre-existing long-term CSV) so the
    ranking agent always sees the freshest data even on partial failure.

    Realtime mode is capped at REALTIME_URL_CAP listing URLs total: once the
    cap is reached, remaining regions are skipped and the ranking agent is
    invoked on whatever has been collected so far.

    `live_filter` (optional) tightens the scrape to the user's brief:
      - house_type → scrape ONLY that single type (quota=MAX_PER_REGION),
        instead of fanning out across all TYPE_QUOTA entries.
      - keyword / bedrooms / min_price / max_price → forwarded into the
        Mudah URL via mudah_scraper._build_search_url.
    None / empty filter → original full-type fan-out behaviour.

    If the filtered scrape returns zero rows, the function still re-snapshots
    tempo from the pre-existing long-term CSV; the upstream expansion_level
    mechanism (search_pipeline.fetch_raw_properties) is responsible for
    widening the search when the resulting pool is empty.
    """
    counts: Dict[str, int] = {}
    _URL_BUDGET.init(REALTIME_URL_CAP)

    # Resolve which (type, quota) pairs to scrape per region from the filter.
    filter_house_type = (live_filter or {}).get("house_type")
    if filter_house_type and filter_house_type in TYPE_QUOTA:
        type_plan: List[tuple[str, int]] = [(filter_house_type, MAX_PER_REGION)]
    else:
        type_plan = list(TYPE_QUOTA.items())

    # Single httpx.AsyncClient shared across every (region, type) scrape so
    # the HTTP/2 connection pool, DNS cache, and TLS session survive the
    # whole realtime run instead of being torn down per-region.
    shared_client = make_shared_client()
    try:
        for region in regions:
            if _URL_BUDGET.exhausted:
                # Budget spent: still expose pre-existing long-term data via tempo
                # so ranking has something to work with for the remaining regions.
                pre = storage.load_longterm(region)
                storage.write_tempo(region, session_id, pre)
                counts[region] = len(pre)
                continue

            # Initialise tempo with whatever long-term data already exists so a
            # total scrape failure still produces a usable file.
            pre = storage.load_longterm(region)
            storage.write_tempo(region, session_id, pre)

            # NOTE: pre-existing rows in long-term CSV were scraped WITHOUT the
            # current live filter, so a "long-term cache full" short-circuit
            # would silently bypass the user's filter requirements. When a live
            # filter is active we always re-hit Mudah for this region.
            if not live_filter and storage.longterm_count(region) >= MAX_PER_REGION:
                counts[region] = len(pre)
                continue

            sem = asyncio.Semaphore(REGION_TYPE_CONCURRENCY)

            async def _bounded(t: str, q: int, _region: str = region) -> int:
                # `_region` default-arg captures the loop variable to avoid the
                # classic late-binding bug when `region` rebinds on next iter.
                async with sem:
                    return await _scrape_one_type_persist(
                        _region, session_id, t, q,
                        filters=live_filter, client=shared_client,
                    )

            results = await asyncio.gather(
                *[_bounded(t, q) for t, q in type_plan],
                return_exceptions=True,
            )
            total_new = sum(r for r in results if isinstance(r, int))

            # Tempo is now the union of (long-term pre-seed written above) +
            # (freshly scraped rows that _scrape_one_type_persist appended via
            # storage.append_tempo). We must NOT re-snapshot from long-term —
            # realtime no longer writes long-term, so doing so would discard
            # every fresh row we just appended.
            rows = storage.read_tempo(region, session_id)
            counts[region] = len(rows)
            logger.info(
                "[realtime] %s: +%d new, tempo_total=%d, budget_remaining=%d, filter=%s",
                region, total_new, len(rows), _URL_BUDGET.remaining, live_filter,
            )

            # ── Progressive variant retry ───────────────────────────────
            # When live_filter is active and the per-region yield is below
            # MIN_REALTIME_PER_REGION, fan out across relaxed variants in
            # order. Stops as soon as we hit the floor OR exhaust variants
            # OR exhaust the global URL budget.
            if (
                live_filter
                and len(rows) < MIN_REALTIME_PER_REGION
                and not _URL_BUDGET.exhausted
            ):
                variants = generate_query_variants(live_filter)[1:]  # skip base
                for vi, variant in enumerate(variants, start=1):
                    if _URL_BUDGET.exhausted:
                        break
                    logger.info(
                        "[realtime] %s: variant retry %d/%d filter=%s",
                        region, vi, len(variants), variant,
                    )
                    v_sem = asyncio.Semaphore(REGION_TYPE_CONCURRENCY)
                    async def _v_bounded(t: str, q: int,
                                          _region: str = region,
                                          _variant: Dict = variant) -> int:
                        async with v_sem:
                            return await _scrape_one_type_persist(
                                _region, session_id, t, q,
                                filters=_variant, client=shared_client,
                            )
                    await asyncio.gather(
                        *[_v_bounded(t, q) for t, q in type_plan],
                        return_exceptions=True,
                    )
                    rows = storage.read_tempo(region, session_id)
                    counts[region] = len(rows)
                    if len(rows) >= MIN_REALTIME_PER_REGION:
                        logger.info(
                            "[realtime] %s: variant %d satisfied floor (%d rows)",
                            region, vi, len(rows),
                        )
                        break
    finally:
        # Always disable the budget so non-realtime / subsequent runs are
        # never accidentally throttled by leftover state.
        _URL_BUDGET.disable()
        try:
            # curl_cffi AsyncSession exposes .close(), not .aclose().
            await shared_client.close()
        except Exception:
            pass

    return counts


# ── pure_fetch: scrape ALL regions × ALL types, save ONLY to long-term CSV
async def fetch_pure_into_longterm(
    regions: Optional[List[str]] = None,
    *,
    per_region_concurrency: int = REGION_TYPE_CONCURRENCY,
    region_concurrency: int = 4,
) -> Dict[str, Dict[str, int]]:
    """Pure-fetch mode: scrape every (region, type) combination, skipping
    Playwright augmentation for speed, and append results to the long-term
    CSV only. No session tempo, no ranking.

    v3 optimisations:
      - region_concurrency 2 → 4 (2× per spec).
      - per_region_concurrency 3 → 6 (from REGION_TYPE_CONCURRENCY bump).
      - ONE httpx.AsyncClient (HTTP/2 + keepalive) is shared across every
        (region, type) scrape — previously each call paid a cold TCP+TLS
        handshake. Run-wide RPS roughly doubles on warm connections.
      - CSV writes are BUFFERED per region and flushed ONCE at end-of-region
        instead of once per (region, type). `append_longterm` rewrites the
        entire CSV each call (pandas merge for schema-union safety); the old
        code paid that O(N) rewrite TYPE_QUOTA× per region. Now: 1× per
        region. On a full Malaysia run this drops storage cost from ~O(R·T·N)
        to ~O(R·N).
    """
    from .mudah_scraper import scrape_region_type as _scrape, BUDGET as _BUDGET
    _BUDGET.disable()

    regions = regions or list(MY_REGIONS)
    counts: Dict[str, Dict[str, int]] = {}
    region_sem = asyncio.Semaphore(max(1, region_concurrency))
    shared_client = make_shared_client()

    async def _do_region(region: str) -> None:
        async with region_sem:
            type_sem = asyncio.Semaphore(max(1, per_region_concurrency))
            per_type: Dict[str, int] = {}
            per_type_written: Dict[str, int] = {}

            async def _do_type(type_key: str, quota: int) -> None:
                async with type_sem:
                    try:
                        rows = await _scrape(
                            region, type_key, quota,
                            filters=None, skip_playwright=True,
                            client=shared_client,
                        )
                    except Exception as e:
                        logger.warning("[pure_fetch] %s/%s scrape raised: %r",
                                       region, type_key, e)
                        rows = []
                    per_type[type_key] = len(rows)
                    # ── INCREMENTAL LONG-TERM FLUSH ─────────────────────
                    # Persist per (region, type) immediately instead of
                    # buffering until end-of-region. Trades the per-region
                    # batch-write optimisation for durability: partial
                    # progress survives Ctrl-C / OOM / network death. The
                    # threading.Lock inside append_longterm serialises
                    # concurrent writers to the same region CSV.
                    written = storage.append_longterm(region, rows) if rows else 0
                    per_type_written[type_key] = written
                    logger.info(
                        "[pure_fetch] %s/%s scraped=%d written=%d longterm_total=%d",
                        region, type_key, len(rows), written,
                        storage.longterm_count(region),
                    )

            await asyncio.gather(
                *[_do_type(t, q) for t, q in TYPE_QUOTA.items()],
                return_exceptions=True,
            )

            counts[region] = per_type
            logger.info(
                "[pure_fetch] %s done: written_per_type=%s longterm_total=%d per_type=%s",
                region, per_type_written, storage.longterm_count(region), per_type,
            )

    try:
        await asyncio.gather(*[_do_region(r) for r in regions], return_exceptions=True)
    finally:
        try:
            await shared_client.close()
        except Exception:
            pass
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
