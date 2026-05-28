"""
Live-mode scrape filter builder.

Goal: when the scraper is running in `realtime` mode, only request listings
that fit the *current* user brief. We DO NOT add new fields to Phase1Data;
instead we derive the filter at scrape time from data the backend already
holds:

  - phase1_data.target / description  (free text, EN/MS/CN)
  - dialogue_history user turns        (Phase 2 deep consultation)
  - semantic_tags (NPP-style negative) / positive_tags (PPP)
  - npp_session.npp_tags
  - search_session.current_budget_range  (= phase1.budget ± 10%)

Output (all keys optional — caller treats None as "do not attach"):
  {
    "house_type":  <TYPE_QUOTA key | None>,   # condo / double-storey / ...
    "keyword":     <Mudah `q=` keyword | None>,
    "bedrooms":    <int | None>,
    "min_price":   <float | None>,
    "max_price":   <float | None>,
  }

Strategy:
  1. Regex pass over the combined text (deterministic, no network).
  2. LLM augment via llm_client.complete_json when regex left holes.
     LLM failure is non-fatal; we keep regex output.
  3. Budget is ALWAYS sourced from search_session.current_budget_range
     (per user spec). LLM is NEVER asked to invent a budget range.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from .types_quota import TYPE_QUOTA, TYPE_SEARCH_KEYWORD

logger = logging.getLogger(__name__)

# ── house_type alias table (EN / MS / CN → TYPE_QUOTA key) ───────────
_HOUSE_TYPE_ALIASES: Dict[str, List[str]] = {
    "condo":          ["condo", "condominium", "服务式公寓", "服務式公寓", "高级公寓", "高級公寓"],
    "apartment":      ["apartment", "apt", "公寓", "组屋", "組屋", "flat"],
    "double-storey":  ["double storey", "double-storey", "2-storey", "two storey",
                       "双层", "雙層", "double storey terrace"],
    "single-storey":  ["single storey", "single-storey", "1-storey", "one storey",
                       "single storey terrace", "单层", "單層"],
    "bungalow":       ["bungalow", "banglo", "洋房", "独立式", "獨立式"],
    "townhouse":      ["townhouse", "town house", "排屋", "联排别墅", "聯排別墅"],
}

_BEDROOM_PATTERNS = [
    # 3 bedroom / 3-bedroom / 3 bed / 3br / 3 rooms / 三房 / 3房
    re.compile(r"(\d{1,2})\s*(?:bed(?:room)?s?|br|rooms?|房间|房間|房)\b", re.I),
    re.compile(r"([一二三四五六七八九十]+)\s*(?:房间|房間|房)"),
]
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _regex_house_type(text: str) -> Optional[str]:
    t = text.lower()
    # Longest alias wins to avoid "apartment" matching inside "service apartment".
    best: tuple[int, Optional[str]] = (0, None)
    for key, aliases in _HOUSE_TYPE_ALIASES.items():
        for a in aliases:
            if a in t and len(a) > best[0]:
                best = (len(a), key)
    return best[1]


_CARPARK_RE = re.compile(r"(?:car\s*park|parking|carpark|停車|停车)", re.I)


def _regex_carpark(text: str) -> bool:
    return bool(_CARPARK_RE.search(text or ""))


def _regex_bedrooms(text: str) -> Optional[int]:
    for pat in _BEDROOM_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        raw = m.group(1)
        if raw.isdigit():
            n = int(raw)
        else:
            n = _CN_NUM.get(raw[-1], 0)
        if 1 <= n <= 15:
            return n
    return None


def _gather_text(session_id: str) -> str:
    """Concatenate all user-derived text the LLM/regex should consider."""
    try:
        from session_manager import (
            get_dialogue_session, get_npp_session,
        )
    except Exception as e:  # pragma: no cover
        logger.error("[live_filter] session_manager import failed: %s", e)
        return ""

    ds = get_dialogue_session(session_id)
    if ds is None:
        return ""

    parts: List[str] = []
    p1 = ds.phase1_data
    if p1.target:      parts.append(p1.target)
    if p1.description: parts.append(p1.description)
    if p1.semantic_tags:  parts.append(" ".join(p1.semantic_tags))
    if p1.positive_tags:  parts.append(" ".join(p1.positive_tags))

    nps = get_npp_session(session_id)
    if nps and nps.npp_tags:
        parts.append(" ".join(nps.npp_tags))

    for msg in ds.dialogue_history:
        if msg.role == "user" and msg.content:
            parts.append(msg.content)

    return "\n".join(parts)


def _budget_range(session_id: str) -> tuple[Optional[float], Optional[float]]:
    try:
        from session_manager import get_search_session
    except Exception:  # pragma: no cover
        return (None, None)
    ss = get_search_session(session_id)
    if not ss:
        return (None, None)
    rng = ss.current_budget_range or {}
    lo = rng.get("min")
    hi = rng.get("max")
    try:
        lo_f = float(lo) if lo not in (None, 0) else None
    except (TypeError, ValueError):
        lo_f = None
    try:
        hi_f = float(hi) if hi not in (None, 0) else None
    except (TypeError, ValueError):
        hi_f = None
    return (lo_f, hi_f)


async def _llm_augment(text: str, regex_hint: Dict[str, Any]) -> Dict[str, Any]:
    """Ask LLM to fill in the holes regex left. Failure → return {}."""
    if not text.strip():
        return {}
    try:
        from llm_client import llm_client  # type: ignore
    except Exception as e:
        logger.info("[live_filter] llm_client unavailable (%s)", e)
        return {"_degraded": True}

    allowed = list(TYPE_QUOTA.keys())
    system = (
        "You extract a Malaysian property-search filter from the buyer's free text. "
        "Reply with ONLY a JSON object with EXACTLY these keys: house_type, bedrooms. "
        f"`house_type` MUST be one of {allowed} or null. "
        "`bedrooms` MUST be an integer 1-15 or null. "
        "If a value is not clearly stated, use null. No prose, no extra keys."
    )
    user = (
        "Regex already extracted: "
        + str({k: v for k, v in regex_hint.items() if v is not None})
        + "\n\nBuyer text:\n" + text[:4000]
    )
    try:
        parsed = await llm_client.complete_json(
            [{"role": "system", "content": system},
             {"role": "user",   "content": user}]
        )
    except Exception as e:
        logger.warning("[live_filter] LLM call failed: %s", e)
        return {"_degraded": True}
    if not isinstance(parsed, dict):
        return {}

    out: Dict[str, Any] = {}
    ht = parsed.get("house_type")
    if isinstance(ht, str) and ht in TYPE_QUOTA:
        out["house_type"] = ht
    br = parsed.get("bedrooms")
    if isinstance(br, (int, float)):
        n = int(br)
        if 1 <= n <= 15:
            out["bedrooms"] = n
    return out


async def build_live_filter(session_id: str) -> Dict[str, Any]:
    """
    Compose the live-mode filter dict. Missing values → key absent (partial fill).
    """
    text = _gather_text(session_id)

    regex_hint: Dict[str, Any] = {
        "house_type": _regex_house_type(text) if text else None,
        "bedrooms":   _regex_bedrooms(text)   if text else None,
        "carpark":    _regex_carpark(text)    if text else False,
    }

    llm_hint: Dict[str, Any] = {}
    if regex_hint["house_type"] is None or regex_hint["bedrooms"] is None:
        llm_hint = await _llm_augment(text, regex_hint)

    _degraded = bool(llm_hint.get("_degraded"))
    house_type: Optional[str] = regex_hint["house_type"] or llm_hint.get("house_type")
    bedrooms:   Optional[int] = regex_hint["bedrooms"]   or llm_hint.get("bedrooms")

    lo, hi = _budget_range(session_id)

    out: Dict[str, Any] = {}
    if house_type:
        out["house_type"] = house_type
        out["keyword"]    = TYPE_SEARCH_KEYWORD.get(house_type)
    if bedrooms is not None:
        out["bedrooms"] = bedrooms
    if regex_hint.get("carpark"):
        out["carpark"] = True
    if lo is not None:
        out["min_price"] = lo
    if hi is not None:
        out["max_price"] = hi

    if _degraded:
        out["_llm_degraded"] = True
        logger.warning("[live_filter] LLM augment degraded → regex-only filter")
    logger.info("[live_filter] session=%s resolved=%s", session_id, out)
    return out
