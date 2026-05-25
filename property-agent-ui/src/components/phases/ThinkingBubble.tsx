// Fake "thinking" indicator for Phase 2.
// Not driven by the LLM — purely a UX placeholder while the chat request
// is in flight. Cycles through a set of phrases with a typing effect and
// a fade transition between phrases.

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { t } from "@/lib/i18n";

const PHRASE_KEYS = [
  "thinking.0",
  "thinking.1",
  "thinking.2",
  "thinking.3",
  "thinking.4",
] as const;

const TYPE_MS = 40;       // ms per character
const HOLD_MS = 700;      // ms to hold full phrase
const FADE_MS = 250;      // ms of fade between phrases

export function ThinkingBubble({ retryCount = 0 }: { retryCount?: number } = {}) {
  const lang = useAppStore((s) => s.lang);
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [typed, setTyped] = useState("");
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const phrase = t(PHRASE_KEYS[phraseIdx], lang);
    let cancelled = false;
    setTyped("");
    setFading(false);

    // Type out
    let i = 0;
    const typeTimer = setInterval(() => {
      if (cancelled) return;
      i += 1;
      setTyped(phrase.slice(0, i));
      if (i >= phrase.length) clearInterval(typeTimer);
    }, TYPE_MS);

    // After full phrase + hold, fade out, then advance.
    const fadeTimer = setTimeout(
      () => {
        if (cancelled) return;
        setFading(true);
        setTimeout(() => {
          if (cancelled) return;
          setPhraseIdx((p) => (p + 1) % PHRASE_KEYS.length);
        }, FADE_MS);
      },
      phrase.length * TYPE_MS + HOLD_MS,
    );

    return () => {
      cancelled = true;
      clearInterval(typeTimer);
      clearTimeout(fadeTimer);
    };
  }, [phraseIdx, lang]);

  return (
    <div className="flex animate-in fade-in slide-in-from-bottom-1 gap-3">
      <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-glow text-primary-foreground shadow-[var(--shadow-glow)]">
        <Bot className="h-3.5 w-3.5" />
      </div>
      <div className="max-w-[78%] rounded-2xl rounded-tl-sm border border-border bg-surface-raised px-4 py-2.5 text-sm leading-relaxed text-muted-foreground">
        {retryCount > 0 && (
          <div className="mb-2 text-xs font-semibold text-orange-500">
            {t("thinking.retry", lang)} ({retryCount}/5)...
          </div>
        )}
        <span
          className="inline-block transition-opacity"
          style={{
            opacity: fading ? 0 : 1,
            transitionDuration: `${FADE_MS}ms`,
          }}
        >
          {typed}
          <span className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-0.5 animate-pulse bg-muted-foreground/70 align-middle" />
        </span>
        <span className="ml-2 inline-flex gap-1 align-middle">
          <Dot delay="0ms" />
          <Dot delay="150ms" />
          <Dot delay="300ms" />
        </span>
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1 w-1 animate-bounce rounded-full bg-muted-foreground/60"
      style={{ animationDelay: delay }}
    />
  );
}
