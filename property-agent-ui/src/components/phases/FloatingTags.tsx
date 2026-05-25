// Floating chips for the profiling page (Phase 1.5).
//
// Each chip surfaces a Phase 1 input value the user typed/picked, so the
// agent's "memory" of what it knows is visible while semantic alignment
// runs in the background.
//
// (Collision contract and layout strategy are unchanged from the original
// file — only the chip *labels* now go through the i18n dict so the chips
// switch language when the toggle is flipped.)

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import type { AgentStyle, Gender, Identity } from "@/lib/types";
import { t, type Lang } from "@/lib/i18n";

type DriftVariant = "a" | "b" | "c" | "d";

interface Anchor {
  key: string;
  label: string;
  side: "left" | "right";
  edgeOffset: string;
  top: string;
  delay: string;
  duration: string;
  variant: DriftVariant;
  emphasis?: boolean;
}

const MIN_WIDTH_PX = 880;

function identityLabel(v: Identity, lang: Lang): string {
  return t(`p1.identity.${v}`, lang);
}
function genderLabel(v: Gender, lang: Lang): string {
  // "Prefer not to say" is too long for a chip; use a short variant.
  if (v === "prefer_not_to_say") return t("p1.gender.undisclosed_short", lang);
  return t(`p1.gender.${v}`, lang);
}
function styleLabel(v: AgentStyle, lang: Lang): string {
  return t(`p1.style.${v}`, lang);
}

function fmtBudget(n: number | undefined): string | null {
  if (!n || n <= 0) return null;
  return `RM ${n.toLocaleString("en-MY")}`;
}

function trimText(v: string | undefined, max = 28): string | null {
  const txt = (v ?? "").trim();
  if (!txt) return null;
  return txt.length > max ? `${txt.slice(0, max - 1)}…` : txt;
}

const LEFT_TOPS = ["14%", "44%", "74%"];
const RIGHT_TOPS = ["12%", "36%", "60%", "84%"];

const VARIANTS: DriftVariant[] = ["a", "b", "c", "d"];

interface ChipSpec {
  key: string;
  label: string;
  emphasis?: boolean;
}

export function FloatingTags() {
  const [visible, setVisible] = useState(false);
  const lang = useAppStore((s) => s.lang);
  const phase1 = useAppStore((s) => s.phase1Form);

  useEffect(() => {
    const check = () => setVisible(window.innerWidth >= MIN_WIDTH_PX);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!visible) return null;

  const specs: ChipSpec[] = [];

  const budget = fmtBudget(phase1?.budget);
  if (budget)
    specs.push({
      key: "budget",
      label: `${t("ft.label.budget", lang)} · ${budget}`,
      emphasis: true,
    });

  const target = trimText(phase1?.target);
  if (target)
    specs.push({
      key: "target",
      label: `${t("ft.label.target", lang)} · ${target.toUpperCase()}`,
      emphasis: true,
    });

  if (phase1?.identity) {
    specs.push({
      key: "identity",
      label: `${t("ft.label.identity", lang)} · ${identityLabel(phase1.identity, lang).toUpperCase()}`,
      emphasis: true,
    });
  }

  if (phase1?.agent_style) {
    specs.push({
      key: "agent_style",
      label: `${t("ft.label.style", lang)} · ${styleLabel(phase1.agent_style, lang).toUpperCase()}`,
    });
  }

  if (phase1?.gender) {
    specs.push({
      key: "gender",
      label: `${t("ft.label.gender", lang)} · ${genderLabel(phase1.gender, lang).toUpperCase()}`,
    });
  }

  const desc = trimText(phase1?.description, 32);
  if (desc) specs.push({ key: "description", label: `“${desc}”` });

  const anchors: Anchor[] = [];
  let leftIdx = 0;
  let rightIdx = 0;
  specs.forEach((spec, i) => {
    const side: "left" | "right" =
      (i % 2 === 0 && leftIdx < LEFT_TOPS.length) ||
      rightIdx >= RIGHT_TOPS.length
        ? "left"
        : "right";
    const top =
      side === "left"
        ? LEFT_TOPS[Math.min(leftIdx++, LEFT_TOPS.length - 1)]
        : RIGHT_TOPS[Math.min(rightIdx++, RIGHT_TOPS.length - 1)];
    anchors.push({
      key: spec.key,
      label: spec.label,
      side,
      edgeOffset: side === "left" ? "5%" : "5%",
      top,
      delay: `${(i * 0.37) % 2.4}s`,
      duration: `${6.7 + ((i * 1.3) % 3.5)}s`,
      variant: VARIANTS[i % VARIANTS.length],
      emphasis: spec.emphasis,
    });
  });

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {anchors.map((a) => (
        <div
          key={a.key}
          className="absolute max-w-[38%]"
          style={{
            [a.side]: a.edgeOffset,
            top: a.top,
            transform: "translateY(-50%)",
          }}
        >
          <div
            className={[
              "drift truncate whitespace-nowrap rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] backdrop-blur-sm",
              `drift-${a.variant}`,
              a.emphasis
                ? "border-primary/40 bg-primary/[0.06] text-foreground/80"
                : "border-border/60 bg-surface/70 text-muted-foreground",
            ].join(" ")}
            style={{
              animationDelay: a.delay,
              animationDuration: a.duration,
            }}
          >
            {a.label}
          </div>
        </div>
      ))}
    </div>
  );
}
