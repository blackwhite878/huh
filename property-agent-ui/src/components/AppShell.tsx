import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { LANG_LABEL, t, type Lang } from "@/lib/i18n";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const lang = useAppStore((s) => s.lang);
  const setLang = useAppStore((s) => s.setLang);

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden">
      <div className="pointer-events-none absolute inset-0 grid-pattern opacity-60" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

      <header className="relative z-10 border-b border-border/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-sm font-semibold tracking-tight">
                LXVII<span className="text-gradient"></span>
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                {t("shell.tagline", lang)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Language toggle — visible on all phases, default EN. */}
            <div
              role="group"
              aria-label={t("shell.language", lang)}
              className="inline-flex items-center rounded-full border border-border bg-surface-raised/60 p-0.5 font-mono text-[10px] uppercase tracking-[0.18em] backdrop-blur"
            >
              {(["en", "zh"] as Lang[]).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  aria-pressed={lang === code}
                  className={[
                    "rounded-full px-3 py-1 transition-all",
                    lang === code
                      ? "bg-primary text-primary-foreground shadow-[var(--shadow-glow)]"
                      : "text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  {code === "en" ? "EN" : "中"}
                </button>
              ))}
              <span className="sr-only">{LANG_LABEL[lang]}</span>
            </div>

            <div className="hidden items-center gap-6 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground md:flex">
              <span className="flex items-center gap-1.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inset-0 animate-ping rounded-full bg-success/80" />
                  <span className="relative h-1.5 w-1.5 rounded-full bg-success" />
                </span>
                {t("shell.online", lang)}
              </span>
              <span>{t("shell.version", lang)}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-6 py-10">
        {children}
      </main>

      <footer className="relative z-10 border-t border-border/40 py-6 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        {t("shell.footer", lang)}
      </footer>
    </div>
  );
}
