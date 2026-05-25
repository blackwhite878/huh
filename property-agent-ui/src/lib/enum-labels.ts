/**
 * Frontend display labels for semantic tags (enums from backend).
 * Maps internal enum keys to user-friendly display text in EN and ZH.
 *
 * `getTagLabel(tag, polarity, lang)` returns the label in the active UI
 * language; if a tag has no zh override it falls back to the EN label
 * (snake_case is also converted to Title Case as a last resort).
 */

import type { Lang } from "./i18n";

type Bilingual = { en: string; zh: string };

export const PPP_LABELS: Record<string, Bilingual> = {
  // Positive Property Preferences (required features)
  needs_security:        { en: "24h Security",       zh: "24 小时保安" },
  needs_gated:           { en: "Gated Community",    zh: "围篱社区" },
  needs_near_mrt:        { en: "Near MRT",           zh: "靠近 MRT" },
  needs_near_lrt:        { en: "Near LRT",           zh: "靠近 LRT" },
  needs_near_highway:    { en: "Close to Highway",   zh: "靠近高速公路" },
  needs_high_floor:      { en: "High Floor",         zh: "高楼层" },
  needs_south_facing:    { en: "South Facing",       zh: "朝南" },
  needs_natural_light:   { en: "Natural Light",      zh: "采光良好" },
  needs_balcony:         { en: "Balcony",            zh: "阳台" },
  needs_pool:            { en: "Swimming Pool",      zh: "游泳池" },
  needs_gym:             { en: "Gym",                zh: "健身房" },
  needs_parking:         { en: "Parking",            zh: "停车位" },
  needs_covered_parking: { en: "Covered Parking",    zh: "有顶车位" },
  needs_lift:            { en: "Lift/Elevator",      zh: "电梯" },
  needs_near_school:     { en: "Near School",        zh: "靠近学校" },
  needs_near_mall:       { en: "Near Mall",          zh: "靠近商场" },
  needs_near_hospital:   { en: "Near Hospital",      zh: "靠近医院" },
  pet_friendly:          { en: "Pet Friendly",       zh: "宠物友好" },
  furnished:             { en: "Furnished",          zh: "带家具" },
  new_building:          { en: "New Building",       zh: "新建楼盘" },
  // Generic / catchall
  modern_style:          { en: "Modern Style",       zh: "现代风格" },
  double_storey:         { en: "Double Storey",      zh: "双层" },
  johor_bahru:           { en: "Johor Bahru",        zh: "新山" },
  kuala_lumpur:          { en: "Kuala Lumpur",       zh: "吉隆坡" },
  penang:                { en: "Penang",             zh: "槟城" },
  iskandar_puteri:       { en: "Iskandar Puteri",    zh: "依斯干达公主城" },
};

export const NPP_LABELS: Record<string, Bilingual> = {
  // Negative Property Preferences (exclusions)
  west_facing:           { en: "West Facing",         zh: "朝西" },
  east_facing:           { en: "East Facing",         zh: "朝东" },
  no_natural_light:      { en: "No Natural Light",    zh: "采光差" },
  no_balcony:            { en: "No Balcony",          zh: "无阳台" },
  high_floor:            { en: "High Floor",          zh: "高楼层" },
  low_floor:             { en: "Low Floor",           zh: "低楼层" },
  top_floor:             { en: "Top Floor",           zh: "顶层" },
  ground_floor:          { en: "Ground Floor",        zh: "底层" },
  far_from_mrt:          { en: "Far from MRT",        zh: "远离 MRT" },
  far_from_bus:          { en: "Far from Bus",        zh: "远离公交" },
  far_from_highway:      { en: "Far from Highway",    zh: "远离高速公路" },
  no_pool:               { en: "No Swimming Pool",    zh: "无游泳池" },
  no_gym:                { en: "No Gym",              zh: "无健身房" },
  no_security:           { en: "No Security",         zh: "无保安" },
  no_parking:            { en: "No Parking",          zh: "无停车位" },
  no_visitor_parking:    { en: "No Visitor Parking",  zh: "无访客车位" },
  frequent_lift_issues:  { en: "Frequent Lift Issues", zh: "电梯频繁故障" },
  far_from_school:       { en: "Far from School",     zh: "远离学校" },
  far_from_hospital:     { en: "Far from Hospital",   zh: "远离医院" },
  far_from_mall:         { en: "Far from Mall",       zh: "远离商场" },
  near_industrial:       { en: "Near Industrial Area", zh: "靠近工业区" },
  noise_area:            { en: "Noisy Area",          zh: "嘈杂地段" },
  near_cemetery:         { en: "Near Cemetery",       zh: "靠近墓地" },
  near_power_lines:      { en: "Near Power Lines",    zh: "靠近高压线" },
  near_mosque:           { en: "Near Mosque",         zh: "靠近清真寺" },
  open_kitchen:          { en: "Open Kitchen",        zh: "开放式厨房" },
  no_storage:            { en: "No Storage",          zh: "无储物空间" },
  small_unit:            { en: "Small Unit",          zh: "户型偏小" },
  high_tenant_mix:       { en: "Mixed Tenants",       zh: "租户复杂" },
  no_dog:                { en: "No Dogs",             zh: "不可养狗" },
  no_noise:              { en: "No Noise Tolerance",  zh: "不可接受噪音" },
};

/**
 * Get display label for a tag in the requested language. Falls back to the
 * EN label, and finally to a Title Case rendering of the snake_case key.
 */
export function getTagLabel(
  tag: string,
  polarity: "pos" | "neg" = "neg",
  lang: Lang = "en",
): string {
  const mapping = polarity === "pos" ? PPP_LABELS : NPP_LABELS;
  const entry = mapping[tag];
  if (entry) return entry[lang] ?? entry.en;
  return tag
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
