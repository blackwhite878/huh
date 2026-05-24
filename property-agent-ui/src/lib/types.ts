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
  // Backend-only payload fields. No Phase 1 UI input today; default to "" so
  // the backend always receives a stable string contract.
  house_type: string;
  location: string;
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
  ai_remarks?: string;
  missing_features?: string[];
  remedy?: string;
  image_url?: string;
  url?: string;
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
}

// Distinct from SearchStatusResponse — used by POST /next_batch
export interface NextBatchResponse {
  batch_index: number;
  total_available: number;
  has_more: boolean;
  tier3_triggered: boolean;
  degraded: boolean;
  results: PropertyResult[];
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
