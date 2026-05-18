// The full reliability report. Shared by MarketDetailPage (fetched by URL)
// and SnapshotPage (fetched by id) so a permalink renders identically.

import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { stagger, fadeUp } from "../lib/motion";
import Stat from "../ui/Stat";
import VerdictHeader from "./VerdictHeader";
import SnapshotBar from "./SnapshotBar";
import WhyPanel from "./WhyPanel";
import AnomalyChart from "./AnomalyChart";
import SubscoreBars from "./SubscoreBars";
import CitationBox from "./CitationBox";

function MarketFacts({ data }: { data: MarketScore }) {
  const m = data.meta;
  const items: [string, string][] = [
    ["Volume", `$${m.volume_usd.toLocaleString()}`],
    ["Liquidity", `$${m.liquidity_usd.toLocaleString()}`],
    ["Unique traders", m.unique_traders.toLocaleString()],
    ["Ends", m.end_date],
    ["Status", m.resolved ? "Resolved" : "Open"],
  ];
  return (
    <motion.div variants={fadeUp} className="card p-6">
      <h2 className="text-xl font-semibold">Market facts</h2>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {items.map(([k, v]) => (
          <Stat key={k} label={k} value={v} />
        ))}
      </div>
    </motion.div>
  );
}

export default function MarketReport({ data }: { data: MarketScore }) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="show"
      className="space-y-5"
    >
      <VerdictHeader data={data} />
      <SnapshotBar asOf={data.as_of} permalink={data.permalink} />
      <WhyPanel reasons={data.reasons} />
      <AnomalyChart series={data.anomaly_series} />
      <SubscoreBars subscores={data.subscores} />
      <MarketFacts data={data} />
      <CitationBox citation={data.citation} />
      <p className="pt-2 text-center text-xs italic text-slate-400">
        Deterministic mock data (backend <code>app/mock.py</code>). Same URL +
        date always yields this exact report — replaced by the real S1–S7
        pipeline later with no frontend change.
      </p>
    </motion.div>
  );
}
