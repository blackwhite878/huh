// ============================================================================
// Type contracts — must stay in sync with Backend.md & Frontend.md
// ============================================================================

// AppState — aligned to Frontend.md §1 (13 states)
export type AppState =
  | "IDLE"
  | "SEMANTIC_ALIGNING"
  | "PROFILING_COMPLETE"
  | "CHATTING"
  | "PENDING_CONFIRMATION"
  | "SEARCHING"
  | "BATCH_1_DISPLAY"
  | "BATCH_2_DISPLAY"
  | "ALL_REJECTED"
  | "ACTION_REQUIRED_UI"
  | "RE_SEARCHING"
  | "TIER3_NO_RESULT"
  | "PHASE_1_INITIAL";

export type AgentStyle = "Professional" | "Friendly" | "Enthusiastic";
export type Identity = "first_time_buyer" | "investor" | "upgrader";
export type Gender = "female" | "male" | "prefer_not_to_say";
export type SearchStage =
  | "idle"
  | "scraping"
  | "ranking"
  | "generating_remarks"
  | "complete";


export interface Phase1Form {
  budget: number;
  agent_style: AgentStyle;
  target: string;
  identity: Identity;
  gender: Gender;
  description: string;
  // REVIEW (low-risk, not auto-fixed): the backend Phase1Data Pydantic model
  // (backend/schemas.py:Phase1Data) does NOT declare `house_type` or
  // `location`. Pydantic v2's default config silently drops unknown fields,
  // so these two values are sent over the wire and immediately discarded
  // server-side — every downstream `getattr(phase1_data, "house_type", "")`
  // returns "". Either remove these fields from the contract or add them to
  // Phase1Data. Left as-is to avoid changing the wire protocol.
  house_type: string;
  location: string;
}

// Aligned 1:1 with PropertyResult by index in the same response.
// See backend/schemas.py:PropertyRemark.
export interface PropertyRemark {
  property_id: string;
  tier: "tier_1" | "tier_2";
  remarks: string;
  missing_features: string[];
  remedy: string | null;
}

// Aligned to backend DialogueMessage.role contract (user | assistant only)
export interface DialogueMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: number;
}

export interface PendingConflict {
  conflicting_field: string;
  proposed_value: unknown;
  reply: string;
}

export interface PropertyResult {
  property_id: string;
  title: string;
  price: number;
  location: string;
  feature_tags: string[];
  tier: "tier_1" | "tier_2";
  // C1 plan-a (strict): backend may return null when no AI commentary was
  // generated. Treat null and undefined identically in the UI.
  ai_remarks?: string | null;
  missing_features?: string[];
  remedy?: string | null;
  image_url?: string;
  url?: string;
  // C4: surfaced by backend Property model; true for demo/mock fixtures.
  // Hidden by ResultsBatch when the session is not degraded / forced_demo.
  is_mock?: boolean;
}

export interface InitSessionResponse {
  session_id: string;
  status: "aligning";
}

export interface SessionReadyResponse {
  status: "aligning" | "ready";
  semantic_tags?: string[];   // negative (NPP keys)
  positive_tags?: string[];   // positive (PPP keys)
  alignment_warning?: boolean;
  error?: string | null;      // NEW — hard-failure cause from backend
}


export interface ChatResponse {
  status: "chatting" | "pending_confirmation" | "searching";
  reply: string;
  fc_attempt?: number;
  conflicting_field?: string;
  proposed_value?: unknown;
}

export interface SearchStatusResponse {
  status: SearchStage;
  batch_index?: number;
  total_available?: number;
  has_more?: boolean;
  tier3_triggered?: boolean;
  degraded?: boolean;
  results?: PropertyResult[];
  // Backend builds this via build_remarks_for_batch and aligns it 1:1 with
  // `results` (same length, same index). Entries may be null when no remark
  // was generated for that property. See backend/main.py:build_remarks_for_batch.
  remarks?: (PropertyRemark | null)[];
}

// Distinct from SearchStatusResponse — used by POST /next_batch
export interface NextBatchResponse {
  batch_index: number;
  total_available: number;
  has_more: boolean;
  tier3_triggered: boolean;
  degraded: boolean;
  results: PropertyResult[];
  // Same 1:1 alignment contract as SearchStatusResponse.remarks above.
  remarks?: (PropertyRemark | null)[];
}

export interface RejectSingleResponse {
  status: "recorded";
  rejection_count: number;
}

export interface RejectAllResponse {
  status: "action_required";
  npp_updated: string[];
  message: string;
}

export interface ActionResolveResponse {
  status: "reset_complete" | "memories_kept";
  cleared?: string[];
  preserved?: string[];
  reset?: string[];
  next_phase: string;
  reply?: string;
}

export interface PropertyDetailResponse {
  ai_summary: string;
  pros: string[];
  cons: string[];
  is_near_match: boolean;
  degraded: boolean;
}

export interface UpdateRequirementsRequest {
  session_id: string;
  updated_fields: Record<string, unknown>;
}

export interface UpdateRequirementsResponse {
  status: "updated";
  cleared_dialogue_segments: string[];
  npp_cleared_tags: string[];
  search_session_reset: boolean;
  rejected_property_ids_cleared: boolean;
}

export interface ReasonDislikeResponse {
  add_npp: string[];
  remove_ppp: string[];
  add_ppp: string[];
  rationale: string;
  applied: boolean;
}
