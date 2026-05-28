# Patch v3 — search_status 噪音清理（方案 C）

## 症狀
uvicorn access log 被 `GET /api/v1/search_status/<id> HTTP/1.1 200 OK` 洗版，
因為前端每 1~2 秒輪詢一次搜尋進度。

## 修法（兩段一起做）

### A. 後端過濾 access log
新增 `backend/access_log_filter.py`，在 `backend/main.py` 啟動時呼叫一次：

```python
from backend.access_log_filter import install_access_log_filter
install_access_log_filter()
```

效果：`/api/v1/search_status/<id>` 的 200 OK 行被丟掉，其他路徑照舊。
非 200（404/500）仍會印，方便發現真錯。

### B. 前端改用 SSE，不再 polling
1. 後端掛 `backend/search_stream_route.py` 的 router：
   ```python
   from backend.search_stream_route import router as search_stream_router
   app.include_router(search_stream_router)
   ```
   端點：`GET /api/v1/search_stream/<search_id>`
   - 只在 status payload 真的變化時 push
   - 每 15s 送一個 SSE comment 保活
   - status 變 `done` / `error` 自動關閉
   - 1 小時硬上限

2. 前端用 `frontend/useSearchStream.ts` 取代舊的 polling hook：
   ```tsx
   const { status, done, error } = useSearchStream(searchId);
   ```
   - 預設用 `EventSource`
   - 環境不支援時 fallback 到 5s polling（仍然遠少於現在的 1~2s）

舊的 `/api/v1/search_status/<id>` 端點保留，給 SSE fallback 與外部腳本使用。

## 檔案
- `backend/access_log_filter.py` — 新增
- `backend/search_stream_route.py` — 新增
- `frontend/useSearchStream.ts` — 新增（取代舊 polling hook）

## 假設與要調整的點
- `search_stream_route.py` 假設可 `from backend.search_registry import get_search_status`。
  若你的 registry 函式不叫這名字，改頂端那個 import 就好。
- `useSearchStream.ts` 假設前端用 `${window.__API_BASE__}` 或同源。
  若你目前用 axios + baseURL，把 `API_BASE` 換成你的設定值即可。
