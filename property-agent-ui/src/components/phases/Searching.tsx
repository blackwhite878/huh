import { useEffect } from "react";
import { Search, Sparkles, BarChart3, FileText } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { subscribeSearchStatus } from "@/lib/api";
import type { AgentStyle, SearchStage } from "@/lib/types";

const COPY: Record<AgentStyle, Record<SearchStage, string>> = {
  professional: {
    scraping: "Sourcing the latest property listings…",
    ranking: "Scoring listings against your preferences…",
    generating_remarks:
      "AI is composing tailored analysis for each property…",
    complete: "Ready.",
  },
  friendly: {
    scraping: "Going to grab the freshest listings for you — back in a sec.",
    ranking: "Picking the ones that fit you best…",
    generating_remarks: "Almost done — writing up the highlights now.",
    complete: "All set!",
  },
  active: {
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

export function Searching() {
  const sessionId = useAppStore((s) => s.sessionId);
  const style = useAppStore((s) => s.phase1Form?.agent_style ?? "professional");
  const searchStage = useAppStore((s) => s.searchStage);
  const setSearchStage = useAppStore((s) => s.setSearchStage);
  const setResults = useAppStore((s) => s.setResults);
  const setAppState = useAppStore((s) => s.setAppState);

  useEffect(() => {
    if (!sessionId) return;
    const stop = subscribeSearchStatus(sessionId, (data) => {
      setSearchStage(data.status);
      if (data.status === "complete") {
        setResults(data);
        setAppState(
          data.tier3_triggered ? "TIER3_NO_RESULT" : "BATCH_1_DISPLAY",
        );
        stop();
      }
    });
    return stop;
  }, [sessionId, setSearchStage, setResults, setAppState]);

  const currentIdx = Math.max(
    0,
    STAGES.findIndex((s) => s.key === (searchStage ?? "scraping")),
  );
  const currentCopy = COPY[style][searchStage ?? "scraping"];

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

      {/* Stage rail */}
      <div className="mt-10 w-full max-w-md">
        <div className="relative">
          <div className="absolute left-5 right-5 top-1/2 h-px -translate-y-1/2 bg-border" />
          <div
            className="absolute left-5 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-primary to-primary-glow transition-all duration-500"
            style={{
              width: `calc(${(currentIdx / (STAGES.length - 1)) * 100}% * (100% - 40px) / 100%)`,
            }}
          />
          <div className="relative flex items-center justify-between">
            {STAGES.map((s, i) => {
              const done = i < currentIdx;
              const active = i === currentIdx;
              const Icon = s.icon;
              return (
                <div
                  key={s.key}
                  className="flex flex-col items-center gap-2"
                >
                  <div
                    className={[
                      "relative flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all",
                      done
                        ? "border-primary bg-primary text-primary-foreground"
                        : active
                          ? "border-primary bg-surface-raised text-primary shadow-[var(--shadow-glow)]"
                          : "border-border bg-surface-raised text-muted-foreground",
                    ].join(" ")}
                  >
                    <Icon className="h-4 w-4" />
                    {active && (
                      <span className="absolute -inset-1 animate-ping rounded-full border border-primary/60" />
                    )}
                  </div>
                  <span
                    className={[
                      "font-mono text-[10px] uppercase tracking-[0.18em]",
                      active || done
                        ? "text-foreground"
                        : "text-muted-foreground",
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
