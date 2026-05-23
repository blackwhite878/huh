import { RotateCcw, ArrowRight, Brain } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import { useActionResolution } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";

export function ActionRequired() {
  const sessionId = useAppStore((s) => s.sessionId);
  const { resolveAction } = useActionResolution(sessionId);

  const choose = async (action: "new_prompt" | "keep_memories") => {
    if (sessionId) {
      try {
        await resolveAction(action);
      } catch (e) {
        console.warn(e);
      }
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/[0.06] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-primary">
          <Brain className="h-3 w-3" />
          preferences updated
        </div>
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
          What&apos;s next?
        </h2>
        <p className="mt-3 text-muted-foreground">
          Your feedback has been learned. Choose how to continue.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ActionCard
          icon={RotateCcw}
          title="Start fresh"
          subtitle="New prompt"
          description="Clear everything and rebuild your profile from scratch."
          onClick={() => choose("new_prompt")}
        />
        <ActionCard
          icon={ArrowRight}
          title="Keep memories"
          subtitle="Continue with learned preferences"
          description="Hold on to your dialogue & exclusions, adjust the search."
          onClick={() => choose("keep_memories")}
          highlight
        />
      </div>
    </div>
  );
}

function ActionCard({
  icon: Icon,
  title,
  subtitle,
  description,
  onClick,
  highlight,
}: {
  icon: typeof RotateCcw;
  title: string;
  subtitle: string;
  description: string;
  onClick: () => void;
  highlight?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "group relative overflow-hidden rounded-2xl border p-6 text-left transition-all hover:translate-y-[-2px]",
        highlight
          ? "border-primary/40 bg-gradient-to-br from-primary/[0.08] to-primary-glow/[0.04] shadow-[var(--shadow-glow)]"
          : "glass-strong border-border shadow-[var(--shadow-elegant)]",
      ].join(" ")}
    >
      <div
        className={[
          "mb-4 flex h-10 w-10 items-center justify-center rounded-xl",
          highlight
            ? "bg-gradient-to-br from-primary to-primary-glow text-primary-foreground"
            : "bg-muted text-foreground",
        ].join(" ")}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {subtitle}
      </div>
      <h3 className="mt-1 text-xl font-semibold tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      <Button
        variant="ghost"
        className="mt-4 h-9 rounded-lg px-0 text-sm font-medium text-foreground hover:bg-transparent"
      >
        Continue
        <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-1" />
      </Button>
    </button>
  );
}
