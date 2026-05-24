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
from mock_data import load_mock_data, get_mock_properties_by_district
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
    try:
        remarks_response = await llm_client.generate_remarks(
            top_properties,
            agent_style=phase1.agent_style,
        )
        remarks = remarks_response.results
    except Exception as e:
        print(f"Remarks generation failed, using degraded mode: {e}")
        # Fallback: generate basic remarks without LLM
        remarks = [
            PropertyRemark(
                property_id=p.property_id,
                tier="tier_1" if i < 5 else "tier_2",
                remarks=f"Property {p.title} at {p.price}",
                missing_features=[],
                remedy=None,
            )
            for i, p in enumerate(top_properties)
        ]

    search_session.search_stage = "complete"
    return remarks, False


async def fetch_raw_properties(
    session_id: str,
    target_description: str,
    expansion_level: int,
) -> list[Property]:
    """
    Fetch raw properties from search districts.
    For MVP, use mock data. In production, call scraper.
    """
    # Parse target to get primary district
    # Format: "condo in Johor Bahru" -> "johor_bahru_city"
    district_map = {
        "johor bahru": "johor_bahru_city",
        "kl": "kuala_lumpur_city",
        "klcc": "kuala_lumpur_city",
        "pj": "petaling_jaya",
        "kuala lumpur": "kuala_lumpur_city",
    }

    primary_district = "johor_bahru_city"  # Default
    target_lower = target_description.lower()
    for key, district in district_map.items():
        if key in target_lower:
            primary_district = district
            break

    # Get search districts based on expansion level
    search_districts = get_search_districts(primary_district, expansion_level)

    # Load mock data filtered by districts
    all_props = load_mock_data()
    filtered_props = [
        p for p in all_props
        if p.administrative_district in search_districts
    ]

    return filtered_props[:50]  # Limit to max_raw_results


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

