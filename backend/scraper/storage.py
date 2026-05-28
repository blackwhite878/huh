"""
Long-term CSV + temporary JSON store for scraped Mudah listings.

CSV schema is aligned 1:1 with mudah_scraper._parse_detail() output.
List / dict fields are JSON-encoded in CSV cells so commas survive
round-trips. Long-term CSV is read/written via pandas so column unions
across schema upgrades are handled automatically (no header drift).

Layout (relative to backend/):
- data/states/{region}.csv          long-term, accumulative
- tempo_data/states/{region}.json   per-session working set
- tempo_data/ranked/{session_id}.json  ranking agent output
"""
from __future__ import annotations
import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import pandas as pd

from schemas import ScrapedProperty

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR    = BACKEND_DIR / "data"     / "states"
TEMPO_DIR   = BACKEND_DIR / "tempo_data" / "states"
RANKED_DIR  = BACKEND_DIR / "tempo_data" / "ranked"

# Mirrors mudah_scraper._parse_detail() return dict (full ~80 cols).
# `listing_url` is FIRST and is the dedup key. `canonical_url` is kept
# as an alias for backward-compat with older readers.
CSV_FIELDS: List[str] = [
    # AD METADATA
    "listing_url", "canonical_url", "list_id", "title", "description",
    "posted_at", "ad_status", "is_featured", "category_name",
    # PRICING
    "price", "price_display", "currency", "price_per_sqft",
    # LOCATION
    "region", "area", "state", "full_address", "postcode",
    "latitude", "longitude",
    # PROPERTY CORE
    "transaction_type", "property_type", "property_sub_type",
    "size_sqft", "land_area", "land_area_unit",
    "bedrooms", "bathrooms", "carpark", "floor_range", "total_floors_unit",
    "furnishing", "condition", "facing_direction", "unit_type", "is_tenanted",
    # TENURE & LEGAL
    "tenure_type", "remaining_tenure", "land_title", "strata_title",
    # FINANCIAL
    "maintenance_fee", "assessment_tax", "deposit_months",
    "utility_deposit_months", "mortgage_estimate", "mortgage_rate",
    # FACILITIES & AMENITIES (Playwright-populated; may be empty in pure_fetch)
    "facilities_list", "nearby_bus_stops", "nearby_schools",
    "nearby_parks", "nearby_hospitals", "nearby_shopping",
    # DEVELOPMENT
    "development_name", "development_url", "developer",
    "completion_year", "total_floors", "total_units",
    # IMAGES
    "image_urls", "image_count",
    # SELLER / AGENT
    "seller_name", "seller_type", "seller_profile_url", "seller_logo_url",
    "ren_number", "firm_license", "is_verified", "total_ads",
    "agent_phone", "agent_whatsapp",
    # SEO
    "og_title", "og_description", "og_image", "meta_description",
    # METADATA
    "source", "scraped_at",
    # Legacy raw bag (pre-refactor CSVs may still hold this).
    "raw_attributes",
]

# Columns serialized as JSON in CSV cells.
_LIST_FIELDS = {
    "image_urls",
    "facilities_list", "nearby_bus_stops", "nearby_schools",
    "nearby_parks", "nearby_hospitals", "nearby_shopping",
}
_DICT_FIELDS = {"raw_attributes"}
_JSON_FIELDS = _LIST_FIELDS | _DICT_FIELDS

# Numeric coercion on read.
_FLOAT_FIELDS = {
    "price", "price_per_sqft", "latitude", "longitude",
    "maintenance_fee", "assessment_tax", "mortgage_estimate",
    "mortgage_rate", "land_area",
}
_INT_FIELDS = {
    "bedrooms", "bathrooms", "size_sqft", "carpark", "total_floors",
    "total_units", "completion_year", "image_count", "total_ads",
    "deposit_months", "utility_deposit_months",
}

# Backward-compat: legacy CSVs (pre-schema-extension) used these names.
_LEGACY_ALIAS: Dict[str, str] = {
    "location_area": "area",
    "city": "area",
    "built_up_sqft": "size_sqft",
    "land_sqft": "land_area",
    "tenure": "tenure_type",
    "property_type_specific": "property_sub_type",
    "agent_name": "seller_name",
}

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


def _encode_for_csv(v: Any, key: str) -> Any:
    if v is None:
        return ""
    if key in _JSON_FIELDS:
        try:
            return json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            return ""
    return v


def _decode_from_csv(v: Any, key: str) -> Any:
    # pandas NaN / empty cell → None.
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        if key in _LIST_FIELDS:
            return []
        if key in _DICT_FIELDS:
            return {}
        return None
    if key in _JSON_FIELDS and isinstance(v, str):
        try:
            return json.loads(v)
        except (TypeError, ValueError):
            # Legacy ';'-joined image_urls format.
            if key == "image_urls":
                return [x for x in v.split(";") if x]
            return [] if key in _LIST_FIELDS else {}
    if key in _FLOAT_FIELDS and isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    if key in _INT_FIELDS and isinstance(v, str):
        try:
            return int(float(v))
        except ValueError:
            return None
    if key in _FLOAT_FIELDS and isinstance(v, (int, float)) and not pd.isna(v):
        return float(v)
    if key in _INT_FIELDS and isinstance(v, (int, float)) and not pd.isna(v):
        return int(v)
    return v


def _normalize_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fold legacy column names into the canonical CSV_FIELDS names."""
    rename: Dict[str, str] = {}
    for old, new in _LEGACY_ALIAS.items():
        if old in df.columns and new not in df.columns:
            rename[old] = new
    if rename:
        df = df.rename(columns=rename)
    # canonical_url ←→ listing_url backfill (old CSVs only had canonical_url).
    if "canonical_url" in df.columns and "listing_url" not in df.columns:
        df["listing_url"] = df["canonical_url"]
    elif "listing_url" in df.columns and "canonical_url" not in df.columns:
        df["canonical_url"] = df["listing_url"]
    return df


def _read_csv_df(p: Path) -> pd.DataFrame:
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame(columns=CSV_FIELDS)
    # Read everything as string; we decode types ourselves.
    df = pd.read_csv(p, dtype=str, keep_default_na=False, na_values=[""])
    return _normalize_alias_columns(df)


def load_longterm(region: str) -> List[Dict]:
    df = _read_csv_df(csv_path(region))
    if df.empty:
        return []
    cols = list(df.columns)
    out: List[Dict] = []
    for rec in df.to_dict(orient="records"):
        out.append({k: _decode_from_csv(rec.get(k), k) for k in cols})
    return out


def longterm_count(region: str) -> int:
    p = csv_path(region)
    if not p.exists() or p.stat().st_size == 0:
        return 0
    # Lightweight: count lines minus header.
    with p.open("r", encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def append_longterm(region: str, rows: Iterable[Dict]) -> int:
    """Append rows to long-term CSV, deduped by listing_url. Uses pandas so
    column unions across schema upgrades are handled (old narrow CSVs gain
    new columns without truncation; new wide rows preserve every field)."""
    new_records: List[Dict] = []
    seen_in_batch: set = set()
    for r in rows:
        url = r.get("listing_url") or r.get("canonical_url")
        if not url or url in seen_in_batch:
            continue
        seen_in_batch.add(url)
        # Mirror the URL into both keys for downstream compat.
        rec = dict(r)
        rec.setdefault("listing_url", url)
        rec.setdefault("canonical_url", url)
        new_records.append(rec)
    if not new_records:
        return 0

    p = csv_path(region)
    with _write_lock:
        existing = _read_csv_df(p)
        existing_urls: set = (
            set(existing["listing_url"].dropna().tolist())
            if "listing_url" in existing.columns else set()
        )
        truly_new = [r for r in new_records if r["listing_url"] not in existing_urls]
        if not truly_new:
            return 0

        new_df = pd.DataFrame(
            [{k: _encode_for_csv(r.get(k), k) for k in CSV_FIELDS} for r in truly_new]
        )
        if existing.empty:
            merged = new_df
        else:
            # Union columns; CSV_FIELDS order first, then any extras.
            all_cols = list(dict.fromkeys(CSV_FIELDS + list(existing.columns)))
            existing = existing.reindex(columns=all_cols, fill_value="")
            new_df = new_df.reindex(columns=all_cols, fill_value="")
            merged = pd.concat([existing, new_df], ignore_index=True)

        # Defensive dedup (pandas-arranged: keep last, stable sort by region+price).
        merged = merged.drop_duplicates(subset=["listing_url"], keep="last")
        if "region" in merged.columns:
            merged = merged.sort_values(
                by=["region", "listing_url"], kind="stable", na_position="last"
            ).reset_index(drop=True)

        merged.to_csv(p, index=False, encoding="utf-8")
        return len(truly_new)


# ─── tempo JSON ────────────────────────────────────────────────────
def tempo_path(region: str, session_id: str) -> Path:
    _ensure_dirs()
    return TEMPO_DIR / f"{region}__{session_id}.json"


def write_tempo(region: str, session_id: str, rows: List[Union[ScrapedProperty, Dict[str, Any]]]) -> Path:
    p = tempo_path(region, session_id)
    serialized = [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in rows]
    with _write_lock, p.open("w", encoding="utf-8") as f:
        json.dump({"region": region, "session_id": session_id, "rows": serialized},
                  f, ensure_ascii=False, indent=2)
    return p


def append_tempo(region: str, session_id: str, rows: List[Dict]) -> int:
    """Append scraped dict rows into the session tempo JSON, dedup by URL."""
    existing = read_tempo(region, session_id)
    existing_urls = {r.get("listing_url") or r.get("canonical_url")
                     for r in existing if (r.get("listing_url") or r.get("canonical_url"))}
    merged: List[Dict] = list(existing)
    added = 0
    seen_in_batch: set = set()
    for r in rows:
        d = r if isinstance(r, dict) else r.model_dump()
        url = d.get("listing_url") or d.get("canonical_url")
        if not url or url in existing_urls or url in seen_in_batch:
            continue
        seen_in_batch.add(url)
        merged.append(d)
        added += 1
    if added:
        write_tempo(region, session_id, merged)
    return added


def read_tempo(region: str, session_id: str) -> List[Dict]:
    p = tempo_path(region, session_id)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows", []) or []
    return [r for r in rows if isinstance(r, dict)]


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
