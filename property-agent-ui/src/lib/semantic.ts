// ============================================================================
// Local fallback for semantic alignment.
// Used by SemanticAligning when the backend is unavailable so that
// Profiling Complete shows real preferences derived from the user's
// Phase 1 free-text description instead of an empty state.
//
// Tags are returned as `polarity:tag` strings:
//   "neg:west_facing"        → exclusion (filter OUT)
//   "pos:needs_security"     → required feature (must HAVE)
// Plain strings without a prefix are treated as "neg" by consumers for
// backward compatibility with earlier backend payloads.
// Pure heuristic — backend should override when present.
// ============================================================================

type Polarity = "neg" | "pos";

interface Rule {
  match: RegExp;
  tag: string;
  polarity: Polarity;
}

const RULES: Rule[] = [
  // ── Negative (exclusions) ────────────────────────────────────────────────
  { polarity: "neg", match: /\b(west[\s-]?facing|afternoon sun|西\s*晒|西\s*向)\b/i, tag: "west_facing" },
  { polarity: "neg", match: /\b(east[\s-]?facing|东\s*向)\b/i, tag: "east_facing" },
  { polarity: "neg", match: /\b(north[\s-]?facing)\b/i, tag: "north_facing" },
  { polarity: "neg", match: /\b(no security|without security|lack of security|无\s*保安|没有\s*保安)\b/i, tag: "no_security" },
  { polarity: "neg", match: /\b(far from (the )?mrt|far from (the )?lrt|远离\s*mrt|远离\s*地铁)\b/i, tag: "far_from_transit" },
  { polarity: "neg", match: /\b(noisy|too loud|noise|嘈杂)\b/i, tag: "noisy" },
  { polarity: "neg", match: /\b(low floor|底层|低楼层)\b/i, tag: "low_floor" },
  { polarity: "neg", match: /\b(no parking|没有\s*停车)\b/i, tag: "no_parking" },
  { polarity: "neg", match: /\b(small (unit|size)|cramped|拥挤|太\s*小)\b/i, tag: "too_small" },
  { polarity: "neg", match: /\b(old building|aged building|老\s*房子)\b/i, tag: "old_building" },
  { polarity: "neg", match: /\b(near (a )?(highway|main road)|临街)\b/i, tag: "near_highway" },
  { polarity: "neg", match: /\b(no lift|no elevator|没有\s*电梯)\b/i, tag: "no_lift" },
  { polarity: "neg", match: /\b(near cemetery|墓地)\b/i, tag: "near_cemetery" },
  { polarity: "neg", match: /\b(flood|flooding|淹水)\b/i, tag: "flood_risk" },
  { polarity: "neg", match: /\b(no balcony|没有\s*阳台)\b/i, tag: "no_balcony" },
  { polarity: "neg", match: /\b(busy area|crowded|人多)\b/i, tag: "crowded_area" },

  // ── Positive (required features) ─────────────────────────────────────────
  // Check positive AFTER negative so "no security" wins over "security".
  { polarity: "pos", match: /\b(must have (security|securities)|need(s)? security|with security|gated|24[\s-]?h(our)?\s*security|要有\s*保安|必须有\s*保安)\b/i, tag: "needs_security" },
  { polarity: "pos", match: /\b(near (the )?(mrt|lrt|transit|subway)|close to (the )?(mrt|lrt|transit)|靠近\s*mrt|近\s*地铁)\b/i, tag: "needs_near_transit" },
  { polarity: "pos", match: /\b(high floor|高楼层|高层)\b/i, tag: "needs_high_floor" },
  { polarity: "pos", match: /\b(with (a )?balcony|need(s)? balcony|要\s*阳台)\b/i, tag: "needs_balcony" },
  { polarity: "pos", match: /\b(with (a )?(pool|swimming pool)|need(s)? pool|要\s*泳池)\b/i, tag: "needs_pool" },
  { polarity: "pos", match: /\b(with (a )?gym|need(s)? gym|要\s*健身房)\b/i, tag: "needs_gym" },
  { polarity: "pos", match: /\b(covered parking|with parking|need(s)? parking|要\s*停车)\b/i, tag: "needs_parking" },
  { polarity: "pos", match: /\b(near (a )?(school|international school)|近\s*学校)\b/i, tag: "needs_near_school" },
  { polarity: "pos", match: /\b(pet[\s-]?friendly|allow(s)? pets?|可\s*养宠物)\b/i, tag: "pet_friendly" },
  { polarity: "pos", match: /\b(furnished|fully[\s-]?furnished|带\s*家具)\b/i, tag: "furnished" },
];

export function deriveTagsFromDescription(input: string): string[] {
  if (!input?.trim()) return [];
  const found = new Map<string, Polarity>();
  // Two-pass: negatives first so "no security" suppresses "needs_security".
  for (const r of RULES.filter((r) => r.polarity === "neg")) {
    if (r.match.test(input)) found.set(r.tag, "neg");
  }
  for (const r of RULES.filter((r) => r.polarity === "pos")) {
    if (r.match.test(input)) {
      // Skip if a directly conflicting negative was already captured.
      if (r.tag === "needs_security" && found.has("no_security")) continue;
      if (r.tag === "needs_near_transit" && found.has("far_from_transit")) continue;
      if (!found.has(r.tag)) found.set(r.tag, "pos");
    }
  }
  return Array.from(found.entries()).map(([tag, pol]) => `${pol}:${tag}`);
}

// Helper for UI: split a tag list into positive vs negative buckets.
// Accepts both prefixed ("neg:foo" / "pos:foo") and legacy bare tags
// (treated as "neg" for backward compatibility with the original contract).
export function partitionTags(tags: string[]): {
  negative: string[];
  positive: string[];
} {
  const negative: string[] = [];
  const positive: string[] = [];
  for (const raw of tags) {
    if (raw.startsWith("pos:")) positive.push(raw.slice(4));
    else if (raw.startsWith("neg:")) negative.push(raw.slice(4));
    else negative.push(raw);
  }
  return { negative, positive };
}
