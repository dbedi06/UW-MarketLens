// Arc score gauge, consistent with the OG share card: a ring that sweeps to
// the score with a count-up number, band word below. Reduced-motion safe.

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

const BAND: Record<string, { word: string; color: string }> = {
  HIGH: { word: "Reliable", color: "#1f7a4d" },
  MEDIUM: { word: "Use with caution", color: "#9a6a14" },
  LOW: { word: "Not recommended", color: "#b3261e" },
};

export default function ScoreGauge({
  score,
  band,
  size = 208,
}: {
  score: number;
  band: string;
  size?: number;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? score : 0);
  const ring = useRef<SVGCircleElement>(null);
  const meta = BAND[band] ?? { word: band, color: "#4B2E83" };

  const stroke = 16;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;

  useEffect(() => {
    function paint(v: number) {
      setDisplay(Math.round(v));
      if (ring.current)
        ring.current.style.strokeDashoffset = `${circ * (1 - v / 100)}`;
    }
    if (reduce) {
      paint(score);
      return;
    }
    const controls = animate(0, score, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: paint,
    });
    return () => controls.stop();
  }, [score, circ, reduce]);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="#E4DFD5"
            strokeWidth={stroke}
          />
          <circle
            ref={ring}
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={meta.color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={circ}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center
          justify-center">
          <span
            className="numeral text-6xl leading-none"
            style={{ color: meta.color }}
          >
            {display}
          </span>
          <span className="mt-1 font-mono text-xs text-ink/40">/ 100</span>
        </div>
      </div>
      <div
        className="mt-4 font-sans text-sm font-extrabold uppercase
          tracking-wide"
        style={{ color: meta.color }}
      >
        {meta.word}
      </div>
    </div>
  );
}
