"""
Search pipeline - orchestrates scraping, tier classification, weighting, and remarks generation.
"""
import asyncio
from typing import Optional

from schemas import Property, PropertyRemark
from session_manager import (
    get_search_session,
    get_dialogue_session,
    tier_classification,
)
from weighting import apply_dynamic_weights, build_top10
from llm_client import llm_client
from mock_data import load_mock_data, get_mock_properties_by_district  # legacy fallback only
from scraper import pipeline as scraper_pipeline
from scraper import seeder as scraper_seeder
from scraper import storage as scraper_storage
from topology import get_search_districts


async def execute_search_pipeline(session_id: str) -> tuple[list[PropertyRemark], bool]:
    """
    Complete search pipeline:
    1. Fetch raw properties (with expansion if needed)
    2. Tier classification
    3. Math weighting
    4. LLM remarks generation
    5. Batch slicing (5+5)

    Returns: (results, tier3_triggered)
    """
    search_session = get_search_session(session_id)
    dialogue_session = get_dialogue_session(session_id)

    if not search_session or not dialogue_session:
        raise ValueError(f"Session not found: {session_id}")

    phase1 = dialogue_session.phase1_data

    # Step 1: Fetch raw properties (with expansion)
    search_session.search_stage = "scraping"
    tier3_triggered = False

    while search_session.expansion_level <= 3:
        raw_properties = await fetch_raw_properties(
            session_id,
            phase1.target,
            search_session.expansion_level,
        )

        if len(raw_properties) > 0:
            search_session.raw_pool = raw_properties
            break

        # No results, try next expansion level
        if search_session.expansion_level < 3:
            search_session.expansion_level += 1
        else:
            # Level 3 exhausted, no results
            tier3_triggered = True
            search_session.search_stage = "complete"
            return [], True

    # Step 2: Tier classification
    search_session.search_stage = "ranking"
    tier1, tier2 = tier_classification(
        search_session.raw_pool,
        search_session.current_budget_range["min"],
        search_session.current_budget_range["max"],
        search_session.rejected_property_ids,
        dialogue_session.phase1_data.semantic_tags,  # Use semantic tags as initial NPP
    )

    search_session.tier1_pool = tier1
    search_session.tier2_pool = tier2

    # Step 3: Math weighting to Top 10
    # HIGH-3: previous code called apply_dynamic_weights twice using a
    # __globals__ lookup as a hack to dodge the import; the first result was
    # immediately discarded. Use the real import and call it once.
    from weighting import BASE_WEIGHT_VECTOR
    dynamic_weights = apply_dynamic_weights(BASE_WEIGHT_VECTOR, phase1.gender, phase1.identity)


    scored_results = build_top10(tier1, tier2, dynamic_weights)

    # Extract properties for LLM remarks
    top_properties = [p for _, p, _ in scored_results]
    search_session.all_results = top_properties

    # Step 4: Generate remarks via LLM
    search_session.search_stage = "generating_remarks"
    # Parallel per-property remarks via Llama 3.1 8B (Chutes light model).
    # Each property has its own try/except inside _remark_one_property, so a
    # single LLM hiccup no longer kills the whole batch with an empty
    # "Remarks generation failed, using degraded mode: " message.
    try:
        remarks_response = await llm_client.generate_remarks_async(
            top_properties,
            agent_style=phase1.agent_style,
        )
        remarks = remarks_response.results
    except Exception as e:
        # Should not happen (per-property catches), but keep a hard fallback.
        print(f"[search_pipeline] remarks batch crashed: "
              f"{type(e).__name__}: {e!r}")
        remarks = [
            PropertyRemark(
                property_id=p.property_id,
                tier="tier_1" if i < 5 else "tier_2",
                remarks=f"{p.title} — {p.price}",
                missing_features=[],
                remedy=None,
            )
            for i, p in enumerate(top_properties)
        ]

    search_session.search_stage = "complete"
    return remarks, False


# ── adapter: scraped Mudah row → Property ─────────────────────────────
_DISTRICT_FROM_REGION = {
    "johor": "johor_bahru_city",
    "kuala-lumpur": "kuala_lumpur_city",
    "selangor": "petaling_jaya",
    "penang": "george_town",
    "melaka": "melaka_city",
    "labuan": "labuan_city",
    "putrajaya": "putrajaya_city",
}


def _row_to_property(row: dict) -> Property | None:
    """Map a scraped Mudah row to the strict Property schema with safe defaults."""
    try:
        price = row.get("price")
        price = float(price) if price not in (None, "") else 0.0
        beds = row.get("bedrooms") or 0
        baths = row.get("bathrooms") or 0
        url = row.get("listing_url") or ""
        if not url:
            return None
        region = (row.get("region") or "").lower()
        district = _DISTRICT_FROM_REGION.get(region, region.replace("-", "_") + "_city")
        return Property(
            property_id=f"MUDAH::{url}"[:128],
            title=(row.get("title") or "Untitled")[:200],
            price=price,
            location=row.get("location") or row.get("city") or region,
            administrative_district=district,
            distance_to_mrt_km=0.0,
            is_gated_guarded=False,
            security_level="medium",
            facilities=[],
            facilities_score=0.5,
            nearby_schools=0,
            nearby_tuition_centers=0,
            nearby_malls=0,
            nearby_clinics=0,
            lifestyle_proximity_score=0.5,
            maintenance_fee_per_sqft=0.0,
            normalized_maintenance_fee=0.0,
            flood_risk="unknown",
            feature_tags=[],
            price_fit_score=0.5,
            security_score=0.5,
            transit_proximity_score=0.5,
            floor_level=0,
            facing="unknown",
            bedrooms=int(beds) if beds else 0,
            bathrooms=int(baths) if baths else 0,
            url=url,
            source="mudah.my",
            is_mock=False,
        )
    except Exception:
        return None


async def fetch_raw_properties(
    session_id: str,
    target_description: str,
    expansion_level: int,
) -> list[Property]:
    """
    Fetch raw properties via the Mudah scraper subsystem (replaces mock_data).
    Expansion level widens the resolved region set; on level 3 we fan out to
    the full Malaysia region list as a last resort.
    """
    regions = scraper_pipeline.resolve_regions(target_description)
    if expansion_level >= 2 and len(regions) == 1:
        # widen to neighbouring federal/state cluster on level 2+
        regions = list(dict.fromkeys(regions + scraper_pipeline.MY_REGIONS[:5]))
    if expansion_level >= 3:
        regions = list(scraper_pipeline.MY_REGIONS)

    # Ensure tempo is populated for this session+regions (demo or realtime
    # per config.yaml; 3-retry-then-forced-demo handled inside seeder).
    mode = scraper_pipeline._load_mode()
    scraper_storage.clear_session_tempo(session_id)
    if mode == "realtime":
        async def realtime():
            return await scraper_seeder.fetch_realtime_into_tempo(session_id, regions)
        def demo():
            return scraper_seeder.load_demo_into_tempo(session_id, regions)
        await scraper_seeder.run_with_retry_then_demo(realtime, demo, retries=3)
    else:
        scraper_seeder.load_demo_into_tempo(session_id, regions)

    rows: list[dict] = []
    for r in regions:
        rows.extend(scraper_storage.read_tempo(r, session_id))

    properties: list[Property] = []
    for row in rows:
        prop = _row_to_property(row)
        if prop is not None:
            properties.append(prop)

    # Legacy mock fallback: if scraper produced zero (e.g. first run with no
    # long-term CSV and realtime disabled), reuse mock_data so the pipeline
    # never starves the tier classifier.
    if not properties:
        all_props = load_mock_data()
        properties = all_props[:50]

    return properties[:50]


async def get_next_batch(session_id: str) -> list[PropertyRemark]:
    """
    Get next batch of 5 properties without triggering rejection learning.
    """
    search_session = get_search_session(session_id)
    if not search_session:
        raise ValueError(f"Session not found: {session_id}")

    # This is a pure UI fetch - no rejection learning
    # In full implementation, would slice from all_results
    return []

