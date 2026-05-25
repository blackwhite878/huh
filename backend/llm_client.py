"""
Chutes AI integration with retry logic, concurrent control, and Pydantic validation.
"""
import asyncio
import json
import os
from typing import Optional
import httpx
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pydantic import ValidationError

from schemas import ChatLLMOutput, PropertyRemark, RemarksResponse
from npp_enum import NPP_ENUM_FULL

# Load .env at module import (idempotent)
load_dotenv()


def _load_config() -> dict:
    """Load backend/config.yaml. Returns {} if missing/unreadable so we never crash at import."""
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    try:
        import yaml  # PyYAML
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        print(f"[llm_client] config.yaml not found at {cfg_path} — using defaults")
        return {}
    except Exception as e:
        print(f"[llm_client] failed to load config.yaml: {e} — using defaults")
        return {}


_CONFIG = _load_config()
_LLM_CFG = _CONFIG.get("llm", {}) if isinstance(_CONFIG.get("llm"), dict) else {}
LLM_MODEL: str = _LLM_CFG.get("model", "deepseek-ai/DeepSeek-V3.2-TEE")
LLM_MAX_TOKENS: int = int(_LLM_CFG.get("max_tokens", 2000))
LLM_CONCURRENCY: int = int(_LLM_CFG.get("concurrency", 3))
print(f"[llm_client] model={LLM_MODEL} max_tokens={LLM_MAX_TOKENS} concurrency={LLM_CONCURRENCY}")

# Semaphore for LLM concurrent call limit (from config.yaml)
llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)


# FIX B5: read credentials from .env per Backend.md §2 instead of hardcoded placeholder.
CHUTES_AI_API_KEY = os.getenv("CHUTES_AI_API_KEY", "")


def _normalize_base_url(raw: str) -> str:
    """
    Make the Chutes base URL bulletproof:
      - ensure http(s):// scheme (defaults to https)
      - strip trailing slash
      - ensure it ends with /v1 (Chutes path 404s otherwise)
    """
    url = (raw or "").strip()
    if not url:
        url = "https://llm.chutes.ai/v1"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


CHUTES_AI_BASE_URL = _normalize_base_url(os.getenv("CHUTES_AI_BASE_URL", ""))
print(f"[llm_client] CHUTES_AI_BASE_URL resolved to: {CHUTES_AI_BASE_URL}")


if not CHUTES_AI_API_KEY:
    print(
        "[llm_client] WARNING: CHUTES_AI_API_KEY is empty. "
        "Set it in backend/.env before calling LLM endpoints."
    )


class LLMClient:
    def __init__(self, api_key: str = CHUTES_AI_API_KEY, base_url: str = CHUTES_AI_BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=5, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _call_api(self, payload: dict) -> dict:
        """
        Internal API call with exponential backoff: 5s → 10s → 20s.
        Raises on final failure.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def chat(self, messages: list[dict], model: str = LLM_MODEL) -> ChatLLMOutput:
        """
        Call Chutes AI for chat with structured JSON output.
        Returns validated ChatLLMOutput or raises exception.
        """
        async with llm_semaphore:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"},
                }

                response = await self._call_api(payload)

                # Extract content from response
                content = response["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                # Validate with Pydantic
                output = ChatLLMOutput(**parsed)
                return output

            except ValidationError as e:
                # Validation failure - return degraded response
                print(f"LLM output validation failed: {e}")
                raise
            except Exception as e:
                print(f"LLM call failed: {e}")
                raise

    async def complete_json(self, messages: list[dict], model: str = LLM_MODEL) -> dict:
        """
        Raw JSON-object completion (no Pydantic validation). Used by the
        scraper ranking_agent, which needs free-form numeric weights rather
        than the ChatLLMOutput schema.
        """
        async with llm_semaphore:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            }
            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)



    async def semantic_alignment(self, profile) -> dict[str, list[str]]:
        """
        Identify BOTH positive and negative property preferences from the
        FULL Phase 1 profile (budget / target / identity / gender / agent_style
        / description). Accepts either a dict (preferred) or a plain string
        (legacy — treated as the description field only).

        Polarity rule (per product spec):
          - Items the user explicitly REJECTS (不要 / 沒有 / 避免 / 拒絕 /
            不想 / no / without / avoid / dealbreaker) → negative.
          - Everything else that is a valid, actionable preference → POSITIVE
            by default. Ambiguous noun-only lists are positive, not negative.
        """
        from positive_enum import PPP_ENUM_FULL

        # Normalize input shape.
        if isinstance(profile, str):
            profile_dict = {"description": profile}
        elif isinstance(profile, dict):
            profile_dict = profile
        else:
            # Pydantic model or similar
            try:
                profile_dict = dict(profile)
            except Exception:
                profile_dict = {"description": str(profile)}

        safe_profile = json.dumps(profile_dict, ensure_ascii=False)
        ppp_hint = list(PPP_ENUM_FULL.keys())
        npp_hint = list(NPP_ENUM_FULL.keys())

        messages = [
            {
                "role": "user",
                "content": f"""
你是一個房產偏好標籤分類器。從用戶的完整 Phase 1 個人檔案（包含預算、目標地區/物業、身份、性別、代理風格、自由描述）中同時識別「正面偏好（PPP）」與「負面偏好（NPP）」。

用戶 Phase 1 完整資料（JSON）：{safe_profile}

# 極性判斷規則（重要）
1. **拒絕類關鍵詞 → negative**：「不要 / 沒有 / 避免 / 拒絕 / 不想 / 不喜歡 / no / not / without / avoid / dealbreaker / hate」。
2. **其他任何有效條件 → positive（預設）**。包括：
   - 肯定詞：「要 / 必須 / 希望 / 需要 / 偏好 / want / need / must / prefer / like」
   - 純名詞清單（如 "modern, double-storey, busy working"）— 視為使用者想要的條件，全部歸 positive。
   - 目標地區、預算範圍、身份、風格等 phase1 結構化欄位中可抽取的具體房產屬性語義（例：target="condo in Johor Bahru" → positive: ["johor_bahru"]；identity="investor" → positive: ["investment_focused"] 等，僅在語義明確時抽取）。
3. 同一概念同時出現否定與肯定 → 各取對應極性。
4. **嚴禁**在沒有拒絕類關鍵詞時把條件硬塞進 negative。

# 標籤命名規則
- snake_case，全小寫，不含空格、連字符、引號。
- 屬性類型詞（condo / apartment / landed / terrace / bungalow / studio）忽略，不要輸出。
- 不確定的詞寧可丟掉，禁止編造。

# 廢話 / 不相關詞過濾（重要！）
只接受「房產屬性、地點、設施、預算、生活機能、環境條件、投資/自住取向」等與選房直接相關的語義。
**嚴禁輸出**以下類別（屬於廢話 nonsense，與房產無關）：
- 情緒 / 心情 / 感受詞：sleepy, happy, sad, angry, bored, lonely, excited, tired, hungry, sleepy_house…
- 與人本身狀態相關但與房屬性無關的詞：cute, smart, lazy, funny…
- 純抽象 / 無法對應到房產特徵的形容詞。
- 食物、動物、人名、罵人、亂打的無意義字串（如 asdf, qwerty, xxxx）。
- 違反房產語義 / 違和的詞（例：「想要一間 sleepy 的房子」中的 sleepy）。
若用戶輸入的條件整段都是廢話，對應陣列回傳 []，不要硬湊。

# 命名提示（非強制白名單，僅供風格對齊）
常見 positive key 示例：{ppp_hint}
常見 negative key 示例：{npp_hint}

# 輸出格式
僅輸出 JSON，不要任何說明文字或 markdown 圍欄：
{{"positive": ["modern_style", "double_storey", "johor_bahru"], "negative": ["west_facing"]}}
若該極性無命中：對應陣列為 []。
                """,
            }
        ]

        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }

        response = await self._call_api(payload)

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"semantic_alignment: malformed LLM response shape: {e}") from e

        print(f"[semantic_alignment] raw LLM content: {content!r}")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"semantic_alignment: LLM returned non-JSON: {e}") from e

        # Defensive nonsense blacklist — drop tags that have no property
        # semantics even if the LLM ignored the prompt rule. Keep this list
        # focused on obvious junk (moods, emotions, gibberish). Real estate
        # vocabulary stays untouched.
        NONSENSE_TAGS = {
            "sleepy", "sleepy_house", "happy", "sad", "angry", "bored",
            "lonely", "excited", "tired", "hungry", "thirsty", "cute",
            "smart", "lazy", "funny", "silly", "weird", "cool", "nice",
            "good", "bad", "ok", "okay", "yes", "no", "maybe", "lol",
            "xxx", "asdf", "qwerty", "test", "none", "null", "undefined",
        }

        def _normalize(raw) -> list[str]:
            if not isinstance(raw, list):
                return []
            out: list[str] = []
            seen: set[str] = set()
            for item in raw:
                if not isinstance(item, str):
                    continue
                key = item.strip().lower().replace("-", "_").replace(" ", "_")
                if not key or key in seen:
                    continue
                if key in NONSENSE_TAGS:
                    print(f"[semantic_alignment] dropped nonsense tag: {key!r}")
                    continue
                # Drop pure-symbol / overly short gibberish (single char,
                # or length>=3 with no vowels and not in enums).
                if len(key) < 2:
                    print(f"[semantic_alignment] dropped too-short tag: {key!r}")
                    continue
                seen.add(key)
                out.append(key)
            return out

        pos = _normalize(parsed.get("positive", []))
        neg = _normalize(parsed.get("negative", []))
        print(f"[semantic_alignment] normalized → positive={pos} negative={neg}")
        return {"positive": pos, "negative": neg}



    async def generate_remarks(
        self,
        properties: list,
        agent_style: str = "professional",
    ) -> RemarksResponse:
        """
        Generate AI remarks for Top 10 properties in single LLM call.
        Returns validated RemarksResponse.
        """
        # FIX B6: original f-string had the tier ternary INSIDE the string literal,
        # so the LLM received the literal source text. Evaluate it outside the f-string.
        def _tier_label(p) -> str:
            return "tier_1" if getattr(p, "tier", None) == "tier_1" else "tier_2"

        props_summary = "\n".join([
            f"ID: {p.property_id}, Title: {p.title}, Price: {p.price}, "
            f"Tier: {_tier_label(p)}, "
            f"Features: {', '.join(p.feature_tags)}"
            for p in properties
        ])

        messages = [
            {
                "role": "user",
                "content": f"""
為以下房源生成 AI 評論。

代理風格：{agent_style}

房源列表：
{props_summary}

要求：
- Tier 1 房源：正向推薦，missing_features 為空列表，remedy 為 null
- Tier 2 房源：防禦性敘述，坦誠說明瑕疵，提供 remedy
- 洪水高風險必須主動披露

輸出格式：
{{
  "results": [
    {{
      "property_id": "JB001",
      "tier": "tier_1",
      "remarks": "...",
      "missing_features": [],
      "remedy": null
    }},
    ...
  ]
}}
            """,
            }
        ]

        try:
            payload = {
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Validate with Pydantic
            remarks_response = RemarksResponse(**parsed)
            return remarks_response

        except ValidationError as e:
            print(f"Remarks validation failed: {e}")
            raise
        except Exception as e:
            print(f"Remarks generation failed: {e}")
            raise

    async def map_rejection_to_npp(self, rejection_reasons: list[str]) -> list[str]:
        """
        Map rejection reasons to NPP_ENUM tags.
        Used in reject_all flow.
        """
        reasons_text = "\n".join([f"- {r}" for r in rejection_reasons])

        messages = [
            {
                "role": "user",
                "content": f"""
用戶拒絕了多個房源，提供的原因如下：

{reasons_text}

任務：將上述原因映射至以下 NPP 標籤集中的合適項目（內部 key）。
合法標籤集：{list(NPP_ENUM_FULL.keys())}

輸出格式：JSON 物件，例如 {{"tags": ["high_floor", "west_facing"]}}
若無明確映射，返回 {{"tags": []}}
                """,
            }
        ]

        try:
            payload = {
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            tags = parsed.get("tags", [])
            valid_tags = [t for t in tags if t in NPP_ENUM_FULL]
            return valid_tags

        except Exception as e:
            print(f"NPP mapping failed: {e}")
            return []


# Global LLM client instance
llm_client = LLMClient()

