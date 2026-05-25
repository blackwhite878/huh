import type { AppState } from "@/lib/types";
import { useAppStore } from "@/lib/store";
import { t } from "@/lib/i18n";

export function StateChip({ state }: { state: AppState }) {
  const lang = useAppStore((s) => s.lang);
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground backdrop-blur">
      <span className="h-1.5 w-1.5 rounded-full bg-primary" />
      {t(`state.${state}`, lang)}
    </div>
  );
}
