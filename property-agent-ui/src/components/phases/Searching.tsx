import { useEffect, useRef, useState } from "react";
import { Search, Sparkles, BarChart3, FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { getClosedSessionReason, subscribeSearchStatus } from "@/lib/api";
import type {
  AgentStyle,
  SearchStage,
  SearchStatusResponse,
} from "@/lib/types";
import { t } from "@/lib/i18n";

const MIN_STAGE_MS = 10_000;

const STAGES: { key: SearchStage; labelKey: string; icon: typeof Search }[] = [
  { key: "scraping",           labelKey: "search.stage.scraping",   icon: Search },
  { key: "ranking",            labelKey: "search.stage.ranking",    icon: BarChart3 },
  { key: "generating_remarks", labelKey: "search.stage.generating", icon: FileText },
];

function stageIndex(stage: SearchStage | null): number {
  if (!stage || stage === "idle") return 0;
  if (stage === "complete") return STAGES.length - 1;
  const i = STAGES.findIndex((s) => s.key === stage);
  return i < 0 ? 0 : i;
}

export function Searching() {
  const lang = useAppStore((s) => s.lang);
  const sessionId = useAppStore((s) => s.sessionId);
  const style = useAppStore((s) => s.phase1Form?.agent_style ?? "Professional");
  const searchStage = useAppStore((s) => s.searchStage);
  const setSearchStage = useAppStore((s) => s.setSearchStage);
  const setResults = useAppStore((s) => s.setResults);
  const setAppState = useAppStore((s) => s.setAppState);
  const resetAll = useAppStore((s) => s.resetAll);

  const [uiIdx, setUiIdx] = useState(0);
  const [backendComplete, setBackendComplete] = useState(false);
  const lastAdvanceAt = useRef<number>(Date.now());
  const completePayload = useRef<SearchStatusResponse | null>(null);

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

  useEffect(() => {
    const backendIdx = backendComplete
      ? STAGES.length - 1
      : stageIndex(searchStage);
    if (uiIdx >= backendIdx) return;

    const elapsed = Date.now() - lastAdvanceAt.current;
    const wait = Math.max(0, MIN_STAGE_MS - elapsed);
    const tm = setTimeout(() => {
      setUiIdx((i) => i + 1);
      lastAdvanceAt.current = Date.now();
    }, wait);
    return () => clearTimeout(tm);
  }, [uiIdx, searchStage, backendComplete]);

  useEffect(() => {
    if (!backendComplete) return;
    if (uiIdx < STAGES.length - 1) return;
    const data = completePayload.current;
    const tm = setTimeout(() => {
      if (data) setResults(data);
      setAppState(
        data?.tier3_triggered ? "TIER3_NO_RESULT" : "BATCH_1_DISPLAY",
      );
    }, MIN_STAGE_MS);
    return () => clearTimeout(tm);
  }, [backendComplete, uiIdx, setResults, setAppState]);

  const uiStageKey: SearchStage =
    backendComplete && uiIdx >= STAGES.length - 1
      ? "complete"
      : STAGES[Math.min(uiIdx, STAGES.length - 1)].key;

  // Defensive: if a future AgentStyle leaks through that we don't have copy
  // for, fall back to Professional. (`t()` would warn on a missing key.)
  const safeStyle: AgentStyle = (["Professional", "Friendly", "Enthusiastic"] as AgentStyle[]).includes(
    style as AgentStyle,
  )
    ? (style as AgentStyle)
    : "Professional";
  const currentCopy = t(`search.copy.${safeStyle}.${uiStageKey}`, lang);

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
                <div key={s.key} className="flex flex-col items-center gap-2">
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
                      className={["h-4 w-4", reached ? "animate-pulse" : ""].join(" ")}
                    />
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
                    {t(s.labelKey, lang)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="mt-12 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {t("search.footer", lang)}
      </p>
    </div>
  );
}
