// Animated radial gauge with a count-up number. Replaces the flat score box.
// The arc sweeps and the number ticks up on mount (collapses instantly under
// prefers-reduced-motion via the global CSS rule + Framer's reduced-motion).

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

const BAND_COLOR: Record<string, string> = {
  HIGH: "#0f9d58",
  MEDIUM: "#d08700",
  LOW: "#dc2626",
};

export default function ScoreGauge({
  score,
  band,
  size = 168,
}: {
  score: number;
  band: string;
  size?: number;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? score : 0);
  const stroke = 12;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const ref = useRef<SVGCircleElement>(null);
  const color = BAND_COLOR[band] ?? "#4B2E83";

  useEffect(() => {
    if (reduce) {
      setDisplay(score);
      if (ref.current)
        ref.current.style.strokeDashoffset = `${circ * (1 - score / 100)}`;
      return;
    }
    const controls = animate(0, score, {
      duration: 1.1,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => {
        setDisplay(Math.round(v));
        if (ref.current)
          ref.current.style.strokeDashoffset = `${circ * (1 - v / 100)}`;
      },
    });
    return () => controls.stop();
  }, [score, circ, reduce]);

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#eef0f4"
          strokeWidth={stroke}
        />
        <circle
          ref={ref}
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ}
        />
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-5xl font-extrabold text-ink tabular-nums">
          {display}
        </div>
        <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
          / 100
        </div>
      </div>
    </div>
  );
}
