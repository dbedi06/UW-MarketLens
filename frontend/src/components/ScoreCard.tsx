// Renders the reliability score, band color, and the three subscore bars.

import type { MarketScore } from "../types";

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="sub">
      <div className="label">
        <span>{label}</span>
        <span>{value}/100</span>
      </div>
      <div className="bar">
        <div style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export default function ScoreCard({ data }: { data: MarketScore }) {
  return (
    <div className="card">
      <h2>Reliability Score</h2>
      <p className="question">{data.market_question}</p>

      <div className="score-row">
        <div className={`big-score band-${data.band}`}>{data.reliability_score}</div>
        <div className="subscores">
          <Bar label="Liquidity health" value={data.subscores.liquidity_health} />
          <Bar label="Trading-pattern integrity" value={data.subscores.anomaly} />
          <Bar label="Resolution quality" value={data.subscores.resolution_quality} />
        </div>
      </div>

      <div className="tags">
        {data.tags.departments.map((d) => (
          <span className="chip" key={d}>{d}</span>
        ))}
        <span className="chip">Resolution: {data.resolution.verdict}</span>
        <span className="chip">{data.anomaly.flagged_windows} flagged windows</span>
      </div>
    </div>
  );
}
