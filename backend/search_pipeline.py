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
                remarks=f"{p.scraped_data.title or p.property_id} — {p.scraped_data.price}",
                missing_features=[],
                remedy=None,
            )
            for i, p in enumerate(top_properties)
        ]

    # FIX: persist remarks so /search_status and /next_batch can hand
    # them to the frontend. Before this they were returned to the
    # BackgroundTasks runner — which discards return values — and lost.
    search_session.remarks_by_id = {r.property_id: r for r in remarks}

    search_session.search_stage = "complete"
    return remarks, False


# ── adapter: scraped Mudah row → Property ─────────────────────────────
def _row_to_property(row: dict) -> Property | None:
    """
    Wrap a mudah_scraper._parse_detail dict (== ScrapedProperty fields) into
    the Property schema unchanged. No field is dropped: raw_attributes and
    image_urls survive verbatim inside scraped_data.
    """
    from schemas import ScrapedProperty
    url = row.get("listing_url") or ""
    if not url:
        return None
    try:
        scraped = ScrapedProperty(**{
            k: v for k, v in row.items()
            if k in ScrapedProperty.model_fields
        })
    except Exception:
        return None
    pid = (row.get("list_id") and f"MUDAH::{row['list_id']}") or f"MUDAH::{url}"
    return Property(
        property_id=pid[:128],
        scraped_data=scraped,
        feature_tags=[],
        price_fit_score=0.0,
        security_score=0.0,
        transit_proximity_score=0.0,
        lifestyle_proximity_score=0.0,
        facilities_score=0.0,
        normalized_maintenance_fee=0.0,
        is_mock=False,
    )


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
        # Live-mode filter: only scrape listings matching the brief
        # (state, property type, budget range, bedrooms, for-sale path).
        from scraper.live_filter import build_live_filter
        live_filter = await build_live_filter(session_id)

        # C5: live_filter may carry a `_llm_degraded` marker meaning the
        # LLM-augment leg failed and we fell back to regex-only extraction.
        # Surface it on the SearchSession so the API layer (and frontend)
        # can warn the user that the live filter is degraded.
        if live_filter.pop("_llm_degraded", False):
            try:
                search_session.llm_filter_degraded = True
            except Exception:
                pass

        async def realtime():
            return await scraper_seeder.fetch_realtime_into_tempo(
                session_id, regions, live_filter=live_filter,
            )
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
    # long-term CSV), reuse mock_data so the pipeline never starves the tier
    # classifier.
    #
    # C4 (hide mocks in realtime): in realtime mode, mocks must NEVER leak
    # into the user-facing result set. If we're in realtime and the scraper
    # legitimately returned nothing (and the auto-degrade-to-demo path in
    # seeder.run_with_retry_then_demo did not engage), return an empty list
    # so the API layer surfaces zero_results truthfully instead of pretending
    # we found mock fixtures.
    if not properties:
        try:
            mode = scraper_pipeline._load_mode()
        except Exception:
            mode = "demo"
        forced_demo = False
        try:
            from scraper import seeder as _seeder
            forced_demo = bool(_seeder.FLAGS.forced_demo)
        except Exception:
            pass
        if mode == "realtime" and not forced_demo:
            return []
        all_props = load_mock_data()
        properties = all_props[:50]

    # Defense-in-depth: even if mock rows somehow entered `properties`
    # (future code paths, mixed pools), strip is_mock=True in pure realtime.
    try:
        mode = scraper_pipeline._load_mode()
    except Exception:
        mode = "demo"
    forced_demo = False
    try:
        from scraper import seeder as _seeder
        forced_demo = bool(_seeder.FLAGS.forced_demo)
    except Exception:
        pass
    if mode == "realtime" and not forced_demo:
        properties = [p for p in properties if not getattr(p, "is_mock", False)]

    return properties[:50]
