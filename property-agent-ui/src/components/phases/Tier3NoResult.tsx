import { SearchX, RotateCcw } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { t } from "@/lib/i18n";

export function Tier3NoResult() {
  const lang = useAppStore((s) => s.lang);
  const resetAll = useAppStore((s) => s.resetAll);
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center py-20 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-surface-raised shadow-[var(--shadow-soft)]">
        <SearchX className="h-7 w-7 text-muted-foreground" />
      </div>
      <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
        {t("t3.title", lang)}
      </h2>
      <p className="mt-3 max-w-md text-muted-foreground">{t("t3.body", lang)}</p>
      <Button
        onClick={resetAll}
        className="mt-8 h-11 rounded-xl bg-foreground px-6 text-sm font-medium text-background"
      >
        <RotateCcw className="mr-1.5 h-4 w-4" />
        {t("t3.cta", lang)}
      </Button>
    </div>
  );
}
