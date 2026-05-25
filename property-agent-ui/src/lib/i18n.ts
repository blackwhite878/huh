// ============================================================================
// Lightweight i18n for the Property Agent UI.
// Two locales: English ("en", default) and Simplified Chinese ("zh").
// No external dependency, no React Context — language lives in the zustand
// store so it persists with the rest of the session snapshot.
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
// Every UI string the app renders goes through `t()`. Keep keys stable.
type Dict = Record<string, { en: string; zh: string }>;

export const DICT: Dict = {
  // Shell
  "shell.tagline": { en: "Property Scouting Agent", zh: "房产顾问代理" },
  "shell.online": { en: "system online", zh: "系统在线" },
  "shell.footer": {
    en: "Crafted by AIC hackathon 2026 by team LXVII",
    zh: "由 LXVII 团队为 AIC 黑客松 2026 打造",
  },
  "shell.language": { en: "Language", zh: "语言" },

  // Phase 1
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
  "p1.label.target": { en: "Target area", zh: "目标区域" },
  "p1.placeholder.target": {
    en: "e.g. Johor Bahru (新山)",
    zh: "例如：新山（Johor Bahru）",
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
  "p1.error":  {
    en: "Couldn't reach the agent backend. Please try again.",
    zh: "无法连接代理后端，请稍后重试。",
  },

  // Phase 2 — Conversation
  "p2.title": { en: "Live consultation", zh: "实时咨询" },
  "p2.subtitle": { en: "Phase 2 : Deep Chatting", zh: "阶段 2 ：深度对话" },
  "p2.input.placeholder": { en: "Type your message…", zh: "请输入消息…" },
  "p2.input.locked": {
    en: "Input locked while the agent works…",
    zh: "代理处理中，输入已锁定…",
  },
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
  "p2.conflict.badge": { en: "Conflict", zh: "冲突" },
  "p2.conflict.yes": { en: "Yes →", zh: "是 →" },
  "p2.conflict.no": { en: "No →", zh: "否 →" },
  "p2.conflict.update": { en: "update", zh: "更新" },
  "p2.conflict.from": { en: "from", zh: "从" },
  "p2.conflict.to": { en: "to", zh: "为" },
  "p2.conflict.keep": { en: "keep", zh: "保留" },
  "p2.conflict.as": { en: "as", zh: "为" },
  "p2.conflict.btn.accept": { en: "Yes, update", zh: "是，更新" },
  "p2.conflict.btn.reject": { en: "Keep original", zh: "保留原值" },
  "p2.updated": { en: "Updated", zh: "已更新" },
  "p2.kept": { en: "Kept", zh: "保留" },
  "p2.auto_search_request": {
    en: "I've shared enough. Please start searching for matches now.",
    zh: "我已提供足够信息，请开始为我搜索匹配的房源。",
  },

  // ThinkingBubble
  "thinking.0": { en: "Reading your requirements", zh: "正在阅读您的需求" },
  "thinking.1": { en: "Cross-referencing dealbreakers", zh: "交叉核对不可接受项" },
  "thinking.2": { en: "Matching against your profile", zh: "与您的档案进行匹配" },
  "thinking.3": { en: "Checking known facts", zh: "校验已知信息" },
  "thinking.4": { en: "Drafting reply", zh: "撰写回复" },
  "thinking.retry": { en: "Retrying", zh: "重试中" },

  // Semantic aligning
  "align.0": { en: "Thinking", zh: "思考中" },
  "align.1": { en: "Aligning", zh: "对齐中" },
  "align.2": { en: "Parsing", zh: "解析中" },
  "align.3": { en: "Cross-referencing", zh: "交叉比对" },
  "align.4": { en: "Drafting", zh: "草拟中" },
  "align.headline.short": {
    en: "Building your personalised requirements profile…",
    zh: "正在构建您的个性化需求档案…",
  },
  "align.headline.warm": {
    en: "Hang tight — getting to know what you like.",
    zh: "请稍候，我们正在了解您的偏好。",
  },
  "align.headline.long": {
    en: "Decoding your preferences — almost there.",
    zh: "正在解读您的偏好，马上就好。",
  },
  "align.fallback": {
    en: "Backend slow — showing locally derived tags. Will refresh if backend responds.",
    zh: "后端响应较慢，先显示本机推导的标签；如有更新将自动刷新。",
  },

  // Profiling complete
  "profile.cta": { en: "Start the conversation", zh: "开始对话" },

  // Searching
  "search.stage.idle": { en: "Preparing the search pipeline…", zh: "搜索流水线准备中…" },
  "search.stage.scraping": {
    en: "Sourcing the latest property listings…",
    zh: "正在获取最新房源列表…",
  },
  "search.stage.ranking": {
    en: "Scoring listings against your preferences…",
    zh: "正在根据您的偏好为房源打分…",
  },
  "search.stage.generating_remarks": {
    en: "AI is composing tailored analysis for each property…",
    zh: "AI 正在为每个房源撰写定制化分析…",
  },
  "search.stage.complete": { en: "Ready.", zh: "已就绪。" },

  // Results batch
  "results.tier_1": { en: "Perfect fit", zh: "完美匹配" },
  "results.tier_2": { en: "Near match", zh: "接近匹配" },
  "results.analysis_pending": { en: "Analysis pending.", zh: "分析生成中。" },
  "results.reject_placeholder": {
    en: "Why isn't this a fit? (helps the agent learn)",
    zh: "为何不合适？（有助于代理学习）",
  },

  // Action required
  "action.start_fresh": { en: "Start fresh", zh: "重新开始" },
  "action.new_prompt": { en: "New prompt", zh: "新的需求" },
  "action.new_prompt.desc": {
    en: "Clear everything and rebuild your profile from scratch.",
    zh: "清空所有记录，从头重新建立档案。",
  },
  "action.keep_memories": { en: "Keep memories", zh: "保留记忆" },
  "action.keep_memories.sub": {
    en: "Continue with learned preferences",
    zh: "保留已学习的偏好",
  },
  "action.keep_memories.desc": {
    en: "Hold on to your dialogue & exclusions, adjust the search.",
    zh: "保留对话与排除项，仅调整搜索条件。",
  },
};

export function t(key: string, lang: Lang): string {
  const entry = DICT[key];
  if (!entry) {
    // Fail loud in dev so missing keys never silently leak English/Chinese.
    if (typeof console !== "undefined") console.warn(`[i18n] missing key: ${key}`);
    return key;
  }
  return entry[lang] ?? entry.en;
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
