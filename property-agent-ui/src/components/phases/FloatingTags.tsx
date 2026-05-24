// Floating decorative chips for the profiling page.
// Hard constraint: chips MUST NOT enter the centered safe zone where the
// headline / sub-copy / progress bars are rendered.
//
// Strategy: anchor each chip to a fixed corner offset (well outside the
// safe zone) and oscillate by only a few pixels via CSS. Because the
// anchor is far from the center AND the animation amplitude is bounded
// (< 8px), it is mathematically impossible for a chip to enter the safe
// zone at any frame. No JS collision loop needed.
//
// On viewports narrower than the safe-zone width + chip margin, chips
// are hidden — there is no honest position that avoids overlap.

import { useEffect, useState } from "react";

interface Anchor {
  label: string;
  // Position relative to the host container. Exactly one of left/right
  // and one of top/bottom is set, in percent.
  left?: string;
  right?: string;
  top?: string;
  bottom?: string;
  delay: string;
}

const ANCHORS: Anchor[] = [
  { label: "BUDGET",       left: "4%",  top: "18%", delay: "0s"   },
  { label: "IDENTITY",     right: "5%", top: "22%", delay: "0.6s" },
  { label: "TARGET",       right: "3%", top: "55%", delay: "1.2s" },
  { label: "LIFESTYLE",    left: "6%",  bottom: "22%", delay: "0.3s" },
  { label: "DEALBREAKERS", right: "8%", bottom: "26%", delay: "0.9s" },
];

// Below this viewport width the safe zone + chip margins do not fit.
const MIN_WIDTH_PX = 880;

export function FloatingTags() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const check = () => setVisible(window.innerWidth >= MIN_WIDTH_PX);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!visible) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {ANCHORS.map((a) => (
        <div
          key={a.label}
          className="float absolute rounded-full border border-border/60 bg-surface/70 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground backdrop-blur-sm"
          style={{
            left: a.left,
            right: a.right,
            top: a.top,
            bottom: a.bottom,
            animationDelay: a.delay,
          }}
        >
          {a.label}
        </div>
      ))}
    </div>
  );
}
