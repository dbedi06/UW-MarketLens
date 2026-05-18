// PILLAR 1 — the "why". Severity-accented reason cards in plain language.

import { motion } from "framer-motion";
import type { ReasonItem } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";

const MARK: Record<string, string> = { good: "[ok]", warn: "[?]", bad: "[x]" };
const SEV_TEXT: Record<string, string> = {
  good: "text-good",
  warn: "text-warn",
  bad: "text-bad",
};
const RAIL: Record<string, string> = {
  good: "border-l-good",
  warn: "border-l-warn",
  bad: "border-l-bad",
};
const FACTOR_LABEL: Record<string, string> = {
  liquidity: "Liquidity health",
  anomaly: "Trading-pattern integrity",
  resolution: "Resolution quality",
};

export default function WhyPanel({ reasons }: { reasons: ReasonItem[] }) {
  return (
    <motion.div variants={fadeUp} className="card accent-rail p-6">
      <SectionHeading
        eyebrow="The why, not the number"
        title="Why this verdict"
        sub="Each factor feeds the composite score. Quote these to justify (or caveat) citing this market."
      />
      <ul className="mt-2 divide-y-2 divide-ink/10 border-t-2 border-ink">
        {reasons.map((r) => (
          <li
            key={r.factor}
            className={`flex gap-4 border-l-4 py-5 pl-5 ${RAIL[r.severity]}`}
          >
            <span
              className={`mt-1 font-mono text-xs font-bold ${SEV_TEXT[r.severity]}`}
            >
              {MARK[r.severity]}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <span className="caption">{FACTOR_LABEL[r.factor]}</span>
                <span className="font-sans text-base font-extrabold
                  tracking-tight text-ink">
                  {r.headline}
                </span>
              </div>
              <p className="mt-1 text-sm leading-relaxed text-ink/70">
                {r.detail}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}
