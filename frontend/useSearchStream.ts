/**
 * frontend/useSearchStream.ts
 * ===========================
 * SSE hook，取代原本對 /api/v1/search_status/<id> 的 setInterval polling。
 *
 * 用法：
 *   const { status, error, done } = useSearchStream(searchId);
 *
 * 若瀏覽器或環境不支援 EventSource（罕見），會自動 fallback 到 5s polling。
 */

import { useEffect, useState } from "react";

export type SearchStatus = {
  status: "queued" | "running" | "done" | "error";
  progress?: { done: number; total: number };
  current?: { region?: string; type?: string };
  rows?: number;
  error?: string | null;
};

const API_BASE =
  (typeof window !== "undefined" && (window as any).__API_BASE__) || "";

export function useSearchStream(searchId: string | null | undefined) {
  const [status, setStatus] = useState<SearchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!searchId) return;
    setStatus(null);
    setError(null);
    setDone(false);

    // 優先 SSE
    if (typeof EventSource !== "undefined") {
      const es = new EventSource(`${API_BASE}/api/v1/search_stream/${searchId}`);

      es.addEventListener("status", (ev: MessageEvent) => {
        try {
          const payload = JSON.parse(ev.data) as SearchStatus;
          setStatus(payload);
          if (payload.status === "done" || payload.status === "error") {
            setDone(true);
            es.close();
          }
        } catch (e) {
          // ignore parse error, keep stream alive
        }
      });

      es.addEventListener("error", () => {
        // 連線錯誤：交給 onerror 統一處理
      });

      es.onerror = () => {
        // EventSource 會自己重試；只在 readyState===CLOSED 才當作真錯
        if (es.readyState === EventSource.CLOSED) {
          setError("stream closed");
          setDone(true);
        }
      };

      return () => es.close();
    }

    // Fallback: 5s polling
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/search_status/${searchId}`);
        if (!r.ok) throw new Error(`http ${r.status}`);
        const payload = (await r.json()) as SearchStatus;
        if (cancelled) return;
        setStatus(payload);
        if (payload.status === "done" || payload.status === "error") {
          setDone(true);
          return;
        }
        setTimeout(tick, 5000);
      } catch (e: any) {
        if (cancelled) return;
        setError(String(e?.message ?? e));
        setTimeout(tick, 5000);
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, [searchId]);

  return { status, error, done };
}
