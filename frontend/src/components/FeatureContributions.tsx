// SHAP per-window attributions for the most-anomalous window of this
// market. Closes the "why, not the number" pillar on the anomaly leg
// by showing which features actually pushed the model's score upward.
//
// Hidden when no contributions are available (SHAP failed or no
// windows scored).

import { motion } from "framer-motion";
import type { FeatureContribution } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";

const FEATURE_LABEL: Record<string, string> = {
  volume: "Volume (USD)",
  bid_ask_spread: "Bid–ask spread",
  unique_traders: "Unique traders",
  price_volatility: "Price volatility",
  time_to_resolution: "Time to resolution",
  log_volume: "Log volume",
  vol_per_trader: "Volume per trader",
  spread_x_vol: "Spread × √volume",
  traders_per_logvol: "Traders / log(volume)",
  amihud_proxy: "Amihud illiquidity proxy",
  spread_per_logvol: "Spread / log(volume)",
  vol_z_rel: "Volume z (per market)",
  volatility_z_rel: "Volatility z (per market)",
  vol_per_trader_z_rel: "Vol/trader z (per market)",
  spread_z_rel: "Spread z (per market)",
  net_unique_wallets: "Unique wallets in window",
  net_top_trader_hhi: "Top-trader HHI",
  net_repeat_counterparty: "Repeat-counterparty ratio",
  net_largest_component: "Largest wallet cluster",
};

export default function FeatureContributions({
  contributions,
  windowIndex,
}: {
  contributions?: FeatureContribution[];
  windowIndex?: number;
}) {
  if (!contributions || contributions.length === 0) {
    return null;
  }

  const hasWindow = windowIndex !== undefined && windowIndex >= 0;

  // Max abs value across the bars for proportional scaling.
  const maxAbs = Math.max(
    1e-9,
    ...contributions.map((c) => Math.abs(c.shap)),
  );

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Feature attribution"
        title={
          hasWindow
            ? `Why window ${windowIndex} was flagged`
            : "What drove the most-anomalous window"
        }
        sub={
          (hasWindow
            ? `This is the most-anomalous window (number ${windowIndex} on the chart above). `
            : "") +
          "SHAP values for the window with the highest anomaly score. Positive (right) = pushed toward 'more anomalous'; negative (left) = pulled toward 'normal'."
        }
      />

      <ul className="mt-4 space-y-2">
        {contributions.map((c) => {
          const pct = (Math.abs(c.shap) / maxAbs) * 100;
          const positive = c.shap >= 0;
          return (
            <li
              key={c.feature}
              className="grid grid-cols-[minmax(140px,auto)_1fr_minmax(64px,auto)]
                items-center gap-3 text-[13px]"
            >
              <span className="truncate font-mono text-ink/75" title={c.feature}>
                {FEATURE_LABEL[c.feature] ?? c.feature}
              </span>
              <div className="relative h-2 bg-ink/[0.05]">
                <div className="absolute inset-y-0 left-1/2 w-px bg-ink/20" />
                <div
                  className={`absolute inset-y-0 ${
                    positive
                      ? "left-1/2 bg-bad/70"
                      : "right-1/2 bg-good/70"
                  }`}
                  style={{ width: `${pct / 2}%` }}
                />
              </div>
              <span
                className={`text-right font-mono tabular-nums ${
                  positive ? "text-bad" : "text-good"
                }`}
              >
                {c.shap >= 0 ? "+" : ""}
                {c.shap.toFixed(3)}
              </span>
            </li>
          );
        })}
      </ul>

      <p className="caption mt-4 italic">
        Computed via SHAP TreeExplainer over the fitted Isolation Forest.
        These are local explanations of the detector's score on this
        window — they show what the model focused on, not what's
        objectively wrong with the market.
      </p>
    </motion.div>
  );
}
