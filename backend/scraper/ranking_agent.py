"""
Ranking agent.

Reads a tempo JSON dataset (per-session, possibly merged across regions),
asks the LLM to produce semantic weight multipliers based on the user's
phase1 brief, then runs a deterministic math scorer and writes a top-10
ranked JSON to tempo_data/ranked/{session_id}.json.

Weight model = hybrid:
  final_weights = normalize( BASE * LLM_multipliers )

LLM only proposes 0.5–1.5x multipliers on a fixed dimension list. The math
scoring stays inside this module so weights cannot leak unbounded influence.
"""
from __future__ import annotations
import json
import logging
import math
from typing import Dict, List, Optional

from . import storage

logger = logging.getLogger(__name__)

# Scoring dimensions (must match keys produced below in _score_one).
DIMENSIONS = [
    "price_fit",
    "location_fit",
    "type_fit",
    "size_fit",
    "recency_fit",
    "description_fit",
]

BASE_WEIGHTS: Dict[str, float] = {
    "price_fit":       0.30,
    "location_fit":    0.20,
    "type_fit":        0.20,
    "size_fit":        0.10,
    "recency_fit":     0.05,
    "description_fit": 0.15,
}
assert abs(sum(BASE_WEIGHTS.values()) - 1.0) < 1e-9


def _norm(weights: Dict[str, float]) -> Dict[str, float]:
    s = sum(weights.values())
    if s <= 0:
        return BASE_WEIGHTS.copy()
    return {k: v / s for k, v in weights.items()}


def _clip(x: float, lo: float = 0.5, hi: float = 1.5) -> float:
    return max(lo, min(hi, x))


# ── deterministic math scoring ───────────────────────────────────────
def _score_one(row: Dict, brief: Dict) -> Dict[str, float]:
    """Per-property dimension scores ∈ [0,1]."""
    # price fit: Gaussian around target budget
    budget = float(brief.get("budget") or 0)
    price = row.get("price")
    try:
        price = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price = None
    if budget > 0 and price is not None:
        diff_ratio = abs(price - budget) / budget
        price_fit = math.exp(-(diff_ratio ** 2) / 0.18)
    else:
        price_fit = 0.0

    target_text = (brief.get("target") or "").lower()
    desc = (row.get("description") or "").lower()
    title = (row.get("title") or "").lower()
    type_key = (row.get("property_type") or "").lower()
    region = (row.get("region") or "").lower()

    # location fit: target string contains region/area tokens
    loc_area = (row.get("location") or "").lower()
    location_fit = 0.0
    for token in {region, loc_area, *target_text.split()}:
        if token and len(token) > 2 and token in target_text:
            location_fit = max(location_fit, 1.0 if token == region else 0.7)

    # type fit
    type_fit = 1.0 if type_key and type_key.replace("-", " ") in target_text else 0.3

    # size fit: prefer >= 800 sqft, capped
    sqft = row.get("built_up_sqft")
    try:
        sqft_v = float(sqft) if sqft else 0
    except (TypeError, ValueError):
        sqft_v = 0
    size_fit = min(1.0, sqft_v / 1500.0) if sqft_v > 0 else 0.0

    # recency: rows lack reliable posted_at → fall back to scraped_at proxy 0.5
    recency_fit = 0.5

    # description fit: keyword overlap with target + positive description length
    target_tokens = {t for t in target_text.split() if len(t) > 3}
    hits = sum(1 for t in target_tokens if t in desc or t in title)
    description_fit = min(1.0, hits / max(1, len(target_tokens))) if target_tokens else 0.3
    if desc:
        description_fit = max(description_fit, min(1.0, len(desc) / 1500.0) * 0.6)

    return {
        "price_fit": price_fit,
        "location_fit": location_fit,
        "type_fit": type_fit,
        "size_fit": size_fit,
        "recency_fit": recency_fit,
        "description_fit": description_fit,
    }


def _weighted(score: Dict[str, float], w: Dict[str, float]) -> float:
    return sum(score[k] * w[k] for k in DIMENSIONS)


# ── optional LLM multiplier producer ─────────────────────────────────
async def _llm_multipliers(brief: Dict) -> Dict[str, float]:
    """
    Asks the existing llm_client for per-dimension multipliers in [0.5, 1.5].
    Falls back to all-1.0 on any error.
    """
    default = {k: 1.0 for k in DIMENSIONS}
    try:
        from llm_client import llm_client  # type: ignore
    except Exception as e:
        logger.info("[rank] llm_client unavailable (%s); using uniform multipliers", e)
        return default

    system_msg = (
        "You are weighting Malaysian property-listing scoring dimensions. "
        "Output ONLY a JSON object with exactly these numeric keys: "
        + ", ".join(DIMENSIONS)
        + ". Every value MUST be a number in [0.5, 1.5]. No prose."
    )
    user_msg = "Buyer brief:\n" + json.dumps(brief, ensure_ascii=False)
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ]

    try:
        parsed = await llm_client.complete_json(messages)
    except Exception as e:
        logger.warning("[rank] LLM multiplier call failed: %s", e)
        return default

    if not isinstance(parsed, dict):
        return default
    out: Dict[str, float] = {}
    for k in DIMENSIONS:
        v = parsed.get(k, 1.0)
        try:
            out[k] = _clip(float(v))
        except (TypeError, ValueError):
            out[k] = 1.0
    return out


# ── public entry ─────────────────────────────────────────────────────
async def rank_top10(session_id: str, brief: Dict, regions: List[str]) -> Dict:
    """
    Aggregate tempo rows across regions, run hybrid scoring, write ranked json.
    `brief` is a serializable phase1 dict.
    """
    pool: List[Dict] = []
    for region in regions:
        pool.extend(storage.read_tempo(region, session_id))

    if not pool:
        payload = {"session_id": session_id, "weights": BASE_WEIGHTS, "top10": []}
        storage.write_ranked(session_id, payload)
        return payload

    multipliers = await _llm_multipliers(brief)
    final_w = _norm({k: BASE_WEIGHTS[k] * multipliers.get(k, 1.0) for k in DIMENSIONS})

    scored = []
    for row in pool:
        s = _score_one(row, brief)
        scored.append({
            "score": _weighted(s, final_w),
            "dimensions": s,
            "listing": row,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    top10 = scored[:10]

    payload = {
        "session_id": session_id,
        "weights_base": BASE_WEIGHTS,
        "weights_multipliers": multipliers,
        "weights_final": final_w,
        "pool_size": len(pool),
        "top10": top10,
    }
    storage.write_ranked(session_id, payload)
    return payload
