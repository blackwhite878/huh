import { useState } from "react";
import {
  MapPin,
  Banknote,
  ArrowRight,
  X,
  Sparkles,
  AlertTriangle,
  Building2,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import type { PropertyResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { t, type Lang } from "@/lib/i18n";

export function ResultsBatch() {
  const lang = useAppStore((s) => s.lang);
  const appState = useAppStore((s) => s.appState);
  const sessionId = useAppStore((s) => s.sessionId);
  const results = useAppStore((s) => s.currentBatch);
  const hasMore = useAppStore((s) => s.hasMore);
  const totalAvailable = useAppStore((s) => s.totalAvailable);
  const rejectionCount = useAppStore((s) => s.rejectionCount);
  const rejectedIds = useAppStore((s) => s.rejectedIds);
  const degraded = useAppStore((s) => s.degraded);
  const batchIndex = useAppStore((s) => s.batchIndex);
  const setResults = useAppStore((s) => s.setResults);
  const setRejectionCount = useAppStore((s) => s.setRejectionCount);
  const addRejectedId = useAppStore((s) => s.addRejectedId);
  const setAppState = useAppStore((s) => s.setAppState);

  const fetchNext = async () => {
    if (!sessionId) return;
    try {
      const data = await api.nextBatch(sessionId);
      setResults(data);
      setAppState("BATCH_2_DISPLAY");
    } catch (e) {
      console.warn(e);
    }
  };

  const reject = async (propertyId: string, reason: string) => {
    if (!sessionId) return;
    addRejectedId(propertyId);
    try {
      const data = await api.rejectSingle(sessionId, propertyId, reason);
      setRejectionCount(data.rejection_count);
      if (data.rejection_count >= totalAvailable && totalAvailable > 0) {
        setAppState("ALL_REJECTED");
        try {
          await api.rejectAll(sessionId);
        } catch (e) {
          console.warn("[rejectAll] failed", e);
        }
        setAppState("ACTION_REQUIRED_UI");
      }
    } catch (e) {
      console.warn(e);
    }
  };

  return (
    <div>
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground backdrop-blur">
            <Sparkles className="h-3 w-3 text-primary" />
            {t("results.batch", lang)} {batchIndex || 1}
            {t("results.batch.suffix", lang)} · {results.length} {t("results.of", lang)} {totalAvailable}
          </div>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            {t("results.title.a", lang)}{" "}
            <span className="text-gradient">{t("results.title.b", lang)}</span>
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("results.subtitle", lang)}
            {rejectionCount > 0 && (
              <>
                {" "}
                <span className="font-mono text-xs">
                  · {rejectionCount} {t("results.declined", lang)}
                </span>
              </>
            )}
          </p>
        </div>
      </div>

      {degraded && (
        <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-warning/40 bg-warning/10 p-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning" />
          <span className="text-foreground/80">{t("results.degraded", lang)}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {results.map((p) => (
          <PropertyCard
            key={p.property_id}
            property={p}
            degraded={degraded}
            rejected={rejectedIds.includes(p.property_id)}
            onReject={reject}
            lang={lang}
          />
        ))}
      </div>

      {appState === "BATCH_1_DISPLAY" && hasMore && (
        <div className="mt-10 flex justify-center">
          <Button
            onClick={fetchNext}
            className="group h-11 rounded-xl bg-gradient-to-br from-primary to-primary-glow px-6 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)]"
          >
            {t("results.cta.next", lang)}
            <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </div>
      )}
    </div>
  );
}

function PropertyCard({
  property,
  degraded,
  rejected,
  onReject,
  lang,
}: {
  property: PropertyResult;
  degraded: boolean;
  rejected: boolean;
  onReject: (id: string, reason: string) => void;
  lang: Lang;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (rejected) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface/40 p-6 text-center text-sm text-muted-foreground">
        {t("results.removed", lang)}
      </div>
    );
  }

  return (
    <div className="glass-strong group relative overflow-hidden rounded-2xl border border-border shadow-[var(--shadow-elegant)] transition-all hover:translate-y-[-2px] hover:shadow-[var(--shadow-glow)]">
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-accent to-muted">
        {property.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={property.image_url}
            alt={property.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Building2 className="h-12 w-12 text-muted-foreground/40" />
          </div>
        )}
        <div className="absolute left-3 top-3 flex gap-1.5">
          <span
            className={[
              "rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] backdrop-blur",
              property.tier === "tier_1"
                ? "bg-primary/85 text-primary-foreground"
                : "bg-warning/85 text-warning-foreground",
            ].join(" ")}
          >
            {property.tier === "tier_1"
              ? t("results.tier_1", lang)
              : t("results.tier_2", lang)}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div>
          <h3 className="text-lg font-semibold leading-tight tracking-tight">
            {property.title}
          </h3>
          <div className="mt-1.5 flex items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {property.location}
            </span>
            <span className="flex items-center gap-1 font-medium text-foreground tabular-nums">
              <Banknote className="h-3.5 w-3.5" />
              RM {property.price.toLocaleString()}
            </span>
          </div>
        </div>

        {property.feature_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {property.feature_tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-border bg-surface/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="rounded-xl border border-border bg-surface/50 p-3">
          {degraded ? (
            <div className="flex items-center gap-2 text-xs text-warning-foreground/80">
              <AlertTriangle className="h-3.5 w-3.5 text-warning" />
              {t("results.degraded_card", lang)}
            </div>
          ) : (
            <>
              <div className="mb-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-primary">
                <Sparkles className="h-3 w-3" /> {t("results.ai_remarks", lang)}
              </div>
              <p className="text-sm leading-relaxed text-foreground/80">
                {property.ai_remarks ?? t("results.analysis_pending", lang)}
              </p>
            </>
          )}

          {property.tier === "tier_2" && property.missing_features && (
            <div className="mt-3 border-t border-border pt-3">
              <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-warning">
                {t("results.tradeoffs", lang)}
              </div>
              <div className="text-xs text-muted-foreground">
                {t("results.missing", lang)}: {property.missing_features.join(", ")}
                {property.remedy && (
                  <div className="mt-1">
                    {t("results.remedy", lang)}: {property.remedy}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {open ? (
          <div className="space-y-2 rounded-xl border border-border bg-surface/60 p-3">
            <Input
              autoFocus
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t("results.reject_placeholder", lang)}
              className="h-9 rounded-lg border-border bg-surface-raised text-sm"
            />
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setOpen(false);
                  setReason("");
                }}
                className="h-8"
              >
                {t("results.btn.cancel", lang)}
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  if (!reason.trim()) return;
                  onReject(property.property_id, reason);
                  setOpen(false);
                }}
                className="h-8 rounded-lg bg-foreground text-background"
              >
                {t("results.btn.submit", lang)}
              </Button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setOpen(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-border py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:border-destructive/40 hover:text-destructive"
          >
            <X className="h-3.5 w-3.5" />
            {t("results.btn.not_interested", lang)}
          </button>
        )}
      </div>
    </div>
  );
}
