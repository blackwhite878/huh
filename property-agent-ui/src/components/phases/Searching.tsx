import { useEffect, useRef, useState } from "react";
import { Search, Sparkles, BarChart3, FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { getClosedSessionReason, subscribeSearchStatus } from "@/lib/api";
import type {
  AgentStyle,
  SearchStage,
  SearchStatusResponse,
} from "@/lib/types";

// Minimum on-screen dwell per pipeline stage. Even if the backend races
// through scraping → ranking → generating in <1s, the UI walks the rail
// at this pace so every step has time to "bling" (pulse + glow ring).
const MIN_STAGE_MS = 10_000;

// NOTE: Phase 1 emits AgentStyle as "Professional" | "Friendly" |
// "Enthusiastic" (capitalised). A previous version of this file keyed
// COPY by "professional" | "friendly" | "active", so COPY[style] was
// undefined and COPY[style][stage] threw the moment the user landed on
// the SEARCHING screen (e.g. right after answering cash/loan). Keys
// here MUST match AgentStyle exactly — guarded below by a fallback.
const COPY: Record<AgentStyle, Record<SearchStage, string>> = {
  Professional: {
    idle: "Preparing the search pipeline…",
    scraping: "Sourcing the latest property listings…",
    ranking: "Scoring listings against your preferences…",
    generating_remarks:
      "AI is composing tailored analysis for each property…",
    complete: "Ready.",
  },
  Friendly: {
    idle: "Warming up…",
    scraping: "Going to grab the freshest listings for you — back in a sec.",
    ranking: "Picking the ones that fit you best…",
    generating_remarks: "Almost done — writing up the highlights now.",
    complete: "All set!",
  },
  Enthusiastic: {
    idle: "Preparing.",
    scraping: "Pulling listings live.",
    ranking: "Ranking by fit.",
    generating_remarks: "Writing remarks.",
    complete: "Done.",
  },
};

const STAGES: { key: SearchStage; label: string; icon: typeof Search }[] = [
  { key: "scraping", label: "Scraping", icon: Search },
  { key: "ranking", label: "Ranking", icon: BarChart3 },
  { key: "generating_remarks", label: "Generating", icon: FileText },
];

function stageIndex(stage: SearchStage | null): number {
  if (!stage || stage === "idle") return 0;
  if (stage === "complete") return STAGES.length - 1;
  const i = STAGES.findIndex((s) => s.key === stage);
  return i < 0 ? 0 : i;
}

export function Searching() {
  const sessionId = useAppStore((s) => s.sessionId);
  const style = useAppStore((s) => s.phase1Form?.agent_style ?? "Professional");
  const searchStage = useAppStore((s) => s.searchStage);
  const setSearchStage = useAppStore((s) => s.setSearchStage);
  const setResults = useAppStore((s) => s.setResults);
  const setAppState = useAppStore((s) => s.setAppState);
  const resetAll = useAppStore((s) => s.resetAll);

  // UI-only stage cursor. Advances one step per MIN_STAGE_MS until it
  // catches up to whatever the backend reports — never skips ahead.
  const [uiIdx, setUiIdx] = useState(0);
  const [backendComplete, setBackendComplete] = useState(false);
  const lastAdvanceAt = useRef<number>(Date.now());
  // Latest payload from backend; we stash it so navigation can wait for
  // the UI rail to finish blinging through every stage before leaving.
  const completePayload = useRef<SearchStatusResponse | null>(null);

  // Subscribe to backend pipeline status. We update the store's
  // searchStage (for any other consumers), capture the completion
  // payload, but DO NOT navigate immediately — the UI rail finishes
  // its dwell first.
  useEffect(() => {
    if (!sessionId) return;
    const stop = subscribeSearchStatus(sessionId, (data) => {
      setSearchStage(data.status);
      if (data.status === "complete") {
        completePayload.current = data;
        setBackendComplete(true);
      }
    }, (error) => {
      if (getClosedSessionReason(error)) {
        stop();
        resetAll();
      }
    });
    return stop;
  }, [sessionId, setSearchStage, resetAll]);

  // Drive the UI cursor forward at MIN_STAGE_MS pacing, capped by the
  // backend stage. When backendComplete is true we let it walk all the
  // way to the last stage.
  useEffect(() => {
    const backendIdx = backendComplete
      ? STAGES.length - 1
      : stageIndex(searchStage);
    if (uiIdx >= backendIdx) return; // already at/ahead of backend

    const elapsed = Date.now() - lastAdvanceAt.current;
    const wait = Math.max(0, MIN_STAGE_MS - elapsed);
    const t = setTimeout(() => {
      setUiIdx((i) => i + 1);
      lastAdvanceAt.current = Date.now();
    }, wait);
    return () => clearTimeout(t);
  }, [uiIdx, searchStage, backendComplete]);

  // Only navigate once the UI has visibly completed the last stage's
  // dwell AND the backend has reported complete.
  useEffect(() => {
    if (!backendComplete) return;
    if (uiIdx < STAGES.length - 1) return;
    const data = completePayload.current;
    const t = setTimeout(() => {
      if (data) setResults(data);
      setAppState(
        data?.tier3_triggered ? "TIER3_NO_RESULT" : "BATCH_1_DISPLAY",
      );
    }, MIN_STAGE_MS);
    return () => clearTimeout(t);
  }, [backendComplete, uiIdx, setResults, setAppState]);

  // Copy reflects whichever stage the UI is currently showcasing — so
  // the headline tracks the rail, not the (possibly faster) backend.
  const uiStageKey: SearchStage =
    backendComplete && uiIdx >= STAGES.length - 1
      ? "complete"
      : STAGES[Math.min(uiIdx, STAGES.length - 1)].key;
  // Defensive: if a future AgentStyle leaks through that we don't have copy
  // for, fall back to Professional instead of throwing into the route
  // errorComponent ("This page didn't load").
  const currentCopy = (COPY[style] ?? COPY.Professional)[uiStageKey];

  return (
    <div className="mx-auto flex min-h-[65vh] max-w-2xl flex-col items-center justify-center text-center">
      <div className="relative mb-8 flex h-24 w-24 items-center justify-center">
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-primary/20 to-primary-glow/10 blur-2xl" />
        <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]">
          <Sparkles className="h-9 w-9 text-primary-foreground animate-pulse" />
        </div>
      </div>

      <h2 className="max-w-md text-balance text-2xl font-medium tracking-tight">
        {currentCopy}
      </h2>

      {/* Stage rail — every reached step keeps blinging (ping + glow). */}
      <div className="mt-10 w-full max-w-md">
        <div className="relative">
          <div className="absolute left-5 right-5 top-1/2 h-px -translate-y-1/2 bg-border" />
          <div
            className="absolute left-5 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-primary to-primary-glow transition-all duration-500"
            style={{
              width: `calc(${(uiIdx / (STAGES.length - 1)) * 100}% * (100% - 40px) / 100%)`,
            }}
          />
          <div className="relative flex items-center justify-between">
            {STAGES.map((s, i) => {
              const reached = i <= uiIdx;
              const active = i === uiIdx;
              const Icon = s.icon;
              return (
                <div
                  key={s.key}
                  className="flex flex-col items-center gap-2"
                >
                  <div
                    className={[
                      "relative flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all",
                      reached
                        ? active
                          ? "border-primary bg-surface-raised text-primary shadow-[var(--shadow-glow)]"
                          : "border-primary bg-primary text-primary-foreground shadow-[var(--shadow-glow)]"
                        : "border-border bg-surface-raised text-muted-foreground",
                    ].join(" ")}
                  >
                    <Icon
                      className={[
                        "h-4 w-4",
                        reached ? "animate-pulse" : "",
                      ].join(" ")}
                    />
                    {/* Every reached step gets a continuous ping ring,
                        not just the active one. Stagger the ping by
                        index so they don't all flash on the same beat. */}
                    {reached && (
                      <>
                        <span
                          className="absolute -inset-1 animate-ping rounded-full border border-primary/60"
                          style={{ animationDelay: `${i * 0.35}s` }}
                        />
                        <span
                          className="absolute -inset-2 rounded-full bg-primary/10 blur-md animate-pulse"
                          style={{ animationDelay: `${i * 0.5}s` }}
                        />
                      </>
                    )}
                  </div>
                  <span
                    className={[
                      "font-mono text-[10px] uppercase tracking-[0.18em]",
                      reached ? "text-foreground" : "text-muted-foreground",
                    ].join(" ")}
                  >
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="mt-12 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        input locked · search pipeline running
      </p>
    </div>
  );
}
