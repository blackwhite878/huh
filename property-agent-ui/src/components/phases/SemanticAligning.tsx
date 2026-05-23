import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { subscribeSessionReady } from "@/lib/api";
import { deriveTagsFromDescription } from "@/lib/semantic";

export function SemanticAligning() {
  const sessionId = useAppStore((s) => s.sessionId);
  const phase1Form = useAppStore((s) => s.phase1Form);
  const style = phase1Form?.agent_style ?? "professional";
  const setSemanticTags = useAppStore((s) => s.setSemanticTags);
  const setAppState = useAppStore((s) => s.setAppState);

  useEffect(() => {
    if (!sessionId) return;
    let done = false;
    const finish = (tags: string[], warning: boolean) => {
      if (done) return;
      done = true;
      setSemanticTags(tags, warning);
      setAppState("PROFILING_COMPLETE");
      stop();
      clearTimeout(fallbackTimer);
    };

    const stop = subscribeSessionReady(sessionId, (data) => {
      if (data.status === "ready") {
        finish(data.semantic_tags ?? [], !!data.alignment_warning);
      }
    });

    // Local fallback: if backend doesn't respond, derive tags from the
    // Phase 1 description so Profiling Complete shows real exclusions.
    const fallbackTimer = setTimeout(() => {
      const tags = deriveTagsFromDescription(phase1Form?.description ?? "");
      finish(tags, true);
    }, 2200);

    return () => {
      stop();
      clearTimeout(fallbackTimer);
    };
  }, [sessionId, phase1Form, setSemanticTags, setAppState]);

  const copy =
    style === "professional"
      ? "Building your personalised requirements profile…"
      : style === "friendly"
        ? "Hang tight — getting to know what you like."
        : "Decoding your preferences — almost there.";

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      {/* Pulse rings */}
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

      {/* Shimmer bars */}
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
