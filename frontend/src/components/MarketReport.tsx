// The full reliability report. Shared by MarketDetailPage (fetched by URL)
// and SnapshotPage (fetched by id) so a permalink renders identically.

import type { MarketScore } from "../types";
import VerdictHeader from "./VerdictHeader";
import SnapshotBar from "./SnapshotBar";
import WhyPanel from "./WhyPanel";
import AnomalyChart from "./AnomalyChart";
import SubscoreBars from "./SubscoreBars";
import CitationBox from "./CitationBox";

function MetaStats({ data }: { data: MarketScore }) {
  const m = data.meta;
  const items: [string, string][] = [
    ["Volume", `$${m.volume_usd.toLocaleString()}`],
    ["Liquidity", `$${m.liquidity_usd.toLocaleString()}`],
    ["Unique traders", m.unique_traders.toLocaleString()],
    ["Ends", m.end_date],
    ["Status", m.resolved ? "Resolved" : "Open"],
  ];
  return (
    <div className="card">
      <h2>Market facts</h2>
      <div className="meta-grid">
        {items.map(([k, v]) => (
          <div className="meta-item" key={k}>
            <span className="meta-k">{k}</span>
            <span className="meta-v">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MarketReport({ data }: { data: MarketScore }) {
  return (
    <div>
      <VerdictHeader data={data} />
      <SnapshotBar asOf={data.as_of} permalink={data.permalink} />
      <WhyPanel reasons={data.reasons} />
      <AnomalyChart series={data.anomaly_series} />
      <SubscoreBars subscores={data.subscores} />
      <MetaStats data={data} />
      <CitationBox citation={data.citation} />
      <p className="placeholder-note">
        Deterministic mock data (backend <code>app/mock.py</code>). Same URL +
        date always yields this exact report — replaced by the real S1–S7
        pipeline later with no frontend change.
      </p>
    </div>
  );
}
