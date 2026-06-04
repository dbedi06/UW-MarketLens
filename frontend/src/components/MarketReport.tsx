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
import ResolutionEvidence from "./ResolutionEvidence";
import FeatureContributions from "./FeatureContributions";
import SubscoreBars from "./SubscoreBars";
import ComputationNote from "./ComputationNote";
import CitationBox from "./CitationBox";
import SocialPreview from "./SocialPreview";

// recharts is heavy — split it into its own chunk.
const AnomalyChart = lazy(() => import("./AnomalyChart"));

function SourceBadge({ source }: { source: "live" | "mock" }) {
  const isLive = source === "live";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-[10px] font-bold uppercase tracking-wider ${
          isLive
            ? "border-warn/40 bg-warn/10 text-warn"
            : "border-line bg-panel text-ink/55"
        }`}
      title={
        isLive
          ? "Score produced by the live S1→S2→S3 chain on real Polymarket data."
          : "Score produced by the deterministic mock data path."
      }
    >
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full ${
          isLive ? "bg-warn" : "bg-ink/30"
        }`}
      />
      {isLive ? "Live" : "Mock"}
    </span>
  );
}

function TrainingBadge({ trainedOn }: { trainedOn?: string }) {
  const label =
    trainedOn === "real-corpus"
      ? "Detector trained on real corpus"
      : trainedOn === "synthetic"
        ? "Detector trained on synthetic streams"
        : "Detector training provenance unknown";
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border bg-panel px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-ink/75">
      {label}
    </span>
  );
}

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
        {data.source && (
          <div className="-mb-6 flex flex-wrap items-center justify-end gap-2">
            <SourceBadge source={data.source} />
            <TrainingBadge trainedOn={data.anomaly.trained_on} />
          </div>
        )}
        <WhyPanel reasons={data.reasons} />
        <ResolutionEvidence resolution={data.resolution} />
        <Suspense fallback={<Skeleton className="h-80" />}>
          <AnomalyChart series={data.anomaly_series} />
        </Suspense>
        <FeatureContributions
          contributions={data.anomaly.top_contributions}
          windowIndex={data.anomaly.top_window_index}
        />
        <SubscoreBars subscores={data.subscores} />
        <ComputationNote />
        <MarketFacts data={data} />
        <CitationBox citation={data.citation} />
        {!hideSocialPreview && (
          <SocialPreview
            snapshotId={data.snapshot_id}
            score={data.reliability_score}
          />
        )}
        <p className="pt-1 text-center text-xs italic text-ink/40">
          {data.source === "live" ? (
            <>
              Live data via the S1→S2→S3 chain. Detector training provenance:{" "}
              {data.anomaly.trained_on === "real-corpus"
                ? "real corpus"
                : data.anomaly.trained_on === "synthetic"
                  ? "synthetic streams"
                  : "unknown"}
              . See <code>MODEL_STATUS.md</code>.
            </>
          ) : (
            <>
              Deterministic mock data (backend <code>app/mock.py</code>). The
              same URL and date always yield this exact report. The real S1-S7
              pipeline replaces it later with no frontend change.
            </>
          )}
        </p>
      </div>
    </motion.div>
  );
}
