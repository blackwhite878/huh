// ============================================================================
// API transport layer — endpoints from Backend.md §4.
// Defaults to fetch; ready to upgrade to SSE without changing call sites.
// ============================================================================
import type {
  ChatResponse,
  InitSessionResponse,
  NextBatchResponse,
  Phase1Form,
  RejectAllResponse,
  RejectSingleResponse,
  SearchStatusResponse,
  SessionReadyResponse,
} from "./types";

const BASE = (() => {
  if (typeof import.meta !== "undefined" && import.meta.env) {
    return (
      (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
      "http://localhost:8000/api/v1"
    );
  }
  return "http://localhost:8000/api/v1";
})();

const TRANSPORT: "sse" | "polling" =
  (typeof import.meta !== "undefined" &&
    (import.meta.env.VITE_TRANSPORT as "sse" | "polling" | undefined)) ||
  "polling";

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

// ============================================================================
// Endpoints
// ============================================================================
export const api = {
  initSession: (body: Phase1Form) =>
    postJSON<InitSessionResponse>("/init_session", body),

  sessionReady: (sessionId: string) =>
    getJSON<SessionReadyResponse>(`/session_ready/${sessionId}`),

  chat: (sessionId: string, message: string) =>
    postJSON<ChatResponse>("/chat", { session_id: sessionId, message }),

  searchStatus: (sessionId: string) =>
    getJSON<SearchStatusResponse>(`/search_status/${sessionId}`),

  nextBatch: (sessionId: string) =>
    postJSON<NextBatchResponse>("/next_batch", { session_id: sessionId }),

  rejectSingle: (sessionId: string, property_id: string, reason: string) =>
    postJSON<RejectSingleResponse>("/reject_single", {
      session_id: sessionId,
      property_id,
      reason,
    }),

  rejectAll: (sessionId: string) =>
    postJSON<RejectAllResponse>("/reject_all", { session_id: sessionId }),

  resolveAction: (sessionId: string, action: "new_prompt" | "keep_memories") =>
    postJSON<{ status: string; reply?: string }>("/resolve_action", {
      session_id: sessionId,
      action,
    }),

  updateRequirements: (
    sessionId: string,
    updated_fields: Record<string, unknown>,
  ) =>
    postJSON("/update_requirements", {
      session_id: sessionId,
      updated_fields,
    }),
};

// ============================================================================
// Polling / SSE subscriptions
// SSE path: GET ${BASE}/{stream}/{sessionId} returning text/event-stream events
// of shape { event: "update", data: <SessionReadyResponse | SearchStatusResponse> }
// Falls back to setInterval(...3s) when TRANSPORT !== "sse" or EventSource fails.
// ============================================================================
type Stop = () => void;

function pollLoop<T>(
  fn: () => Promise<T>,
  onData: (data: T) => void,
  intervalMs = 3000,
): Stop {
  let cancelled = false;
  let inFlight = false;
  const tick = async () => {
    if (cancelled || inFlight) return;
    inFlight = true;
    try {
      const data = await fn();
      if (!cancelled) onData(data);
    } catch (e) {
      console.warn("[poll] error", e);
    } finally {
      inFlight = false;
    }
  };
  tick();
  const handle = setInterval(tick, intervalMs);
  return () => {
    cancelled = true;
    clearInterval(handle);
  };
}

function sseLoop<T>(
  path: string,
  onData: (data: T) => void,
  fallback: () => Stop,
): Stop {
  if (
    typeof window === "undefined" ||
    typeof EventSource === "undefined" ||
    TRANSPORT !== "sse"
  ) {
    return fallback();
  }
  try {
    const es = new EventSource(`${BASE}${path}`);
    let fellBack: Stop | null = null;
    es.onmessage = (ev) => {
      try {
        onData(JSON.parse(ev.data) as T);
      } catch (e) {
        console.warn("[sse] parse error", e);
      }
    };
    es.onerror = () => {
      es.close();
      if (!fellBack) fellBack = fallback();
    };
    return () => {
      es.close();
      fellBack?.();
    };
  } catch {
    return fallback();
  }
}

export function subscribeSessionReady(
  sessionId: string,
  onData: (d: SessionReadyResponse) => void,
): Stop {
  return sseLoop<SessionReadyResponse>(
    `/session_ready/${sessionId}/stream`,
    onData,
    () => pollLoop(() => api.sessionReady(sessionId), onData, 3000),
  );
}

export function subscribeSearchStatus(
  sessionId: string,
  onData: (d: SearchStatusResponse) => void,
): Stop {
  return sseLoop<SearchStatusResponse>(
    `/search_status/${sessionId}/stream`,
    onData,
    () => pollLoop(() => api.searchStatus(sessionId), onData, 3000),
  );
}
