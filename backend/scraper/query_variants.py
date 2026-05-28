"""
scraper/query_variants.py
─────────────────────────
Progressive constraint relaxation for live-search retries.

When fetch_realtime_into_tempo() returns a thin result set, the caller can
fan out across these variants instead of immediately falling back to demo
data. Order is strictly monotonic: each variant relaxes ONE more constraint
than the previous one.

Inspired by Hackathon-67/scraper/live/search_fallback.py but:
  - Operates on huh's filter shape (house_type/bedrooms/carpark/min_price/max_price)
    rather than the hack repo's `budget` scalar.
  - Returns deep copies, never mutates the input.
  - Caller decides when to stop (e.g. after enough rows collected).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


def generate_query_variants(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return progressively-relaxed filter variants.

    Variant order:
      0. As-given (always first; lets the caller treat the list uniformly).
      1. Drop `carpark` constraint.
      2. Drop `bedrooms` constraint.
      3. Drop both carpark + bedrooms AND widen price band by 20%.

    `house_type` is NEVER relaxed — switching it would silently return a
    different category of property.
    """
    base = deepcopy(filters or {})
    variants: List[Dict[str, Any]] = [base]

    if base.get("carpark"):
        v = deepcopy(base)
        v.pop("carpark", None)
        variants.append(v)

    if base.get("bedrooms") is not None:
        v = deepcopy(base)
        v.pop("bedrooms", None)
        variants.append(v)

    # Final widest variant — only emit when it actually differs from base.
    v_wide = deepcopy(base)
    v_wide.pop("carpark", None)
    v_wide.pop("bedrooms", None)
    for key, factor in (("min_price", 0.8), ("max_price", 1.2)):
        val = v_wide.get(key)
        try:
            if val is not None and float(val) > 0:
                v_wide[key] = float(val) * factor
        except (TypeError, ValueError):
            pass
    if v_wide != base and v_wide not in variants:
        variants.append(v_wide)

    return variants
