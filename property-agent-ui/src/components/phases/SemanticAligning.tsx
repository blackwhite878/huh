import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { getClosedSessionReason, subscribeSessionReady } from "@/lib/api";
import { deriveTagsFromDescription } from "@/lib/semantic";
import { FloatingTags } from "./FloatingTags";
import { t } from "@/lib/i18n";
import type { AgentStyle } from "@/lib/types";

// Verbs cycled in the "thinking word" chip. Pure UX — not driven by the
// backend. Five phrases × ~1.2s slot each = one 6s loop, matched to the
// .think-word keyframes in styles.css.
const THINKING_WORD_KEYS = [
  "align.0",
  "align.1",
  "align.2",
  "align.3",
  "align.4",
] as const;

// Backend is authoritative. The local-derived path is a UI placeholder ONLY —
// even after it runs, a subsequent backend "ready" event will overwrite it.
const LOCAL_PLACEHOLDER_AFTER_MS = 60_000;

export function SemanticAligning() {
  const lang = useAppStore((s) => s.lang);
  const sessionId = useAppStore((s) => s.sessionId);
  const description = useAppStore((s) => s.phase1Form?.description) ?? "";
  const style = useAppStore((s) => s.phase1Form?.agent_style) ?? "Professional";
  const setSemanticTags = useAppStore((s) => s.setSemanticTags);
  const setAppState = useAppStore((s) => s.setAppState);
  const resetAll = useAppStore((s) => s.resetAll);

  // Snapshot the language at the moment the placeholder fires so the
  // fallback warning is written in the user's current locale. (It is
  // persisted into store as a plain string — see `setSemanticTags`.)
  const fallbackMsg = t("align.fallback", lang);

  useEffect(() => {
    if (!sessionId) return;
    let stop: (() => void) | null = null;
    let placeholderTimer: ReturnType<typeof setTimeout> | null = null;
    let backendWon = false;

    stop = subscribeSessionReady(
      sessionId,
      (data) => {
        if (data.status !== "ready") return;
        backendWon = true;
        const merged = [
          ...(data.positive_tags ?? []).map((tg) => `pos:${tg}`),
          ...(data.semantic_tags ?? []).map((tg) => `neg:${tg}`),
        ];
        setSemanticTags(merged, !!data.alignment_warning, data.error ?? null);
        setAppState("PROFILING_COMPLETE");
        if (placeholderTimer) clearTimeout(placeholderTimer);
        stop?.();
      },
      (error) => {
        if (!getClosedSessionReason(error)) return;
        if (placeholderTimer) clearTimeout(placeholderTimer);
        stop?.();
        resetAll();
      },
    );

    placeholderTimer = setTimeout(() => {
      if (backendWon) return;
      const tags = deriveTagsFromDescription(description);
      setSemanticTags(tags, true, fallbackMsg);
      setAppState("PROFILING_COMPLETE");
    }, LOCAL_PLACEHOLDER_AFTER_MS);

    return () => {
      stop?.();
      if (placeholderTimer) clearTimeout(placeholderTimer);
    };
  }, [sessionId, description, setSemanticTags, setAppState, resetAll, fallbackMsg]);

  // Style → headline key. Falls back to Professional if a future style
  // value sneaks through without a translation.
  const styleKey: AgentStyle = (["Professional", "Friendly", "Enthusiastic"] as AgentStyle[]).includes(
    style as AgentStyle,
  )
    ? (style as AgentStyle)
    : "Professional";
  const copy = t(`align.headline.${styleKey}`, lang);

  return (
    <div className="relative flex min-h-[60vh] flex-col items-center justify-center text-center">
      <FloatingTags />
      <div
        aria-live="polite"
        className="relative mb-6 inline-flex h-7 items-center justify-center overflow-hidden rounded-full border border-primary/30 bg-primary/[0.06] px-3 font-mono text-[10px] uppercase tracking-[0.22em] text-primary"
      >
        <div className="pointer-events-none mr-1 h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_oklch(0.58_0.19_258/0.65)]" />
        <div className="relative h-4 w-[140px]">
          {THINKING_WORD_KEYS.map((k, i) => (
            <span
              key={k}
              className="think-word absolute inset-0 flex items-center justify-center whitespace-nowrap"
              style={{
                animationDelay: `${(i * 6) / THINKING_WORD_KEYS.length}s`,
              }}
            >
              {t(k, lang)}…
            </span>
          ))}
        </div>
      </div>

      <div className="relative mb-8 h-20 w-20">
        <div className="pulse-ring absolute inset-0 rounded-full" />
        <div
          className="pulse-ring absolute inset-0 rounded-full"
          style={{ animationDelay: "0.5s" }}
        />
        <div className="absolute inset-2 rounded-full bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-3 w-3 rounded-full bg-background" />
        </div>
      </div>

      <h2 className="max-w-md text-2xl font-medium tracking-tight">{copy}</h2>
      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        {t("align.subtitle", lang)}
      </p>

      <div className="mt-10 flex w-full max-w-xs flex-col gap-2">
        {[100, 80, 60].map((w, i) => (
          <div
            key={i}
            className="shimmer h-2 overflow-hidden rounded-full bg-muted"
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    </div>
  );
}
