/**
 * API Client - Frontend integration with backend endpoints
 * All requests use the /api/v1 base path
 */

import type {
  Phase1Form,
  InitSessionResponse,
  SessionReadyResponse,
  ChatResponse,
  SearchStatusResponse,
  NextBatchResponse,
  RejectSingleResponse,
  RejectAllResponse,
  ActionResolveResponse,
  PropertyDetailResponse,
  UpdateRequirementsRequest,
  UpdateRequirementsResponse,
} from "./types";

const API_BASE_URL = process.env.VITE_API_URL || "http://localhost:8000";

export const apiClient = {
  /**
   * 4.1 Initialize session with Phase 1 data
   * Async launch semantic alignment, return immediately
   */
  async initSession(phase1Data: Phase1Form): Promise<InitSessionResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/init_session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        budget: phase1Data.budget,
        agent_style: phase1Data.agent_style,
        target: phase1Data.target,
        identity: phase1Data.identity,
        gender: phase1Data.gender,
      }),
    });
    if (!response.ok) throw new Error(`Init failed: ${response.statusText}`);
    return response.json();
  },

  /**
   * 4.2 Poll semantic alignment completion
   */
  async sessionReady(sessionId: string): Promise<SessionReadyResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/session_ready/${sessionId}`
    );
    if (!response.ok) throw new Error(`Session ready check failed`);
    return response.json();
  },

  /**
   * 4.3 Send chat message for Phase 2 dialogue
   */
  async chat(
    sessionId: string,
    message: string
  ): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });
    if (!response.ok) throw new Error(`Chat failed: ${response.statusText}`);
    return response.json();
  },

  /**
   * 4.4 Poll search pipeline progress
   */
  async searchStatus(sessionId: string): Promise<SearchStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/search_status/${sessionId}`
    );
    if (!response.ok) throw new Error(`Search status check failed`);
    return response.json();
  },

  /**
   * 4.5 Fetch next batch of 5 properties
   */
  async nextBatch(sessionId: string): Promise<NextBatchResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/next_batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) throw new Error(`Next batch failed`);
    return response.json();
  },

  /**
   * 4.6 Record single property rejection
   */
  async rejectSingle(
    sessionId: string,
    propertyId: string,
    reason: string
  ): Promise<RejectSingleResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/reject_single`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        property_id: propertyId,
        reason,
      }),
    });
    if (!response.ok) throw new Error(`Reject single failed`);
    return response.json();
  },

  /**
   * 4.7 Trigger NPP learning on all rejection
   */
  async rejectAll(sessionId: string): Promise<RejectAllResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/reject_all`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!response.ok) throw new Error(`Reject all failed`);
    return response.json();
  },

  /**
   * 4.8 Resolve ACTION_REQUIRED_UI - New Prompt or Keep Memories
   */
  async resolveAction(
    sessionId: string,
    action: "new_prompt" | "keep_memories"
  ): Promise<ActionResolveResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/resolve_action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        action,
      }),
    });
    if (!response.ok) throw new Error(`Resolve action failed`);
    return response.json();
  },

  /**
   * 4.9 Deep fetch property detail page
   */
  async fetchDetail(
    sessionId: string,
    propertyUrl: string
  ): Promise<PropertyDetailResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/fetch_detail`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        property_url: propertyUrl,
      }),
    });
    if (!response.ok) throw new Error(`Fetch detail failed`);
    return response.json();
  },

  /**
   * 4.10 Update Phase 1 requirements
   * Only clears relevant dialogue segments and NPP tags
   */
  async updateRequirements(
    sessionId: string,
    updatedFields: Record<string, any>
  ): Promise<UpdateRequirementsResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/update_requirements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        updated_fields: updatedFields,
      }),
    });
    if (!response.ok) throw new Error(`Update requirements failed`);
    return response.json();
  },
};
