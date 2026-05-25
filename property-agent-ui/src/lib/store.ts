import { create } from "zustand";
import type {
  AppState,
  DialogueMessage,
  PendingConflict,
  Phase1Form,
  PropertyResult,
  SearchStage,
} from "./types";
import type { Lang } from "./i18n";

// ─── Temporary session memory (Phase 2.5 spec) ────────────────────────
// Persistence rules:
//   * Saved to localStorage so an accidental Reload survives.
//   * Wiped automatically if the user is idle for > IDLE_TTL_MS
//     (default 15 min).
//   * `resetAll()` wipes it ("Return home" / Phase 3 new prompt).
//   * `resetForKeepMemories()` keeps it ("Keep asking with memory").
//   * Each new browser session starts empty IFF the previous one
//     expired — otherwise we restore so Reload can recover from the
//     error boundary.
const STORAGE_KEY = "wsdfc:session:v1";
const IDLE_TTL_MS = 15 * 60 * 1000;

interface PersistedSnapshot {
  sessionId: string | null;
  phase1Form: Phase1Form | null;
  semanticTags: string[];          // negative (NPP) keys
  positiveTags: string[];          // positive (PPP) keys
  alignmentWarning: boolean;
  alignmentError: string | null;
  dialogueMessages: DialogueMessage[];
  rejectedIds: string[];
  appState: AppState;
  lang: Lang;
  savedAt: number;
}

function safeWindow(): Window | null {
  return typeof window === "undefined" ? null : window;
}

function readSnapshot(): PersistedSnapshot | null {
  const w = safeWindow();
  if (!w) return null;
  try {
    const raw = w.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const snap = JSON.parse(raw) as PersistedSnapshot;
    if (!snap || typeof snap !== "object") return null;
    if (Date.now() - (snap.savedAt ?? 0) > IDLE_TTL_MS) {
      // Expired — wipe it so the next read returns empty.
      w.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return snap;
  } catch {
    return null;
  }
}

function writeSnapshot(snap: PersistedSnapshot) {
  const w = safeWindow();
  if (!w) return;
  try {
    w.localStorage.setItem(STORAGE_KEY, JSON.stringify(snap));
  } catch {
    /* quota / private mode — silently ignore */
  }
}

export function hasPersistedSessionSnapshot(): boolean {
  return readSnapshot() !== null;
}

export function clearPersistedSessionSnapshot() {
  clearSnapshot();
}

function clearSnapshot() {
  const w = safeWindow();
  if (!w) return;
  try {
    w.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

interface AppStore {
  // State machine
  appState: AppState;
  setAppState: (s: AppState) => void;

  // UI language (Phase 1 toggle persists for the whole session)
  lang: Lang;
  setLang: (l: Lang) => void;

  // Session
  sessionId: string | null;
  setSessionId: (id: string | null) => void;

  // Phase 1
  phase1Form: Phase1Form | null;
  setPhase1Form: (f: Phase1Form) => void;

  // Semantic tags
  semanticTags: string[];          // NPP (negative)
  positiveTags: string[];          // PPP (positive)
  alignmentWarning: boolean;
  alignmentError: string | null;
  setSemanticTags: (tags: string[], warning?: boolean, error?: string | null) => void;
  setPositiveTags: (tags: string[]) => void;

  // Dialogue
  dialogueMessages: DialogueMessage[];
  appendMessage: (m: DialogueMessage) => void;
  resetDialogue: () => void;

  // Pending conflict
  pendingConflict: PendingConflict | null;
  setPendingConflict: (p: PendingConflict | null) => void;

  // Search progress
  searchStage: SearchStage | null;
  setSearchStage: (s: SearchStage | null) => void;

  // Results
  currentBatch: PropertyResult[];
  batchIndex: number;
  totalAvailable: number;
  hasMore: boolean;
  tier3Triggered: boolean;
  degraded: boolean;
  setResults: (data: {
    results?: PropertyResult[];
    batch_index?: number;
    total_available?: number;
    has_more?: boolean;
    tier3_triggered?: boolean;
    degraded?: boolean;
  }) => void;

  // Rejection
  rejectionCount: number;
  rejectedIds: string[];
  setRejectionCount: (n: number) => void;
  addRejectedId: (id: string) => void;

  // Cleanup handles
  pollHandles: ReturnType<typeof setInterval>[];
  registerHandle: (h: ReturnType<typeof setInterval>) => void;
  clearAllHandles: () => void;

  // Full reset
  resetAll: () => void;
  resetForKeepMemories: () => void;

  // Persistence — Phase 2.5
  hydrateFromStorage: () => boolean;     // true if a snapshot was restored
  persistNow: () => void;                // force-save (also called on every relevant setter)
  bumpActivity: () => void;              // refresh savedAt without changing data
  hasRestorableSession: () => boolean;
}

const initialResults = {
  currentBatch: [] as PropertyResult[],
  batchIndex: 0,
  totalAvailable: 0,
  hasMore: false,
  tier3Triggered: false,
  degraded: false,
};

export const useAppStore = create<AppStore>((set, get) => {
  // Build a snapshot of the persistable slice of state.
  const snapshot = (): PersistedSnapshot => {
    const s = get();
    return {
      sessionId: s.sessionId,
      phase1Form: s.phase1Form,
      semanticTags: s.semanticTags,
      positiveTags: s.positiveTags,
      alignmentWarning: s.alignmentWarning,
      alignmentError: s.alignmentError,
      dialogueMessages: s.dialogueMessages,
      rejectedIds: s.rejectedIds,
      appState: s.appState,
      lang: s.lang,
      savedAt: Date.now(),
    };
  };
  const save = () => writeSnapshot(snapshot());

  return {
    appState: "IDLE",
    setAppState: (s) => {
      set({ appState: s });
      save();
    },

    lang: "en",
    setLang: (l) => {
      set({ lang: l });
      save();
    },

    sessionId: null,
    setSessionId: (id) => {
      set({ sessionId: id });
      save();
    },

    phase1Form: null,
    setPhase1Form: (f) => {
      set({ phase1Form: f });
      save();
    },

    semanticTags: [],
    positiveTags: [],
    alignmentWarning: false,
    alignmentError: null,
    setSemanticTags: (tags, warning = false, error = null) => {
      set({ semanticTags: tags, alignmentWarning: warning, alignmentError: error });
      save();
    },
    setPositiveTags: (tags) => {
      set({ positiveTags: tags });
      save();
    },

    dialogueMessages: [],
    appendMessage: (m) => {
      set((st) => ({ dialogueMessages: [...st.dialogueMessages, m] }));
      save();
    },
    resetDialogue: () => {
      set({ dialogueMessages: [] });
      save();
    },

    pendingConflict: null,
    setPendingConflict: (p) => set({ pendingConflict: p }),

    searchStage: null,
    setSearchStage: (s) => set({ searchStage: s }),

    ...initialResults,
    setResults: (data) =>
      set({
        currentBatch: data.results ?? get().currentBatch,
        batchIndex: data.batch_index ?? get().batchIndex,
        totalAvailable: data.total_available ?? get().totalAvailable,
        hasMore: data.has_more ?? get().hasMore,
        tier3Triggered: data.tier3_triggered ?? get().tier3Triggered,
        degraded: data.degraded ?? get().degraded,
      }),

    rejectionCount: 0,
    rejectedIds: [],
    setRejectionCount: (n) => set({ rejectionCount: n }),
    addRejectedId: (id) => {
      set((st) =>
        st.rejectedIds.includes(id)
          ? st
          : { rejectedIds: [...st.rejectedIds, id] },
      );
      save();
    },

    pollHandles: [],
    registerHandle: (h) =>
      set((st) => ({ pollHandles: [...st.pollHandles, h] })),
    clearAllHandles: () => {
      get().pollHandles.forEach((h) => clearInterval(h));
      set({ pollHandles: [] });
    },

    resetAll: () => {
      get().pollHandles.forEach((h) => clearInterval(h));
      // "Return home" / "new prompt" = fresh session — wipe temp memory.
      clearSnapshot();
      // Preserve the user's chosen language across a reset; it is a UI
      // preference, not session data.
      const keptLang = get().lang;
      set({
        appState: "IDLE",
        lang: keptLang,
        sessionId: null,
        phase1Form: null,
        semanticTags: [],
        positiveTags: [],
        alignmentWarning: false,
        alignmentError: null,
        dialogueMessages: [],
        pendingConflict: null,
        searchStage: null,
        rejectionCount: 0,
        rejectedIds: [],
        pollHandles: [],
        ...initialResults,
      });
    },

    resetForKeepMemories: () => {
      get().pollHandles.forEach((h) => clearInterval(h));
      set({
        appState: "CHATTING",
        pendingConflict: null,
        searchStage: null,
        rejectionCount: 0,
        rejectedIds: [],
        pollHandles: [],
        ...initialResults,
      });
      // Persist the kept memory so Reload still recovers it.
      save();
    },

    // ── Persistence API ──────────────────────────────────────────────
    hydrateFromStorage: () => {
      const snap = readSnapshot();
      if (!snap) return false;
      // Only restore "in-flight" sessions — never restore terminal /
      // transient states that would skip past required UX gates.
      const restorableStates: AppState[] = [
        "CHATTING",
        "PENDING_CONFIRMATION",
        "BATCH_1_DISPLAY",
        "BATCH_2_DISPLAY",
        "ALL_REJECTED",
        "ACTION_REQUIRED_UI",
        "TIER3_NO_RESULT",
        "PROFILING_COMPLETE",
      ];
      const safeState: AppState = restorableStates.includes(snap.appState)
        ? snap.appState
        : snap.dialogueMessages.length > 0
          ? "CHATTING"
          : "IDLE";

      set({
        sessionId: snap.sessionId,
        phase1Form: snap.phase1Form,
        semanticTags: snap.semanticTags ?? [],
        positiveTags: snap.positiveTags ?? [],
        alignmentWarning: snap.alignmentWarning ?? false,
        alignmentError: snap.alignmentError ?? null,
        dialogueMessages: snap.dialogueMessages ?? [],
        rejectedIds: snap.rejectedIds ?? [],
        appState: safeState,
        lang: snap.lang ?? get().lang,
        // Reset transient runtime state — we never persist mid-flight
        // search progress or live conflicts.
        pendingConflict: null,
        searchStage: null,
        ...initialResults,
      });
      // Touch savedAt so the restore itself counts as activity.
      save();
      return true;
    },

    persistNow: save,
    bumpActivity: () => writeSnapshot(snapshot()),
    hasRestorableSession: () => readSnapshot() !== null,
  };
});

// Bump activity on user interaction so the 15-min idle timer is
// measured from the user's last real action, not just from the last
// state mutation. Cheap, passive, no React dependency.
if (typeof window !== "undefined") {
  const bump = () => {
    try {
      useAppStore.getState().bumpActivity();
    } catch {
      /* ignore */
    }
  };
  ["click", "keydown", "pointerdown"].forEach((ev) =>
    window.addEventListener(ev, bump, { passive: true }),
  );
}
