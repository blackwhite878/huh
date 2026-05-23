# Property Agent UI - Backend Setup Guide

## Overview

This is the FastAPI backend for the Intelligent Property Sales Agent system. It implements the complete end-to-end pipeline as specified in `Backend.md`:

1. **Phase 1**: Session initialization with semantic alignment
2. **Phase 2**: Multi-round dialogue with LLM
3. **Search Pipeline**: Tier classification → Math weighting → LLM remarks → Batch delivery
4. **NPP Learning**: Rejection feedback → Tag mapping → User preference updates

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and add your Chutes AI credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
CHUTES_AI_API_KEY=your-key-here
CHUTES_AI_BASE_URL=https://llm.chutes.ai/v1
APP_SECRET_KEY=your-secret-key
```

### 3. Configuration

`config.yaml` contains non-sensitive settings:

```yaml
app:
  demo_mode: true    # MVP: use mock data, skip scraping
  debug: true

llm:
  model: "deepseek-ai/DeepSeek-V3-0324"
  max_tokens: 2000
  max_concurrent_calls: 3   # Semaphore limit for concurrent LLM calls
```

### 4. Run the Backend

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)

## API Endpoints

All endpoints follow the `/api/v1` prefix pattern specified in Backend.md.

### Phase 1: Session Initialization

#### `POST /api/v1/init_session`
Initialize new session with Phase 1 data. Async launches semantic alignment.

```json
{
  "budget": 500000,
  "agent_style": "professional",
  "target": "condo in Johor Bahru",
  "identity": "first_time_buyer",
  "gender": "female"
}
```

Response:
```json
{
  "session_id": "uuid-v4",
  "status": "aligning"
}
```

#### `GET /api/v1/session_ready/{session_id}`
Poll semantic alignment completion (3 sec intervals from frontend).

Response when ready:
```json
{
  "status": "ready",
  "semantic_tags": ["near_school", "no_security"],
  "alignment_warning": false
}
```

### Phase 2: Chat & Dialogue

#### `POST /api/v1/chat`
Send chat message. LLM outputs structured JSON with conflict detection & FC trigger.

```json
{
  "session_id": "uuid",
  "message": "我想靠近地鐵站"
}
```

Response (chatting):
```json
{
  "status": "chatting",
  "reply": "請問您需要幾個房間呢？",
  "fc_attempt": 1
}
```

Response (conflict detected):
```json
{
  "status": "pending_confirmation",
  "reply": "您之前選擇的是 Johor Bahru，現在想換到 KL 嗎？",
  "conflicting_field": "target",
  "proposed_value": "condo in KL"
}
```

Response (FC triggered):
```json
{
  "status": "searching",
  "reply": "好的，讓我為您搜索合適的房源。",
  "fc_attempt": 1
}
```

### Search Pipeline

#### `GET /api/v1/search_status/{session_id}`
Poll search pipeline progress (3 sec intervals).

Response (in progress):
```json
{
  "status": "scraping"
}
```

Response (complete):
```json
{
  "status": "complete",
  "batch_index": 1,
  "total_available": 10,
  "has_more": true,
  "tier3_triggered": false,
  "degraded": false,
  "results": [
    {
      "property_id": "JB001",
      "tier": "tier_1",
      "remarks": "Modern condo with excellent security features...",
      "missing_features": [],
      "remedy": null
    },
    ...
  ]
}
```

#### `POST /api/v1/next_batch`
Fetch next batch (pure UI fetch, no rejection learning).

```json
{
  "session_id": "uuid"
}
```

### Rejection & NPP Learning

#### `POST /api/v1/reject_single`
Record single property rejection.

```json
{
  "session_id": "uuid",
  "property_id": "JB001",
  "reason": "樓層太高，有西晒"
}
```

Response:
```json
{
  "status": "recorded",
  "rejection_count": 1
}
```

#### `POST /api/v1/reject_all`
All results rejected - triggers NPP learning.

Response:
```json
{
  "status": "action_required",
  "npp_updated": ["high_floor", "west_facing"],
  "message": "已更新您的偏好記錄。請選擇下一步操作。"
}
```

### Action Resolution

#### `POST /api/v1/resolve_action`
Resolve ACTION_REQUIRED_UI - either reset or keep memories.

New Prompt (full reset):
```json
{
  "session_id": "uuid",
  "action": "new_prompt"
}
```

Keep Memories (preserve NPP + dialogue, reset search):
```json
{
  "session_id": "uuid",
  "action": "keep_memories"
}
```

## Architecture

### Three Independent Session Types

All share the same `session_id` but have independent lifecycle:

1. **DialogueSession**: Phase 1 data, dialogue history, FC attempts
2. **NPPSession**: Negative preferences tags, rejection buffer
3. **SearchSession**: Raw pool, tier pools, batch index, expansion level

### Search Pipeline Steps

```
Step 1: Fetch raw properties (with expansion if needed)
  ↓
Step 2: Tier Classification (hard constraints first)
  - Tier 1: No NPP conflicts, passes budget
  - Tier 2: Minor conflicts (1-2), passes budget
  - Dropped: Serious conflicts or budget violation
  ↓
Step 3: Math Weighting (to Top 10)
  - Base weights: price_fit, security, facilities, lifestyle, maintenance, transit
  - Dynamic multipliers: gender × identity
  - Normalize to Σ = 1.0
  ↓
Step 4: LLM Remarks Generation (single API call for Top 10)
  - Tier 1: Positive remarks, no missing features
  - Tier 2: Defensive remarks with remedy suggestions
  ↓
Step 5: Batch Return (5 + 5)
  - First batch: Top 5
  - Next batch: Remaining 5
```

### Weight Vector

```python
BASE_WEIGHT_VECTOR = {
    "price_fit_score": 0.30,
    "security_score": 0.25,
    "facilities_score": 0.20,
    "lifestyle_proximity_score": 0.15,
    "maintenance_fee_score": 0.05,  # Inverted: (1 - normalized_fee)
    "transit_proximity_score": 0.05,
}  # Σ = 1.0
```

### Gender & Identity Multipliers

Applied before normalization:

```python
GENDER_MULTIPLIERS = {
    "female": {
        "security_score": 1.30,
        "lifestyle_proximity_score": 1.15,
    },
    ...
}

IDENTITY_MULTIPLIERS = {
    "first_time_buyer": {
        "price_fit_score": 1.30,
        "facilities_score": 1.10,
        "maintenance_fee_score": 1.20,
    },
    ...
}
```

## Core Constraints (Non-negotiable)

Per Backend.md:

1. ✅ **Budget hard constraint in Python** - never depends on LLM
2. ✅ **Tier classification before weighting** - NPP conflicts filtered first
3. ✅ **NPP enum frozen** - 40 tags, no runtime expansion
4. ✅ **Mock data passes full pipeline** - not bypassed
5. ✅ **Pydantic validation on all LLM outputs** - validation failures retry
6. ✅ **Semaphore limits concurrent LLM calls** - configurable in config.yaml
7. ✅ **Search session reset = batch_index to 1** - expansion_level to 0
8. ✅ **No auto-re-search after reject_all** - must enter ACTION_REQUIRED_UI
9. ✅ **NPP tags only use internal keys** - display labels for UI/prompts only
10. ✅ **Topolog expansion strictly by admin district** - no coordinate calculations

## Mock Data

For MVP (demo_mode: true), uses 40+ property records:

- Distributed across 3+ administrative districts
- ≥80% satisfy "budget ±10% + no NPP conflicts" baseline
- Each NPP tag appears in ≥2 properties
- All have valid scores and complete feature set

Run with demo_mode to test full pipeline without scraping.

## LLM Concurrent Control

Semaphore limits concurrent Chutes AI calls:

```python
llm_semaphore = asyncio.Semaphore(settings.llm.max_concurrent_calls)
```

Default: 3 concurrent calls. Adjust in `config.yaml` based on API limits.

## Degraded Mode

Triggered by:
- LLM `RateLimitError`
- Network timeout
- Validation failure (after 3 retries)

In degraded mode:
- Remarks set to `null`
- `degraded: true` flag set
- Results sorted by math weighting only (no LLM input)

## Development Notes

### File Structure

```
backend/
├── main.py                 # FastAPI app + all endpoints
├── schemas.py              # Pydantic models
├── session_manager.py      # Session lifecycle management
├── llm_client.py          # Chutes AI integration
├── weighting.py           # Math weighting + scoring
├── search_pipeline.py     # Search orchestration
├── npp_enum.py            # NPP constant definitions (frozen)
├── topology.py            # Admin district graph
├── mock_data.py           # Mock properties for MVP
├── config.yaml            # Config (non-sensitive)
├── .env.example           # Env template
└── requirements.txt       # Dependencies
```

### Testing the Pipeline

1. **Init Session**: POST /api/v1/init_session
2. **Poll Alignment**: GET /api/v1/session_ready/{id} (3 sec × 5)
3. **Chat**: POST /api/v1/chat (simulate dialogue)
4. **Trigger Search**: Chat with FC = true
5. **Poll Search**: GET /api/v1/search_status/{id} (3 sec × 10)
6. **View Results**: Inspect search_status response
7. **Reject Single**: POST /api/v1/reject_single
8. **Reject All**: POST /api/v1/reject_all
9. **Action**: POST /api/v1/resolve_action (new_prompt or keep_memories)

## Frontend Integration

Frontend connects via `apiClient` in `src/lib/api-client.ts`:

```typescript
// Example
const response = await apiClient.initSession(phase1Data);
const sessionId = response.session_id;
```

Environment variable:
```
VITE_API_URL=http://localhost:8000
```

## Production Checklist

- [ ] Replace mock data with live scraper
- [ ] Switch demo_mode to false
- [ ] Configure Redis for session persistence
- [ ] Add authentication/API keys
- [ ] Set up Chutes AI rate limit monitoring
- [ ] Enable CORS restrictions (frontend domain only)
- [ ] Use database for session storage
- [ ] Add logging/monitoring
- [ ] Test with live Chutes AI calls

