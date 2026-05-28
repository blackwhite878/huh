"""
backend/search_stream_route.py
==============================
Drop-in: SSE 版搜尋進度端點。前端用 EventSource 訂閱，不再 polling。

掛載方式（在 backend/main.py 中）：

    from backend.search_stream_route import router as search_stream_router
    app.include_router(search_stream_router)

需要的相依：你的專案已有的 search registry（記錄 search_id -> status dict）。
本檔假設可從 backend.search_registry import get_search_status(search_id) -> dict|None
回傳形如：
    {
        "status": "running" | "done" | "error",
        "progress": {"done": 42, "total": 120},
        "current": {"region": "johor", "type": "condo"},
        "rows": 318,
        "error": None,
    }

如果你的 registry 函式名不同，改下面這行 import 即可。
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

try:
    from backend.search_registry import get_search_status  # type: ignore
except Exception:  # 兼容不同路徑
    from search_registry import get_search_status  # type: ignore

router = APIRouter()

# 兩次 push 之間最小間隔（秒）。狀態沒變就不 push，但每 KEEPALIVE 秒至少送一個 comment 防 proxy 斷線。
PUSH_INTERVAL = 0.5
KEEPALIVE = 15.0
MAX_DURATION = 60 * 60  # 1 小時硬上限


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


async def _stream(search_id: str, request: Request) -> AsyncIterator[bytes]:
    last_payload: str | None = None
    last_push = 0.0
    started = asyncio.get_event_loop().time()

    while True:
        if await request.is_disconnected():
            return

        now = asyncio.get_event_loop().time()
        if now - started > MAX_DURATION:
            yield _sse("timeout", {"search_id": search_id})
            return

        status = get_search_status(search_id)
        if status is None:
            yield _sse("error", {"error": "unknown search_id", "search_id": search_id})
            return

        payload = json.dumps(status, ensure_ascii=False, sort_keys=True)
        changed = payload != last_payload

        if changed:
            yield _sse("status", status)
            last_payload = payload
            last_push = now
        elif now - last_push > KEEPALIVE:
            # 保活註解，瀏覽器/反向代理不會視為訊息
            yield b": keepalive\n\n"
            last_push = now

        if status.get("status") in ("done", "error"):
            return

        await asyncio.sleep(PUSH_INTERVAL)


@router.get("/api/v1/search_stream/{search_id}")
async def search_stream(search_id: str, request: Request) -> StreamingResponse:
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",  # nginx 防 buffer
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        _stream(search_id, request),
        media_type="text/event-stream",
        headers=headers,
    )
