"""
CLI seeding entrypoint.

Examples:
  python -m backend.scraper.cli seed
  python -m backend.scraper.cli seed --region johor
  python -m backend.scraper.cli status
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys

from . import seeder, storage
from .types_quota import MY_REGIONS


def cmd_status() -> None:
    rows = [(r, storage.longterm_count(r)) for r in MY_REGIONS]
    for r, n in rows:
        print(f"{r:20s} {n:4d}")


async def cmd_seed(region: str | None) -> None:
    regions = [region] if region else MY_REGIONS
    results = await seeder.ensure_all_regions(regions)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed")
    s.add_argument("--region", default=None)
    sub.add_parser("status")

    args = p.parse_args()
    if args.cmd == "status":
        cmd_status()
        return 0
    if args.cmd == "seed":
        asyncio.run(cmd_seed(args.region))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
