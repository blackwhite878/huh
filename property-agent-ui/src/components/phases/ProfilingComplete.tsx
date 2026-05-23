import { ArrowRight, AlertTriangle, ShieldCheck } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";

export function ProfilingComplete() {
  const semanticTags = useAppStore((s) => s.semanticTags);
  const alignmentWarning = useAppStore((s) => s.alignmentWarning);
  const setAppState = useAppStore((s) => s.setAppState);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-success">
          <ShieldCheck className="h-3 w-3" />
          profile aligned
        </div>
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
          Your <span className="text-gradient">preference signature</span>
        </h2>
        <p className="mt-3 text-muted-foreground">
          We detected the following negative preferences. These will be filtered
          out automatically during your property search.
        </p>
      </div>

      <div className="glass-strong rounded-3xl border border-border p-8 shadow-[var(--shadow-elegant)]">
        {alignmentWarning && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground/90">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning" />
            <span>
              Semantic alignment ran in degraded mode — only minimal preferences
              were detected. You can refine them during the conversation.
            </span>
          </div>
        )}

        <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Detected exclusions ({semanticTags.length})
        </div>

        {semanticTags.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface/40 p-6 text-center text-sm text-muted-foreground">
            No specific exclusions detected. Tell the agent more in the next step.
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {semanticTags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-primary/20 bg-primary/[0.06] px-3 py-1.5 font-mono text-xs text-primary"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        <div className="mt-8 flex items-center justify-end">
          <Button
            onClick={() => setAppState("CHATTING")}
            className="group h-11 rounded-xl bg-gradient-to-br from-primary to-primary-glow px-6 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-all hover:translate-y-[-1px]"
          >
            Begin consultation
            <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
