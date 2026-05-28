"""
scraper/listing_validator.py
────────────────────────────
ADDITIVE quality gate. Runs AFTER the existing _is_complete() check, never
replaces it. Drops rows that pass the mandatory-fields check but are still
obviously junk (placeholder titles, prices outside plausible ranges).

Adapted from Hackathon-67/scraper/utils/listing_validator.py:
  - is_valid_url is INTENTIONALLY OMITTED because huh's LISTING_HREF_RE
    (≥6-digit ID requirement) is strictly stricter than the hack repo's
    `/d+\\.htm` pattern. Re-introducing the looser check would regress.
  - Price bounds are configurable so unusual but real listings
    (e.g. RM 450 shared rooms) can be allowed by tuning the floor.
"""
from __future__ import annotations

from typing import Any, Iterable, Tuple

_BAD_TITLES = frozenset({
    "", "www.mudah.my", "mudah.my", "loading", "untitled",
    "property", "real estate", "for sale", "for rent",
})

# Sale floor is generous (RM 10k) — covers tiny rural lots; rent ceiling
# 30k caters to luxury KL penthouses. Tune via overrides in storage.
DEFAULT_SALE_RANGE: Tuple[float, float] = (10_000.0, 100_000_000.0)
DEFAULT_RENT_RANGE: Tuple[float, float] = (200.0, 30_000.0)


def is_valid_title(title: Any) -> bool:
    if not isinstance(title, str):
        return False
    t = title.strip().lower()
    if t in _BAD_TITLES:
        return False
    return len(t) > 5


def is_valid_price(price: Any, listing_type: str = "sale") -> bool:
    """`listing_type` ∈ {"sale", "rent"}. None price → True (caller may
    have intentionally left it null and dropped via _is_complete already)."""
    if price is None:
        return True
    try:
        v = float(price)
    except (TypeError, ValueError):
        return False
    lo, hi = (DEFAULT_RENT_RANGE if str(listing_type).lower().startswith("rent")
              else DEFAULT_SALE_RANGE)
    return lo <= v <= hi


def is_valid_row(row: dict) -> bool:
    """Convenience: apply both checks. Used as a filter() predicate."""
    if not is_valid_title(row.get("title")):
        return False
    listing_type = row.get("listing_type") or row.get("property_action") or "sale"
    return is_valid_price(row.get("price"), listing_type)


def filter_valid(rows: Iterable[dict]) -> list:
    return [r for r in rows if is_valid_row(r)]
