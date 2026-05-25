"""
Per-region property-type quota.

Region universe: 13 states + 3 federal territories of Malaysia.
Per region quota sums to 100. Quota fill policy is (A): if a single type
under-fills, the deficit is cross-typed (back-filled by other types ranked
by remaining headroom) so each region eventually reaches 100 if possible.

Quota mirrors the user's spec:
- condo            30
- double-storey    25
- single-storey    15  (single terrace)
- bungalow         10
- apartment        10
- townhouse        10
                  ===
                  100
"""
from __future__ import annotations
from typing import Dict, List

MY_REGIONS: List[str] = [
    # 13 states
    "johor", "kedah", "kelantan", "melaka", "negeri-sembilan",
    "pahang", "perak", "perlis", "penang", "sabah",
    "sarawak", "selangor", "terengganu",
    # 3 federal territories
    "kuala-lumpur", "labuan", "putrajaya",
]

# Canonical type keys + Mudah.my category hints used by mudah_scraper.
TYPE_QUOTA: Dict[str, int] = {
    "condo":          30,
    "double-storey":  25,
    "single-storey":  15,
    "bungalow":       10,
    "apartment":      10,
    "townhouse":      10,
}

# Hard floor / ceiling per region.
MIN_PER_REGION = 50
MAX_PER_REGION = 100

assert sum(TYPE_QUOTA.values()) == MAX_PER_REGION, "TYPE_QUOTA must sum to 100"

# Mudah.my search keyword per type (Mudah search box uses free text well).
TYPE_SEARCH_KEYWORD: Dict[str, str] = {
    "condo":         "condominium",
    "double-storey": "double storey house",
    "single-storey": "single storey house",
    "bungalow":      "bungalow",
    "apartment":     "apartment",
    "townhouse":     "townhouse",
}


def display_region(region_key: str) -> str:
    return region_key.replace("-", " ").title()
