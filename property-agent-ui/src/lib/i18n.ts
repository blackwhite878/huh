// ============================================================================
// Lightweight i18n for the Property Agent UI.
// Two locales: English ("en", default) and Simplified Chinese ("zh").
// No external dependency, no React Context — language lives in the zustand
// store so it persists with the rest of the session snapshot.
//
// Every UI string the app renders MUST go through `t()`. Adding a new visible
// string? Add a key here in both languages. Missing keys log a dev warning
// (see `t()` below) so language gaps are caught loudly in development.
// ============================================================================

export type Lang = "en" | "zh";

export const LANG_LABEL: Record<Lang, string> = {
  en: "English",
  zh: "简体中文",
};

// Human-readable name used inside LLM prompts (e.g. "answer in <X>").
export const LANG_PROMPT_NAME: Record<Lang, string> = {
  en: "English",
  zh: "Simplified Chinese",
};

// ── Translation dictionary ──────────────────────────────────────────────
type Dict = Record<string, { en: string; zh: string }>;

export const DICT: Dict = {
  // ── Shell ────────────────────────────────────────────────────────────
  "shell.tagline": { en: "Property Scouting Agent", zh: "房产顾问代理" },
  "shell.online": { en: "system online", zh: "系统在线" },
  "shell.version": { en: "v1.0 · mvp", zh: "v1.0 · 试运行" },
  "shell.footer": {
    en: "Crafted by AIC hackathon 2026 by team LXVII",
    zh: "由 LXVII 团队为 AIC 黑客松 2026 打造",
  },
  "shell.language": { en: "Language", zh: "语言" },

  // ── StateChip ────────────────────────────────────────────────────────
  "state.IDLE":                 { en: "Phase 1 : Onboarding",          zh: "阶段 1 ：信息收集" },
  "state.PHASE_1_INITIAL":      { en: "Phase 1 : Onboarding",          zh: "阶段 1 ：信息收集" },
  "state.SEMANTIC_ALIGNING":    { en: "Aligning semantic profile",     zh: "正在对齐语义档案" },
  "state.PROFILING_COMPLETE":   { en: "Profile ready",                  zh: "档案已就绪" },
  "state.CHATTING":             { en: "Phase 2 : Live consultation",   zh: "阶段 2 ：实时咨询" },
  "state.PENDING_CONFIRMATION": { en: "Awaiting confirmation",          zh: "等待确认" },
  "state.SEARCHING":            { en: "Searching properties",           zh: "正在搜索房源" },
  "state.BATCH_1_DISPLAY":      { en: "Results · Batch 1",              zh: "结果 · 第 1 批" },
  "state.BATCH_2_DISPLAY":      { en: "Results · Batch 2",              zh: "结果 · 第 2 批" },
  "state.ALL_REJECTED":         { en: "Learning from feedback",         zh: "正在学习您的反馈" },
  "state.ACTION_REQUIRED_UI":   { en: "Choose next action",             zh: "请选择下一步操作" },
  "state.RE_SEARCHING":         { en: "Re-running search",              zh: "重新搜索中" },
  "state.TIER3_NO_RESULT":      { en: "Search exhausted",               zh: "搜索已穷尽" },

  // ── Phase 1 (PhaseOneForm) ───────────────────────────────────────────
  "p1.badge": { en: "Phase 1 · structured profiling", zh: "阶段 1 · 结构化档案" },
  "p1.title.a": { en: "Tell us what", zh: "告诉我们" },
  "p1.title.home": { en: "home", zh: "家" },
  "p1.title.b": { en: "means", zh: "对您意味着什么" },
  "p1.title.c": { en: "to you.", zh: "" },
  "p1.subtitle": {
    en: "A few quick details so the AI can build your personalised property profile. We'll align on semantics in the background.",
    zh: "请提供几项基本信息，AI 将据此为您建立个人化的房产档案。我们将在后台完成语义对齐。",
  },
  "p1.label.budget": { en: "Budget (RM)", zh: "预算（令吉 RM）" },
  "p1.placeholder.budget": { en: "500,000", zh: "500,000" },
  "p1.label.target": { en: "Target area", zh: "目标区域" },
  "p1.placeholder.target": {
    en: "e.g. Johor Bahru",
    zh: "例如：新山 (Johor Bahru)",
  },
  "p1.label.description": {
    en: "What features are must-haves, dealbreakers, or nice-to-haves? (at least 10 characters)",
    zh: "哪些条件是必要、不可接受或加分的？（至少 10 个字符）",
  },
  "p1.placeholder.description": {
    en: "e.g. Car park, must have security, prefer high floor and close to MRT. Avoid noisy main roads.",
    zh: "例如：必须有车位与保安，希望高楼层、靠近地铁，避免临近吵闹的主干道。",
  },
  "p1.hint.description": {
    en: "Used to generate preference tags during semantic alignment.",
    zh: "用于在语义对齐阶段生成偏好标签。",
  },
  "p1.label.identity": { en: "Buyer identity", zh: "购房者身份" },
  "p1.identity.first_time_buyer": { en: "First-time Buyer", zh: "首次购房者" },
  "p1.identity.first_time_buyer.hint": { en: "Budget-focused", zh: "偏重预算" },
  "p1.identity.investor": { en: "Investor", zh: "投资者" },
  "p1.identity.investor.hint": { en: "Yield-driven", zh: "偏重回报" },
  "p1.identity.upgrader": { en: "Upgrader", zh: "改善型买家" },
  "p1.identity.upgrader.hint": { en: "Lifestyle-focused", zh: "偏重生活" },
  "p1.label.gender": { en: "Gender", zh: "性别" },
  "p1.gender.female": { en: "Female", zh: "女" },
  "p1.gender.male": { en: "Male", zh: "男" },
  "p1.gender.prefer_not_to_say": { en: "Prefer not to say", zh: "不便透露" },
  "p1.gender.undisclosed_short": { en: "Undisclosed", zh: "未透露" },
  "p1.label.style": { en: "Agent Personalities", zh: "顾问风格" },
  "p1.style.Professional": { en: "Professional", zh: "专业" },
  "p1.style.Professional.hint": { en: "Crisp · advisory", zh: "干练 · 顾问式" },
  "p1.style.Friendly": { en: "Friendly", zh: "亲切" },
  "p1.style.Friendly.hint": { en: "Warm · conversational", zh: "温和 · 对话式" },
  "p1.style.Enthusiastic": { en: "Enthusiastic", zh: "热情" },
  "p1.style.Enthusiastic.hint": { en: "Punchy · proactive", zh: "积极 · 主动" },
  "p1.fields": { en: "5 fields", zh: "共 5 项" },
  "p1.cta": { en: "Build my profile", zh: "建立我的档案" },
  "p1.cta.loading": { en: "Initialising…", zh: "初始化中…" },
  "p1.error": {
    en: "Couldn't reach the agent backend. Please try again.",
    zh: "无法连接代理后端，请稍后重试。",
  },
  "p1.error.prefix": {
    en: "Couldn't reach the agent backend:",
    zh: "无法连接代理后端：",
  },

  // ── Phase 1.5 (SemanticAligning) ─────────────────────────────────────
  "align.0": { en: "Thinking",          zh: "思考中" },
  "align.1": { en: "Aligning",          zh: "对齐中" },
  "align.2": { en: "Parsing",           zh: "解析中" },
  "align.3": { en: "Cross-referencing", zh: "交叉比对" },
  "align.4": { en: "Drafting",          zh: "草拟中" },
  "align.headline.Professional": {
    en: "Building your personalised requirements profile…",
    zh: "正在构建您的个性化需求档案…",
  },
  "align.headline.Friendly": {
    en: "Hang tight — getting to know what you like.",
    zh: "请稍候，我们正在了解您的偏好。",
  },
  "align.headline.Enthusiastic": {
    en: "Decoding your preferences — almost there.",
    zh: "正在解读您的偏好，马上就好。",
  },
  "align.subtitle": {
    en: "semantic alignment · phase 1.5",
    zh: "语义对齐 · 阶段 1.5",
  },
  "align.fallback": {
    en: "Backend slow — showing locally derived tags. Will refresh if backend responds.",
    zh: "后端响应较慢，先显示本机推导的标签；如有更新将自动刷新。",
  },

  // ── ProfilingComplete ────────────────────────────────────────────────
  "pc.badge": { en: "profile aligned", zh: "档案已对齐" },
  "pc.title.a": { en: "Your", zh: "您的" },
  "pc.title.b": { en: "preference signature", zh: "偏好画像" },
  "pc.subtitle": {
    en: "We detected the following preferences. Required features will be prioritised; exclusions will be filtered out during your property search.",
    zh: "我们识别出以下偏好。搜索时将优先满足必要条件，并过滤掉排除项。",
  },
  "pc.alignment_failed": { en: "Semantic alignment failed", zh: "语义对齐失败" },
  "pc.degraded_warning": {
    en: "Semantic alignment ran in degraded mode — only minimal preferences were detected. You can refine them during the conversation.",
    zh: "语义对齐以降级模式运行 — 仅识别到最少的偏好。您可以在对话中进一步细化。",
  },
  "pc.required": { en: "Required features", zh: "必要条件" },
  "pc.exclusions": { en: "Exclusions", zh: "排除项" },
  "pc.no_required": { en: "No required features detected yet.", zh: "暂未识别到必要条件。" },
  "pc.no_exclusions": {
    en: "No specific exclusions detected. Tell the agent more in the next step.",
    zh: "未识别到明确的排除项。请在下一步中告诉代理更多信息。",
  },
  "pc.cta": { en: "Begin consultation", zh: "开始咨询" },

  // ── Phase 2 (Conversation) ───────────────────────────────────────────
  "p2.title": { en: "Live consultation", zh: "实时咨询" },
  "p2.subtitle": { en: "Phase 2 : Deep Chatting", zh: "阶段 2 ：深度对话" },
  "p2.input.placeholder": { en: "Type your message…", zh: "请输入消息…" },
  "p2.input.locked": {
    en: "Input locked while the agent works…",
    zh: "代理处理中，输入已锁定…",
  },
  "p2.input.char_count_aria": { en: "character count", zh: "字数统计" },
  "p2.error.generic": {
    en: "Sorry, I encountered an error and couldn't process your request. Please try again.",
    zh: "抱歉，处理您的请求时发生了错误，请重试。",
  },
  "p2.deadsession.offline": {
    en: "Connection lost — your session has been closed. Please start over.",
    zh: "连接中断，会话已关闭，请重新开始。",
  },
  "p2.deadsession.restarted": {
    en: "The server was restarted and your session is no longer available. Local memory has been cleared.",
    zh: "服务器已重启，原会话已失效，本机暂存已清除，请重新开始。",
  },
  "p2.popup.badge": { en: "ready · enough context", zh: "已就绪 · 信息充足" },
  "p2.popup.title": { en: "We have what we need.", zh: "信息已收集完整。" },
  "p2.popup.redirect": {
    en: "Redirecting to property search in",
    zh: "即将进入房源搜索，倒计时",
  },
  "p2.popup.stay": { en: "Stay & chat more", zh: "继续对话" },
  "p2.popup.seconds": { en: "s", zh: "秒" },

  // Conflict UI
  "p2.conflict.badge": { en: "Conflict", zh: "冲突" },
  "p2.conflict.yes": { en: "Yes →", zh: "是 →" },
  "p2.conflict.no": { en: "No →", zh: "否 →" },
  "p2.conflict.update.prefix": { en: "update", zh: "更新" },
  "p2.conflict.update.from":   { en: "from",   zh: "从" },
  "p2.conflict.update.to":     { en: "to",     zh: "为" },
  "p2.conflict.keep.prefix":   { en: "keep",   zh: "保留" },
  "p2.conflict.keep.as":       { en: "as",     zh: "为" },
  "p2.conflict.btn.accept": { en: "Yes, update", zh: "是，更新" },
  "p2.conflict.btn.reject": { en: "Keep original", zh: "保留原值" },
  "p2.conflict.msg.updated": {
    en: "Updated {field} from {prev} to {next}.",
    zh: "已将 {field} 从 {prev} 更新为 {next}。",
  },
  "p2.conflict.msg.kept": {
    en: "Kept {field} as {prev}.",
    zh: "保留 {field} 为 {prev}。",
  },

  // Conflict field labels
  "field.budget":      { en: "budget",      zh: "预算" },
  "field.target":      { en: "target",      zh: "目标区域" },
  "field.identity":    { en: "identity",    zh: "身份" },
  "field.gender":      { en: "gender",      zh: "性别" },
  "field.agent_style": { en: "agent style", zh: "顾问风格" },
  "field.house_type":  { en: "house type",  zh: "房型" },
  "field.location":    { en: "location",    zh: "位置" },
  "field.description": { en: "description", zh: "描述" },
  "field.bedrooms":    { en: "bedrooms",    zh: "卧室数" },
  "field.bathrooms":   { en: "bathrooms",   zh: "浴室数" },

  // Synthetic auto-search message (sent to backend; user-visible in chat).
  "p2.auto_search_request": {
    en: "I've shared enough. Please start searching for matches now.",
    zh: "我已提供足够信息，请开始为我搜索匹配的房源。",
  },

  // ── ThinkingBubble ───────────────────────────────────────────────────
  "thinking.0": { en: "Reading your requirements",      zh: "正在阅读您的需求" },
  "thinking.1": { en: "Cross-referencing dealbreakers", zh: "交叉核对不可接受项" },
  "thinking.2": { en: "Matching against your profile",  zh: "与您的档案进行匹配" },
  "thinking.3": { en: "Checking known facts",           zh: "校验已知信息" },
  "thinking.4": { en: "Drafting reply",                 zh: "撰写回复" },
  "thinking.retry": { en: "Retrying", zh: "重试中" },

  // ── Searching ────────────────────────────────────────────────────────
  // Headline copy keyed by agent style × stage. Keys MUST match AgentStyle.
  "search.copy.Professional.idle":                { en: "Preparing the search pipeline…",                       zh: "搜索流水线准备中…" },
  "search.copy.Professional.scraping":            { en: "Sourcing the latest property listings…",               zh: "正在获取最新房源列表…" },
  "search.copy.Professional.ranking":             { en: "Scoring listings against your preferences…",           zh: "正在根据您的偏好为房源打分…" },
  "search.copy.Professional.generating_remarks":  { en: "AI is composing tailored analysis for each property…", zh: "AI 正在为每个房源撰写定制化分析…" },
  "search.copy.Professional.complete":            { en: "Ready.",                                                zh: "已就绪。" },
  "search.copy.Friendly.idle":                    { en: "Warming up…",                                            zh: "正在预热…" },
  "search.copy.Friendly.scraping":                { en: "Going to grab the freshest listings for you — back in a sec.", zh: "正在为您抓取最新房源，稍等片刻。" },
  "search.copy.Friendly.ranking":                 { en: "Picking the ones that fit you best…",                   zh: "正在挑选最适合您的房源…" },
  "search.copy.Friendly.generating_remarks":      { en: "Almost done — writing up the highlights now.",          zh: "马上完成 — 正在整理重点信息。" },
  "search.copy.Friendly.complete":                { en: "All set!",                                               zh: "全部就绪！" },
  "search.copy.Enthusiastic.idle":                { en: "Preparing.",                                             zh: "准备中。" },
  "search.copy.Enthusiastic.scraping":            { en: "Pulling listings live.",                                 zh: "正在实时抓取房源。" },
  "search.copy.Enthusiastic.ranking":             { en: "Ranking by fit.",                                        zh: "按匹配度排序。" },
  "search.copy.Enthusiastic.generating_remarks":  { en: "Writing remarks.",                                       zh: "撰写点评。" },
  "search.copy.Enthusiastic.complete":            { en: "Done.",                                                  zh: "完成。" },

  "search.stage.scraping":   { en: "Scraping",   zh: "抓取" },
  "search.stage.ranking":    { en: "Ranking",    zh: "排序" },
  "search.stage.generating": { en: "Generating", zh: "生成" },
  "search.footer": {
    en: "input locked · search pipeline running",
    zh: "输入已锁定 · 搜索流水线运行中",
  },

  // ── ResultsBatch ─────────────────────────────────────────────────────
  "results.batch":      { en: "batch",  zh: "第" },
  "results.batch.suffix": { en: "",      zh: " 批" },
  "results.of":         { en: "of",     zh: "/" },
  "results.title.a":    { en: "Curated", zh: "为您精选的" },
  "results.title.b":    { en: "matches", zh: "匹配房源" },
  "results.subtitle": {
    en: "Ranked by your weighted preference profile.",
    zh: "已按您的加权偏好排序。",
  },
  "results.declined":   { en: "declined", zh: "已剔除" },
  "results.degraded": {
    en: "AI analysis is temporarily unavailable — results are sorted by weighted scoring only.",
    zh: "AI 分析暂时不可用 — 结果仅按加权评分排序。",
  },
  "results.tier_1":     { en: "Perfect fit", zh: "完美匹配" },
  "results.tier_2":     { en: "Near match",  zh: "接近匹配" },
  "results.ai_remarks": { en: "AI Remarks",  zh: "AI 点评" },
  "results.degraded_card": {
    en: "AI analysis temporarily unavailable",
    zh: "AI 分析暂时不可用",
  },
  "results.analysis_pending": { en: "Analysis pending.", zh: "分析生成中。" },
  "results.tradeoffs":  { en: "Trade-offs",  zh: "取舍" },
  "results.missing":    { en: "Missing",     zh: "缺少" },
  "results.remedy":     { en: "Remedy",      zh: "建议" },
  "results.removed": {
    en: "Removed from list — your feedback was recorded.",
    zh: "已从列表移除 — 您的反馈已记录。",
  },
  "results.cta.next":         { en: "View more matches", zh: "查看更多匹配" },
  "results.reject_placeholder": {
    en: "Why isn't this a fit? (helps the agent learn)",
    zh: "为何不合适？（有助于代理学习）",
  },
  "results.btn.cancel":         { en: "Cancel",         zh: "取消" },
  "results.btn.submit":         { en: "Submit",         zh: "提交" },
  "results.btn.not_interested": { en: "Not interested", zh: "不感兴趣" },

  // ── ActionRequired ───────────────────────────────────────────────────
  "ar.badge":    { en: "preferences updated", zh: "偏好已更新" },
  "ar.title":    { en: "What's next?",         zh: "下一步如何？" },
  "ar.subtitle": {
    en: "Your feedback has been learned. Choose how to continue.",
    zh: "您的反馈已被学习。请选择继续方式。",
  },
  "ar.continue": { en: "Continue", zh: "继续" },
  "action.start_fresh":   { en: "Start fresh",        zh: "重新开始" },
  "action.new_prompt":    { en: "New prompt",         zh: "新的需求" },
  "action.new_prompt.desc": {
    en: "Clear everything and rebuild your profile from scratch.",
    zh: "清空所有记录，从头重新建立档案。",
  },
  "action.keep_memories":      { en: "Keep memories", zh: "保留记忆" },
  "action.keep_memories.sub": {
    en: "Continue with learned preferences",
    zh: "保留已学习的偏好",
  },
  "action.keep_memories.desc": {
    en: "Hold on to your dialogue & exclusions, adjust the search.",
    zh: "保留对话与排除项，仅调整搜索条件。",
  },

  // ── Tier3NoResult ────────────────────────────────────────────────────
  "t3.title": { en: "No matches found", zh: "未找到匹配房源" },
  "t3.body": {
    en: "We expanded the search across Level 0 – 3 administrative zones, but no listings cleared your constraints. Try widening your budget or relaxing a feature.",
    zh: "我们已将搜索扩大至 0–3 级行政区域，但仍无房源满足您的全部条件。请尝试放宽预算或调整某项要求。",
  },
  "t3.cta": { en: "Reset search", zh: "重新搜索" },

  // ── FloatingTags ─────────────────────────────────────────────────────
  "ft.label.budget":   { en: "BUDGET",   zh: "预算" },
  "ft.label.target":   { en: "TARGET",   zh: "目标" },
  "ft.label.identity": { en: "IDENTITY", zh: "身份" },
  "ft.label.style":    { en: "STYLE",    zh: "风格" },
  "ft.label.gender":   { en: "GENDER",   zh: "性别" },
};

// `t(key, lang, vars?)` — main translation entry point.
// `vars` performs simple `{name}` substitution after lookup.
export function t(
  key: string,
  lang: Lang,
  vars?: Record<string, string | number>,
): string {
  const entry = DICT[key];
  if (!entry) {
    if (typeof console !== "undefined")
      console.warn(`[i18n] missing key: ${key}`);
    return key;
  }
  let out = entry[lang] ?? entry.en;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      out = out.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    }
  }
  return out;
}

// ── Bilingual location bracket ──────────────────────────────────────────
// User's rule (verbatim): show the primary-language name with the other in
// round brackets — e.g. when lang="en"  → "Johor Bahru（新山）"
//                       when lang="zh" → "新山（Johor Bahru）"
// Applied to known location labels only; freeform user input is preserved.
export const LOCATION_BILINGUAL: Record<string, { en: string; zh: string }> = {
  johor: { en: "Johor", zh: "柔佛" },
  johor_bahru: { en: "Johor Bahru", zh: "新山" },
  jb: { en: "Johor Bahru", zh: "新山" },
  kuala_lumpur: { en: "Kuala Lumpur", zh: "吉隆坡" },
  kl: { en: "Kuala Lumpur", zh: "吉隆坡" },
  penang: { en: "Penang", zh: "槟城" },
  pulau_pinang: { en: "Penang", zh: "槟城" },
  iskandar_puteri: { en: "Iskandar Puteri", zh: "依斯干达公主城" },
  iskandar: { en: "Iskandar Puteri", zh: "依斯干达公主城" },
  selangor: { en: "Selangor", zh: "雪兰莪" },
  petaling_jaya: { en: "Petaling Jaya", zh: "八打灵再也" },
  shah_alam: { en: "Shah Alam", zh: "莎阿南" },
  subang_jaya: { en: "Subang Jaya", zh: "梳邦再也" },
  ipoh: { en: "Ipoh", zh: "怡保" },
  melaka: { en: "Melaka", zh: "马六甲" },
};

export function formatLocation(key: string, lang: Lang): string {
  const entry = LOCATION_BILINGUAL[key.toLowerCase().replace(/\s+/g, "_")];
  if (!entry) return key;
  return lang === "en"
    ? `${entry.en}（${entry.zh}）`
    : `${entry.zh}（${entry.en}）`;
}

// Detect whether a snake_case tag key is a known location.
export function isLocationTag(key: string): boolean {
  return key.toLowerCase().replace(/\s+/g, "_") in LOCATION_BILINGUAL;
}
