"""
FastAPI application - Main entry point with all API endpoints.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json as _json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schemas import (
    Phase1Data,
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
)
from session_manager import (
    create_session,
    get_dialogue_session,
    get_npp_session,
    get_search_session,
    add_dialogue_message,
    increment_fc_attempts,
    record_rejection,
    update_npp_tags,
    reset_all_sessions,
    keep_memories_reset,
    reset_search_session,  # FIX B4: was missing — caused NameError in update_requirements
    update_semantic_tags,
)
from llm_client import llm_client
from search_pipeline import execute_search_pipeline


# FastAPI app setup
app = FastAPI(
    title="Property Agent UI - Backend API",
    description="API for intelligent property sales agent system",
    version="1.0.0",
)

# FIX B9: CORS spec forbids credentials=True with wildcard origins.
# Browsers silently reject such responses. For MVP we disable credentials;
# in production list explicit origins instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background tasks ────────────────────────────────────────────────
async def async_semantic_alignment(session_id: str, description: str):
    """
    Background task: run semantic alignment, persist tags + any hard error.
    """
    try:
        result = await llm_client.semantic_alignment(description)
        update_semantic_tags(session_id, result, error=None)
    except Exception as e:
        # HARD failure (network/HTTP/parse) — surface to frontend, don't pretend it's "ready with 0 tags".
        msg = f"{type(e).__name__}: {e}"
        print(f"[async_semantic_alignment] hard failure: {msg}")
        update_semantic_tags(session_id, {"positive": [], "negative": []}, error=msg)



# ─── 4.1 POST /api/v1/init_session ──────────────────────────────────
@app.post("/api/v1/init_session", response_model=InitSessionResponse)
async def init_session(
    phase1_data: Phase1Data,
    background_tasks: BackgroundTasks,
):
    """
    Initialize new session with Phase 1 data.
    Async launch semantic alignment, return immediately.
    """
    session_id = create_session(phase1_data)

    # Launch semantic alignment in background
    background_tasks.add_task(
        async_semantic_alignment,
        session_id,
        phase1_data.description,  # Changed from phase1_data.target to phase1_data.description
    )

    return InitSessionResponse(
        session_id=session_id,
        status="aligning",
    )


# ─── 4.2 GET /api/v1/session_ready/{session_id} ──────────────────────
@app.get("/api/v1/session_ready/{session_id}", response_model=SessionReadyResponse)
async def session_ready(session_id: str):
    """
    Poll endpoint - check if semantic alignment is complete.
    """
    dialogue_session = get_dialogue_session(session_id)
    if not dialogue_session:
        raise HTTPException(status_code=404, detail="Session not found")

    phase1 = dialogue_session.phase1_data

    if not phase1.semantic_alignment_done:
        return SessionReadyResponse(status="aligning")

    total = len(phase1.semantic_tags) + len(phase1.positive_tags)
    return SessionReadyResponse(
        status="ready",
        semantic_tags=phase1.semantic_tags,
        positive_tags=phase1.positive_tags,
        alignment_warning=(total == 0),
        error=phase1.alignment_error,
    )


# ─── 4.2b GET /api/v1/session_ready/{session_id}/stream (SSE) ───────
@app.get("/api/v1/session_ready/{session_id}/stream")
async def session_ready_stream(session_id: str):
    """
    SSE companion to /session_ready. Pushes one event every 1s until status='ready',
    then closes. Frontend EventSource consumes `data: <json>` lines.
    """
    if not get_dialogue_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        max_iters = 120  # 120 * 1s = 2 min hard cap
        for _ in range(max_iters):
            ds = get_dialogue_session(session_id)
            if not ds:
                payload = {"status": "aligning"}
            else:
                p = ds.phase1_data
                if not p.semantic_alignment_done:
                    payload = {"status": "aligning"}
                else:
                    total = len(p.semantic_tags) + len(p.positive_tags)
                    payload = {
                        "status": "ready",
                        "semantic_tags": p.semantic_tags,
                        "positive_tags": p.positive_tags,
                        "alignment_warning": (total == 0),
                        "error": p.alignment_error,
                    }
            yield f"data: {_json.dumps(payload)}\n\n"
            if payload["status"] == "ready":
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )




# ─── 4.3 POST /api/v1/chat ──────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str
    # Optional enrichment from the frontend so the LLM does not re-ask
    # facts the user already provided. Safe-additive: older clients omit it.
    client_context: dict | None = None


class ChatOpeningRequest(BaseModel):
    """Phase 2 proactive-opening request.

    Triggered once when the user enters Phase 2. No user text is supplied;
    the LLM produces the first question on its own, anchored on Phase 1
    data + semantic tags + optional client-supplied confirmed_facts.
    """
    session_id: str
    client_context: dict | None = None


def _build_phase2_system_prompt(dialogue_session, client_context: dict | None) -> str:
    """Single source of truth for the Phase 2 system prompt.

    Shared by /chat and /chat_opening so behaviour cannot drift between
    the proactive opener and subsequent turns.
    """
    p1 = dialogue_session.phase1_data
    system_prompt = f"""
你是一位資深的智能房產銷售代理（馬來西亞市場）。
你的任務：在 Phase 2 對話中，**主動、有條理地追問**用戶理想房產的細節，
直到收集足夠資訊後觸發搜索。

=== Phase 1 已確認資料（權威，禁止重複追問）===
- 預算 budget：{p1.budget}
- 代理風格 agent_style：{p1.agent_style}
- 目標 target：{p1.target}
- 身份 identity：{p1.identity}
- 性別 gender：{p1.gender}
- 用戶自述 description：{getattr(p1, 'description', '')}
- 房屋類型 house_type：{getattr(p1, 'house_type', '') or '(未填)'}
- 地點 location：{getattr(p1, 'location', '') or '(未填)'}
- 隱含偏好 semantic_tags：{', '.join(p1.semantic_tags) if p1.semantic_tags else '(無)'}

=== 你必須主動追問的「必填細節」(must-fill bracket) ===
1. 具體地點 / 區域偏好（若 Phase 1 location 為空或過於籠統）
2. 期望臥室數量 bedrooms
3. 期望浴室數量 bathrooms
4. 必備設施 must-haves（停車位、保安、泳池…）
5. 絕對不要 dealbreakers（噪音、樓層、朝向…）
6. 入住時間 timeline
7. 融資方式 financing（現金 / 房貸）

每次只追問 1–2 個最關鍵且尚未明朗的細節，語氣自然，配合 agent_style。
**禁止**重複詢問 confirmed_facts 中任何已知值。

=== 衝突檢測（必須）===
若用戶新訊息中提到的值與 Phase 1 / 先前 Phase 2 已確認值不一致
（如預算、地點、臥室數、房屋類型變更），必須 conflict_detected=true，
conflicting_field 用 snake_case 欄位名，proposed_value 為用戶新值。

=== 搜索觸發 ===
當上方「必填細節」中至少 3 項已被用戶明確回答時，設 fc_trigger=true，
reply 寫一句承上啟下的話（例如「資料齊全了，我這就為您挑選合適的房源。」）。

=== 輸出格式（嚴格 JSON，不得多餘文字）===
{{
  "reply": "你的回應文本",
  "conflict_detected": false,
  "conflicting_field": null,
  "proposed_value": null,
  "fc_trigger": false
}}
    """

    ctx = client_context or {}
    confirmed_facts = ctx.get("confirmed_facts") or []
    instruction = ctx.get("instruction") or ""
    if confirmed_facts or instruction:
        facts_block = "\n".join(f"- {f}" for f in confirmed_facts)
        system_prompt += (
            "\n\n=== KNOWN FACTS (authoritative — DO NOT re-ask) ===\n"
            + facts_block
            + ("\n\nINSTRUCTION: " + instruction if instruction else "")
        )
    return system_prompt


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Phase 2 main dialogue endpoint.
    LLM outputs structured JSON, backend parses and returns appropriate status.
    """
    dialogue_session = get_dialogue_session(request.session_id)
    if not dialogue_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add user message to history
    add_dialogue_message(request.session_id, "user", request.message)

    # Build conversation for LLM
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in dialogue_session.dialogue_history
    ]

    system_prompt = _build_phase2_system_prompt(
        dialogue_session, request.client_context
    )
    messages.insert(0, {"role": "system", "content": system_prompt})

    try:
        # Call LLM for structured output with retry logic
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception), # Retry on any exception from LLM client
            reraise=True,
        )
        async def call_llm_with_retry():
            return await llm_client.chat(messages)

        llm_output = await call_llm_with_retry()

        # Add assistant response to history
        add_dialogue_message(request.session_id, "assistant", llm_output.reply)

        # Determine response status
        if llm_output.conflict_detected:
            return ChatResponse(
                status="pending_confirmation",
                reply=llm_output.reply,
                conflicting_field=llm_output.conflicting_field,
                proposed_value=llm_output.proposed_value,
            )

        if llm_output.fc_trigger:
            # Check attempt limit
            attempts = increment_fc_attempts(request.session_id)
            if attempts > 2:
                # Force trigger without more attempts
                pass

            # CRIT-1: actually kick off the search pipeline. Without this the
            # search_session.search_stage stays "idle" forever and the
            # frontend Searching page hangs.
            background_tasks.add_task(execute_search_pipeline, request.session_id)

            return ChatResponse(
                status="searching",
                reply=llm_output.reply,
                fc_attempt=attempts,
            )

        return ChatResponse(
            status="chatting",
            reply=llm_output.reply,
            fc_attempt=dialogue_session.fc_trigger_attempts,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ─── 4.3b POST /api/v1/chat_opening ─────────────────────────────────
@app.post("/api/v1/chat_opening", response_model=ChatResponse)
async def chat_opening(request: ChatOpeningRequest):
    """
    Proactive Phase 2 opening: the agent speaks first.

    Idempotent: if the dialogue already has any assistant message we
    return the most recent one instead of generating a new opener. This
    prevents duplicate openings on React StrictMode double-mounts or
    accidental re-entry into the Phase 2 screen.
    """
    dialogue_session = get_dialogue_session(request.session_id)
    if not dialogue_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Idempotency guard
    for msg in dialogue_session.dialogue_history:
        if msg.role == "assistant":
            # Return the last assistant message (most recent opener/turn).
            last_assistant = next(
                (m for m in reversed(dialogue_session.dialogue_history) if m.role == "assistant"),
                None,
            )
            return ChatResponse(
                status="chatting",
                reply=last_assistant.content if last_assistant else "",
                fc_attempt=dialogue_session.fc_trigger_attempts,
            )

    system_prompt = _build_phase2_system_prompt(
        dialogue_session, request.client_context
    )

    # Synthetic kickoff turn. Not persisted to dialogue_history so it
    # never bleeds into the user-visible transcript.
    kickoff_user = (
        "[SYSTEM_KICKOFF] 對話即將開始。請依據上方 Phase 1 已確認資料與 KNOWN FACTS，"
        "用一句簡短的歡迎語自我介紹，然後立刻提出『必填細節』中尚未明朗、"
        "對搜索最關鍵的 1 個問題。輸出仍須嚴格遵守 JSON 格式；"
        "禁止重複追問任何 confirmed_facts；禁止觸發 fc_trigger。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": kickoff_user},
    ]

    try:
        llm_output = await llm_client.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat_opening error: {str(e)}")

    # Persist only the assistant reply. fc_trigger / conflicts are
    # ignored on the opener (no user input to conflict with, nothing to
    # search yet) — they would be logic errors from the model.
    add_dialogue_message(request.session_id, "assistant", llm_output.reply)

    return ChatResponse(
        status="chatting",
        reply=llm_output.reply,
        fc_attempt=dialogue_session.fc_trigger_attempts,
    )


# ─── 4.4 GET /api/v1/search_status/{session_id} ──────────────────────
@app.get("/api/v1/search_status/{session_id}", response_model=SearchStatusResponse)
async def search_status(session_id: str):
    """
    Poll search pipeline progress.
    """
    search_session = get_search_session(session_id)
    if not search_session:
        raise HTTPException(status_code=404, detail="Session not found")

    status = search_session.search_stage

    if status in ["scraping", "ranking", "generating_remarks"]:
        return SearchStatusResponse(status=status)

    if status == "complete":
        # Calculate batch
        total = len(search_session.all_results)
        batch_start = (search_session.batch_index - 1) * 5
        batch_end = batch_start + 5
        batch_results = search_session.all_results[batch_start:batch_end]

        has_more = (batch_end < total)

        return SearchStatusResponse(
            status="complete",
            batch_index=search_session.batch_index,
            total_available=total,
            has_more=has_more,
            tier3_triggered=False,
            degraded=False,
            results=batch_results,
        )

    # CRIT-2: when stage is "idle" (pipeline not yet scheduled), report idle
    # truthfully instead of pretending to scrape.
    return SearchStatusResponse(status="idle")



# ─── 4.5 POST /api/v1/next_batch ────────────────────────────────────
class NextBatchRequest(BaseModel):
    session_id: str


@app.post("/api/v1/next_batch", response_model=NextBatchResponse)
async def next_batch(request: NextBatchRequest):
    """
    Fetch next batch of 5 properties.
    Pure UI fetch - no rejection learning triggered.
    """
    search_session = get_search_session(request.session_id)
    if not search_session:
        raise HTTPException(status_code=404, detail="Session not found")

    search_session.batch_index += 1

    total = len(search_session.all_results)
    batch_start = (search_session.batch_index - 1) * 5
    batch_end = batch_start + 5
    batch_results = search_session.all_results[batch_start:batch_end]

    has_more = (batch_end < total)

    return NextBatchResponse(
        batch_index=search_session.batch_index,
        total_available=total,
        has_more=has_more,
        tier3_triggered=False,
        degraded=False,
        results=batch_results or [],
    )


# ─── 4.6 POST /api/v1/reject_single ─────────────────────────────────
class RejectSingleRequest(BaseModel):
    session_id: str
    property_id: str
    reason: str


@app.post("/api/v1/reject_single", response_model=RejectSingleResponse)
async def reject_single(request: RejectSingleRequest):
    """
    Record single property rejection.
    Adds to blacklist and pending rejection buffer for NPP learning.
    """
    search_session = get_search_session(request.session_id)
    if not search_session:
        raise HTTPException(status_code=404, detail="Session not found")

    record_rejection(
        request.session_id,
        request.property_id,
        request.reason,
    )

    rejection_count = len(search_session.rejected_property_ids)

    return RejectSingleResponse(
        status="recorded",
        rejection_count=rejection_count,
    )


# ─── 4.7 POST /api/v1/reject_all ────────────────────────────────────
class RejectAllRequest(BaseModel):
    session_id: str


@app.post("/api/v1/reject_all", response_model=RejectAllResponse)
async def reject_all(request: RejectAllRequest):
    """
    All properties rejected - trigger NPP learning.
    """
    npp_session = get_npp_session(request.session_id)
    search_session = get_search_session(request.session_id)

    if not npp_session or not search_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Extract rejection reasons from buffer
    rejection_reasons = [
        item["content"] for item in npp_session.pending_rejection_buffer
    ]

    # Map to NPP tags
    try:
        new_npp_tags = await llm_client.map_rejection_to_npp(rejection_reasons)
        update_npp_tags(request.session_id, new_npp_tags)
    except Exception as e:
        print(f"NPP mapping error: {e}")
        new_npp_tags = []

    return RejectAllResponse(
        status="action_required",
        npp_updated=new_npp_tags,
        message="已更新您的偏好記錄。請選擇下一步操作。",
    )


# ─── 4.8 POST /api/v1/resolve_action ────────────────────────────────
class ResolveActionRequest(BaseModel):
    session_id: str
    action: str  # "new_prompt" or "keep_memories"


@app.post("/api/v1/resolve_action", response_model=ActionResolveResponse)
async def resolve_action(request: ResolveActionRequest):
    """
    Resolve ACTION_REQUIRED_UI - either New Prompt or Keep Memories.
    """
    if request.action == "new_prompt":
        reset_all_sessions(request.session_id)
        return ActionResolveResponse(
            status="reset_complete",
            cleared=["dialogue_session", "npp_session", "search_session"],
            next_phase="phase_1",
        )

    elif request.action == "keep_memories":
        keep_memories_reset(request.session_id)
        return ActionResolveResponse(
            status="memories_kept",
            preserved=["npp_tags", "dialogue_history"],
            reset=["search_session"],
            next_phase="phase_2",
            reply="好的，我已保留您的偏好記錄。請告訴我您想如何調整搜索條件？",
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# ─── 4.9 POST /api/v1/fetch_detail ──────────────────────────────────
class FetchDetailRequest(BaseModel):
    session_id: str
    property_url: str


@app.post("/api/v1/fetch_detail", response_model=PropertyDetailResponse)
async def fetch_detail(request: FetchDetailRequest):
    """
    Deep fetch single property detail page.
    Generate AI analysis summary.
    """
    # In MVP, return mock detail
    return PropertyDetailResponse(
        ai_summary="This is a premium property with excellent facilities and location.",
        pros=["距離 MRT 僅 200 米", "管理費合理"],
        cons=["樓齡已 12 年"],
        is_near_match=True,
        degraded=False,
    )


# ─── 4.10 POST /api/v1/update_requirements ──────────────────────────
@app.post("/api/v1/update_requirements", response_model=UpdateRequirementsResponse)
async def update_requirements(request: UpdateRequirementsRequest):
    """
    Update Phase 1 requirements. Only clears relevant dialogue segments and NPP tags.
    """
    dialogue_session = get_dialogue_session(request.session_id)
    if not dialogue_session:
        raise HTTPException(status_code=404, detail="Session not found")

    cleared_dialogue_segments = []  # Placeholder for actual logic
    npp_cleared_tags = []  # Placeholder for actual logic
    search_session_reset = True  # Always reset search session on update
    rejected_property_ids_cleared = True  # Always clear rejected properties

    # TODO: Implement actual logic for clearing dialogue segments and NPP tags
    # based on updated_fields. This will require more detailed logic in session_manager.

    # For now, we'll just update the phase1_data directly for demonstration
    for field, value in request.updated_fields.items():
        if hasattr(dialogue_session.phase1_data, field):
            setattr(dialogue_session.phase1_data, field, value)

    # Reset search session and clear rejected properties
    reset_search_session(request.session_id)

    return UpdateRequirementsResponse(
        status="updated",
        cleared_dialogue_segments=cleared_dialogue_segments,
        npp_cleared_tags=npp_cleared_tags,
        search_session_reset=search_session_reset,
        rejected_property_ids_cleared=rejected_property_ids_cleared,
    )


# ─── Health check ────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ─── Root ────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Property Agent UI Backend API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

