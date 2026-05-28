"""
backend/access_log_filter.py
============================
Drop-in: 過濾 uvicorn access log 裡 /api/v1/search_status/<id> 的高頻輪詢 200 OK。
其它路徑照舊輸出。

用法（在 backend/main.py 啟動 app 之前一次性 import）:

    from backend.access_log_filter import install_access_log_filter
    install_access_log_filter()

然後 uvicorn 啟動時不需要任何額外參數。
"""

from __future__ import annotations

import logging
import re

# 任何想壓掉的高頻輪詢端點都加進這個 regex
_POLL_PATH_RE = re.compile(r'"GET /api/v1/search_status/[0-9a-f\-]+ HTTP/[\d.]+" 200')


class _PollNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        # True = keep, False = drop
        return _POLL_PATH_RE.search(msg) is None


def install_access_log_filter() -> None:
    """安裝到 uvicorn.access logger。冪等。"""
    logger = logging.getLogger("uvicorn.access")
    # 避免重複安裝
    for f in logger.filters:
        if isinstance(f, _PollNoiseFilter):
            return
    logger.addFilter(_PollNoiseFilter())
