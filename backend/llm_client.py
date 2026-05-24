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

# Semaphore for LLM concurrent call limit
# Read from config.yaml in production
llm_semaphore = asyncio.Semaphore(3)

# FIX B5: read credentials from .env per Backend.md §2 instead of hardcoded placeholder.
CHUTES_AI_API_KEY = os.getenv("CHUTES_AI_API_KEY", "")
CHUTES_AI_BASE_URL = os.getenv("CHUTES_AI_BASE_URL", "https://llm.chutes.ai/v1")

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

    async def chat(self, messages: list[dict], model: str = "deepseek-ai/DeepSeek-V3-0324") -> ChatLLMOutput:
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

    async def semantic_alignment(self, description: str) -> dict[str, list[str]]:
        """
        Identify BOTH positive and negative property preferences.

        Returns {"positive": [...PPP keys...], "negative": [...NPP keys...]}.
        On any failure returns {"positive": [], "negative": []}.
        """
        from positive_enum import PPP_ENUM_FULL

        # Escape description so embedded quotes don't break the prompt JSON
        safe_desc = json.dumps(description, ensure_ascii=False)

        messages = [
            {
                "role": "user",
                "content": f"""
從以下用戶輸入中同時識別「正面偏好」與「負面偏好」。

用戶輸入：{safe_desc}

規則：
- 「我不要 X」「沒有 X」「避免 X」→ 放入 negative
- 「我要 X」「必須有 X」「希望 X」「需要 X」→ 放入 positive
- 同一語義若同時被否定與肯定（如 "no west-facing, need east-facing"），各取其對應極性的 tag
- 只能使用以下白名單 tag（內部 key）

合法 positive tag：{list(PPP_ENUM_FULL.keys())}
合法 negative tag：{list(NPP_ENUM_FULL.keys())}

僅輸出 JSON，不要任何說明文字：
{{"positive": ["needs_security"], "negative": ["west_facing"]}}
若該極性無命中：對應陣列為 []。
                """,
            }
        ]

        try:
            payload = {
                "model": "deepseek-ai/DeepSeek-V3-0324",
                "messages": messages,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            pos = [t for t in parsed.get("positive", []) if t in PPP_ENUM_FULL]
            neg = [t for t in parsed.get("negative", []) if t in NPP_ENUM_FULL]
            return {"positive": pos, "negative": neg}

        except Exception as e:
            print(f"Semantic alignment failed: {e}")
            return {"positive": [], "negative": []}


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
                "model": "deepseek-ai/DeepSeek-V3-0324",
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
                "model": "deepseek-ai/DeepSeek-V3-0324",
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

