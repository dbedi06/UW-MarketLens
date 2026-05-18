// The full reliability report. Shared by MarketDetailPage (by URL) and
// SnapshotPage (by id) so a permalink renders identically.
//
// Layout: sticky decision-support rail (ReportSummary) + scrolling evidence
// on desktop; single stacked column below lg.

import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { stagger, fadeUp } from "../lib/motion";
import Stat from "../ui/Stat";
import Skeleton from "../ui/Skeleton";
import SectionHeading from "../ui/SectionHeading";
import ReportSummary from "./ReportSummary";
import WhyPanel from "./WhyPanel";
import SubscoreBars from "./SubscoreBars";
import ComputationNote from "./ComputationNote";
import CitationBox from "./CitationBox";
import SocialPreview from "./SocialPreview";

// recharts is heavy — split it into its own chunk.
const AnomalyChart = lazy(() => import("./AnomalyChart"));

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
    <motion.div variants={fadeUp} className="surface-tint rounded-2xl p-6">
      <SectionHeading eyebrow="Context" title="Market facts" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {items.map(([k, v]) => (
          <Stat key={k} label={k} value={v} />
        ))}
      </div>
    </motion.div>
  );
}

export default function MarketReport({
  data,
  hideSocialPreview = false,
}: {
  data: MarketScore;
  hideSocialPreview?: boolean;
}) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="show"
      className="grid items-start gap-x-16 gap-y-10
        lg:grid-cols-[380px_minmax(0,1fr)]"
    >
      <div className="lg:sticky lg:top-24">
        <ReportSummary data={data} />
      </div>

      <div className="space-y-10">
        <WhyPanel reasons={data.reasons} />
        <Suspense fallback={<Skeleton className="h-80" />}>
          <AnomalyChart series={data.anomaly_series} />
        </Suspense>
        <SubscoreBars subscores={data.subscores} />
        <ComputationNote />
        <MarketFacts data={data} />
        <CitationBox citation={data.citation} />
        {!hideSocialPreview && (
          <SocialPreview snapshotId={data.snapshot_id} />
        )}
        <p className="pt-1 text-center text-xs italic text-ink/40">
          Deterministic mock data (backend <code>app/mock.py</code>). The same
          URL and date always yield this exact report. The real S1-S7 pipeline
          replaces it later with no frontend change.
        </p>
      </div>
    </motion.div>
  );
}
