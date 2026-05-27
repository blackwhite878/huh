# Property Agent UI

An AI-powered Malaysian property search agent. Describe what you want, the agent profiles your needs through conversation, scrapes live listings from [Mudah.my](https://www.mudah.my), classifies and ranks them, then walks you through a shortlist — all in a chat-style UI.

---

## Architecture

```
property-agent-ui/        ← React 19 + TanStack Router (Vite)
backend/
  main.py                 ← FastAPI — all REST endpoints
  llm_client.py           ← Chutes AI client (DeepSeek-V3, Llama, Qwen)
  search_pipeline.py      ← Scrape → tier classify → weight → remarks
  scraper/                ← Mudah.my async scraper (Playwright + BS4)
  session_manager.py      ← In-memory session state
  topology.py             ← Malaysian district/region graph
  config.yaml             ← LLM model + scraper config
```

**LLM:** [Chutes AI](https://chutes.ai) — OpenAI-compatible, hosts DeepSeek-V3, Llama 3.1, Qwen 2.5  
**Scraper mode:** `realtime` (live Mudah.my) or `demo` (bundled CSV — no API key needed)

---

## Prerequisites

| Tool    | Version |
|---------|---------|
| Python  | 3.10+   |
| Node.js | 18+     |
| npm     | 9+      |

---

## Setup

### 1 — Get a Chutes AI API key

1. Sign up at <https://chutes.ai>
2. Generate an API key from your dashboard

> Skip this if you only want to run in **demo mode** — no key required.

---

### 2 — Clone

```bash
git clone --depth 1 https://github.com/MAXAJIE/wsdfc.git
cd wsdfc
```

---

### 3 — Backend

#### macOS / Linux

```bash
cd backend

python3 -m venv venv
source venv/bin/activate

pip install -r ../requirements.txt
playwright install chromium

cp .env.example .env
# Open .env and add your key:
# CHUTES_AI_API_KEY=your-key-here
```

#### Windows

```cmd
cd backend

python -m venv venv
venv\Scripts\activate.bat

pip install -r ..\requirements.txt
playwright install chromium

copy .env.example .env
REM Open .env and add your key:
REM CHUTES_AI_API_KEY=your-key-here
```

#### `.env` reference

```
CHUTES_AI_API_KEY=your-key-here
CHUTES_AI_BASE_URL=https://llm.chutes.ai/v1
APP_SECRET_KEY=change-me-in-production
```

---

### 4 — Demo mode (no API key, no scraping)

In `backend/config.yaml`, set:

```yaml
scraper:
  mode: "demo"
```

The backend serves bundled mock listings and the UI shows a degradation popup. Good for local development and UI work.

---

### 5 — Run the backend

```bash
# Inside backend/ with venv active
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

---

### 6 — Run the frontend

Open a **new terminal** from the repo root:

```bash
cd property-agent-ui
npm install
npm run dev
```

Open **http://localhost:5173**

The Vite dev proxy already points to `http://localhost:8000` — no extra config needed.

---

### 7 — Quick-start scripts (optional)

These scripts handle venv creation, dependency install, and env checks in one step.

**macOS / Linux:**
```bash
bash backend/start.sh
```

**Windows:**
```cmd
backend\start.bat
```

Then run the frontend separately (Step 6).

---

## Realtime mode notes

Set `mode: "realtime"` in `config.yaml` to scrape live listings.

**Recommended for testing:** choose **Johor Bahru, Johor** as your location — it's the best-supported region. Scraping other regions may be slow or incomplete.

Watch the backend console for scraper progress:

```
[scrape] list region=johor type=condo page=1 extracted=40 new=40 (running_total=40)
[scrape] list region=johor type=condo page=2 extracted=41 new=41 (running_total=81)
[scrape] region=johor url=https://www.mudah.my/... title='...' price=550000.0 bedrooms=4
```

If the scraper fails three consecutive times it auto-degrades to demo mode and the UI shows a popup.

---

## User flow

1. **Phase 1** — set budget, describe your target, pick buyer identity and agent style
2. **Alignment** — LLM extracts structured preference tags from your free-text description
3. **Conversation** — agent asks clarifying questions; detects and resolves preference conflicts
4. **Search** — pipeline scrapes Mudah.my, classifies listings into Tier 1/2, applies dynamic weights, generates per-property AI remarks
5. **Results** — two batches of 5 listings; reject individually or all at once
6. **Resolution** — on full rejection, choose "refine search" (full reset) or "keep memories" (soft reset, NPP tags preserved)

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/init_session` | Start session with Phase 1 data |
| `GET`  | `/api/v1/session_ready/{id}` | Poll semantic alignment status |
| `POST` | `/api/v1/chat` | Send a chat message |
| `GET`  | `/api/v1/search_status/{id}` | Poll search pipeline progress |
| `POST` | `/api/v1/next_batch` | Fetch second batch of results |
| `POST` | `/api/v1/reject_single` | Reject one listing |
| `POST` | `/api/v1/reject_all` | Reject all, trigger NPP learning |
| `POST` | `/api/v1/resolve_action` | Choose next step after full rejection |
| `GET`  | `/api/v1/system_status` | Scraper health + demo/degraded flags |

**Example — init session:**

```bash
curl -X POST http://localhost:8000/api/v1/init_session \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 500000,
    "agent_style": "Professional",
    "target": "condo in Johor Bahru",
    "identity": "first_time_buyer",
    "gender": "female",
    "description": "Looking for a family home near good schools, prefer gated community"
  }'
```

---

## Configuration

`backend/config.yaml`:

```yaml
llm:
  model: deepseek-ai/DeepSeek-V3.2-TEE   # main dialogue model
  max_tokens: 2000
  concurrency: 3                           # max parallel LLM calls

scraper:
  mode: "demo"              # "realtime" | "demo"
  retries: 3
  realtime_budget_seconds: 90
```

Optional environment variable overrides:

```bash
REMARKS_MODEL=chutesai/Llama-3.1-8B-Instruct
REASONING_MODEL=Qwen/Qwen2.5-7B-Instruct
REMARKS_MAX_TOKENS=512
REMARKS_CONCURRENCY=8
```

---

## Project structure

```
wsdfc/
├── requirements.txt
├── backend/
│   ├── .env.example
│   ├── config.yaml
│   ├── main.py
│   ├── llm_client.py
│   ├── search_pipeline.py
│   ├── session_manager.py
│   ├── schemas.py
│   ├── topology.py
│   ├── weighting.py
│   ├── mock_data.py
│   ├── npp_enum.py
│   ├── positive_enum.py
│   ├── startup.py
│   ├── start.sh / start.bat
│   └── scraper/
│       ├── mudah_scraper.py
│       ├── pipeline.py
│       ├── seeder.py
│       ├── storage.py
│       └── live_filter.py
└── property-agent-ui/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── routes/
        ├── components/
        ├── hooks/
        └── lib/
```

---

## Troubleshooting

**Backend won't start — missing `.env`**
```bash
cp backend/.env.example backend/.env
# Add CHUTES_AI_API_KEY
```

**`playwright install` not found**  
Make sure your venv is active, then run:
```bash
playwright install chromium
```

**Live scrape always falls back to demo**  
Mudah.my may be rate-limiting headless requests. Try increasing `realtime_budget_seconds` in `config.yaml`, or switch to `mode: "demo"` for development.

**CORS errors in the browser**  
Confirm the backend is on port `8000` and the frontend dev server is on port `5173`. The FastAPI CORS middleware allows all origins in this build.

**`python` not found on macOS / Linux**  
Use `python3`. The `start.sh` script handles this automatically.

---

## License

See repository for license details.
