// PILLAR 1 — the "why". Plain-language reasons a student can quote to defend
// (or reject) a citation. This is the product's core differentiator.

import type { ReasonItem } from "../types";

const ICON: Record<string, string> = { good: "✓", warn: "!", bad: "✕" };
const FACTOR_LABEL: Record<string, string> = {
  liquidity: "Liquidity health",
  anomaly: "Trading-pattern integrity",
  resolution: "Resolution quality",
};

export default function WhyPanel({ reasons }: { reasons: ReasonItem[] }) {
  return (
    <div className="card">
      <h2>Why this verdict</h2>
      <p className="question">
        Each factor below feeds the composite score. Quote these in your paper to
        justify (or caveat) citing this market.
      </p>
      <ul className="reasons">
        {reasons.map((r) => (
          <li key={r.factor} className={`reason sev-${r.severity}`}>
            <span className="reason-icon">{ICON[r.severity]}</span>
            <div>
              <div className="reason-head">
                <span className="reason-factor">{FACTOR_LABEL[r.factor]}</span>
                <span className="reason-headline">{r.headline}</span>
              </div>
              <p className="reason-detail">{r.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
