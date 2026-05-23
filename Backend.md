# 智能房產銷售代理系統 — Backend 架構文件

> 本文件為 Backend 唯一規範來源。所有業務邏輯、Session 管理、API 端點實現、數據管道均以本文件為準。
> 版本：v4.0（已整合全部待確認項 T-03 ~ T-07 及業務側直接確認答案，無待確認佔位符）

---

## 1. 技術棧

### 1.1 後端

| 層級 | 選型 | 說明 |
|---|---|---|
| 後端框架 | **Python + FastAPI** | 異步、高並發 |
| LLM | **Chutes AI Pro** | Function Calling + 結構化 JSON 輸出 |
| 爬虫 | **Playwright（異步）+ BeautifulSoup4** | 列表頁靜態抓取 + 詳情頁深度鑽取 |
| Session 存儲 | **Python dict（內存）** | MVP 限定，重啟丟失為已知接受風險，無 Redis |
| 數據驗證 | **Pydantic v2** | 所有 LLM 輸出必須過 Pydantic Schema 驗證 |
| Mock 數據 | 本地 JSON + 預標注 NPP 字段 | DEMO_MODE 兜底，必須過完整管道 |
| 並發控制 | **asyncio.Semaphore** | 限制最大並發 LLM 請求數，見第 6 節 |

### 1.2 前端（T-03 已裁定）

| 層 | 選型 | 說明 |
|---|---|---|
| 框架 | **Next.js 14+（App Router）** | SSR/SSG 靈活切換；API Routes 作 BFF 層代理 Chutes AI 調用，避免前端直接暴露 API Key；部署至 Vercel 零配置 |
| 語言 | **TypeScript** | Response Schema 契約（`BatchResponse`, `PropertyRemark`）直接定義為 interface，編譯時捕獲狀態機字段名拼寫錯誤 |
| 狀態管理 | **Zustand** | 輕量；適合多階段狀態機；persist 中間件可按需實現本地草稿保存 |
| UI 組件 | **Tailwind CSS + shadcn/ui** | shadcn/ui 提供 Combobox、Dialog、Button 等無障礙基礎組件 |
| 實時通信 | **SSE（Server-Sent Events）** | 搜索管道耗時長（爬虫 + LLM），SSE 實現進度推送，比 Polling 更節省連接資源 |

**前端狀態機類型（TypeScript）：**

```typescript
type AgentState =
  | "IDLE"
  | "SEMANTIC_ALIGNING"
  | "PROFILING_COMPLETE"
  | "CHATTING"
  | "PENDING_CONFIRMATION"
  | "SEARCHING"
  | "BATCH_1_DISPLAY"
  | "BATCH_2_DISPLAY"
  | "ALL_REJECTED"
  | "ACTION_REQUIRED_UI"
  | "RE_SEARCHING"
  | "TIER3_NO_RESULT"
  | "PHASE_1_INITIAL";
```

**前端架構約束：**
- 狀態機驅動邏輯由 Zustand store 統一管理，**禁止將狀態散落在各組件的 `useState`**
- `SEARCHING` 狀態的輸入框鎖定必須在 store 層實現，不依賴組件內部判斷

---

## 2. 環境配置（.env + config.yaml）

### 2.1 .env（敏感憑證，不入版本控制）

```dotenv
# Chutes AI
CHUTES_AI_API_KEY=your_chutes_ai_api_key_here
CHUTES_AI_BASE_URL=https://llm.chutes.ai/v1

# 應用
APP_SECRET_KEY=your_secret_key_here
```

### 2.2 config.yaml（非敏感配置，可入版本控制）

```yaml
app:
  demo_mode: false          # true = 跳過爬虫，強制使用 Mock 數據
  debug: false

llm:
  model: "deepseek-ai/DeepSeek-V3-0324"
  max_tokens: 2000
  max_concurrent_calls: 3   # asyncio.Semaphore 上限，根據 Chutes AI 控制台 RPM 調整

scraper:
  request_delay_seconds: [2, 5]   # 隨機延遲範圍
  rotate_user_agents: true
  max_concurrent_requests: 2
  timeout_seconds: 15
  retry_on_timeout: 2

search:
  budget_tolerance: 0.10          # ±10%
  batch_size: 5                   # 每批返回條數
  max_raw_results: 50             # 爬虫目標原始數量
  max_expansion_level: 3

session:
  fc_trigger_max_attempts: 2
  rejection_continuity_window_seconds: 5.0
```

---

## 3. Session 架構 — 三類獨立生命週期

三類 Session 共用同一 `session_id`，各自獨立存儲、獨立重置，互不污染。

### 3.1 Dialogue Session

```python
{
  "session_id": "uuid",
  "phase1_data": {
    "budget": 500000,
    "agent_style": "professional",   # 合法值：professional | friendly | active
    "target": "condo in JB",
    "identity": "first_time_buyer",  # 合法值：first_time_buyer | investor | upgrader
    "gender": "female",              # 合法值：female | male | prefer_not_to_say
    "semantic_tags": ["near_school", "no_security"]  # Semantic Alignment Layer 寫入（NPP 內部 key）
  },
  "dialogue_history": [{"role": "user", "content": "..."}, ...],
  "fc_trigger_attempts": 0    # 追問輪次計數，上限 2 次（config.yaml fc_trigger_max_attempts）
}
```

**重置規則：**
- `New Prompt`：清空全部 `dialogue_history` 與 `phase1_data`
- 字段更新（`update_requirements`）：規則引擎只刪除含被修改字段語義的 utterance 片段，保留非衝突上下文

### 3.2 NPP Session

```python
{
  "session_id": "uuid",
  "npp_tags": ["west_facing", "high_floor"],   # NPP_ENUM 內部 key 列表
  "pending_rejection_buffer": [],              # 暫存每條 reject_single 的原因
  "last_rejection_message": None              # 用於連續消息時間窗口防竟態
}
```

**重置規則：**
- `New Prompt`：NPP Session 完全清零，同步從 `dialogue_history` 刪除所有 NPP 相關 utterance
- `Keep Memories`：NPP Session 完整保留，不清零
- `update_requirements`：只清除與被修改字段語義相關的 `npp_tags`（例如修改 `target` 只清除地理相關 NPP tags）

### 3.3 Search Session

```python
{
  "session_id": "uuid",
  "raw_pool": [],
  "expansion_level": 0,                      # 行政區拓撲擴張級別 0–3
  "current_budget_range": {"min": 450000, "max": 550000},
  "batch_index": 1,
  "tier1_pool": [],
  "tier2_pool": [],
  "all_results": [],
  "rejected_property_ids": [],               # 當前 Search Session 黑名單
  "search_stage": "idle"                     # scraping | ranking | generating_remarks | complete
}
```

**重置規則：**
- 每次重新搜索（`New Prompt` 或 `Keep Memories`）完全重置：`batch_index` 歸 1，`expansion_level` 歸 0，`rejected_property_ids` 清空

---

## 4. API 端點完整規範

### 4.1 `POST /api/v1/init_session`

語義對齊在此端點異步啟動，**立即返回** `session_id`，不等待 LLM 完成。

```json
// Request
{
  "budget": 500000,
  "agent_style": "professional",
  "target": "condo in Johor Bahru",
  "identity": "first_time_buyer",
  "gender": "female"
}

// Response（立即返回，不等待語義對齊）
{
  "session_id": "uuid-v4",
  "status": "aligning"
}
```

**後端執行順序：**
1. 創建三類 Session，寫入 `phase1_data`
2. 異步啟動 `semantic_alignment()`（後台任務）
3. 立即返回 `session_id`

### 4.2 `GET /api/v1/session_ready/{session_id}`

前端每 3 秒輪詢此端點，直至語義對齊完成。

```json
// Response — 未完成
{"status": "aligning"}

// Response — 完成
{
  "status": "ready",
  "semantic_tags": ["near_school", "no_security"]
}

// Response — 對齊失敗降級
{
  "status": "ready",
  "semantic_tags": [],
  "alignment_warning": true
}
```

### 4.3 `POST /api/v1/chat`

Phase 2 主對話端點。LLM 在每次返回中同時輸出結構化 JSON，後端解析後返回對應 status。

**LLM 輸出格式（Pydantic 強制驗證）：**
```python
class ChatLLMOutput(BaseModel):
    reply: str                              # 對話回覆文本
    conflict_detected: bool                 # 是否偵測到字段衝突
    conflicting_field: Optional[str]        # 衝突字段名
    proposed_value: Optional[Any]           # 用戶意圖的新值
    fc_trigger: bool                        # 是否觸發 Function Calling
```

```json
// Request
{"session_id": "uuid", "message": "我想靠近地鐵站"}

// Response — 普通對話
{"status": "chatting", "reply": "請問您需要幾個房間呢？", "fc_attempt": 1}

// Response — 字段衝突，進入 PENDING_CONFIRMATION
{
  "status": "pending_confirmation",
  "reply": "您之前選擇的是 Johor Bahru，現在想換到 KL 嗎？請確認。",
  "conflicting_field": "target",
  "proposed_value": "condo in KL"
}

// Response — FC 觸發，搜索啟動
{
  "status": "searching",
  "reply": "好的，讓我為您搜索合適的房源。"
}
```

**FC 觸發規則：**
- `property_type` 為必填，未填時**不作過濾條件**，FC 照常觸發（不阻塞）
- 追問上限 2 輪：`fc_trigger_attempts >= 2` 時強制觸發 FC，選填字段置 null
- `PENDING_CONFIRMATION` 期間後端阻斷 FC 路徑，不允許觸發搜索

### 4.4 `GET /api/v1/search_status/{session_id}`

前端每 3 秒輪詢此端點，獲取搜索管道進度。

```json
// 各中間狀態
{"status": "scraping"}
{"status": "ranking"}
{"status": "generating_remarks"}

// 完成
{
  "status": "complete",
  "batch_index": 1,
  "total_available": 10,
  "has_more": true,
  "tier3_triggered": false,
  "degraded": false,
  "results": [/* 5 條，含獨立 remarks */]
}

// 無結果（Level 3 擴張後仍無結果）
{
  "status": "complete",
  "tier3_triggered": true,
  "total_available": 0,
  "results": []
}
```

### 4.5 `POST /api/v1/next_batch`

純 UI 獲取動作，**不計入拒絕次數，不觸發 NPP 學習**。

```json
// Request
{"session_id": "uuid"}

// Response
{
  "batch_index": 2,
  "total_available": 10,
  "has_more": false,
  "tier3_triggered": false,
  "degraded": false,
  "results": [/* 剩餘 N 條 */]
}
```

### 4.6 `POST /api/v1/reject_single`

用戶拒絕單條房源時立即調用。寫入 `rejected_property_ids` 黑名單，並追加至 `pending_rejection_buffer`。

```json
// Request
{
  "session_id": "uuid",
  "property_id": "A001",
  "reason": "樓層太高，有西晒"
}

// Response
{
  "status": "recorded",
  "rejection_count": 3
}
```

**後端執行：**
```python
async def reject_single(session_id: str, property_id: str, reason: str):
    session = get_search_session(session_id)
    npp_session = get_npp_session(session_id)

    session.rejected_property_ids.append(property_id)

    timestamp = time.time()
    await handle_rejection_message(session_id, reason, timestamp)

    return {"status": "recorded", "rejection_count": len(session.rejected_property_ids)}
```

### 4.7 `POST /api/v1/reject_all`

所有房源拒絕後由前端自動觸發。**不攜帶 rejection_reasons**（已由 `reject_single` 收集）。觸發 NPP 學習管道。

```json
// Request
{"session_id": "uuid"}

// Response
{
  "status": "action_required",
  "npp_updated": ["high_floor", "west_facing"],
  "message": "已更新您的偏好記錄。請選擇下一步操作。"
}
```

**後端執行：**
1. 從 `pending_rejection_buffer` 提取所有原因
2. 調用 LLM 將原因映射至 `NPP_ENUM` 標籤（內部 key）
3. 更新 `npp_tags`（追加，去重）
4. 返回 `action_required`，等待用戶選擇

### 4.8 `POST /api/v1/resolve_action`

```json
// Request — New Prompt
{"session_id": "uuid", "action": "new_prompt"}

// Response
{
  "status": "reset_complete",
  "cleared": ["dialogue_session", "npp_session", "search_session"],
  "next_phase": "phase_1"
}

// Request — Keep Memories
{"session_id": "uuid", "action": "keep_memories"}

// Response
{
  "status": "memories_kept",
  "preserved": ["npp_tags", "dialogue_history"],
  "reset": ["search_session"],
  "next_phase": "phase_2",
  "reply": "好的，我已保留您的偏好記錄。請告訴我您想如何調整搜索條件？"
}
```

### 4.9 `POST /api/v1/fetch_detail`

深度爬取單個房源詳情頁，生成 AI 分析摘要。

**支持網站：** EdgeProp.my、Mudah.my、PropSocial.my、StarProperty.my、iProperty.com.my（全部爬虫覆蓋網站）

```json
// Request
{"session_id": "uuid", "property_url": "https://..."}

// Response
{
  "ai_summary": "...",
  "pros": ["距離 MRT 僅 200 米", "管理費合理"],
  "cons": ["樓齡已 12 年", "停車位需額外購買"],
  "is_near_match": true,
  "degraded": false
}
```

### 4.10 `POST /api/v1/update_requirements`

**只清除與被修改字段語義相關的 dialogue 片段和 NPP tags**，不做全量清除。

```json
// Request
{"session_id": "uuid", "updated_fields": {"target": "condo in KL"}}

// Response
{
  "status": "updated",
  "cleared_dialogue_segments": ["location_related"],
  "npp_cleared_tags": ["far_from_mrt"],
  "search_session_reset": true,
  "rejected_property_ids_cleared": true
}
```

---

## 5. 核心數據管道 — 完整執行順序

```
[Phase 1] 結構化畫像
    ↓
[Phase 1 末尾異步] 語義對齊層 → 寫入 phase1_data.semantic_tags
    ↓
[Phase 2] 防幻覺多輪對話 + LLM 衝突偵測 + 動態權重計算（Σ = 1.0）
    ↓ FC 觸發
[Step 1] 爬虫層 → 原始 50 條
    ↓
[Step 2] Tier 分級（硬約束，先於數學加權）
    ↓
[Step 3] 數學加權 → Top 10
    ↓
[Step 4] Chutes AI 單次調用 → Top 10 獨立 Remarks
    ↓
[Step 5] 批次返回（5 + 5）
```

### 5.1 語義對齊層（Semantic Alignment Layer）

**觸發時機：** `init_session` 調用後異步執行，完成後寫入 `session_ready`。

```python
async def semantic_alignment(session_id: str, raw_description: str):
    prompt = f"""
    用戶輸入："{raw_description}"
    任務：識別以上輸入中隱含的負面偏好，僅返回以下合法標籤集中的命中項（使用內部 key）。
    合法標籤集（內部 key）：{list(NPP_ENUM_FULL.keys())}
    輸出格式：JSON 數組，如 ["west_facing", "far_from_mrt"]
    若無命中，返回空數組 []。
    """
    result = await safe_llm_call(prompt)
    tags = parse_json_tags(result)  # Pydantic 驗證，失敗返回 []

    dialogue_session = get_dialogue_session(session_id)
    dialogue_session["phase1_data"]["semantic_tags"] = tags
    dialogue_session["phase1_data"]["semantic_alignment_done"] = True
```

**約束：**
- 映射結果**不自動寫入 `npp_tags`**，僅作 Phase 2 system prompt 預熱
- LLM 推斷失敗時，`semantic_tags` 設為 `[]`，返回 `session_ready` 時附帶 `alignment_warning: true`
- 前端輪詢 `session_ready` 直至此異步任務完成

### 5.2 爬虫層

**目標網站優先級（已裁定）：**

| 優先級 | 網站 | 反爬等級 | 策略 |
|---|---|---|---|
| P1 | EdgeProp.my | 🟡 中等 | Playwright + 隨機 UA + 限速 |
| P1 | Mudah.my | 🟡 中等 | BeautifulSoup4 靜態抓取 |
| P2 | PropSocial.my | 🟢 較低 | BeautifulSoup4 靜態抓取 |
| P2 | StarProperty.my | 🟢 較低 | BeautifulSoup4 靜態抓取 |
| P3 | iProperty.com.my | 🔴 高 | 備用，需測試後決定 |
| ❌ 排除 | PropertyGuru.com.my | 🔴 極高 | Cloudflare Bot Management，不納入 |

爬虫參數從 `config.yaml scraper` 節讀取。

**DEMO_MODE 兜底：**
```python
async def fetch_properties(params: SearchParams) -> list[Property]:
    if settings.demo_mode:
        return load_mock_data(params)
    try:
        results = await playwright_scraper.fetch(params)
        if not results:
            raise RuntimeError("Empty result from scraper")
        return results
    except Exception:
        return load_mock_data(params)  # Mock 數據必須過完整管道
```

### 5.3 Tier 分級（先於數學加權執行）

```python
budget_min = phase1_budget * (1 - settings.search.budget_tolerance)
budget_max = phase1_budget * (1 + settings.search.budget_tolerance)

for property in raw_50:
    # 1. 價格硬約束（Python 算法層，絕對不依賴 LLM）
    if not (budget_min <= property.price <= budget_max):
        continue

    # 2. 黑名單攔截（當前 Search Session 作用域）
    if property.property_id in session.rejected_property_ids:
        continue

    # 3. NPP 衝突分級
    npp_conflicts = get_npp_conflicts(property.feature_tags, session.npp_tags)
    if len(npp_conflicts) == 0:
        heap_a.append(property)       # Tier 1 候選
    elif is_minor_conflict(npp_conflicts):
        heap_b.append(property)       # Tier 2 候選
    else:
        pass                          # 嚴重衝突，淘汰
```

### 5.4 數學加權（路徑 X）

**基礎權重向量（已裁定）：**

| 維度 | 基礎權重 | 評分方向 |
|---|---|---|
| `price_fit_score` | **0.30** | 正向，越接近預算中位數得分越高 |
| `security_score` | **0.25** | 正向，門禁保安、低犯罪率 |
| `facilities_score` | **0.20** | 正向，設施匹配度 |
| `lifestyle_proximity_score` | **0.15** | 正向，學校、商圈、診所等 |
| `maintenance_fee_score` | **0.05** | 負向，管理費越高得分越低（取反） |
| `transit_proximity_score` | **0.05** | 正向，MRT/LRT/巴士距離 |

```python
BASE_WEIGHT_VECTOR = {
    "price_fit_score":            0.30,
    "security_score":             0.25,
    "facilities_score":           0.20,
    "lifestyle_proximity_score":  0.15,
    "maintenance_fee_score":      0.05,  # 負向，scoring 時取反
    "transit_proximity_score":    0.05,
}
# Σ = 1.00

def compute_score(property: Property, w: dict) -> float:
    return (
        w["price_fit_score"]            * property.price_fit_score +
        w["security_score"]             * property.security_score +
        w["facilities_score"]           * property.facilities_score +
        w["lifestyle_proximity_score"]  * property.lifestyle_proximity_score +
        w["maintenance_fee_score"]      * (1 - property.normalized_maintenance_fee) +
        w["transit_proximity_score"]    * property.transit_proximity_score
    )

def build_top10(heap_a: list, heap_b: list, weight_vector: dict) -> list:
    scored_a = [(compute_score(p, weight_vector), p, "tier_1") for p in heap_a]
    scored_a.sort(reverse=True)
    if len(scored_a) >= 10:
        return scored_a[:10]
    needed = 10 - len(scored_a)
    scored_b = [(compute_score(p, weight_vector), p, "tier_2") for p in heap_b]
    scored_b.sort(reverse=True)
    return scored_a + scored_b[:needed]
```

> `price_fit_score` 計算：`1 - abs(price - budget_midpoint) / (budget_midpoint * 0.10)`
>
> `flood_risk` 字段不納入加權評分，保留在數據模型中，Tier 2 Remarks 主動披露。

**動態權重乘數（T-06 已裁定）：**

```python
# 乘數不是絕對權重，是對基礎權重的相對放大/縮小系數。
# 應用後統一歸一化至 Σ=1.0。基準乘數為 1.0（不調整）。

GENDER_MULTIPLIERS = {
    "female": {
        "security_score":            1.30,   # 女性對保安配置敏感度更高
        "lifestyle_proximity_score": 1.15,   # 女性更重視生活便利圈
    },
    "male": {},
    "prefer_not_to_say": {}                  # 全部為 1.0，與 male 基準一致
}

IDENTITY_MULTIPLIERS = {
    "first_time_buyer": {
        "price_fit_score":       1.30,       # 首購族預算緊張
        "facilities_score":      1.10,       # 重視設施完整性
        "maintenance_fee_score": 1.20,       # 對管理費敏感
    },
    "investor": {
        "maintenance_fee_score":   1.25,     # 現金流考量
        "transit_proximity_score": 1.30,     # 影響租金與轉售價
    },
    "upgrader": {
        "facilities_score":  1.20,           # 追求高端設施
        "security_score":    1.15,           # 更注重居住品質
    }
}

def apply_dynamic_weights(base: dict, gender: str, identity: str) -> dict:
    """應用動態乘數後歸一化，確保 Σ = 1.0。"""
    adjusted = base.copy()
    for dim, multiplier in GENDER_MULTIPLIERS.get(gender, {}).items():
        adjusted[dim] *= multiplier
    for dim, multiplier in IDENTITY_MULTIPLIERS.get(identity, {}).items():
        adjusted[dim] *= multiplier
    total = sum(adjusted.values())
    assert total > 0, "權重總和為零，歸一化失敗"
    normalized = {k: v / total for k, v in adjusted.items()}
    assert abs(sum(normalized.values()) - 1.0) < 1e-9, "歸一化驗證失敗"
    return normalized
```

**歸一化驗證示例（female + first_time_buyer）：**

| 維度 | 基礎權重 | Gender 乘數 | Identity 乘數 | 調整後 | 歸一化後（Σ=1.0） |
|---|---|---|---|---|---|
| price_fit | 0.30 | 1.00 | 1.30 | 0.390 | **0.318** |
| security | 0.25 | 1.30 | 1.00 | 0.325 | **0.265** |
| facilities | 0.20 | 1.00 | 1.10 | 0.220 | **0.179** |
| lifestyle | 0.15 | 1.15 | 1.00 | 0.173 | **0.141** |
| maintenance | 0.05 | 1.00 | 1.20 | 0.060 | **0.049** |
| transit | 0.05 | 1.00 | 1.00 | 0.050 | **0.041** |
| **總計** | **1.00** | — | — | **1.218** | **1.000** ✅ |

### 5.5 Chutes AI 單次調用生成 Remarks

```python
class PropertyRemark(BaseModel):
    property_id: str
    tier: Literal["tier_1", "tier_2"]
    remarks: str
    missing_features: list[str]   # Tier 1 時為空列表 []
    remedy: Optional[str]         # Tier 1 時為 null

class RemarksResponse(BaseModel):
    results: list[PropertyRemark]
```

**Prompt 約束：**
- Tier 1：正向推薦敘述，`missing_features: []`, `remedy: null`
- Tier 2：防禦性敘述，坦誠說明瑕疵，提供 remedy，洪水高風險必須主動披露
- 語氣風格遵循 `phase1_data.agent_style`（`professional` / `friendly` / `active`）

### 5.6 批次返回規則

- 標準 5+5；不足 10 條時第二批返回 N 條（N < 5），`has_more: false`
- `tier3_triggered` 僅在總結果數為 0 時觸發
- `batch_index` 每次重新搜索歸 1

---

## 6. 核心機制詳細規範

### 6.1 行政區拓撲擴張

**觸發條件：** 當前 `expansion_level` 下結果為 0，且 `expansion_level < 3`。

```
Level 0：用戶目標行政區
Level 1：相鄰行政區（共享邊界）
Level 2：次級輻射區（Level 1 的相鄰區，排除已搜索區）
Level 3：泛市區（整個縣/市）
超出 Level 3 → TIER3_NO_RESULT
```

**約束：**
- 拓撲擴張**不放寬預算**，±10% 在所有級別保持不變
- `Keep Memories` 後 Search Session 重置，擴張從 Level 0 重新開始
- 擴張依賴 `TOPOLOGY_GRAPH`（見第 8 節），禁止坐標/公里制計算

**終結安全約束：** 任何擴張路徑的終點必須為 `BATCH_1_DISPLAY` 或 `TIER3_NO_RESULT`，嚴禁回繞至 `ACTION_REQUIRED_UI`。

### 6.2 NPP 決策網關 — ACTION_REQUIRED_UI

**觸發條件：** 前端調用 `POST /api/v1/reject_all`（所有結果已拒絕）。

**狀態機：**

| 當前狀態 | 觸發事件 | 後續狀態 |
|---|---|---|
| `ALL_REJECTED` | 系統收到 `reject_all` | `ACTION_REQUIRED_UI` |
| `ACTION_REQUIRED_UI` | 用戶選「New Prompt」 | `PHASE_1_INITIAL`（清空全部 3 類 Session） |
| `ACTION_REQUIRED_UI` | 用戶選「Keep Memories」 | `CHATTING`（Phase 2，保留 NPP + dialogue） |
| `CHATTING` | 再次觸發 FC | `SEARCHING`（從 Level 0 開始） |

### 6.3 NPP 更新與學習閉環

**時序：**
```
reject_single × N → pending_rejection_buffer 累積
reject_all 觸發 →
    獨立 LLM 調用：將 buffer 中所有原因映射至 NPP_ENUM（內部 key）
    → 更新 npp_tags（追加，去重）
    → 返回 action_required
```

**連續消息時間窗口（防竟態）：**

```python
async def handle_rejection_message(session_id: str, message: str, timestamp: float):
    npp_session = get_npp_session(session_id)
    last = npp_session.last_rejection_message
    window = settings.session.rejection_continuity_window_seconds  # 5.0 秒
    if last and (timestamp - last["timestamp"]) <= window:
        merged = await llm_judge_continuity(last["content"], message)
        if merged:
            npp_session.pending_rejection_buffer[-1]["content"] += f"；{message}"
        else:
            npp_session.pending_rejection_buffer.append({"content": message, "timestamp": timestamp})
    else:
        npp_session.pending_rejection_buffer.append({"content": message, "timestamp": timestamp})
    npp_session.last_rejection_message = {"content": message, "timestamp": timestamp}
```

### 6.4 NPP 枚舉標籤集（T-04 已裁定，開發前凍結）

```python
# 格式：internal_key -> display_label
# 最終集合不超過 40 個標籤
# 禁止運行時動態擴展，標籤不得重叠

NPP_ENUM_FULL: dict[str, str] = {
    # 朝向類
    "west_facing":          "西晒",
    "east_facing":          "東晒",
    "no_natural_light":     "無自然採光",
    "no_balcony":           "無陽台",           # 馬來西亞濕熱氣候，陽台為強需求

    # 樓層類
    "high_floor":           "高樓層",
    "low_floor":            "低樓層",
    "top_floor":            "頂樓",
    "ground_floor":         "地層",

    # 交通類
    "far_from_mrt":         "遠地鐵",
    "far_from_bus":         "遠巴士站",
    "far_from_highway":     "遠高速入口",

    # 設施類
    "no_pool":              "無游泳池",
    "no_gym":               "無健身房",
    "no_security":          "無保安",
    "no_parking":           "無停車位",
    "no_visitor_parking":   "無訪客停車位",      # 高頻投訴項
    "frequent_lift_issues": "電梯經常故障",      # 高層樓盤特有痛點

    # 周邊類
    "far_from_school":      "遠學校",
    "far_from_hospital":    "遠醫院",
    "far_from_mall":        "遠商場",
    "near_industrial":      "近工業區",
    "noise_area":           "噪音區",
    "near_cemetery":        "近墓地",           # 華人買家敏感度極高
    "near_power_lines":     "近高壓電線",        # 健康顧慮，影響轉售
    "near_mosque":          "近清真寺",          # 禮拜時段噪音（非信仰因素）

    # 房型類
    "open_kitchen":         "開放式廚房",
    "no_storage":           "無儲藏室",
    "small_unit":           "小戶型",

    # 樓盤狀態類
    "high_tenant_mix":      "租戶混雜",          # 出租比例過高，影響居住品質
    "high_vacancy":         "空置率高",          # 反映樓盤吸引力不足

    # 樓齡類
    "old_building":         "樓齡過高",
    "incomplete_project":   "未完工項目",

    # 管理類
    "high_maintenance_fee": "高管理費",
    "low_maintenance":      "低維護水平",
}

# 僅 internal_key 集合用於比對
NPP_ENUM = set(NPP_ENUM_FULL.keys())
```

**映射失敗處理：**
- LLM 無法映射 → 提示用戶重新表述，禁止靜默忽略
- 禁止動態擴展枚舉集，保持精確比對穩定性

### 6.5 Function Calling 觸發邏輯

**Phase 1 已有字段（直接注入 system prompt，不再追問）：**
預算、identity、gender、agent_style、目標區域

**FC 字段處理：**

| 字段 | 類型 | 缺失時行為 |
|---|---|---|
| `property_type` | 必填 | 未填則**不作過濾條件**，FC 照常觸發 |
| `must_have_features` | 選填 | 置 null |
| `floor_preference` | 選填 | 置 null |
| `purchase_purpose` | 選填 | 置 null |

**追問上限：** `fc_trigger_attempts >= 2` 時強制觸發 FC。

### 6.6 PENDING_CONFIRMATION

**偵測方式：** LLM 在 `/api/v1/chat` 回覆中輸出結構化 JSON，後端解析 `conflict_detected` 字段。

**執行規則：**
- 系統進入 `PENDING_CONFIRMATION`，禁止靜默覆寫 Phase 1 字段
- 確認「是」→ 調用 `update_requirements`，只清除相關字段
- 確認「否」→ 保持原有字段
- 期間後端阻斷 FC 搜索觸發

---

## 7. Chutes AI 容錯與並發控制（T-05 已裁定）

```python
import asyncio
from asyncio import Semaphore

# 根據 config.yaml llm.max_concurrent_calls 讀取
llm_semaphore = Semaphore(settings.llm.max_concurrent_calls)

async def safe_llm_call(payload: dict) -> dict:
    async with llm_semaphore:
        return await call_chutes_ai(payload)

async def call_chutes_ai(payload: dict) -> dict:
    """指數退避重試：5s → 10s → 20s。"""
    for attempt in range(3):
        try:
            response = await chutes_client.messages.create(**payload)
            validated = parse_and_validate(response)  # Pydantic Schema 驗證
            return validated
        except RateLimitError:
            if attempt < 2:
                wait = 5 * (2 ** attempt)   # 5s, 10s, 20s
                await asyncio.sleep(wait)
            else:
                notify_frontend_degraded()
                return degraded_math_only_result()
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(5 * (2 ** attempt))
            else:
                notify_frontend_degraded()
                return degraded_math_only_result()
```

**降級結果規範：** `degraded: true`，每條 `remarks: null`，排序依數學加權得分降序。

**DEMO_MODE 觸發條件：** 爬虫異常 **或** `RateLimitError`（與超時錯誤同等處理）。

**本 session 內 LLM 調用點估算：**

| 調用點 | 頻率 | Token 估算 |
|---|---|---|
| 語義對齊層（init_session） | 每 session 1次 | ~500 tokens |
| FC 追問（Phase 2 chat） | 每輪 1次，最多 2輪 | ~800 tokens/輪 |
| Remarks 生成（Top 10） | 每次搜索 1次 | ~2000 tokens |
| NPP 更新（reject_all） | 每次全拒絕 1次 | ~1000 tokens |
| 連續消息合並判斷 | 低頻 | ~200 tokens |

單次完整會話約消耗 **5,000–6,000 tokens**。

> **啟動前行動：** 登錄 Chutes AI 控制台記錄實際 RPM 與 TPM，填入 `config.yaml llm.max_concurrent_calls`。

---

## 8. 行政區拓撲圖（T-07 已裁定，開發前凍結）

```python
TOPOLOGY_GRAPH = {

    # ─── 柔佛巴魯 ────────────────────────────────────────────
    "johor_bahru_city": {
        "display_name": "新山市區",
        "level_1_adjacent": ["skudai", "tebrau", "larkin", "stulang"],
        "level_2_secondary": ["kulai", "pasir_gudang", "senai", "gelang_patah"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "skudai": {
        "display_name": "士古來",
        "level_1_adjacent": ["johor_bahru_city", "gelang_patah", "senai"],
        "level_2_secondary": ["kulai", "tebrau", "larkin"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "tebrau": {
        "display_name": "地不佬",
        "level_1_adjacent": ["johor_bahru_city", "pasir_gudang", "stulang"],
        "level_2_secondary": ["kota_tinggi", "larkin", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "iskandar_puteri": {
        "display_name": "依斯干達公主城（舊稱：努沙再也）",
        "level_1_adjacent": ["gelang_patah", "skudai", "johor_bahru_city"],
        "level_2_secondary": ["kulai", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "gelang_patah": {
        "display_name": "格令勿刹",
        "level_1_adjacent": ["iskandar_puteri", "skudai", "kulai"],
        "level_2_secondary": ["johor_bahru_city", "senai"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "pasir_gudang": {
        "display_name": "巴西古當",
        "level_1_adjacent": ["tebrau", "kota_tinggi"],
        "level_2_secondary": ["johor_bahru_city", "stulang"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "senai": {
        "display_name": "士乃",
        "level_1_adjacent": ["skudai", "kulai", "gelang_patah"],
        "level_2_secondary": ["johor_bahru_city", "iskandar_puteri"],
        "level_3_pan_urban": "johor_bahru_district"
    },
    "kulai": {
        "display_name": "古來",
        "level_1_adjacent": ["senai", "gelang_patah", "skudai"],
        "level_2_secondary": ["iskandar_puteri", "johor_bahru_city"],
        "level_3_pan_urban": "johor_bahru_district"
    },

    # ─── 吉隆坡 ──────────────────────────────────────────────
    "kuala_lumpur_city": {
        "display_name": "吉隆坡市中心（KLCC / Bukit Bintang）",
        "level_1_adjacent": ["mont_kiara", "chow_kit", "ampang", "pudu"],
        "level_2_secondary": ["petaling_jaya", "kepong", "puchong", "wangsa_maju"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "mont_kiara": {
        "display_name": "孟沙（Mont Kiara）",
        "level_1_adjacent": ["kuala_lumpur_city", "kepong", "sri_hartamas"],
        "level_2_secondary": ["petaling_jaya", "damansara"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "ampang": {
        "display_name": "安邦",
        "level_1_adjacent": ["kuala_lumpur_city", "wangsa_maju", "cheras"],
        "level_2_secondary": ["pandan_indah", "pudu"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },
    "cheras": {
        "display_name": "蕉賴",
        "level_1_adjacent": ["ampang", "pudu", "sg_besi"],
        "level_2_secondary": ["puchong", "kajang"],
        "level_3_pan_urban": "kuala_lumpur_federal_territory"
    },

    # ─── 八打靈再也 ──────────────────────────────────────────
    "petaling_jaya": {
        "display_name": "八打靈再也（PJ）",
        "level_1_adjacent": ["subang_jaya", "damansara", "kuala_lumpur_city"],
        "level_2_secondary": ["puchong", "shah_alam", "mont_kiara"],
        "level_3_pan_urban": "petaling_district"
    },
    "subang_jaya": {
        "display_name": "莎阿南花園（Subang Jaya）",
        "level_1_adjacent": ["petaling_jaya", "puchong", "shah_alam"],
        "level_2_secondary": ["damansara", "kuala_lumpur_city"],
        "level_3_pan_urban": "petaling_district"
    },
    "damansara": {
        "display_name": "白沙羅（Damansara）",
        "level_1_adjacent": ["petaling_jaya", "mont_kiara", "subang_jaya"],
        "level_2_secondary": ["kuala_lumpur_city", "kepong"],
        "level_3_pan_urban": "petaling_district"
    },

    # ─── 泛市區節點（Level 3 終點，非搜索起點）─────────────────
    "johor_bahru_district": {
        "display_name": "新山縣（全域）",
        "is_pan_urban": True
    },
    "kuala_lumpur_federal_territory": {
        "display_name": "吉隆坡聯邦直轄區（全域）",
        "is_pan_urban": True
    },
    "petaling_district": {
        "display_name": "八打靈縣（全域）",
        "is_pan_urban": True
    },
}

def get_search_districts(target_district: str, expansion_level: int) -> list[str]:
    """
    根據目標區和擴張級別，返回應當納入搜索的行政區列表。
    """
    if target_district not in TOPOLOGY_GRAPH:
        raise ValueError(f"未知行政區：{target_district}")

    node = TOPOLOGY_GRAPH[target_district]

    if expansion_level == 0:
        return [target_district]
    elif expansion_level == 1:
        return [target_district] + node.get("level_1_adjacent", [])
    elif expansion_level == 2:
        return (
            [target_district]
            + node.get("level_1_adjacent", [])
            + node.get("level_2_secondary", [])
        )
    elif expansion_level == 3:
        pan_urban = node.get("level_3_pan_urban")
        return [pan_urban] if pan_urban else []
    else:
        return []
```

**拓撲圖約束：**
1. 地名必須以 `administrative_district` 字段的內部 key（snake_case）為準，前端顯示使用 `display_name`
2. Mock 數據中的 `administrative_district` 字段必須從以上節點 key 中取值，不允許自由字符串
3. Level 3 的 `pan_urban` 節點僅為擴張終點標識，不作為用戶可選的搜索起點
4. 已有節點的邻接關係不得在運行時修改，須走代碼變更流程

---

## 9. Mock 數據規範

### 9.1 Property 數據模型（爬虫輸出字段契約）

```python
class Property(BaseModel):
    property_id: str
    title: str
    price: float
    location: str
    administrative_district: str           # 必須為 TOPOLOGY_GRAPH 節點 key
    distance_to_mrt_km: float
    is_gated_guarded: bool
    security_level: Literal["high", "medium", "low"]
    facilities: list[str]
    facilities_score: float
    nearby_schools: int
    nearby_tuition_centers: int
    nearby_malls: int
    nearby_clinics: int
    lifestyle_proximity_score: float
    maintenance_fee_per_sqft: float
    normalized_maintenance_fee: float      # 歸一化後用於評分
    flood_risk: Literal["high", "medium", "low", "unknown"]  # 不納入評分
    feature_tags: list[str]                # 必須為 NPP_ENUM（internal key）的子集
    price_fit_score: float
    security_score: float
    transit_proximity_score: float
    floor_level: int
    facing: str
    bedrooms: int
    bathrooms: int
    url: str
    source: str
    is_mock: bool
```

### 9.2 Mock 數據集最低要求

- 總量：≥ 30 條
- 質量：≥ 80% 滿足「預算 ±10% + 無 NPP 衝突」（基於空 NPP 狀態）
- 覆蓋：每個 `NPP_ENUM` 標籤至少在 2 條數據中出現
- 地理：分布於至少 3 個不同行政區（Level 0、1、2），確保拓撲擴張邏輯可演示
- `administrative_district` 字段必須與 `TOPOLOGY_GRAPH` 節點 key 完全對應

---

## 10. 關鍵開發約束（不可違反）

1. **預算硬約束在 Python 算法層執行**，絕對不依賴 LLM 判斷價格
2. **Tier 分級必須先於數學加權執行**，NPP 衝突房源無法進入 Top 10
3. **NPP 枚舉集在開發前凍結**，運行時禁止動態擴展
4. **NPP 清零時必須同步清洗 `dialogue_history` 中的相關 utterance**
5. **Mock 數據必須過完整管道**，不允許繞過 Tier 分級和數學加權
6. **`batch_index` 重置僅在新的獨立批次序列開始時執行**，每次重新搜索歸 1
7. **所有 LLM 輸出必須經過 Pydantic Schema 驗證**，驗證失敗觸發重試而非靜默通過
8. **`reject_all` 後禁止自動重搜**，必須進入 `ACTION_REQUIRED_UI`
9. **拓撲擴張必須嚴格按行政區劃邏輯遞進**，禁止坐標/公里制計算
10. **動態權重乘數應用後必須歸一化**，`assert abs(sum(final_weights.values()) - 1.0) < 1e-9`
11. **`Rejected_Property_IDs` 作用域嚴格限於當前 Search Session**，Search Session 重置時同步清空
12. **語義對齊完成前不得響應 `session_ready: ready`**，前端輪詢直至確認完成
13. **`PENDING_CONFIRMATION` 期間後端阻斷 FC 搜索路徑**
14. **`update_requirements` 只清除與被修改字段相關的 dialogue 片段和 NPP tags**，不做全量清除
15. **`property_type` 為 null 時不作過濾條件**，不阻塞 FC 觸發
16. **`RateLimitError` 與超時錯誤同等處理**，觸發 DEMO_MODE 兜底
17. **LLM 並發請求必須受 `asyncio.Semaphore` 限制**，上限從 `config.yaml` 讀取
18. **NPP 所有比對和存儲均使用 internal key（snake_case）**，display_label 僅用於前端顯示和 LLM Prompt
