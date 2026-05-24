// Floating chips for the profiling page (Phase 1.5).
//
// Surfaces the live Phase 1 facts the agent is reasoning over —
// budget, house type, location — alongside the original decorative
// labels. Values come from the store; missing optional fields render
// as "—" rather than blank chips.
//
// Hard constraint: chips MUST NOT enter the centered safe zone where the
// headline / sub-copy / progress bars are rendered.
//
// Strategy:
//   - Anchor each chip to a fixed corner offset (well outside the safe
//     zone) and animate inside a bounded amplitude (~10px).
//   - Motion is 2D + slight rotation, driven by one of four irregular
//     drift keyframes with prime-ish durations/delays — no two chips
//     share the same phase, so the overall pattern is non-periodic on
//     human timescales (no synchronous up/down bobbing).
//   - On viewports narrower than the safe-zone width + chip margin,
//     chips are hidden — there is no honest position that avoids overlap.

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

type DriftVariant = "a" | "b" | "c" | "d";

interface Anchor {
  key: string;
  label: string;
  // Position relative to the host container. Exactly one of left/right
  // and one of top/bottom is set, in percent.
  left?: string;
  right?: string;
  top?: string;
  bottom?: string;
  delay: string;
  duration: string;
  variant: DriftVariant;
  emphasis?: boolean;
}

// Below this viewport width the safe zone + chip margins do not fit.
const MIN_WIDTH_PX = 880;

function fmtBudget(n: number | undefined): string {
  if (!n || n <= 0) return "—";
  return `RM ${n.toLocaleString("en-MY")}`;
}

function fmtText(v: string | undefined): string {
  const t = (v ?? "").trim();
  return t.length ? t : "—";
}

export function FloatingTags() {
  const [visible, setVisible] = useState(false);
  const phase1 = useAppStore((s) => s.phase1Form);

  useEffect(() => {
    const check = () => setVisible(window.innerWidth >= MIN_WIDTH_PX);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!visible) return null;

  const anchors: Anchor[] = [
    {
      key: "budget",
      label: `BUDGET · ${fmtBudget(phase1?.budget)}`,
      left: "4%",
      top: "16%",
      delay: "0s",
      duration: "7.3s",
      variant: "a",
      emphasis: true,
    },
    {
      key: "house_type",
      label: `HOUSE TYPE · ${fmtText(phase1?.house_type)}`,
      right: "4%",
      top: "18%",
      delay: "0.7s",
      duration: "8.9s",
      variant: "b",
      emphasis: true,
    },
    {
      key: "location",
      label: `LOCATION · ${fmtText(phase1?.location)}`,
      left: "5%",
      bottom: "20%",
      delay: "1.3s",
      duration: "6.7s",
      variant: "c",
      emphasis: true,
    },
    {
      key: "identity",
      label: "IDENTITY",
      right: "6%",
      top: "52%",
      delay: "0.4s",
      duration: "9.7s",
      variant: "d",
    },
    {
      key: "target",
      label: "TARGET",
      right: "8%",
      bottom: "24%",
      delay: "1.9s",
      duration: "7.9s",
      variant: "a",
    },
    {
      key: "lifestyle",
      label: "LIFESTYLE",
      left: "7%",
      top: "48%",
      delay: "1.1s",
      duration: "8.3s",
      variant: "b",
    },
    {
      key: "dealbreakers",
      label: "DEALBREAKERS",
      left: "9%",
      bottom: "44%",
      delay: "2.3s",
      duration: "10.1s",
      variant: "c",
    },
  ];

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {anchors.map((a) => (
        <div
          key={a.key}
          className={[
            "drift absolute rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] backdrop-blur-sm",
            `drift-${a.variant}`,
            a.emphasis
              ? "border-primary/40 bg-primary/[0.06] text-foreground/80"
              : "border-border/60 bg-surface/70 text-muted-foreground",
          ].join(" ")}
          style={{
            left: a.left,
            right: a.right,
            top: a.top,
            bottom: a.bottom,
            animationDelay: a.delay,
            animationDuration: a.duration,
          }}
        >
          {a.label}
        </div>
      ))}
    </div>
  );
}
