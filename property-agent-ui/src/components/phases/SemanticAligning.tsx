import { useEffect, useState } from "react";

import { useAppStore } from "@/lib/store";
import { subscribeSessionReady } from "@/lib/api";
import { deriveTagsFromDescription } from "@/lib/semantic";

// Backend is authoritative. The local-derived path is a UI placeholder ONLY —
// even after it runs, a subsequent backend "ready" event will overwrite it.
const LOCAL_PLACEHOLDER_AFTER_MS = 60_000;

export function SemanticAligning() {
  const sessionId = useAppStore((s) => s.sessionId);
  const description = useAppStore((s) => s.phase1Form?.description) ?? "";
  const style = useAppStore((s) => s.phase1Form?.agent_style) ?? "professional";
  const setSemanticTags = useAppStore((s) => s.setSemanticTags);
  const setAppState = useAppStore((s) => s.setAppState);

  useEffect(() => {
    if (!sessionId) return;
    let stop: (() => void) | null = null;
    let placeholderTimer: ReturnType<typeof setTimeout> | null = null;
    let backendWon = false;

    stop = subscribeSessionReady(sessionId, (data) => {
      if (data.status !== "ready") return;
      backendWon = true;
      const merged = [
        ...(data.positive_tags ?? []).map((t) => `pos:${t}`),
        ...(data.semantic_tags ?? []).map((t) => `neg:${t}`),
      ];
      // Backend is authoritative: always overwrite, even if placeholder ran first.
      setSemanticTags(merged, !!data.alignment_warning, data.error ?? null);
      setAppState("PROFILING_COMPLETE");
      if (placeholderTimer) clearTimeout(placeholderTimer);
      stop?.();
    });

    placeholderTimer = setTimeout(() => {
      if (backendWon) return;
      const tags = deriveTagsFromDescription(description);
      setSemanticTags(
        tags,
        true,
        "Backend slow — showing locally derived tags. Will refresh if backend responds.",
      );
      setAppState("PROFILING_COMPLETE");
    }, LOCAL_PLACEHOLDER_AFTER_MS);

    return () => {
      stop?.();
      if (placeholderTimer) clearTimeout(placeholderTimer);
    };
  }, [sessionId, description, setSemanticTags, setAppState]);

  const copy =
    style === "professional"
      ? "Building your personalised requirements profile…"
      : style === "friendly"
        ? "Hang tight — getting to know what you like."
        : "Decoding your preferences — almost there.";

  // Rotating witty status lines so the wait feels alive.
  const STATUS_LINES = [
    "Reading your dealbreakers…",
    "Mapping budget to market tiers…",
    "Aligning location semantics…",
    "Inferring lifestyle signals…",
    "Cross-checking positive preferences…",
    "Finalising your profile tags…",
  ];
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1600);
    return () => clearInterval(id);
  }, []);

  const statusLine = STATUS_LINES[tick % STATUS_LINES.length];

  // Floating chip labels that gently drift to entertain the eye.
  const FLOAT_CHIPS = ["budget", "target", "identity", "style", "dealbreakers", "lifestyle"];

  return (
    <div className="relative flex min-h-[60vh] flex-col items-center justify-center overflow-hidden text-center">
      {/* Floating ambient chips */}
      <div className="pointer-events-none absolute inset-0">
        {FLOAT_CHIPS.map((label, i) => (
          <span
            key={label}
            className="absolute rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground backdrop-blur"
            style={{
              left: `${10 + ((i * 67) % 80)}%`,
              top: `${15 + ((i * 41) % 70)}%`,
              animation: `floatDrift ${6 + (i % 3)}s ease-in-out ${i * 0.4}s infinite alternate`,
              opacity: 0.55,
            }}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Orbit ring with spinning conic gradient */}
      <div className="relative mb-8 h-28 w-28">
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background:
              "conic-gradient(from 0deg, transparent 0deg, oklch(0.58 0.19 258 / 0.55) 90deg, transparent 180deg, oklch(0.58 0.19 258 / 0.55) 270deg, transparent 360deg)",
            animation: "spin 2.4s linear infinite",
            WebkitMask:
              "radial-gradient(closest-side, transparent calc(100% - 4px), #000 calc(100% - 3px))",
            mask: "radial-gradient(closest-side, transparent calc(100% - 4px), #000 calc(100% - 3px))",
          }}
        />
        <div className="pulse-ring absolute inset-2 rounded-full" />
        <div
          className="pulse-ring absolute inset-2 rounded-full"
          style={{ animationDelay: "0.6s" }}
        />
        <div className="absolute inset-6 rounded-full bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className="h-2.5 w-2.5 rounded-full bg-background"
            style={{ animation: "pulse 1.4s ease-in-out infinite" }}
          />
        </div>
      </div>

      <h2 className="max-w-md text-2xl font-medium tracking-tight">{copy}</h2>
      <p
        key={tick}
        className="mt-2 min-h-[1.25rem] text-sm text-muted-foreground"
        style={{ animation: "fadeSlideIn 0.5s ease-out" }}
      >
        {statusLine}
      </p>
      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        semantic alignment · phase 1.5
      </p>

      {/* Marching progress bars */}
      <div className="mt-10 flex w-full max-w-xs flex-col gap-2">
        {[100, 80, 60].map((w, i) => (
          <div
            key={i}
            className="relative h-2 overflow-hidden rounded-full bg-muted"
            style={{ width: `${w}%` }}
          >
            <div
              className="absolute inset-y-0 left-0 w-1/3 rounded-full bg-gradient-to-r from-transparent via-primary/70 to-transparent"
              style={{ animation: `march 1.8s linear ${i * 0.25}s infinite` }}
            />
          </div>
        ))}
      </div>

      <style>{`
        @keyframes march {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
        @keyframes floatDrift {
          0%   { transform: translate(0, 0); }
          100% { transform: translate(12px, -14px); }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

