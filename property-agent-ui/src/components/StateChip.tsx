import type { AppState } from "@/lib/types";

const LABELS: Record<AppState, string> = {
  IDLE: "Phase 1 · Onboarding",
  PHASE_1_INITIAL: "Phase 1 · Onboarding",
  SEMANTIC_ALIGNING: "Aligning semantic profile",
  PROFILING_COMPLETE: "Profile ready",
  CHATTING: "Phase 2 · Live consultation",
  PENDING_CONFIRMATION: "Awaiting confirmation",
  SEARCHING: "Searching properties",
  BATCH_1_DISPLAY: "Results · Batch 1",
  BATCH_2_DISPLAY: "Results · Batch 2",
  ALL_REJECTED: "Learning from feedback",
  ACTION_REQUIRED_UI: "Choose next action",
  RE_SEARCHING: "Re-running search",
  TIER3_NO_RESULT: "Search exhausted",
};

export function StateChip({ state }: { state: AppState }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground backdrop-blur">
      <span className="h-1.5 w-1.5 rounded-full bg-primary" />
      {LABELS[state]}
    </div>
  );
}
