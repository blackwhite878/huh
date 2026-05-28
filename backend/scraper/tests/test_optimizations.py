"""Golden-fixture regression tests for the scraper optimisations.

Run: python -m pytest backend/scraper/tests/test_optimizations.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.scraper.mudah_scraper import _clean_price, _build_search_url
from backend.scraper.listing_validator import (
    is_valid_title, is_valid_price, is_valid_row,
)
from backend.scraper.query_variants import generate_query_variants


# ── _clean_price K/M ────────────────────────────────────────────────────
def test_price_plain():
    assert _clean_price("RM 1,200,000") == 1_200_000.0

def test_price_k_suffix():
    assert _clean_price("RM 550K") == 550_000.0

def test_price_m_suffix():
    assert _clean_price("RM 1.2M") == 1_200_000.0

def test_price_lowercase_suffix():
    assert _clean_price("rm 850k") == 850_000.0

def test_price_no_prefix_rejected():
    # Never extract a number that lacks the `rm` prefix — guards against
    # picking up "3" from "3 bedroom apartment".
    assert _clean_price("3 bedroom apartment") is None

def test_price_garbage_returns_none():
    assert _clean_price("call for price") is None


# ── _build_search_url carpark ───────────────────────────────────────────
def test_build_url_no_carpark():
    url = _build_search_url("kuala-lumpur", "condo", 1, filters={})
    assert "carpark" not in url

def test_build_url_with_carpark():
    url = _build_search_url(
        "kuala-lumpur", "condo", 1,
        filters={"carpark": True, "keyword": "condo"},
    )
    # carpark token appended to the q= free-text query.
    assert "carpark" in url
    assert "q=condo+carpark" in url


# ── ListingValidator ────────────────────────────────────────────────────
def test_title_rejects_junk():
    for bad in ("", "loading", "mudah.my", "Property"):
        assert not is_valid_title(bad), bad

def test_title_accepts_real():
    assert is_valid_title("3-bedroom condo in Mont Kiara")

def test_price_bounds_sale():
    assert is_valid_price(450_000, "sale")
    assert not is_valid_price(1_000, "sale")          # below floor

def test_price_bounds_rent():
    assert is_valid_price(1_800, "rent")
    assert not is_valid_price(35_000, "rent")         # above ceiling

def test_price_null_passthrough():
    # None is OK at this layer — upstream _is_complete owns mandatory enforcement.
    assert is_valid_price(None, "sale")

def test_is_valid_row_composite():
    assert is_valid_row({"title": "Condo at KLCC", "price": 850_000,
                         "listing_type": "sale"})
    assert not is_valid_row({"title": "loading", "price": 850_000,
                             "listing_type": "sale"})


# ── query_variants progressive relaxation ───────────────────────────────
def test_variants_baseline_only():
    v = generate_query_variants({"house_type": "condo"})
    assert v == [{"house_type": "condo"}]

def test_variants_drops_carpark_first():
    base = {"house_type": "condo", "carpark": True, "bedrooms": 3}
    variants = generate_query_variants(base)
    assert variants[0] == base
    assert "carpark" not in variants[1]
    assert variants[1].get("bedrooms") == 3

def test_variants_drops_bedrooms_next():
    base = {"house_type": "condo", "carpark": True, "bedrooms": 3}
    variants = generate_query_variants(base)
    # Find the variant that drops bedrooms but kept carpark-already-removed.
    assert any("bedrooms" not in v for v in variants[2:])

def test_variants_widens_price():
    base = {"house_type": "condo", "min_price": 500_000, "max_price": 800_000}
    variants = generate_query_variants(base)
    wide = variants[-1]
    assert wide["min_price"] == 400_000.0
    assert wide["max_price"] == 960_000.0

def test_variants_never_relaxes_house_type():
    base = {"house_type": "bungalow", "carpark": True, "bedrooms": 5}
    for v in generate_query_variants(base):
        assert v.get("house_type") == "bungalow"
