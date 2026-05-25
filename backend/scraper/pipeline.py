"""
High-level pipeline glue. Called from backend/search_pipeline.py.

- decides demo vs realtime from config
- runs retry-then-demo
- triggers ranking_agent
- returns the ranked payload + degradation flags for the API layer
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import seeder, ranking_agent, storage
from .types_quota import MY_REGIONS

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_mode() -> str:
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        mode = (cfg.get("scraper") or {}).get("mode", "demo")
    except Exception as e:
        logger.warning("config.yaml unreadable (%s); defaulting to demo", e)
        mode = "demo"
    if mode not in ("demo", "realtime"):
        mode = "demo"
    return mode


# Alias table: Chinese / Malay / common English variants → canonical region key.
REGION_ALIASES: Dict[str, List[str]] = {
    "johor":           ["johor", "柔佛", "jb", "johor bahru", "johor-bahru"],
    "kedah":           ["kedah", "吉打"],
    "kelantan":        ["kelantan", "吉兰丹", "吉蘭丹"],
    "melaka":          ["melaka", "malacca", "马六甲", "馬六甲"],
    "negeri-sembilan": ["negeri sembilan", "negeri-sembilan", "森美兰", "森美蘭", "ns"],
    "pahang":          ["pahang", "彭亨"],
    "perak":           ["perak", "霹雳", "霹靂"],
    "perlis":          ["perlis", "玻璃市"],
    "penang":          ["penang", "pulau pinang", "槟城", "檳城"],
    "sabah":           ["sabah", "沙巴"],
    "sarawak":         ["sarawak", "砂拉越", "砂劳越"],
    "selangor":        ["selangor", "雪兰莪", "雪蘭莪", "pj", "petaling jaya", "shah alam", "subang"],
    "terengganu":      ["terengganu", "登嘉楼", "登嘉樓"],
    "kuala-lumpur":    ["kuala lumpur", "kuala-lumpur", "kl", "klcc", "吉隆坡"],
    "labuan":          ["labuan", "纳闽", "納閩"],
    "putrajaya":       ["putrajaya", "布城", "布特拉再也"],
}

# Group aliases that fan-out to multiple regions.
REGION_GROUP_ALIASES: Dict[str, List[str]] = {
    # 联邦直辖区 / Federal Territories → KL + Labuan + Putrajaya
    "联邦直辖区": ["kuala-lumpur", "labuan", "putrajaya"],
    "聯邦直轄區": ["kuala-lumpur", "labuan", "putrajaya"],
    "federal territory":     ["kuala-lumpur", "labuan", "putrajaya"],
    "federal territories":   ["kuala-lumpur", "labuan", "putrajaya"],
    "wilayah persekutuan":   ["kuala-lumpur", "labuan", "putrajaya"],
    "malaysia": list(MY_REGIONS),
    "全马":     list(MY_REGIONS),
    "全馬":     list(MY_REGIONS),
}


def resolve_regions(target_text: Optional[str]) -> List[str]:
    """Map free text (EN/MS/CN) to canonical region keys. De-duplicated, order preserved."""
    if not target_text:
        return MY_REGIONS[:1]
    t = target_text.lower()
    seen: set = set()
    out: List[str] = []

    for group_key, regions in REGION_GROUP_ALIASES.items():
        if group_key.lower() in t:
            for r in regions:
                if r not in seen:
                    seen.add(r); out.append(r)

    for region, aliases in REGION_ALIASES.items():
        if region in seen:
            continue
        if any(a in t for a in aliases):
            seen.add(region); out.append(region)

    return out or MY_REGIONS[:1]


async def run_pipeline(session_id: str, brief: Dict) -> Dict:
    """
    End-to-end:
      1. resolve regions from brief.target
      2. fill tempo (demo or realtime with 3-retry then demo fallback)
      3. rank top10
    """
    regions = resolve_regions(brief.get("target"))
    mode = _load_mode()

    # ensure session tempo is fresh
    storage.clear_session_tempo(session_id)
    seeder.reset_flags()  # per-search reset; FLAGS.forced_demo will re-arm on failure

    if mode == "realtime":
        async def realtime():
            return await seeder.fetch_realtime_into_tempo(session_id, regions)
        def demo():
            return seeder.load_demo_into_tempo(session_id, regions)
        counts = await seeder.run_with_retry_then_demo(realtime, demo, retries=3)
    else:
        counts = seeder.load_demo_into_tempo(session_id, regions)

    ranked = await ranking_agent.rank_top10(session_id, brief, regions)
    return {
        "mode_requested": mode,
        "forced_demo": seeder.FLAGS.forced_demo,
        "last_error": seeder.FLAGS.last_error,
        "regions": regions,
        "tempo_counts": counts,
        "ranked": ranked,
    }
