import { useState } from "react";
import { ArrowRight, Building2, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";

import type {
  AgentStyle,
  Gender,
  Identity,
  Phase1Form,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { t } from "@/lib/i18n";

const IDENTITY_VALUES: Identity[] = ["first_time_buyer", "investor", "upgrader"];
const GENDER_VALUES: Gender[] = ["female", "male", "prefer_not_to_say"];
const STYLE_VALUES: AgentStyle[] = ["Professional", "Friendly", "Enthusiastic"];

export function PhaseOneForm() {
  const lang = useAppStore((s) => s.lang);
  const setSessionId = useAppStore((s) => s.setSessionId);
  const setPhase1Form = useAppStore((s) => s.setPhase1Form);
  const setAppState = useAppStore((s) => s.setAppState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Phase1Form>({
    budget: 500000,
    agent_style: "Professional",
    target: "",
    identity: "first_time_buyer",
    gender: "prefer_not_to_say",
    description: "",
    house_type: "",
    location: "",
  });

  const valid =
    form.budget > 0 &&
    form.target.trim().length > 0 &&
    form.description.trim().length >= 10;

  const submit = async () => {
    if (!valid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      setPhase1Form(form);
      const res = await api.initSession(form);
      setSessionId(res.session_id);
      setAppState("SEMANTIC_ALIGNING");
    } catch (e) {
      console.error(e);
      setError(
        e instanceof Error
          ? `${t("p1.error.prefix", lang)} ${e.message}`
          : t("p1.error", lang),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative">
      {/* Hero */}
      <div className="mb-10 max-w-2xl">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground backdrop-blur">
          <Sparkles className="h-3 w-3 text-primary" />
          {t("p1.badge", lang)}
        </div>
        <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight md:text-5xl">
          {lang === "en" ? (
            <>
              {t("p1.title.a", lang)} <span className="text-gradient">{t("p1.title.home", lang)}</span> {t("p1.title.b", lang)}
              <br />
              {t("p1.title.c", lang)}
            </>
          ) : (
            <>
              {t("p1.title.a", lang)}
              <span className="text-gradient">{t("p1.title.home", lang)}</span>
              {t("p1.title.b", lang)}
            </>
          )}
        </h1>
        <p className="mt-4 max-w-lg text-base leading-relaxed text-muted-foreground">
          {t("p1.subtitle", lang)}
        </p>
      </div>

      <div className="glass-strong relative overflow-hidden rounded-3xl border border-border shadow-[var(--shadow-elegant)]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

        <div className="grid gap-8 p-8 md:grid-cols-2 md:p-10">
          {/* Budget */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("p1.label.budget", lang)}
            </Label>
            <Input
              type="number"
              inputMode="numeric"
              min={0}
              step={10000}
              value={form.budget || ""}
              onChange={(e) =>
                setForm({ ...form, budget: Number(e.target.value) || 0 })
              }
              className="h-12 rounded-xl border-border-strong bg-surface-raised/80 text-lg font-medium tabular-nums"
              placeholder={t("p1.placeholder.budget", lang)}
            />
          </div>

          {/* Target */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("p1.label.target", lang)}
            </Label>
            <Input
              value={form.target}
              onChange={(e) => setForm({ ...form, target: e.target.value })}
              className="h-12 rounded-xl border-border-strong bg-surface-raised/80 text-base"
              placeholder={t("p1.placeholder.target", lang)}
            />
          </div>

          {/* Description */}
          <div className="space-y-2.5 md:col-span-2">
            <div className="flex items-baseline justify-between">
              <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {t("p1.label.description", lang)}
              </Label>
              <span className="font-mono text-[10px] tabular-nums text-muted-foreground/70">
                {form.description.trim().length}/600
              </span>
            </div>
            <Textarea
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value.slice(0, 600) })
              }
              rows={4}
              className="min-h-[112px] rounded-xl border-border-strong bg-surface-raised/80 text-[15px] leading-relaxed placeholder:text-muted-foreground/60"
              placeholder={t("p1.placeholder.description", lang)}
            />
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground/70">
              {t("p1.hint.description", lang)}
            </p>
          </div>

          {/* Identity */}
          <div className="space-y-2.5 md:col-span-2">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("p1.label.identity", lang)}
            </Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {IDENTITY_VALUES.map((v) => (
                <Choice
                  key={v}
                  active={form.identity === v}
                  onClick={() => setForm({ ...form, identity: v })}
                  label={t(`p1.identity.${v}`, lang)}
                  hint={t(`p1.identity.${v}.hint`, lang)}
                />
              ))}
            </div>
          </div>

          {/* Gender */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("p1.label.gender", lang)}
            </Label>
            <div className="grid grid-cols-3 gap-2">
              {GENDER_VALUES.map((v) => (
                <Choice
                  key={v}
                  active={form.gender === v}
                  onClick={() => setForm({ ...form, gender: v })}
                  label={t(`p1.gender.${v}`, lang)}
                  compact
                />
              ))}
            </div>
          </div>

          {/* Style */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("p1.label.style", lang)}
            </Label>
            <div className="grid grid-cols-3 gap-2">
              {STYLE_VALUES.map((v) => (
                <Choice
                  key={v}
                  active={form.agent_style === v}
                  onClick={() => setForm({ ...form, agent_style: v })}
                  label={t(`p1.style.${v}`, lang)}
                  hint={t(`p1.style.${v}.hint`, lang)}
                  compact
                />
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="border-t border-destructive/40 bg-destructive/10 px-8 py-3 text-sm text-destructive md:px-10">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between gap-4 border-t border-border/60 bg-surface/40 px-8 py-5 md:px-10">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            <Building2 className="h-3.5 w-3.5" />
            {t("p1.fields", lang)}
          </div>
          <Button
            onClick={submit}
            disabled={!valid || submitting}
            className="group h-11 rounded-xl bg-gradient-to-br from-primary to-primary-glow px-6 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-all hover:translate-y-[-1px]"
          >
            {submitting ? t("p1.cta.loading", lang) : t("p1.cta", lang)}
            <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function Choice({
  active,
  onClick,
  label,
  hint,
  compact,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  hint?: string;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "group relative rounded-xl border text-left transition-all",
        compact ? "px-3 py-2.5" : "px-4 py-3.5",
        active
          ? "border-primary/50 bg-primary/[0.06] shadow-[0_0_0_3px_oklch(0.58_0.19_258/0.08)]"
          : "border-border bg-surface-raised/60 hover:border-border-strong hover:bg-surface-raised",
      ].join(" ")}
    >
      <div
        className={[
          "font-medium leading-tight tracking-tight",
          compact ? "text-sm" : "text-[15px]",
          active ? "text-foreground" : "text-foreground/90",
        ].join(" ")}
      >
        {label}
      </div>
      {hint && (
        <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
          {hint}
        </div>
      )}
      {active && (
        <span className="absolute right-3 top-3 h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_oklch(0.58_0.19_258/0.6)]" />
      )}
    </button>
  );
}
