"""
FastAPI application - Main entry point with all API endpoints.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    Background task: Run semantic alignment and update session.
    """
    try:
        tags = await llm_client.semantic_alignment(description)
        update_semantic_tags(session_id, tags)
    except Exception as e:
        print(f"Semantic alignment error: {e}")
        update_semantic_tags(session_id, [])


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

    alignment_warning = len(phase1.semantic_tags) == 0
    return SessionReadyResponse(
        status="ready",
        semantic_tags=phase1.semantic_tags,
        alignment_warning=alignment_warning,
    )


# ─── 4.3 POST /api/v1/chat ──────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
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
        {
            "role": msg.role,
            "content": msg.content,
        }
        for msg in dialogue_session.dialogue_history
    ]

    # System prompt with semantic tags
    system_prompt = f"""
你是一位智能房產銷售代理。
用戶資料：
- 預算：{dialogue_session.phase1_data.budget}
- 代理風格：{dialogue_session.phase1_data.agent_style}
- 目標：{dialogue_session.phase1_data.target}
- 身份：{dialogue_session.phase1_data.identity}
- 性別：{dialogue_session.phase1_data.gender}

隱含偏好（無自然採光等）：{', '.join(dialogue_session.phase1_data.semantic_tags)}

任務：
1. 進行多輪對話以完整用戶需求
2. 檢測字段衝突（例如預算更改、地點更改等）
3. 在有足夠信息時觸發 Function Calling 啟動搜索

輸出格式（JSON）：
{{
  "reply": "你的回應文本",
  "conflict_detected": false,
  "conflicting_field": null,
  "proposed_value": null,
  "fc_trigger": false
}}

如果檢測到衝突：
{{
  "reply": "您之前選擇的是 X，現在想改為 Y 嗎？",
  "conflict_detected": true,
  "conflicting_field": "target",
  "proposed_value": "新地點",
  "fc_trigger": false
}}

如果準備觸發搜索：
{{
  "reply": "好的，讓我為您搜索合適的房源。",
  "conflict_detected": false,
  "conflicting_field": null,
  "proposed_value": null,
  "fc_trigger": true
}}
    """

    messages.insert(0, {"role": "system", "content": system_prompt})

    try:
        # Call LLM for structured output
        llm_output = await llm_client.chat(messages)

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

    return SearchStatusResponse(status="scraping")


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

