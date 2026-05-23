// ============================================================================
// Local fallback for semantic alignment.
// Used by SemanticAligning when the backend is unavailable so that
// Profiling Complete shows real exclusions derived from the user's
// Phase 1 free-text description instead of an empty state.
// Pure heuristic — backend should override when present.
// ============================================================================

interface Rule {
  match: RegExp;
  tag: string;
}

// Negative-preference dictionary (English + lightweight CJK cues).
// Each rule maps a phrase to a snake_case feature tag the search layer
// can later interpret as an exclusion.
const RULES: Rule[] = [
  { match: /\b(west[\s-]?facing|afternoon sun|西\s*晒|西\s*向)\b/i, tag: "west_facing" },
  { match: /\b(east[\s-]?facing|东\s*向)\b/i, tag: "east_facing" },
  { match: /\b(north[\s-]?facing)\b/i, tag: "north_facing" },
  { match: /\b(no security|without security|无\s*保安|没有\s*保安)\b/i, tag: "no_security" },
  { match: /\b(far from (the )?mrt|far from (the )?lrt|远离\s*mrt|远离\s*地铁)\b/i, tag: "far_from_transit" },
  { match: /\b(near (the )?mrt|close to mrt|靠近\s*mrt|近\s*地铁)\b/i, tag: "needs_near_transit" },
  { match: /\b(noisy|too loud|noise|嘈杂)\b/i, tag: "noisy" },
  { match: /\b(low floor|底层|低楼层)\b/i, tag: "low_floor" },
  { match: /\b(high floor|高楼层|高层)\b/i, tag: "needs_high_floor" },
  { match: /\b(no parking|没有\s*停车)\b/i, tag: "no_parking" },
  { match: /\b(small (unit|size)|cramped|拥挤|太\s*小)\b/i, tag: "too_small" },
  { match: /\b(old building|aged building|老\s*房子)\b/i, tag: "old_building" },
  { match: /\b(near (a )?(highway|main road)|临街)\b/i, tag: "near_highway" },
  { match: /\b(no lift|no elevator|没有\s*电梯)\b/i, tag: "no_lift" },
  { match: /\b(near cemetery|墓地)\b/i, tag: "near_cemetery" },
  { match: /\b(flood|flooding|淹水)\b/i, tag: "flood_risk" },
  { match: /\b(no balcony|没有\s*阳台)\b/i, tag: "no_balcony" },
  { match: /\b(busy area|crowded|人多)\b/i, tag: "crowded_area" },
];

export function deriveTagsFromDescription(input: string): string[] {
  if (!input?.trim()) return [];
  const found = new Set<string>();
  for (const r of RULES) {
    if (r.match.test(input)) found.add(r.tag);
  }
  return Array.from(found);
}
