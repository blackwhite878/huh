import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { subscribeSessionReady } from "@/lib/api";
import { deriveTagsFromDescription } from "@/lib/semantic";
import { FloatingTags } from "./FloatingTags";

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

  return (
    <div className="relative flex min-h-[60vh] flex-col items-center justify-center text-center">
      <FloatingTags />
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
        semantic alignment · phase 1.5
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
