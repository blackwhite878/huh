# Mudah.my Scraper Subsystem

Lean async scraper bolted onto the existing FastAPI backend, with long-term CSV + per-session JSON cache and an LLM-weighted ranking agent.

## Layout

```
backend/
├── data/states/{region}.csv                 long-term, append-only, deduped by listing_url
├── tempo_data/states/{region}__{sid}.json   per-session working set (cleared on FastAPI start & on session end)
├── tempo_data/ranked/{sid}.json             ranking agent output: top-10 + weights + dimensions
└── scraper/
    ├── types_quota.py        16 Malaysian regions, type quotas
    ├── storage.py            CSV + tempo JSON IO
    ├── mudah_scraper.py      httpx + BS4 (Playwright fallback) for Mudah.my
    ├── seeder.py             ensure_region + retry-then-demo orchestrator
    ├── ranking_agent.py      hybrid LLM-multiplier + deterministic math top-10
    └── pipeline.py           glue: config → fetch → rank
```

## Modes (`config.yaml`)

```yaml
scraper:
  mode: demo        # demo | realtime
```

- **demo**: read `data/states/{region}.csv` into `tempo_data/...`, then rank.
- **realtime**: scrape Mudah.my live. On three consecutive failures, switches to demo and sets `forced_demo=true` on `/api/v1/system_status` so the frontend can show a popup.

## Quota (sum = 100 per region)

| Type | Count |
|---|---|
| condo | 30 |
| double-storey | 25 |
| single-storey | 15 |
| bungalow | 10 |
| apartment | 10 |
| townhouse | 10 |

Back-fill policy (A): when one type cannot reach its quota, the deficit is back-filled by other types based on remaining headroom. If a region's CSV already contains MAX=100 rows, the seeder skips that region entirely (no overwrite).

## Lifecycle

- FastAPI startup wipes `tempo_data/` (matches the "LLM memory / NPP / PPP" reset rule).
- A search call → `pipeline.run_pipeline(session_id, brief)` → ranked payload + `forced_demo` flag.
- Frontend reads `GET /api/v1/system_status` for the popup gate.

## CLI seeding

```bash
python -m backend.scraper.cli seed                       # seed all 16 regions
python -m backend.scraper.cli seed --region johor        # seed one
python -m backend.scraper.cli status                     # list per-region row counts
```
