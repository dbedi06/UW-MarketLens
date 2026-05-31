// Subscores as animated progress bars, each with a hover explanation.

import { motion } from "framer-motion";
import type { Subscores } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";
import InfoTip from "../ui/InfoTip";

type ScoreKey = "liquidity_health" | "anomaly" | "resolution_quality";

const EXPLAIN: Record<ScoreKey, string> = {
  liquidity_health:
    "How deep and broadly-traded the market is. Thin markets are easy for one actor to move.",
  anomaly:
    "How normal the trading pattern looks. Lower = more statistically unusual activity.",
  resolution_quality:
    "How well the market's resolution is corroborated by independent reporting.",
};
const LABEL: Record<ScoreKey, string> = {
  liquidity_health: "Liquidity health",
  anomaly: "Trading-pattern integrity",
  resolution_quality: "Resolution quality",
};
const KEYS: ScoreKey[] = ["liquidity_health", "anomaly", "resolution_quality"];

function barColor(v: number) {
  return v >= 70 ? "bg-good" : v >= 40 ? "bg-warn" : "bg-bad";
}

export default function SubscoreBars({ subscores }: { subscores: Subscores }) {
  const resApplies = subscores.resolution_applicable !== false;
  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading eyebrow="Composition" title="Subscore breakdown" />
      <div className="divide-y-2 divide-ink/10 border-t-2 border-ink">
        {KEYS.map((k) => {
          const value = subscores[k];
          const isResolutionNA = k === "resolution_quality" && !resApplies;
          const explain = isResolutionNA
            ? "Market hasn't resolved yet — no independent reporting can confirm or refute the outcome. Composite score excludes this leg and reweights the other two."
            : EXPLAIN[k];
          return (
            <div key={k} className="py-5">
              <div className="mb-2 flex items-baseline justify-between">
                <span className="flex items-center gap-2 font-sans text-sm
                  font-bold text-ink">
                  {LABEL[k]}
                  <InfoTip text={explain} />
                </span>
                <span className="font-mono text-lg font-bold tabular-nums text-ink">
                  {isResolutionNA ? (
                    <span className="text-ink/55">N / A</span>
                  ) : (
                    <>
                      {value}
                      <span className="text-ink/30"> / 100</span>
                    </>
                  )}
                </span>
              </div>
              <div className="h-3 overflow-hidden bg-ink/10">
                {!isResolutionNA && (
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${value}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                    className={`h-full ${barColor(value)}`}
                  />
                )}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-ink/45">
                {explain}
              </p>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}
