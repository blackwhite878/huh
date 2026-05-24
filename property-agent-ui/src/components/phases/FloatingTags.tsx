// Floating chips for the profiling page (Phase 1.5).
//
// Surfaces the live Phase 1 facts the agent is reasoning over —
// budget, house type, location — alongside the original decorative
// labels. Values come from the store; missing optional fields render
// as "—" rather than blank chips.
//
// Collision contract (NON-NEGOTIABLE):
//   1. Chips MUST NOT enter the centered safe zone (headline / sub-copy
//      / progress bars).
//   2. Chips MUST NOT visually collide with each other, even with the
//      longest label and full drift amplitude.
//
// Strategy:
//   - All chips anchored to the left OR right edge (never the center).
//   - Per side, chips are distributed across non-overlapping vertical
//     bands. Each band reserves >= 22% of the host height; chip is ~28px
//     tall + drift amplitude ~8px, so even at viewport=700px the gap
//     between consecutive band centers (~150px) >> chip footprint.
//   - Each chip is clamped to max-width 38% of the host so its right/left
//     edge cannot reach the center safe zone.
//   - Motion uses 4 irregular drift variants with prime-ish durations and
//     unique delays → non-periodic on human timescales.
//   - On viewports narrower than MIN_WIDTH_PX the safe zone + chip
//     margins do not fit honestly, so chips are hidden.

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";

type DriftVariant = "a" | "b" | "c" | "d";

interface Anchor {
  key: string;
  label: string;
  // Exactly one of left/right is set (chips always edge-anchored).
  side: "left" | "right";
  edgeOffset: string; // e.g. "4%"
  top: string;        // vertical center expressed as top %
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

  // Non-overlapping vertical bands. Left has 3 slots, right has 4 slots.
  // Min gap between consecutive `top` on the same side = 22%.
  const anchors: Anchor[] = [
    // ── LEFT column (3 slots: 14% / 44% / 74%) ──────────────────────
    {
      key: "budget",
      label: `BUDGET · ${fmtBudget(phase1?.budget)}`,
      side: "left",
      edgeOffset: "4%",
      top: "14%",
      delay: "0s",
      duration: "7.3s",
      variant: "a",
      emphasis: true,
    },
    {
      key: "lifestyle",
      label: "LIFESTYLE",
      side: "left",
      edgeOffset: "6%",
      top: "44%",
      delay: "1.1s",
      duration: "8.3s",
      variant: "b",
    },
    {
      key: "location",
      label: `LOCATION · ${fmtText(phase1?.location)}`,
      side: "left",
      edgeOffset: "5%",
      top: "74%",
      delay: "1.3s",
      duration: "6.7s",
      variant: "c",
      emphasis: true,
    },
    // ── RIGHT column (4 slots: 12% / 36% / 60% / 84%) ───────────────
    {
      key: "house_type",
      label: `HOUSE TYPE · ${fmtText(phase1?.house_type)}`,
      side: "right",
      edgeOffset: "4%",
      top: "12%",
      delay: "0.7s",
      duration: "8.9s",
      variant: "b",
      emphasis: true,
    },
    {
      key: "identity",
      label: "IDENTITY",
      side: "right",
      edgeOffset: "6%",
      top: "36%",
      delay: "0.4s",
      duration: "9.7s",
      variant: "d",
    },
    {
      key: "target",
      label: "TARGET",
      side: "right",
      edgeOffset: "7%",
      top: "60%",
      delay: "1.9s",
      duration: "7.9s",
      variant: "a",
    },
    {
      key: "layout",
      label: "LAYOUT",
      side: "right",
      edgeOffset: "5%",
      top: "84%",
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
        // Outer wrapper owns the absolute anchor + vertical centering.
        // Inner element owns the drift animation, so the two transforms
        // don't compete (keyframes would otherwise overwrite translateY).
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
