import { useState } from "react";
import { Settings2, ChevronDown, ChevronUp, X } from "lucide-react";
import { useAppStore } from "@/lib/store";
import type { AppState, PropertyResult } from "@/lib/types";

const STATES: AppState[] = [
  "IDLE",
  "PHASE_1_INITIAL",
  "SEMANTIC_ALIGNING",
  "PROFILING_COMPLETE",
  "CHATTING",
  "PENDING_CONFIRMATION",
  "SEARCHING",
  "BATCH_1_DISPLAY",
  "BATCH_2_DISPLAY",
  "ALL_REJECTED",
  "ACTION_REQUIRED_UI",
  "RE_SEARCHING",
  "TIER3_NO_RESULT",
];

const SAMPLE: PropertyResult[] = [
  {
    property_id: "demo-1",
    title: "Sunrise Residence Tower B",
    price: 520000,
    location: "Mount Austin, JB",
    feature_tags: ["pool", "gym", "24h security", "near MRT"],
    tier: "tier_1",
    ai_remarks:
      "Strong fit on budget and security profile. Walking distance to two international schools — a notable plus for your stated lifestyle preferences.",
  },
  {
    property_id: "demo-2",
    title: "Greenfield Vista Suites",
    price: 485000,
    location: "Iskandar Puteri, JB",
    feature_tags: ["high floor", "balcony", "covered parking"],
    tier: "tier_2",
    ai_remarks:
      "Excellent unit fundamentals, slightly below average on transit proximity. Strong rental upside given the development pipeline nearby.",
    missing_features: ["MRT < 500m"],
    remedy: "Grab-friendly area, 7-min ride to KSL transit hub.",
  },
];

// Dev-only state inspector. Gated on import.meta.env.DEV and hidden by default
// behind a tiny corner pill so it never overlaps real form controls (Phase 1
// submit button sits in the same bottom-right region).
export function DevPanel() {
  const enabled =
    typeof import.meta !== "undefined" && import.meta.env?.DEV === true;
  const [mounted, setMounted] = useState(enabled);
  const [open, setOpen] = useState(false);
  const appState = useAppStore((s) => s.appState);
  const setAppState = useAppStore((s) => s.setAppState);
  const setSessionId = useAppStore((s) => s.setSessionId);
  const sessionId = useAppStore((s) => s.sessionId);
  const setSemanticTags = useAppStore((s) => s.setSemanticTags);
  const setResults = useAppStore((s) => s.setResults);
  const setPendingConflict = useAppStore((s) => s.setPendingConflict);
  const appendMessage = useAppStore((s) => s.appendMessage);
  const setPhase1Form = useAppStore((s) => s.setPhase1Form);

  if (!mounted) return null;

  const seed = (target: AppState) => {
    if (!sessionId) setSessionId(crypto.randomUUID());
    if (!useAppStore.getState().phase1Form) {
      setPhase1Form({
        budget: 500000,
        agent_style: "professional",
        target: "Condo",
        identity: "first_time_buyer",
        gender: "prefer_not_to_say",
        description:
          "Car park, must have security, prefer high floor and close to MRT. Avoid noisy main roads.",
        house_type: "Condo",
        location: "Johor Bahru",
      });
    }
    switch (target) {
      case "PROFILING_COMPLETE":
        setSemanticTags(["west_facing", "no_security", "far_from_mrt"]);
        break;
      case "CHATTING":
        setSemanticTags(["west_facing", "no_security"]);
        break;
      case "PENDING_CONFIRMATION":
        setSemanticTags(["west_facing"]);
        appendMessage({
          role: "assistant",
          content: "Hi — tell me a bit more about your dream home.",
        });
        setPendingConflict({
          conflicting_field: "target",
          proposed_value: "condo in KL",
          reply:
            "You previously mentioned Johor Bahru — would you like to switch the search to Kuala Lumpur instead?",
        });
        break;
      case "BATCH_1_DISPLAY":
      case "BATCH_2_DISPLAY":
        setResults({
          results: SAMPLE,
          batch_index: target === "BATCH_2_DISPLAY" ? 2 : 1,
          total_available: 4,
          has_more: target === "BATCH_1_DISPLAY",
          tier3_triggered: false,
          degraded: false,
        });
        break;
      case "ALL_REJECTED":
      case "ACTION_REQUIRED_UI":
        setResults({
          results: [],
          batch_index: 2,
          total_available: 4,
          has_more: false,
          tier3_triggered: false,
          degraded: false,
        });
        break;
      case "TIER3_NO_RESULT":
        setResults({
          results: [],
          batch_index: 0,
          total_available: 0,
          has_more: false,
          tier3_triggered: true,
          degraded: false,
        });
        break;
    }
    setAppState(target);
  };

  // Collapsed: tiny non-blocking pill at the very corner.
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open dev state panel"
        className="fixed bottom-3 left-3 z-50 flex h-7 items-center gap-1.5 rounded-full border border-border bg-surface-raised/80 px-2.5 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground shadow-sm backdrop-blur hover:text-foreground"
      >
        <Settings2 className="h-3 w-3 text-primary" />
        dev
      </button>
    );
  }

  return (
    <div className="fixed bottom-3 left-3 z-50 font-mono text-xs">
      <div className="glass-strong w-72 rounded-2xl border border-border-strong shadow-[var(--shadow-elegant)]">
        <div className="flex items-center justify-between gap-2 px-3 py-2">
          <div className="flex items-center gap-2">
            <Settings2 className="h-3.5 w-3.5 text-primary" />
            <span className="uppercase tracking-[0.18em] text-muted-foreground">
              dev · state
            </span>
            <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-primary">
              {appState}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setOpen(false)}
              className="rounded p-1 hover:bg-muted"
              aria-label="Collapse"
            >
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
            <button
              onClick={() => setMounted(false)}
              className="rounded p-1 hover:bg-muted"
              aria-label="Hide dev panel"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1 border-t border-border/60 p-2">
          {STATES.map((s) => (
            <button
              key={s}
              onClick={() => seed(s)}
              className={[
                "rounded-lg px-2 py-1.5 text-left text-[10px] uppercase tracking-[0.1em] transition-colors",
                s === appState
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted",
              ].join(" ")}
            >
              {s.toLowerCase().replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
