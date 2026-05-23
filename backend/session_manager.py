"""
Core business logic - Session management and pipeline orchestration.
"""
import time
import uuid
from typing import Optional
from schemas import (
    DialogueSession,
    NPPSession,
    SearchSession,
    Phase1Data,
    Property,
)
from npp_enum import NPP_ENUM

# In-memory session storage (MVP - will be lost on restart)
# In production, use Redis or database
_dialogue_sessions: dict[str, DialogueSession] = {}
_npp_sessions: dict[str, NPPSession] = {}
_search_sessions: dict[str, SearchSession] = {}


def create_session(phase1_data: Phase1Data) -> str:
    """
    Create three independent session types with same session_id.
    Called from POST /api/v1/init_session
    """
    session_id = str(uuid.uuid4())

    # Create Dialogue Session
    dialogue_session = DialogueSession(
        session_id=session_id,
        phase1_data=phase1_data,
    )
    _dialogue_sessions[session_id] = dialogue_session

    # Create NPP Session
    npp_session = NPPSession(session_id=session_id)
    _npp_sessions[session_id] = npp_session

    # Create Search Session
    budget_min = phase1_data.budget * 0.9  # ±10% tolerance
    budget_max = phase1_data.budget * 1.1
    search_session = SearchSession(
        session_id=session_id,
        current_budget_range={"min": budget_min, "max": budget_max},
    )
    _search_sessions[session_id] = search_session

    return session_id


def get_dialogue_session(session_id: str) -> Optional[DialogueSession]:
    """Retrieve dialogue session."""
    return _dialogue_sessions.get(session_id)


def get_npp_session(session_id: str) -> Optional[NPPSession]:
    """Retrieve NPP session."""
    return _npp_sessions.get(session_id)


def get_search_session(session_id: str) -> Optional[SearchSession]:
    """Retrieve search session."""
    return _search_sessions.get(session_id)


def update_semantic_tags(session_id: str, tags: list[str]) -> None:
    """
    Update semantic alignment tags in dialogue session.
    Called after async semantic_alignment() completes.
    """
    dialogue_session = get_dialogue_session(session_id)
    if dialogue_session:
        dialogue_session.phase1_data.semantic_tags = tags
        dialogue_session.phase1_data.semantic_alignment_done = True


def reset_dialogue_session(session_id: str) -> None:
    """
    Reset dialogue session completely (New Prompt action).
    """
    dialogue_session = get_dialogue_session(session_id)
    if dialogue_session:
        dialogue_session.dialogue_history = []
        dialogue_session.fc_trigger_attempts = 0


def reset_npp_session(session_id: str) -> None:
    """
    Reset NPP session completely (New Prompt action).
    """
    npp_session = get_npp_session(session_id)
    if npp_session:
        npp_session.npp_tags = []
        npp_session.pending_rejection_buffer = []
        npp_session.last_rejection_message = None


def reset_search_session(session_id: str):
    """
    Resets the search session for a given session_id.
    """
    if session_id in _search_sessions:
        _search_sessions[session_id] = SearchSession(session_id=session_id)


def reset_all_sessions(session_id: str) -> None:
    """
    Full reset for New Prompt action.
    """
    reset_dialogue_session(session_id)
    reset_npp_session(session_id)
    reset_search_session(session_id)


def keep_memories_reset(session_id: str) -> None:
    """
    Partial reset for Keep Memories action.
    - Preserve: dialogue_history, npp_tags
    - Reset: search_session, expansion_level, batch_index
    """
    reset_search_session(session_id)


def add_dialogue_message(session_id: str, role: str, content: str) -> None:
    """Add message to dialogue history."""
    dialogue_session = get_dialogue_session(session_id)
    if dialogue_session:
        from schemas import DialogueMessage
        from datetime import datetime, timezone
        message = DialogueMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        dialogue_session.dialogue_history.append(message)


def increment_fc_attempts(session_id: str) -> int:
    """Increment FC trigger attempts counter."""
    dialogue_session = get_dialogue_session(session_id)
    if dialogue_session:
        dialogue_session.fc_trigger_attempts += 1
        return dialogue_session.fc_trigger_attempts
    return 0


def record_rejection(session_id: str, property_id: str, reason: str) -> None:
    """
    Record single property rejection.
    """
    search_session = get_search_session(session_id)
    npp_session = get_npp_session(session_id)

    if search_session:
        search_session.rejected_property_ids.append(property_id)

    if npp_session:
        timestamp = time.time()
        npp_session.pending_rejection_buffer.append({
            "content": reason,
            "timestamp": timestamp,
        })
        npp_session.last_rejection_message = {
            "content": reason,
            "timestamp": timestamp,
        }


def update_npp_tags(session_id: str, new_tags: list[str]) -> None:
    """
    Update NPP tags (append and deduplicate).
    """
    npp_session = get_npp_session(session_id)
    if npp_session:
        combined = list(set(npp_session.npp_tags + new_tags))
        npp_session.npp_tags = combined


def tier_classification(
    properties: list[Property],
    budget_min: float,
    budget_max: float,
    rejected_ids: list[str],
    npp_tags: list[str],
) -> tuple[list[Property], list[Property]]:
    """
    Tier 1: No NPP conflicts, passes budget constraint
    Tier 2: Minor NPP conflicts, passes budget constraint
    Tier 3+: Serious conflicts or budget violation - dropped

    Returns: (tier1_pool, tier2_pool)
    """
    tier1_pool = []
    tier2_pool = []

    for prop in properties:
        # Budget hard constraint (Python algorithm, never rely on LLM)
        if not (budget_min <= prop.price <= budget_max):
            continue

        # Blacklist check (current Search Session scope)
        if prop.property_id in rejected_ids:
            continue

        # NPP conflict classification
        prop_npp_tags = set(prop.feature_tags)
        npp_tags_set = set(npp_tags)
        conflicts = prop_npp_tags.intersection(npp_tags_set)

        if len(conflicts) == 0:
            tier1_pool.append(prop)
        elif len(conflicts) <= 2:  # Minor: 1-2 conflicts
            tier2_pool.append(prop)
        # else: serious conflicts, drop

    return tier1_pool, tier2_pool

