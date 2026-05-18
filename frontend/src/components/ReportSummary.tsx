// The decision-support summary. Lives in the sticky left rail so the verdict,
// score, snapshot link and a copy-citation action stay in view while the
// evidence scrolls. Folds in what VerdictHeader used to show.

import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";
import ScoreGauge from "../ui/ScoreGauge";
import Badge from "../ui/Badge";
import SnapshotBar from "./SnapshotBar";

export default function ReportSummary({ data }: { data: MarketScore }) {
  async function copyCitation() {
    await navigator.clipboard.writeText(data.citation.apa);
    toast("APA citation copied");
  }

  return (
    <motion.aside variants={fadeUp} className="card">
      <div className="block-purple flex items-center justify-between px-5 py-2">
        <span className="font-mono text-[11px] font-medium uppercase
          tracking-[0.14em] text-gold">
          Verdict
        </span>
        <Badge tone="gold">{data.band}</Badge>
      </div>

      <div className="p-6">
        <ScoreGauge score={data.reliability_score} band={data.band} />

        <div className="mt-6 border-t-2 border-ink pt-4">
          <h1 className="display text-xl text-ink">{data.headline}</h1>
          <p className="mt-2 text-sm leading-relaxed text-ink/55">
            {data.market_question}
          </p>
        </div>

        <button onClick={copyCitation} className="btn-primary mt-6 w-full">
          Copy citation
        </button>
        <SnapshotBar asOf={data.as_of} permalink={data.permalink} compact />
      </div>
    </motion.aside>
  );
}
