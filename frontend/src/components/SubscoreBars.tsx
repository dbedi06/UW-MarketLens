// Subscores as animated progress bars, each with a hover explanation.

import { motion } from "framer-motion";
import type { Subscores } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";

const EXPLAIN: Record<keyof Subscores, string> = {
  liquidity_health:
    "How deep and broadly-traded the market is. Thin markets are easy for one actor to move.",
  anomaly:
    "How normal the trading pattern looks. Lower = more statistically unusual activity.",
  resolution_quality:
    "How well the market's resolution is corroborated by independent reporting.",
};
const LABEL: Record<keyof Subscores, string> = {
  liquidity_health: "Liquidity health",
  anomaly: "Trading-pattern integrity",
  resolution_quality: "Resolution quality",
};

function barColor(v: number) {
  return v >= 70 ? "bg-good" : v >= 40 ? "bg-warn" : "bg-bad";
}

export default function SubscoreBars({ subscores }: { subscores: Subscores }) {
  const keys = Object.keys(subscores) as (keyof Subscores)[];
  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading eyebrow="Composition" title="Subscore breakdown" />
      <div className="space-y-5">
        {keys.map((k) => (
          <div key={k} title={EXPLAIN[k]}>
            <div className="mb-1.5 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">
                {LABEL[k]}{" "}
                <span className="cursor-help text-slate-300" aria-label={EXPLAIN[k]}>
                  ⓘ
                </span>
              </span>
              <span className="font-mono font-semibold tabular-nums text-slate-500">
                {subscores[k]}
                <span className="text-slate-300">/100</span>
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${subscores[k]}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                className={`h-full rounded-full ${barColor(subscores[k])}`}
              />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
