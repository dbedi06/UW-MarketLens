// The three numeric subscores that compose the reliability score, each with a
// hover explanation so the number isn't a black box.

import type { Subscores } from "../types";

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

export default function SubscoreBars({ subscores }: { subscores: Subscores }) {
  const keys = Object.keys(subscores) as (keyof Subscores)[];
  return (
    <div className="card">
      <h2>Subscore breakdown</h2>
      <div className="subscores">
        {keys.map((k) => (
          <div className="sub" key={k} title={EXPLAIN[k]}>
            <div className="label">
              <span>
                {LABEL[k]} <span className="info-dot" aria-label={EXPLAIN[k]}>ⓘ</span>
              </span>
              <span>{subscores[k]}/100</span>
            </div>
            <div className="bar">
              <div style={{ width: `${subscores[k]}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
