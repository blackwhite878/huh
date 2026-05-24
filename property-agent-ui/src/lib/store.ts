import { create } from "zustand";
import type {
  AppState,
  DialogueMessage,
  PendingConflict,
  Phase1Form,
  PropertyResult,
  SearchStage,
} from "./types";

interface AppStore {
  // State machine
  appState: AppState;
  setAppState: (s: AppState) => void;

  // Session
  sessionId: string | null;
  setSessionId: (id: string | null) => void;

  // Phase 1
  phase1Form: Phase1Form | null;
  setPhase1Form: (f: Phase1Form) => void;

  // Semantic tags
  semanticTags: string[];
  alignmentWarning: boolean;
  alignmentError: string | null;
  setSemanticTags: (tags: string[], warning?: boolean, error?: string | null) => void;

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
}

const initialResults = {
  currentBatch: [] as PropertyResult[],
  batchIndex: 0,
  totalAvailable: 0,
  hasMore: false,
  tier3Triggered: false,
  degraded: false,
};

export const useAppStore = create<AppStore>((set, get) => ({
  appState: "IDLE",
  setAppState: (s) => set({ appState: s }),

  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  phase1Form: null,
  setPhase1Form: (f) => set({ phase1Form: f }),

  semanticTags: [],
  alignmentWarning: false,
  alignmentError: null,
  setSemanticTags: (tags, warning = false, error = null) =>
    set({ semanticTags: tags, alignmentWarning: warning, alignmentError: error }),

  dialogueMessages: [],
  appendMessage: (m) =>
    set((st) => ({ dialogueMessages: [...st.dialogueMessages, m] })),
  resetDialogue: () => set({ dialogueMessages: [] }),

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
  addRejectedId: (id) =>
    set((st) =>
      st.rejectedIds.includes(id)
        ? st
        : { rejectedIds: [...st.rejectedIds, id] },
    ),

  pollHandles: [],
  registerHandle: (h) =>
    set((st) => ({ pollHandles: [...st.pollHandles, h] })),
  clearAllHandles: () => {
    get().pollHandles.forEach((h) => clearInterval(h));
    set({ pollHandles: [] });
  },

  resetAll: () => {
    get().pollHandles.forEach((h) => clearInterval(h));
    set({
      appState: "IDLE",
      sessionId: null,
      phase1Form: null,
      semanticTags: [],
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
  },
}));
