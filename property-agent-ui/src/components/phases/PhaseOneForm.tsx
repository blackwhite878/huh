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

const IDENTITIES: { value: Identity; label: string; hint: string }[] = [
  { value: "first_time_buyer", label: "First-time Buyer", hint: "Budget-focused" },
  { value: "investor", label: "Investor", hint: "Yield-driven" },
  { value: "upgrader", label: "Upgrader", hint: "Lifestyle-focused" },
];
const GENDERS: { value: Gender; label: string }[] = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];
const STYLES: { value: AgentStyle; label: string; hint: string }[] = [
  { value: "professional", label: "Professional", hint: "Crisp · advisory" },
  { value: "friendly", label: "Friendly", hint: "Warm · conversational" },
  { value: "active", label: "Active", hint: "Punchy · proactive" },
];

export function PhaseOneForm() {
  const setSessionId = useAppStore((s) => s.setSessionId);
  const setPhase1Form = useAppStore((s) => s.setPhase1Form);
  const setAppState = useAppStore((s) => s.setAppState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Phase1Form>({
    budget: 500000,
    agent_style: "professional",
    target: "",
    identity: "first_time_buyer",
    gender: "prefer_not_to_say",
    description: "",
    // Backend-only fields (no Phase 1 UI). Sent as empty string when unknown.
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
          ? `Couldn't reach the agent backend: ${e.message}`
          : "Couldn't reach the agent backend. Please try again.",
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
          Phase 1 · structured profiling
        </div>
        <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight md:text-5xl">
          Tell us what <span className="text-gradient">home</span> means
          <br />
          to you.
        </h1>
        <p className="mt-4 max-w-lg text-base leading-relaxed text-muted-foreground">
          A few quick details so the AI can build your personalised property
          profile. We&apos;ll align on semantics in the background.
        </p>
      </div>

      {/* Form card */}
      <div className="glass-strong relative overflow-hidden rounded-3xl border border-border shadow-[var(--shadow-elegant)]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

        <div className="grid gap-8 p-8 md:grid-cols-2 md:p-10">
          {/* Budget */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Budget (RM)
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
              placeholder="500,000"
            />
          </div>

          {/* Target */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Target area / property
            </Label>
            <Input
              value={form.target}
              onChange={(e) => setForm({ ...form, target: e.target.value })}
              className="h-12 rounded-xl border-border-strong bg-surface-raised/80 text-base"
              placeholder="e.g. Condo in Johor Bahru"
            />
          </div>

          {/* Description — free text for semantic alignment */}
          <div className="space-y-2.5 md:col-span-2">
            <div className="flex items-baseline justify-between">
              <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                What should we avoid? · describe your dealbreakers
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
              placeholder="e.g. No west-facing units, must have security, prefer high floor and close to MRT. Avoid noisy main roads."
            />
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground/70">
              Used to derive your exclusion tags during semantic alignment.
            </p>
          </div>


          {/* Identity */}
          <div className="space-y-2.5 md:col-span-2">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Buyer identity
            </Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {IDENTITIES.map((it) => (
                <Choice
                  key={it.value}
                  active={form.identity === it.value}
                  onClick={() => setForm({ ...form, identity: it.value })}
                  label={it.label}
                  hint={it.hint}
                />
              ))}
            </div>
          </div>

          {/* Gender */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Gender
            </Label>
            <div className="grid grid-cols-3 gap-2">
              {GENDERS.map((g) => (
                <Choice
                  key={g.value}
                  active={form.gender === g.value}
                  onClick={() => setForm({ ...form, gender: g.value })}
                  label={g.label}
                  compact
                />
              ))}
            </div>
          </div>

          {/* Style */}
          <div className="space-y-2.5">
            <Label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Agent tone
            </Label>
            <div className="grid grid-cols-3 gap-2">
              {STYLES.map((s) => (
                <Choice
                  key={s.value}
                  active={form.agent_style === s.value}
                  onClick={() => setForm({ ...form, agent_style: s.value })}
                  label={s.label}
                  hint={s.hint}
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
            5 fields · 30 seconds
          </div>
          <Button
            onClick={submit}
            disabled={!valid || submitting}
            className="group h-11 rounded-xl bg-gradient-to-br from-primary to-primary-glow px-6 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-all hover:translate-y-[-1px]"
          >
            {submitting ? "Initialising…" : "Build my profile"}
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
