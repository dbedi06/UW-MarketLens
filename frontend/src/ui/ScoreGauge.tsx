// Bold Swiss: the score IS the graphic. A huge expanded numeral that counts
// up, a band word, and a thick progress rule. No timid ring.

import { useEffect, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

const BAND: Record<string, { word: string; color: string }> = {
  HIGH: { word: "Reliable", color: "#1f7a4d" },
  MEDIUM: { word: "Use with caution", color: "#9a6a14" },
  LOW: { word: "Not recommended", color: "#b3261e" },
};

export default function ScoreGauge({
  score,
  band,
}: {
  score: number;
  band: string;
  size?: number;
}) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? score : 0);
  const meta = BAND[band] ?? { word: band, color: "#4B2E83" };

  useEffect(() => {
    if (reduce) {
      setDisplay(score);
      return;
    }
    const controls = animate(0, score, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    return () => controls.stop();
  }, [score, reduce]);

  return (
    <div className="w-full">
      <div className="caption">Reliability</div>
      <div className="mt-1 flex items-end gap-2">
        <span
          className="numeral text-[6.5rem] sm:text-[7.5rem]"
          style={{ color: meta.color }}
        >
          {display}
        </span>
        <span className="mb-3 font-mono text-sm text-ink/40">/ 100</span>
      </div>
      <div className="mt-2 h-2 w-full bg-line">
        <div
          className="h-full transition-[width] duration-1000 ease-out"
          style={{ width: `${display}%`, background: meta.color }}
        />
      </div>
      <div
        className="mt-3 font-sans text-sm font-extrabold uppercase
          tracking-wide"
        style={{ color: meta.color }}
      >
        {meta.word}
      </div>
    </div>
  );
}
