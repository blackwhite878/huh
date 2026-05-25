"""
Long-term CSV + temporary JSON store for scraped Mudah listings.

Layout (relative to backend/):
- data/states/{region}.csv          long-term, accumulative, never overwritten
                                    when already at MAX_PER_REGION; otherwise
                                    appended (deduped by listing url).
- tempo_data/states/{region}.json   per-session working set. Cleared on
                                    FastAPI startup AND when session ends.
- tempo_data/ranked/{session_id}.json  ranking agent output (top10).

CSV columns are kept stable for downstream Pydantic schema mapping.
"""
from __future__ import annotations
import csv
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Resolve paths relative to backend/ (this file lives in backend/scraper/).
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR    = BACKEND_DIR / "data"     / "states"
TEMPO_DIR   = BACKEND_DIR / "tempo_data" / "states"
RANKED_DIR  = BACKEND_DIR / "tempo_data" / "ranked"

CSV_FIELDS: List[str] = [
    "listing_url", "source", "scraped_at",
    "title", "price", "currency",
    "property_type", "region",
    "location_area", "city",
    "bedrooms", "bathrooms",
    "built_up_sqft", "land_sqft",
    "tenure", "furnishing",
    "agent_name", "agent_phone",
    "posted_at",
    "description",
    "image_urls",   # ';'-joined
]

_write_lock = threading.Lock()


def _ensure_dirs() -> None:
    for d in (DATA_DIR, TEMPO_DIR, RANKED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def clear_all_tempo() -> None:
    """Wipe tempo_data/. Called on FastAPI startup."""
    tempo_root = BACKEND_DIR / "tempo_data"
    if tempo_root.exists():
        shutil.rmtree(tempo_root, ignore_errors=True)
    _ensure_dirs()


def clear_session_tempo(session_id: str) -> None:
    """Wipe a single session's tempo + ranked files."""
    _ensure_dirs()
    for region_file in TEMPO_DIR.glob(f"*__{session_id}.json"):
        region_file.unlink(missing_ok=True)
    ranked = RANKED_DIR / f"{session_id}.json"
    ranked.unlink(missing_ok=True)


# ─── long-term CSV ─────────────────────────────────────────────────
def csv_path(region: str) -> Path:
    _ensure_dirs()
    return DATA_DIR / f"{region}.csv"


def load_longterm(region: str) -> List[Dict]:
    p = csv_path(region)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def longterm_count(region: str) -> int:
    return len(load_longterm(region))


def append_longterm(region: str, rows: Iterable[Dict]) -> int:
    """Append rows, deduped by listing_url. Returns rows actually written."""
    p = csv_path(region)
    existing_urls = {r["listing_url"] for r in load_longterm(region)}
    new_rows = [r for r in rows if r.get("listing_url") and r["listing_url"] not in existing_urls]
    if not new_rows:
        return 0
    file_exists = p.exists()
    with _write_lock, p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if not file_exists:
            w.writeheader()
        for r in new_rows:
            # normalise list → ';'-joined
            if isinstance(r.get("image_urls"), list):
                r = {**r, "image_urls": ";".join(r["image_urls"])}
            w.writerow(r)
    return len(new_rows)


# ─── tempo JSON (session-scoped working set) ───────────────────────
def tempo_path(region: str, session_id: str) -> Path:
    _ensure_dirs()
    return TEMPO_DIR / f"{region}__{session_id}.json"


def write_tempo(region: str, session_id: str, rows: List[Dict]) -> Path:
    p = tempo_path(region, session_id)
    with _write_lock, p.open("w", encoding="utf-8") as f:
        json.dump({"region": region, "session_id": session_id, "rows": rows}, f, ensure_ascii=False, indent=2)
    return p


def read_tempo(region: str, session_id: str) -> List[Dict]:
    p = tempo_path(region, session_id)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rows", [])


# ─── ranked JSON (top-10 output of ranking agent) ──────────────────
def ranked_path(session_id: str) -> Path:
    _ensure_dirs()
    return RANKED_DIR / f"{session_id}.json"


def write_ranked(session_id: str, payload: Dict) -> Path:
    p = ranked_path(session_id)
    with _write_lock, p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


def read_ranked(session_id: str) -> Optional[Dict]:
    p = ranked_path(session_id)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
