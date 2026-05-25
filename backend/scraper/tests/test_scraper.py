"""
Unit + integration tests for the wsdfc scraper subsystem.

These tests use only local HTML fixtures + monkeypatched scrape_region_type;
they never hit the network. Run from inside the wsdfc repo root:

    pip install pytest pytest-asyncio httpx beautifulsoup4 pyyaml
    pytest -q backend/scraper/tests
"""
from __future__ import annotations
import asyncio
import json
import re
from pathlib import Path

import pytest

from backend.scraper import mudah_scraper, seeder, storage
from backend.scraper.types_quota import TYPE_QUOTA, MAX_PER_REGION


# ── fixtures: tiny realistic-ish Mudah HTML ────────────────────────────
LISTING_HTML = """
<!doctype html><html><body>
<a href="/selangor/condo-for-sale-nice-place-123456.htm">A</a>
<a href="/selangor/condo-for-sale-nicer-place-234567.htm">B</a>
<a href="/property/properties-in-selangor/">index page (must be ignored)</a>
<a href="https://www.facebook.com/mudah">fb</a>
<a href="https://www.mudah.my/static/logo.svg">logo</a>
""" + ("x" * 1000) + "</body></html>"

DETAIL_HTML_NEXTDATA = """
<!doctype html><html><body>
<h1>Cozy Condo in Mont Kiara</h1>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"ad":{
  "adId":"123456","subject":"Cozy Condo in Mont Kiara",
  "price":850000,"region":"selangor","area":"Mont Kiara","city":"KL",
  "sellerName":"Jane Tan","contact":"+60 12-3456789",
  "listTime":"2026-05-01","body":"Spacious unit with KLCC view.",
  "parameters":[
    {"label":"Bedrooms","value":"3"},
    {"label":"Bathrooms","value":"2"},
    {"label":"Built-up size","value":"1,200 sq ft"},
    {"label":"Tenure","value":"Freehold"},
    {"label":"Furnishing","value":"Fully Furnished"}
  ],
  "images":[{"url":"https://img.mudah.my/a.jpg"},{"url":"https://img.mudah.my/b.jpg"}]
}}}}
</script>
""" + ("y" * 1000) + "</body></html>"

DETAIL_HTML_DOM_ONLY = """
<!doctype html><html><body>
<h1>Double Storey House, Subang</h1>
<div data-testid="ad-price">RM 1,250,000</div>
<meta name="keywords" content="Subang Jaya, Selangor"/>
<div id="property-adview-description">Nice double storey. <button>Hide</button></div>
<p>3 bedrooms, 2 bathrooms, 1,800 sq ft. Call +60 12-9988776.</p>
<img src="https://img.mudah.my/c.jpg"/>
""" + ("z" * 1000) + "</body></html>"


# ── tests: parsing ─────────────────────────────────────────────────────
def test_extract_listing_urls_only_detail_pages():
    urls = mudah_scraper._extract_listing_urls(LISTING_HTML)
    assert len(urls) == 2
    assert all(re.search(r"-\d{6,}\.htm$", u) for u in urls)
    assert all("facebook" not in u for u in urls)
    assert not any("properties-in-" in u for u in urls)


def test_build_search_url_is_path_based():
    url = mudah_scraper._build_search_url("kuala-lumpur", "condo", 2)
    assert url.startswith("https://www.mudah.my/kuala-lumpur/properties-for-sale?")
    assert "o=2" in url
    assert "q=condominium" in url
    # the broken `location=` query form must NOT be used
    assert "location=" not in url


def test_parse_detail_uses_next_data_when_present():
    row = mudah_scraper._parse_detail(DETAIL_HTML_NEXTDATA, "https://www.mudah.my/x-123456.htm",
                                       "selangor", "condo")
    assert row["title"] == "Cozy Condo in Mont Kiara"
    assert row["price"] == 850000.0
    assert row["bedrooms"] == 3
    assert row["bathrooms"] == 2
    assert row["built_up_sqft"] == 1200
    assert row["tenure"] == "Freehold"
    assert row["furnishing"] == "Fully Furnished"
    assert row["agent_name"] == "Jane Tan"
    assert row["agent_phone"].startswith("+60")
    assert row["image_urls"][0].startswith("https://img.mudah.my/")
    assert row["region"] == "selangor"
    assert row["property_type"] == "condo"


def test_parse_detail_falls_back_to_dom_selectors():
    row = mudah_scraper._parse_detail(DETAIL_HTML_DOM_ONLY, "https://www.mudah.my/y-234567.htm",
                                       "selangor", "double-storey")
    assert row["title"] == "Double Storey House, Subang"
    assert row["price"] == 1250000.0
    assert row["bedrooms"] == 3
    assert row["bathrooms"] == 2
    assert row["built_up_sqft"] == 1800
    assert "Subang" in (row["location"] or "")
    assert row["description"] and "Nice" in row["description"]
    assert "+60" in (row["agent_phone"] or "")


# ── tests: storage ─────────────────────────────────────────────────────
def _row(url, **over):
    base = {
        "listing_url": url, "source": "mudah.my", "scraped_at": "2026-05-01T00:00:00Z",
        "title": "t", "price": 100.0, "currency": "MYR",
        "property_type": "condo", "region": "selangor",
        "location": "x", "city": "x",
        "bedrooms": 2, "bathrooms": 2,
        "built_up_sqft": 900, "land_sqft": None,
        "tenure": None, "furnishing": None,
        "agent_name": None, "agent_phone": None,
        "posted_at": None, "description": None,
        "image_urls": ["https://img/a.jpg", "https://img/b.jpg"],
    }
    base.update(over); return base


def test_append_longterm_dedupes_and_joins_image_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "data" / "states")
    monkeypatch.setattr(storage, "TEMPO_DIR", tmp_path / "tempo" / "states")
    monkeypatch.setattr(storage, "RANKED_DIR", tmp_path / "tempo" / "ranked")

    rows = [_row("u1"), _row("u2"), _row("u1")]  # u1 dup
    assert storage.append_longterm("selangor", rows) == 2

    # second call with same urls writes 0
    assert storage.append_longterm("selangor", [_row("u1"), _row("u2")]) == 0

    loaded = storage.load_longterm("selangor")
    assert len(loaded) == 2
    # round-trip: list field survives as a list
    assert loaded[0]["image_urls"] == ["https://img/a.jpg", "https://img/b.jpg"]


def test_append_tempo_persists_partial(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "data" / "states")
    monkeypatch.setattr(storage, "TEMPO_DIR", tmp_path / "tempo" / "states")
    monkeypatch.setattr(storage, "RANKED_DIR", tmp_path / "tempo" / "ranked")

    sid = "s1"
    assert storage.append_tempo("selangor", sid, [_row("u1")]) == 1
    assert storage.append_tempo("selangor", sid, [_row("u1"), _row("u2")]) == 1
    rows = storage.read_tempo("selangor", sid)
    assert {r["listing_url"] for r in rows} == {"u1", "u2"}


# ── tests: seeder orchestration (mocked scrape) ────────────────────────
@pytest.mark.asyncio
async def test_fetch_realtime_persists_partial_and_writes_tempo(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "data" / "states")
    monkeypatch.setattr(storage, "TEMPO_DIR", tmp_path / "tempo" / "states")
    monkeypatch.setattr(storage, "RANKED_DIR", tmp_path / "tempo" / "ranked")

    calls = {"n": 0}

    async def fake_scrape(region, type_key, quota):
        calls["n"] += 1
        # condo succeeds with 2 rows; everything else fails
        if type_key == "condo":
            return [_row(f"{region}-{type_key}-{i}", property_type=type_key) for i in range(2)]
        raise RuntimeError("simulated ban")

    monkeypatch.setattr(seeder, "scrape_region_type", fake_scrape)

    sid = "sess-test"
    counts = await seeder.fetch_realtime_into_tempo(sid, ["selangor"])
    # CSV should have the 2 condo rows
    csv_rows = storage.load_longterm("selangor")
    assert len(csv_rows) == 2
    assert all(r["property_type"] == "condo" for r in csv_rows)
    # tempo file must exist and mirror CSV
    tempo_rows = storage.read_tempo("selangor", sid)
    assert len(tempo_rows) == 2
    assert counts["selangor"] == 2


@pytest.mark.asyncio
async def test_run_with_retry_then_demo_flags_on_empty(monkeypatch):
    seeder.reset_flags()

    async def realtime_empty():
        return {"selangor": 0}

    def demo():
        return {"selangor": 5}

    out = await seeder.run_with_retry_then_demo(realtime_empty, demo, retries=2)
    assert out == {"selangor": 5}
    assert seeder.FLAGS.forced_demo is True
    assert seeder.FLAGS.last_error and "empty" in seeder.FLAGS.last_error


@pytest.mark.asyncio
async def test_run_with_retry_then_demo_passes_through_on_success(monkeypatch):
    seeder.reset_flags()

    async def realtime_ok():
        return {"selangor": 3}

    def demo():
        raise AssertionError("demo should not be called")

    out = await seeder.run_with_retry_then_demo(realtime_ok, demo, retries=3)
    assert out == {"selangor": 3}
    assert seeder.FLAGS.forced_demo is False


@pytest.mark.asyncio
async def test_scrape_region_type_zero_target_short_circuits(monkeypatch):
    # Should NOT touch the network when target_count <= 0.
    called = {"n": 0}

    async def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("network must not be touched")

    monkeypatch.setattr(mudah_scraper, "_get", boom)
    rows = await mudah_scraper.scrape_region_type("selangor", "condo", 0)
    assert rows == []
    assert called["n"] == 0
