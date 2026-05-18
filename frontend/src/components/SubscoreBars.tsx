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
      <div className="divide-y-2 divide-ink/10 border-t-2 border-ink">
        {keys.map((k) => (
          <div key={k} className="py-5" title={EXPLAIN[k]}>
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-sans text-sm font-bold text-ink">
                {LABEL[k]}
              </span>
              <span className="font-mono text-lg font-bold tabular-nums text-ink">
                {subscores[k]}
                <span className="text-ink/30"> / 100</span>
              </span>
            </div>
            <div className="h-3 overflow-hidden bg-ink/10">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${subscores[k]}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                className={`h-full ${barColor(subscores[k])}`}
              />
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink/45">
              {EXPLAIN[k]}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
