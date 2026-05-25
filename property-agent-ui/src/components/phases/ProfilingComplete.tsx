import { ArrowRight, AlertTriangle, ShieldCheck, Minus, Plus } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { partitionTags } from "@/lib/semantic";
import { getTagLabel } from "@/lib/enum-labels";
import { t } from "@/lib/i18n";

export function ProfilingComplete() {
  const lang = useAppStore((s) => s.lang);
  const semanticTags = useAppStore((s) => s.semanticTags);
  const alignmentWarning = useAppStore((s) => s.alignmentWarning);
  const alignmentError = useAppStore((s) => s.alignmentError);
  const setAppState = useAppStore((s) => s.setAppState);

  const { negative, positive } = partitionTags(semanticTags);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-success">
          <ShieldCheck className="h-3 w-3" />
          {t("pc.badge", lang)}
        </div>
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
          {t("pc.title.a", lang)}{" "}
          <span className="text-gradient">{t("pc.title.b", lang)}</span>
        </h2>
        <p className="mt-3 text-muted-foreground">{t("pc.subtitle", lang)}</p>
      </div>

      <div className="glass-strong rounded-3xl border border-border p-8 shadow-[var(--shadow-elegant)]">
        {alignmentError && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive-foreground/90">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
            <div>
              <div className="font-medium">{t("pc.alignment_failed", lang)}</div>
              <div className="mt-0.5 break-all font-mono text-[11px] opacity-80">{alignmentError}</div>
            </div>
          </div>
        )}
        {alignmentWarning && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground/90">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning" />
            <span>{t("pc.degraded_warning", lang)}</span>
          </div>
        )}

        {/* Required features (positive) */}
        <div className="mb-6">
          <div className="mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            <Plus className="h-3 w-3 text-success" />
            {t("pc.required", lang)} ({positive.length})
          </div>
          {positive.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-surface/40 p-4 text-center text-xs text-muted-foreground">
              {t("pc.no_required", lang)}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {positive.map((tag) => (
                <span
                  key={`pos-${tag}`}
                  className="rounded-full border border-success/30 bg-success/10 px-3 py-1.5 font-mono text-xs text-success"
                >
                  +{getTagLabel(tag, "pos", lang)}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Exclusions (negative) */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            <Minus className="h-3 w-3 text-primary" />
            {t("pc.exclusions", lang)} ({negative.length})
          </div>
          {negative.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-surface/40 p-4 text-center text-xs text-muted-foreground">
              {t("pc.no_exclusions", lang)}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {negative.map((tag) => (
                <span
                  key={`neg-${tag}`}
                  className="rounded-full border border-primary/20 bg-primary/[0.06] px-3 py-1.5 font-mono text-xs text-primary"
                >
                  −{getTagLabel(tag, "neg", lang)}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mt-8 flex items-center justify-end">
          <Button
            onClick={() => setAppState("CHATTING")}
            className="group h-11 rounded-xl bg-gradient-to-br from-primary to-primary-glow px-6 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-all hover:translate-y-[-1px]"
          >
            {t("pc.cta", lang)}
            <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
