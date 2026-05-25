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

// Extra context attached to every Phase 2 chat call so the backend
// (and the LLM prompt it builds) can avoid re-asking known facts.
export interface ChatContext {
  phase1: Phase1Form;
  semantic_tags: string[];
  confirmed_facts: string[];
  instruction: string;
  // UI language selected by the user. Backend appends an OUTPUT_LANGUAGE
  // directive to the system prompt so every assistant reply is rendered
  // in this language. Safe-additive: older backends ignore unknown fields.
  lang?: "en" | "zh";
}

const BASE = (() => {
  const envBase =
    typeof import.meta !== "undefined" && import.meta.env
      ? (import.meta.env.VITE_API_BASE_URL as string | undefined)
      : undefined;
  if (envBase) return envBase;

  // F-HIGH-3: hardcoded fallback is only safe in dev. In production builds
  // missing VITE_API_BASE_URL would silently send requests to localhost,
  // which fails (mixed-content / unreachable) without a clear error.
  const isProd =
    typeof import.meta !== "undefined" &&
    import.meta.env &&
    (import.meta.env as { PROD?: boolean }).PROD;
  if (isProd) {
    throw new Error(
      "VITE_API_BASE_URL is not set. Configure it in your production env.",
    );
  }
  return "http://localhost:8000/api/v1";
})();

export function getApiBaseUrl(): string {
  return BASE;
}


const TRANSPORT: "sse" | "polling" =
  (typeof import.meta !== "undefined" &&
    (import.meta.env.VITE_TRANSPORT as "sse" | "polling" | undefined)) ||
  "polling";

export type ClosedSessionReason = "offline" | "restarted";

interface ApiError extends Error {
  status?: number;
  body?: unknown;
  detail?: unknown;
}

function getErrorStatus(error: unknown): number | undefined {
  return typeof error === "object" && error !== null && "status" in error
    ? (error as { status?: number }).status
    : undefined;
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message.toLowerCase();
  try {
    return JSON.stringify(error).toLowerCase();
  } catch {
    return String(error).toLowerCase();
  }
}

function isMissingSessionError(error: unknown): boolean {
  const status = getErrorStatus(error);
  const text = errorText(error);
  return (
    status === 404 ||
    status === 410 ||
    text.includes("session not found") ||
    text.includes("session_not_found") ||
    text.includes("unknown session")
  );
}

function isNetworkError(error: unknown): boolean {
  const status = getErrorStatus(error);
  const text = errorText(error);
  return (
    status === undefined &&
    (error instanceof TypeError ||
      text.includes("failed to fetch") ||
      text.includes("networkerror") ||
      text.includes("load failed"))
  );
}

export function getClosedSessionReason(
  error: unknown,
): ClosedSessionReason | null {
  if (isMissingSessionError(error)) return "restarted";
  if (isNetworkError(error)) return "offline";
  return null;
}

async function createHttpError(
  method: "GET" | "POST",
  path: string,
  res: Response,
): Promise<ApiError> {
  let body: unknown = null;
  let detail = "";
  try {
    const text = await res.text();
    if (text) {
      try {
        body = JSON.parse(text) as unknown;
        const parsedDetail = (body as { detail?: unknown }).detail;
        detail = typeof parsedDetail === "string" ? parsedDetail : text;
      } catch {
        body = text;
        detail = text;
      }
    }
  } catch {
    /* ignore body parse failures */
  }
  const error = new Error(
    `${method} ${path} failed: ${res.status} ${res.statusText}${
      detail ? ` — ${detail}` : ""
    }`,
  ) as ApiError;
  error.status = res.status;
  error.body = body;
  error.detail = (body as { detail?: unknown } | null)?.detail;
  return error;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw await createHttpError("POST", path, res);
  }
  return res.json() as Promise<T>;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw await createHttpError("GET", path, res);
  }
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

  chat: (
    sessionId: string,
    message: string,
    context?: ChatContext,
  ) =>
    postJSON<ChatResponse>("/chat", {
      session_id: sessionId,
      message,
      // Optional enrichment so backend can dedupe questions. Unknown
      // fields are ignored by older backends — safe additive payload.
      ...(context ? { client_context: context } : {}),
    }),

  // Proactive Phase 2 opener — server speaks first. Idempotent on the
  // backend so duplicate calls (StrictMode, fast re-mounts) return the
  // existing opener instead of generating a new one.
  chatOpening: (sessionId: string, context?: ChatContext) =>
    postJSON<ChatResponse>("/chat_opening", {
      session_id: sessionId,
      ...(context ? { client_context: context } : {}),
    }),

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
  onError?: (error: unknown) => void,
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
      if (!cancelled) onError?.(e);
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
  onError?: (error: unknown) => void,
): Stop {
  return sseLoop<SessionReadyResponse>(
    `/session_ready/${sessionId}/stream`,
    onData,
    () => pollLoop(() => api.sessionReady(sessionId), onData, onError, 3000),
  );
}

export function subscribeSearchStatus(
  sessionId: string,
  onData: (d: SearchStatusResponse) => void,
  onError?: (error: unknown) => void,
): Stop {
  return sseLoop<SearchStatusResponse>(
    `/search_status/${sessionId}/stream`,
    onData,
    () => pollLoop(() => api.searchStatus(sessionId), onData, onError, 3000),
  );
}
