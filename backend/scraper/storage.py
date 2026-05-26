"""
Long-term CSV + temporary JSON store for scraped Mudah listings.

Storage format is aligned 1:1 with mudah_scraper._parse_detail() output
(see schemas.ScrapedProperty). Every field returned by the scraper is
persisted; list and dict fields are JSON-serialized in CSV cells so no
information is lost on round-trip.

Layout (relative to backend/):
- data/states/{region}.csv          long-term, accumulative
- tempo_data/states/{region}.json   per-session working set
- tempo_data/ranked/{session_id}.json  ranking agent output
"""
from __future__ import annotations
import csv
import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from schemas import ScrapedProperty

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR    = BACKEND_DIR / "data"     / "states"
TEMPO_DIR   = BACKEND_DIR / "tempo_data" / "states"
RANKED_DIR  = BACKEND_DIR / "tempo_data" / "ranked"

# Mirrors schemas.ScrapedProperty / mudah_scraper._parse_detail output.
CSV_FIELDS: List[str] = [
    "listing_url", "list_id", "source", "scraped_at",
    "title", "price", "currency",
    "property_type", "category_name",
    "region", "location_area", "city",
    "bedrooms", "bathrooms",
    "built_up_sqft", "land_sqft",
    "tenure", "furnishing",
    "land_title", "property_type_specific",
    "agent_name", "agent_phone",
    "posted_at",
    "description",
    "image_urls",      # JSON-encoded list
    "raw_attributes",  # JSON-encoded dict (dynamic Mudah parameters)
]

_LIST_FIELDS = {"image_urls"}
_JSON_FIELDS = {"image_urls", "raw_attributes"}

_write_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _ensure_dirs() -> None:
    for d in (DATA_DIR, TEMPO_DIR, RANKED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def clear_all_tempo() -> None:
    tempo_root = BACKEND_DIR / "tempo_data"
    if tempo_root.exists():
        shutil.rmtree(tempo_root, ignore_errors=True)
    _ensure_dirs()


def clear_session_tempo(session_id: str) -> None:
    _ensure_dirs()
    for region_file in TEMPO_DIR.glob(f"*__{session_id}.json"):
        region_file.unlink(missing_ok=True)
    ranked = RANKED_DIR / f"{session_id}.json"
    ranked.unlink(missing_ok=True)


# ─── long-term CSV ─────────────────────────────────────────────────
def csv_path(region: str) -> Path:
    _ensure_dirs()
    return DATA_DIR / f"{region}.csv"


def _row_for_csv(r: Dict) -> Dict:
    out: Dict = {}
    for k in CSV_FIELDS:
        v = r.get(k)
        if v is None:
            out[k] = ""
            continue
        if k in _JSON_FIELDS:
            # Always JSON-encode lists/dicts so commas/semicolons survive.
            try:
                out[k] = json.dumps(v, ensure_ascii=False)
            except (TypeError, ValueError):
                out[k] = ""
        else:
            out[k] = v
    unknown = [k for k in r.keys() if k not in CSV_FIELDS]
    if unknown:
        logger.debug("append_longterm: dropping unknown fields %s", unknown)
    return out


def _row_from_csv(r: Dict) -> Dict:
    out: Dict[str, Any] = dict(r)
    for k in _JSON_FIELDS:
        v = out.get(k)
        if not v:
            out[k] = [] if k in _LIST_FIELDS else {}
            continue
        if isinstance(v, str):
            try:
                out[k] = json.loads(v)
            except (TypeError, ValueError):
                # Backward-compat with the old ';'-joined image_urls format.
                if k == "image_urls":
                    out[k] = [x for x in v.split(";") if x]
                else:
                    out[k] = {}
    # Coerce numerics so downstream scorers don't need to.
    for num_k in ("price",):
        v = out.get(num_k)
        if isinstance(v, str) and v:
            try: out[num_k] = float(v)
            except ValueError: out[num_k] = None
        elif v == "":
            out[num_k] = None
    for int_k in ("bedrooms", "bathrooms", "built_up_sqft", "land_sqft"):
        v = out.get(int_k)
        if isinstance(v, str) and v:
            try: out[int_k] = int(float(v))
            except ValueError: out[int_k] = None
        elif v == "":
            out[int_k] = None
    return out


def load_longterm(region: str) -> List[Dict]:
    p = csv_path(region)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", newline="") as f:
        return [_row_from_csv(r) for r in csv.DictReader(f)]


def longterm_count(region: str) -> int:
    return len(load_longterm(region))


def append_longterm(region: str, rows: Iterable[Dict]) -> int:
    p = csv_path(region)
    existing_urls = {r["listing_url"] for r in load_longterm(region)}
    new_rows: List[Dict] = []
    seen_in_batch: set = set()
    for r in rows:
        url = r.get("listing_url")
        if not url or url in existing_urls or url in seen_in_batch:
            continue
        seen_in_batch.add(url)
        new_rows.append(r)
    if not new_rows:
        return 0
    file_exists = p.exists() and p.stat().st_size > 0
    with _write_lock, p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if not file_exists:
            w.writeheader()
        for r in new_rows:
            w.writerow(_row_for_csv(r))
    return len(new_rows)


# ─── tempo JSON ────────────────────────────────────────────────────
def tempo_path(region: str, session_id: str) -> Path:
    _ensure_dirs()
    return TEMPO_DIR / f"{region}__{session_id}.json"


def write_tempo(region: str, session_id: str, rows: List[ScrapedProperty]) -> Path:
    p = tempo_path(region, session_id)
    serialized = [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in rows]
    with _write_lock, p.open("w", encoding="utf-8") as f:
        json.dump({"region": region, "session_id": session_id, "rows": serialized},
                  f, ensure_ascii=False, indent=2)
    return p


def append_tempo(region: str, session_id: str, rows: List[ScrapedProperty]) -> int:
    existing = read_tempo(region, session_id)
    existing_urls = {r.get("listing_url") for r in existing if r.get("listing_url")}
    merged = list(existing)
    added = 0
    seen_in_batch: set = set()
    for r in rows:
        url = r.listing_url  # Access directly from ScrapedProperty
        if not url or url in existing_urls or url in seen_in_batch:
            continue
        seen_in_batch.add(url)
        merged.append(r.model_dump()) # Append dict representation
        added += 1
    if added:
        write_tempo(region, session_id, [ScrapedProperty(**r) for r in merged]) # Re-validate on write
    return added


def read_tempo(region: str, session_id: str) -> List[ScrapedProperty]:
    p = tempo_path(region, session_id)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [ScrapedProperty(**r) for r in data.get("rows", [])]


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
