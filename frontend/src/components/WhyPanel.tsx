// PILLAR 1 — the "why". Severity-accented reason cards in plain language.

import { motion } from "framer-motion";
import type { ReasonItem } from "../types";
import { fadeUp, stagger } from "../lib/motion";

const ICON: Record<string, string> = { good: "✓", warn: "!", bad: "✕" };
const ACCENT: Record<string, string> = {
  good: "border-l-good bg-good/[0.04]",
  warn: "border-l-warn bg-warn/[0.04]",
  bad: "border-l-bad bg-bad/[0.04]",
};
const DOT: Record<string, string> = {
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
};
const FACTOR_LABEL: Record<string, string> = {
  liquidity: "Liquidity health",
  anomaly: "Trading-pattern integrity",
  resolution: "Resolution quality",
};

export default function WhyPanel({ reasons }: { reasons: ReasonItem[] }) {
  return (
    <motion.div variants={fadeUp} className="card p-6">
      <h2 className="text-xl font-semibold">Why this verdict</h2>
      <p className="mt-1 text-sm text-slate-500">
        Each factor feeds the composite score. Quote these to justify (or
        caveat) citing this market.
      </p>
      <motion.ul
        variants={stagger}
        initial="hidden"
        animate="show"
        className="mt-5 space-y-3"
      >
        {reasons.map((r) => (
          <motion.li
            key={r.factor}
            variants={fadeUp}
            className={`flex gap-4 rounded-xl border border-slate-200/70
              border-l-4 p-4 ${ACCENT[r.severity]}`}
          >
            <span
              className={`mt-0.5 grid h-7 w-7 flex-none place-items-center
                rounded-full text-sm font-bold text-white ${DOT[r.severity]}`}
            >
              {ICON[r.severity]}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-2.5">
                <span className="text-[11px] font-semibold uppercase
                  tracking-wider text-slate-400">
                  {FACTOR_LABEL[r.factor]}
                </span>
                <span className="font-semibold text-ink">{r.headline}</span>
              </div>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">
                {r.detail}
              </p>
            </div>
          </motion.li>
        ))}
      </motion.ul>
    </motion.div>
  );
}
