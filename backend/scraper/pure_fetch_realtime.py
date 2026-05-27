"""
scraper/pure_fetch_realtime.py
──────────────────────────────
Pure-fetch mode that REUSES the realtime scraper's runtime semantics
(shared HTTP/2 client + bounded region/type concurrency + storage layer)
to bulk-refresh every (region, type) combination on Mudah.

What it does
============
1. Iterates MY_REGIONS × TYPE_QUOTA.
2. Runs scrapes with the same shared httpx.AsyncClient + nested semaphore
   pattern as `seeder.fetch_realtime_into_tempo` (so the connection pool,
   DNS cache and TLS session survive the whole run).
3. Persists rows through the existing storage layer
   (`storage.append_longterm`) — long-term per-region CSVs stay the
   authoritative source, deduped by `listing_url`, schema-unioned by
   pandas exactly like realtime mode.
4. After every region flush, AND once at end-of-run, writes a single
   *clean* aggregate CSV via pandas — one tidy table across all regions
   with stable column order, sorted by (region, property_type,
   scraped_at desc), deduped by listing_url.
5. Prints rich progress to stdout: per-(region,type) row counts +
   elapsed seconds, per-region totals, and a final pandas summary
   table.

Differences vs realtime
=======================
- No live_filter (pure_fetch is a bulk refresh, not a brief-driven
  search).
- No REALTIME_URL_CAP (no 100-URL ceiling).
- No session tempo / ranking (pure_fetch has no session_id).
- No retry-then-demo fallback (bulk refresh is best-effort per cell;
  failed cells log and continue).

Run modes
=========
- As a CLI:
      python -m scraper.pure_fetch_realtime
      python -m scraper.pure_fetch_realtime --regions johor selangor
- Programmatically (e.g. from pipeline.py):
      from scraper.pure_fetch_realtime import run_pure_fetch_realtime
      counts = await run_pure_fetch_realtime()
"""
from __future__ import annotations

# ── Direct-script bootstrap ──────────────────────────────────────────
# This module ships with package-relative imports (`from . import storage`,
# `from .mudah_scraper import ...`) and is intended to be launched as
# `python -m scraper.pure_fetch_realtime` (or `python -m
# backend.scraper.pure_fetch_realtime`). When users invoke it directly
# via `python backend/scraper/pure_fetch_realtime.py`, Python sets
# __package__ to None and the relative imports blow up with
# "ImportError: attempted relative import with no known parent package".
# To keep the documented `python -m` entrypoint working AND let direct
# execution "just work", detect the no-parent-package case, inject the
# repo root into sys.path, and re-execute ourselves as the proper
# `backend.scraper.pure_fetch_realtime` module via runpy. This shim is
# a strict no-op for normal `-m` / import use because the guard requires
# both __name__ == "__main__" AND an empty __package__.
if __package__ in (None, "") and __name__ == "__main__":
    import os as _os, sys as _sys, runpy as _runpy
    _here = _os.path.abspath(_os.path.dirname(__file__))
    # .../<repo>/backend/scraper/pure_fetch_realtime.py
    # sibling `storage.py` does `from schemas import ScrapedProperty`,
    # which lives at backend/schemas.py — so `backend/` must also be on
    # sys.path, mirroring the documented `python -m scraper.pure_fetch_realtime`
    # invocation from inside backend/.
    _backend_dir = _os.path.dirname(_here)
    _repo_root = _os.path.dirname(_backend_dir)
    for _p in (_repo_root, _backend_dir):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    _runpy.run_module(
        "scraper.pure_fetch_realtime",
        run_name="__main__",
        alter_sys=True,
    )
    _sys.exit(0)


import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from . import storage
from .mudah_scraper import (
    BUDGET as _URL_BUDGET,
    make_shared_client,
    scrape_region_type,
)
from .types_quota import MY_REGIONS, TYPE_QUOTA

logger = logging.getLogger(__name__)

# Mirror seeder.REGION_TYPE_CONCURRENCY — keep both knobs in lockstep so
# pure_fetch_realtime and realtime exert the same per-region pressure.
REGION_TYPE_CONCURRENCY: int = 6
REGION_CONCURRENCY: int = 4

# Clean aggregate CSV path. Sits next to the per-region long-term CSVs
# under backend/data/ (not inside states/ to avoid storage._read_csv_df
# globbing it as a region file).
AGGREGATE_CSV: Path = storage.DATA_DIR.parent / "pure_fetch_realtime.csv"

# Columns surfaced in the clean aggregate — a curated, human-friendly
# subset of storage.CSV_FIELDS. Everything else stays in the per-region
# long-term CSVs (full ~80-col schema).
CLEAN_COLUMNS: List[str] = [
    "scraped_at", "region", "property_type", "transaction_type",
    "title", "price", "price_display", "currency",
    "bedrooms", "bathrooms", "carpark", "size_sqft",
    "area", "state", "full_address", "furnishing",
    "seller_name", "seller_type", "listing_url",
]


# ───────────────────────── console logging setup ─────────────────────────
def _configure_console_logging(level: int = logging.INFO) -> None:
    """Force visible stdout logging even when imported into a host app
    that has already configured logging (e.g. uvicorn). Idempotent."""
    root = logging.getLogger()
    if not any(
        isinstance(h, logging.StreamHandler) and getattr(h, "_pure_fetch_rt", False)
        for h in root.handlers
    ):
        h = logging.StreamHandler(stream=sys.stdout)
        h.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        h._pure_fetch_rt = True  # type: ignore[attr-defined]
        root.addHandler(h)
    root.setLevel(min(root.level or level, level))
    logging.getLogger(__name__).setLevel(level)
    logging.getLogger("scraper").setLevel(level)


# ───────────────────────── aggregate CSV writer ──────────────────────────
def _write_clean_aggregate(regions: List[str]) -> pd.DataFrame:
    """Re-snapshot the clean aggregate CSV from the per-region long-term
    CSVs that storage.append_longterm just refreshed. One pandas write,
    schema-stable, dedup by listing_url, sorted for human reading."""
    frames: List[pd.DataFrame] = []
    for region in regions:
        rows = storage.load_longterm(region)
        if not rows:
            continue
        df = pd.DataFrame(rows)
        for col in CLEAN_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        frames.append(df[CLEAN_COLUMNS])

    if not frames:
        empty = pd.DataFrame(columns=CLEAN_COLUMNS)
        AGGREGATE_CSV.parent.mkdir(parents=True, exist_ok=True)
        empty.to_csv(AGGREGATE_CSV, index=False)
        return empty

    agg = pd.concat(frames, ignore_index=True)
    agg = agg.drop_duplicates(subset=["listing_url"], keep="last")
    agg = agg.sort_values(
        by=["region", "property_type", "scraped_at"],
        ascending=[True, True, False],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)

    AGGREGATE_CSV.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(AGGREGATE_CSV, index=False)
    return agg


# ───────────────────────── core orchestrator ─────────────────────────────
async def run_pure_fetch_realtime(
    regions: Optional[List[str]] = None,
    types: Optional[List[str]] = None,
    *,
    region_concurrency: int = REGION_CONCURRENCY,
    per_region_concurrency: int = REGION_TYPE_CONCURRENCY,
) -> Dict[str, Dict[str, int]]:
    """Bulk-refresh long-term CSVs using realtime-mode runtime primitives.

    Returns: {region: {type_key: rows_scraped}} — identical shape to
    seeder.fetch_pure_into_longterm so pipeline.run_pipeline can swap
    this in without touching its response contract.
    """
    _configure_console_logging()

    regions = list(regions) if regions else list(MY_REGIONS)
    type_plan: List[tuple[str, int]] = (
        [(t, TYPE_QUOTA[t]) for t in types if t in TYPE_QUOTA]
        if types else list(TYPE_QUOTA.items())
    )
    if not type_plan:
        raise ValueError(f"No valid types in {types!r}; valid keys: {list(TYPE_QUOTA)}")

    # Pure-fetch must never inherit the realtime 100-URL cap.
    _URL_BUDGET.disable()

    counts: Dict[str, Dict[str, int]] = {}
    region_sem = asyncio.Semaphore(max(1, region_concurrency))
    shared_client = make_shared_client()

    logger.info(
        "[pure_fetch_realtime] start regions=%d types=%d region_concurrency=%d per_region_concurrency=%d",
        len(regions), len(type_plan), region_concurrency, per_region_concurrency,
    )
    run_t0 = time.perf_counter()

    async def _do_region(region: str) -> None:
        async with region_sem:
            type_sem = asyncio.Semaphore(max(1, per_region_concurrency))
            per_type: Dict[str, int] = {}
            buffer: List[Dict] = []
            buf_lock = asyncio.Lock()
            region_t0 = time.perf_counter()
            logger.info("[pure_fetch_realtime] %s ▶ scraping %d types", region, len(type_plan))

            async def _do_type(type_key: str, quota: int) -> None:
                async with type_sem:
                    cell_t0 = time.perf_counter()
                    try:
                        rows = await scrape_region_type(
                            region, type_key, quota,
                            filters=None,
                            client=shared_client,
                        )
                    except Exception as e:
                        logger.warning(
                            "[pure_fetch_realtime] %s/%s scrape raised: %r",
                            region, type_key, e,
                        )
                        rows = []
                    elapsed = time.perf_counter() - cell_t0
                    per_type[type_key] = len(rows)
                    if rows:
                        async with buf_lock:
                            buffer.extend(rows)
                    logger.info(
                        "[pure_fetch_realtime]   %s/%s rows=%d elapsed=%.2fs",
                        region, type_key, len(rows), elapsed,
                    )

            await asyncio.gather(
                *[_do_type(t, q) for t, q in type_plan],
                return_exceptions=True,
            )

            # Realtime-style persistence: one append_longterm flush per
            # region (pandas merge + listing_url dedup happens inside).
            written = storage.append_longterm(region, buffer) if buffer else 0
            total_now = storage.longterm_count(region)
            counts[region] = per_type
            logger.info(
                "[pure_fetch_realtime] %s ◀ flush buffered=%d written=%d longterm_total=%d elapsed=%.2fs per_type=%s",
                region, len(buffer), written, total_now,
                time.perf_counter() - region_t0, per_type,
            )

    try:
        await asyncio.gather(*[_do_region(r) for r in regions], return_exceptions=True)
    finally:
        try:
            await shared_client.aclose()
        except Exception:
            pass

    # Clean aggregate CSV — one tidy pandas table across all regions.
    agg = _write_clean_aggregate(regions)

    elapsed = time.perf_counter() - run_t0
    logger.info(
        "[pure_fetch_realtime] DONE total_rows=%d aggregate_csv=%s elapsed=%.2fs",
        len(agg), AGGREGATE_CSV, elapsed,
    )

    # Final human-readable summary table to stdout.
    summary_rows = [
        {
            "region": r,
            "rows_longterm": storage.longterm_count(r),
            **{f"type::{t}": counts.get(r, {}).get(t, 0) for t, _ in type_plan},
        }
        for r in regions
    ]
    summary = pd.DataFrame(summary_rows)
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("\n=== pure_fetch_realtime summary ===")
        print(summary.to_string(index=False))
        print(f"\nAggregate CSV : {AGGREGATE_CSV}")
        print(f"Aggregate rows: {len(agg)}\n")

    return counts


# ───────────────────────────── CLI entry ─────────────────────────────────
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="scraper.pure_fetch_realtime",
        description="Pure-fetch bulk refresh using realtime-mode runtime semantics.",
    )
    p.add_argument(
        "--regions", nargs="*", default=None,
        help=f"Subset of regions to scrape. Default: all {len(MY_REGIONS)} MY_REGIONS.",
    )
    p.add_argument(
        "--types", nargs="*", default=None,
        help=f"Subset of property types. Default: all TYPE_QUOTA keys ({list(TYPE_QUOTA)}).",
    )
    p.add_argument("--region-concurrency", type=int, default=REGION_CONCURRENCY)
    p.add_argument("--per-region-concurrency", type=int, default=REGION_TYPE_CONCURRENCY)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    _configure_console_logging()
    asyncio.run(run_pure_fetch_realtime(
        regions=args.regions,
        types=args.types,
        region_concurrency=args.region_concurrency,
        per_region_concurrency=args.per_region_concurrency,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
