"""
Integration test suite for complete end-to-end pipeline.
Tests the flow from session init → semantic alignment → chat → search → rejection → NPP learning.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from main import app
from session_manager import (
    create_session,
    get_dialogue_session,
    get_npp_session,
    get_search_session,
)
from schemas import Phase1Data
from llm_client import llm_client


@pytest.fixture
def test_phase1_data():
    """Sample Phase 1 data for testing."""
    return Phase1Data(
        budget=500000,
        agent_style="professional",
        target="condo in Johor Bahru",
        identity="first_time_buyer",
        gender="female",
    )


@pytest.mark.asyncio
async def test_session_creation(test_phase1_data):
    """Test session creation creates all three session types."""
    session_id = create_session(test_phase1_data)

    assert session_id is not None
    assert len(session_id) > 0

    # Verify all three sessions exist
    dialogue_session = get_dialogue_session(session_id)
    npp_session = get_npp_session(session_id)
    search_session = get_search_session(session_id)

    assert dialogue_session is not None
    assert npp_session is not None
    assert search_session is not None

    # Verify Phase 1 data is correct
    assert dialogue_session.phase1_data.budget == 500000
    assert dialogue_session.phase1_data.identity == "first_time_buyer"

    # Verify search session has correct budget range
    assert search_session.current_budget_range["min"] == 450000  # ±10%
    assert search_session.current_budget_range["max"] == 550000


@pytest.mark.asyncio
async def test_semantic_alignment_update(test_phase1_data):
    """Test semantic alignment tag update."""
    session_id = create_session(test_phase1_data)

    # Simulate semantic alignment completion
    from session_manager import update_semantic_tags
    test_tags = ["near_school", "no_security"]
    update_semantic_tags(session_id, test_tags)

    dialogue_session = get_dialogue_session(session_id)
    assert dialogue_session.phase1_data.semantic_tags == test_tags
    assert dialogue_session.phase1_data.semantic_alignment_done is True


@pytest.mark.asyncio
async def test_tier_classification():
    """Test tier classification algorithm."""
    from session_manager import tier_classification
    from mock_data import load_mock_data

    properties = load_mock_data()

    # Test with no NPP tags (all should be tier 1 if budget-compliant)
    tier1, tier2 = tier_classification(
        properties,
        budget_min=400000,
        budget_max=600000,
        rejected_ids=[],
        npp_tags=[],
    )

    assert len(tier1) > 0
    assert len(tier2) == 0

    # Test with NPP tags
    tier1, tier2 = tier_classification(
        properties,
        budget_min=400000,
        budget_max=600000,
        rejected_ids=[],
        npp_tags=["high_floor", "west_facing"],
    )

    # Some properties should move to tier2 or be dropped
    assert len(tier1) + len(tier2) <= len(properties)


@pytest.mark.asyncio
async def test_weight_application():
    """Test dynamic weight calculation."""
    from weighting import apply_dynamic_weights, BASE_WEIGHT_VECTOR

    # Test female + first_time_buyer
    weights = apply_dynamic_weights(
        BASE_WEIGHT_VECTOR,
        gender="female",
        identity="first_time_buyer",
    )

    # Must sum to 1.0
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9

    # Female should have higher security_score multiplier
    assert weights["security_score"] > BASE_WEIGHT_VECTOR["security_score"]

    # First_time_buyer should have higher price_fit multiplier
    assert weights["price_fit_score"] > BASE_WEIGHT_VECTOR["price_fit_score"]


@pytest.mark.asyncio
async def test_top10_ranking():
    """Test Top 10 ranking algorithm."""
    from weighting import build_top10, BASE_WEIGHT_VECTOR, apply_dynamic_weights
    from mock_data import load_mock_data

    properties = load_mock_data()
    tier1 = properties[:15]  # Simulate tier 1
    tier2 = properties[15:30]  # Simulate tier 2

    weights = apply_dynamic_weights(BASE_WEIGHT_VECTOR, "female", "first_time_buyer")
    top10 = build_top10(tier1, tier2, weights)

    assert len(top10) <= 10

    # Should be sorted by score descending
    scores = [score for score, _, _ in top10]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_rejection_flow(test_phase1_data):
    """Test rejection recording and NPP buffer accumulation."""
    from session_manager import record_rejection

    session_id = create_session(test_phase1_data)

    # Record rejections
    record_rejection(session_id, "JB001", "樓層太高")
    record_rejection(session_id, "JB002", "西晒太厲害")

    search_session = get_search_session(session_id)
    npp_session = get_npp_session(session_id)

    # Check blacklist
    assert "JB001" in search_session.rejected_property_ids
    assert "JB002" in search_session.rejected_property_ids

    # Check NPP buffer
    assert len(npp_session.pending_rejection_buffer) == 2


@pytest.mark.asyncio
async def test_npp_tag_update(test_phase1_data):
    """Test NPP tag updating (append, deduplicate)."""
    from session_manager import update_npp_tags

    session_id = create_session(test_phase1_data)

    # Add tags
    update_npp_tags(session_id, ["high_floor", "west_facing"])
    npp_session = get_npp_session(session_id)
    assert len(npp_session.npp_tags) == 2

    # Add overlapping tags
    update_npp_tags(session_id, ["high_floor", "far_from_mrt"])
    assert len(npp_session.npp_tags) == 3  # Deduplicated


@pytest.mark.asyncio
async def test_session_reset():
    """Test full session reset (New Prompt action)."""
    from session_manager import reset_all_sessions, add_dialogue_message

    test_phase1_data = Phase1Data(
        budget=500000,
        agent_style="professional",
        target="condo in Johor Bahru",
        identity="first_time_buyer",
        gender="female",
    )
    session_id = create_session(test_phase1_data)

    # Add some data
    add_dialogue_message(session_id, "user", "Hello")
    add_dialogue_message(session_id, "assistant", "Hi")

    dialogue_session = get_dialogue_session(session_id)
    assert len(dialogue_session.dialogue_history) == 2

    # Reset
    reset_all_sessions(session_id)

    # Check reset
    dialogue_session = get_dialogue_session(session_id)
    assert len(dialogue_session.dialogue_history) == 0
    assert dialogue_session.fc_trigger_attempts == 0


@pytest.mark.asyncio
async def test_mock_data_quality():
    """Verify mock data meets requirements."""
    from mock_data import load_mock_data
    from npp_enum import NPP_ENUM

    properties = load_mock_data()

    # At least 30 properties
    assert len(properties) >= 30

    # All feature_tags are in NPP_ENUM
    for prop in properties:
        for tag in prop.feature_tags:
            assert tag in NPP_ENUM, f"Invalid tag: {tag}"

    # Budget distribution: ≥80% within ±10% of 500000
    compliant = sum(
        1 for p in properties
        if 450000 <= p.price <= 550000
    )
    assert compliant / len(properties) >= 0.80

    # All NPP tags covered
    all_tags = set()
    for prop in properties:
        all_tags.update(prop.feature_tags)

    # Spot check some important tags
    assert "high_floor" in all_tags or "low_floor" in all_tags
    assert "no_security" in all_tags or "no_gym" in all_tags


@pytest.mark.asyncio
async def test_topology_expansion():
    """Test administrative district topology expansion."""
    from topology import get_search_districts

    # Level 0: just the district
    districts = get_search_districts("johor_bahru_city", 0)
    assert districts == ["johor_bahru_city"]

    # Level 1: target + adjacent
    districts = get_search_districts("johor_bahru_city", 1)
    assert "johor_bahru_city" in districts
    assert "skudai" in districts
    assert "tebrau" in districts
    assert len(districts) > 1

    # Level 2: includes secondary
    districts = get_search_districts("johor_bahru_city", 2)
    assert len(districts) > len(get_search_districts("johor_bahru_city", 1))

    # Level 3: pan-urban (district level)
    districts = get_search_districts("johor_bahru_city", 3)
    assert "johor_bahru_district" in districts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

