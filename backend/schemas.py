"""
Core data models and types.
Pydantic v2 validation for all LLM outputs and API contracts.
"""
from typing import Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Phase 1 ───────────────────────────────────────────────────────
class Phase1Data(BaseModel):
    budget: float
    agent_style: Literal["professional", "friendly", "active"]
    target: str  # e.g., "condo in Johor Bahru"
    identity: Literal["first_time_buyer", "investor", "upgrader"]
    gender: Literal["female", "male", "prefer_not_to_say"]
    description: str  # Added description field
    semantic_tags: list[str] = Field(default_factory=list)   # negative (NPP keys)
    positive_tags: list[str] = Field(default_factory=list)   # positive (PPP keys)
    semantic_alignment_done: bool = False
    alignment_error: Optional[str] = None     # NEW — hard-failure cause for UI



# ─── Dialogue ───────────────────────────────────────────────────────
class DialogueMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None


class DialogueSession(BaseModel):
    session_id: str
    phase1_data: Phase1Data
    dialogue_history: list[DialogueMessage] = Field(default_factory=list)
    fc_trigger_attempts: int = 0


# ─── LLM Chat Output ───────────────────────────────────────────────
class ChatLLMOutput(BaseModel):
    reply: str
    conflict_detected: bool = False
    conflicting_field: Optional[str] = None
    proposed_value: Optional[Any] = None
    fc_trigger: bool = False


# ─── NPP (Negative Property Preferences) ────────────────────────────
class NPPSession(BaseModel):
    session_id: str
    npp_tags: list[str] = Field(default_factory=list)
    pending_rejection_buffer: list[dict] = Field(default_factory=list)
    last_rejection_message: Optional[dict] = None


# ─── Property & Search ──────────────────────────────────────────────
class Property(BaseModel):
    property_id: str
    title: str
    price: float
    location: str
    administrative_district: str
    distance_to_mrt_km: float
    is_gated_guarded: bool
    security_level: Literal["high", "medium", "low"]
    facilities: list[str]
    facilities_score: float
    nearby_schools: int
    nearby_tuition_centers: int
    nearby_malls: int
    nearby_clinics: int
    lifestyle_proximity_score: float
    maintenance_fee_per_sqft: float
    normalized_maintenance_fee: float
    flood_risk: Literal["high", "medium", "low", "unknown"]
    feature_tags: list[str]  # NPP_ENUM internal keys
    price_fit_score: float
    security_score: float
    transit_proximity_score: float
    floor_level: int
    facing: str
    bedrooms: int
    bathrooms: int
    url: str
    source: str
    is_mock: bool


class PropertyRemark(BaseModel):
    property_id: str
    tier: Literal["tier_1", "tier_2"]
    remarks: str
    missing_features: list[str]
    remedy: Optional[str]


class RemarksResponse(BaseModel):
    results: list[PropertyRemark]


class SearchSession(BaseModel):
    session_id: str
    raw_pool: list[Property] = Field(default_factory=list)
    expansion_level: int = 0
    current_budget_range: dict = Field(default_factory=lambda: {"min": 0, "max": 0})
    batch_index: int = 1
    tier1_pool: list[Property] = Field(default_factory=list)
    tier2_pool: list[Property] = Field(default_factory=list)
    all_results: list[Property] = Field(default_factory=list)
    rejected_property_ids: list[str] = Field(default_factory=list)
    search_stage: Literal["idle", "scraping", "ranking", "generating_remarks", "complete"] = "idle"


# ─── API Response Models ────────────────────────────────────────────
class InitSessionResponse(BaseModel):
    session_id: str
    status: Literal["aligning"]


class SessionReadyResponse(BaseModel):
    status: Literal["aligning", "ready"]
    semantic_tags: Optional[list[str]] = None     # negative (NPP keys)
    positive_tags: Optional[list[str]] = None     # positive (PPP keys)
    alignment_warning: bool = False
    error: Optional[str] = None                   # NEW — surfaces real failure cause



class ChatResponse(BaseModel):
    status: Literal["chatting", "pending_confirmation", "searching"]
    reply: str
    fc_attempt: int = 0
    conflicting_field: Optional[str] = None
    proposed_value: Optional[Any] = None


# FIX B2: results was list[PropertyRemark] but main.py returns list[Property].
# Aligned to actual payload shape; frontend PropertyResult is a superset and accepts both.
class SearchStatusResponse(BaseModel):
    status: Literal["idle", "scraping", "ranking", "generating_remarks", "complete"]

    batch_index: Optional[int] = None
    total_available: Optional[int] = None
    has_more: Optional[bool] = None
    tier3_triggered: Optional[bool] = None
    degraded: Optional[bool] = None
    results: Optional[list[Property]] = None


# FIX B3: same as B2.
class NextBatchResponse(BaseModel):
    batch_index: int
    total_available: int
    has_more: bool
    tier3_triggered: bool
    degraded: bool
    results: list[Property]


# FIX B1: added rejection_count which main.py already passes.
class RejectSingleResponse(BaseModel):
    status: Literal["recorded"]
    rejection_count: int


class RejectAllResponse(BaseModel):
    status: Literal["action_required"]
    npp_updated: list[str]
    message: str


class ActionResolveResponse(BaseModel):
    status: Literal["reset_complete", "memories_kept"]
    cleared: Optional[list[str]] = None
    preserved: Optional[list[str]] = None
    reset: Optional[list[str]] = None
    next_phase: str
    reply: Optional[str] = None


class PropertyDetailResponse(BaseModel):
    ai_summary: str
    pros: list[str]
    cons: list[str]
    is_near_match: bool
    degraded: bool


class UpdateRequirementsRequest(BaseModel):
    session_id: str
    updated_fields: dict[str, Any]


class UpdateRequirementsResponse(BaseModel):
    status: Literal["updated"]
    cleared_dialogue_segments: list[str]
    npp_cleared_tags: list[str]
    search_session_reset: bool
    rejected_property_ids_cleared: bool
