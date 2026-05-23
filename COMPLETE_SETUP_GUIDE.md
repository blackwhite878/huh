# Complete System Setup Guide

## 📋 Architecture Overview

This is a complete end-to-end intelligent property sales agent system with:

- **Backend**: Python FastAPI with async LLM integration (Chutes AI)
- **Frontend**: React + TypeScript with Zustand state management
- **Pipeline**: Semantic alignment → Multi-turn dialogue → Tier classification → Math weighting → LLM remarks → Batch delivery

## 🚀 Getting Started (5 minutes)

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Chutes AI API key

### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# or (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your Chutes AI credentials
```

### Step 2: Start Backend

```bash
# Option A: With startup checks
python startup.py

# Option B: Direct uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: **http://localhost:8000**
- Swagger API: http://localhost:8000/docs

### Step 3: Frontend Setup

```bash
cd property-agent-ui

# Install dependencies
npm install
# or
bun install

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
# or
bun run dev
```

Frontend runs at: **http://localhost:5173**

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: Profiling                        │
├─────────────────────────────────────────────────────────────┤
│  1. POST /api/v1/init_session                               │
│     └─> Create 3 independent sessions (Dialogue, NPP, Search)
│     └─> Async: Semantic alignment started in background      │
│  2. GET /api/v1/session_ready/{id} [Poll 3s × N]            │
│     └─> Wait for semantic_alignment_done = true             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  PHASE 2: Multi-turn Chat                    │
├─────────────────────────────────────────────────────────────┤
│  3. POST /api/v1/chat                                        │
│     └─> LLM outputs structured JSON:                        │
│         - reply: conversational text                         │
│         - conflict_detected: bool (field change?)            │
│         - fc_trigger: bool (search ready?)                   │
│  4. Handle responses:                                        │
│     - "chatting": continue conversation                      │
│     - "pending_confirmation": ask user to confirm change     │
│     - "searching": transition to search pipeline             │
└─────────��───────────────────────────────────────────────────┘
                           ↓
┌───────────────────────────────��─────────────────────────────┐
│                  SEARCH PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│  5. Chat triggers search (fc_trigger=true)                  │
│  6. GET /api/v1/search_status/{id} [Poll 3s × N]            │
│     │                                                         │
│     ├─> "scraping": Fetching raw properties                 │
│     │   └─> Tier classification (budget + NPP conflicts)     │
│     │   └─> If no results → expand admin district           │
│     │                                                         │
│     ├─> "ranking": Math weighting (Top 10)                  │
│     │   └─> Base weights × gender multipliers × identity    │
│     │   └─> Normalize to Σ = 1.0                            │
│     │                                                         │
│     ├─> "generating_remarks": LLM single call               │
│     │   └─> Tier 1: positive remarks                        │
│     │   └─> Tier 2: defensive + remedy                      │
│     │                                                         │
│     └─> "complete": Ready for display                        │
│         └─> Batch 1: results[0:5]                           │
│         └─> has_more: true/false                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              RESULTS & REJECTION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│  7. Display batch with rejection buttons                     │
│  8. POST /api/v1/reject_single {property_id, reason}        │
│     └─> Record in blacklist + pending_rejection_buffer      │
│  9. POST /api/v1/next_batch [if has_more]                   │
│     └─> Fetch batch 2 (pure UI fetch)                       │
│ 10. All rejected? → POST /api/v1/reject_all                 │
│     └─> LLM: Map reasons → NPP tags                         │
│     └─> Update npp_tags (append, deduplicate)               │
│     └─> Transition to ACTION_REQUIRED_UI                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│            ACTION REQUIRED - User Choice                     │
├─────────────────────────────────────────────────────────────┤
│ 11. POST /api/v1/resolve_action                             │
│     │                                                         │
│     ├─ action: "new_prompt"                                 │
│     │  └─> Reset all 3 sessions                             │
│     │  └─> Return to PHASE 1                                │
│     │                                                         │
│     └─ action: "keep_memories"                              │
│        └─> Preserve: dialogue_history, npp_tags             │
│        └─> Reset: search_session, expansion_level           │
│        └─> Return to PHASE 2 for refinement                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔑 Key Components

### Backend Modules

```
backend/
├── main.py                 # FastAPI app + 10 endpoints
├── schemas.py              # Pydantic models (strict validation)
├── session_manager.py      # Session lifecycle (3 types)
├── llm_client.py          # Chutes AI integration + retry logic
├── weighting.py           # Math weighting + dynamic multipliers
├── search_pipeline.py     # Search orchestration
├── npp_enum.py            # NPP frozen enum (40 tags)
├── topology.py            # Admin district graph
├── mock_data.py           # 40+ properties for MVP
├── config.yaml            # Non-sensitive config
├── .env.example           # Env template
├── requirements.txt       # Python dependencies
├── README.md              # Backend documentation
├── startup.py             # Startup checks
├── test_api.py            # Manual API test suite
└── test_integration.py    # Unit + integration tests
```

### Frontend Components

```
property-agent-ui/src/
├── lib/
│   ├── types.ts           # TypeScript contracts
│   ├── store.ts           # Zustand state machine
│   ├── api-client.ts      # API integration (NEW)
│   └── utils.ts
├── hooks/
│   ├── use-api.ts         # API hooks (NEW)
│   └── use-mobile.tsx
├── components/
│   ├── phases/
│   │   ├── Phase1Form.tsx     # NEW
│   │   ├── Phase2Chat.tsx     # NEW
│   │   ├── ResultsDisplay.tsx # NEW
│   │   ├── ActionRequired.tsx # UPDATED
│   │   └── Searching.tsx
│   └── ui/
│       ├── button.tsx
│       ├── card.tsx
│       └── ... (shadcn/ui components)
└── routes/
    ├── __root.tsx
    └── index.tsx
```

## 🧪 Testing

### Manual API Testing

```bash
cd backend
python test_api.py
```

This runs the complete flow:
1. Init session
2. Poll alignment
3. Send chat messages
4. Trigger search
5. Poll search progress
6. Reject properties
7. Trigger NPP learning
8. Resolve action

### Unit Tests

```bash
cd backend
pytest test_integration.py -v
```

Tests:
- Session creation & reset
- Tier classification
- Weight calculation
- Top 10 ranking
- Rejection flow
- NPP updates
- Topology expansion
- Mock data validation

## 📝 API Endpoint Reference

### Session Initialization
- `POST /api/v1/init_session` - Create session
- `GET /api/v1/session_ready/{session_id}` - Poll alignment

### Chat
- `POST /api/v1/chat` - Send message

### Search
- `GET /api/v1/search_status/{session_id}` - Poll progress
- `POST /api/v1/next_batch` - Fetch next batch

### Rejection
- `POST /api/v1/reject_single` - Reject one property
- `POST /api/v1/reject_all` - Reject all (trigger NPP)

### Action
- `POST /api/v1/resolve_action` - New prompt or keep memories

### Utility
- `POST /api/v1/fetch_detail` - Deep fetch property detail
- `POST /api/v1/update_requirements` - Update Phase 1 fields

## ⚙️ Configuration

### Backend Config (config.yaml)

```yaml
app:
  demo_mode: true           # Use mock data
  debug: true

llm:
  model: "deepseek-ai/DeepSeek-V3-0324"
  max_tokens: 2000
  max_concurrent_calls: 3   # Semaphore limit

scraper:
  request_delay_seconds: [2, 5]
  rotate_user_agents: true
  max_concurrent_requests: 2
  timeout_seconds: 15

search:
  budget_tolerance: 0.10          # ±10%
  batch_size: 5                   # Per batch
  max_raw_results: 50             # Scraper target
  max_expansion_level: 3

session:
  fc_trigger_max_attempts: 2
  rejection_continuity_window_seconds: 5.0
```

### Frontend Config (.env.local)

```
VITE_API_URL=http://localhost:8000
```

## 🎯 Key Constraints (Per Backend.md)

✅ **Budget hard constraint** - Python algorithm, never LLM-dependent
✅ **Tier classification before weighting** - NPP conflicts filtered first
✅ **NPP enum frozen** - 40 tags, no runtime expansion
✅ **Mock data full pipeline** - Not bypassed
✅ **Pydantic validation** - All LLM outputs validated, retry on failure
✅ **Semaphore limits** - Concurrent LLM calls controlled
✅ **Session reset** - batch_index → 1, expansion_level → 0
✅ **No auto-re-search** - Must enter ACTION_REQUIRED_UI
✅ **Internal keys only** - NPP tags use snake_case keys
✅ **Topology strict** - Admin districts only, no coordinates

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Must be 3.10+

# Check dependencies
pip list | grep fastapi

# Check .env file
cat .env  # Should have CHUTES_AI_API_KEY

# Run startup checks
python startup.py
```

### Frontend can't reach backend

```bash
# Check backend running
curl http://localhost:8000/health

# Check .env.local
cat property-agent-ui/.env.local
# Should have: VITE_API_URL=http://localhost:8000

# Restart frontend dev server
cd property-agent-ui
npm run dev
```

### LLM calls failing

```bash
# Check Chutes AI API key in .env
grep CHUTES_AI_API_KEY backend/.env

# Test with mock data first
# Set demo_mode: true in config.yaml

# Check rate limits
# Adjust max_concurrent_calls in config.yaml
```

### Tests failing

```bash
# Run startup checks
python backend/startup.py

# Run API test
python backend/test_api.py

# Run unit tests
cd backend
pytest test_integration.py -v
```

## 📚 Documentation

- **Backend.md** - Complete system specification (constraints, API contracts)
- **backend/README.md** - Backend setup & architecture
- **This file** - Complete setup guide

## 🚢 Deployment Notes

For production:

1. **Database**: Replace in-memory sessions with Redis/PostgreSQL
2. **Auth**: Add API key authentication
3. **Scraping**: Enable live scraper (disable demo_mode)
4. **Monitoring**: Add logging, error tracking
5. **CORS**: Restrict to frontend domain only
6. **Rate Limiting**: Implement per-user limits
7. **Caching**: Cache LLM responses
8. **Testing**: Run full test suite before deploy

## 📞 Support

For issues:
1. Check Backend.md for specification
2. Run `python startup.py` to validate setup
3. Run `python test_api.py` for manual testing
4. Check logs in main.py for errors
5. Verify .env has correct API credentials

