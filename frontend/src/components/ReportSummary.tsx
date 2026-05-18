// The decision-support summary. Lives in the sticky left rail so the verdict,
// score, snapshot link and a copy-citation action stay in view while the
// evidence scrolls. Folds in what VerdictHeader used to show.

import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";
import ScoreGauge from "../ui/ScoreGauge";
import Badge, { bandTone } from "../ui/Badge";
import SnapshotBar from "./SnapshotBar";

export default function ReportSummary({ data }: { data: MarketScore }) {
  async function copyCitation() {
    await navigator.clipboard.writeText(data.citation.apa);
    toast("APA citation copied");
  }

  return (
    <motion.aside
      variants={fadeUp}
      className="card accent-rail flex flex-col items-center gap-4 p-6 text-center"
    >
      <ScoreGauge score={data.reliability_score} band={data.band} />
      <Badge tone={bandTone(data.band)}>{data.band} RELIABILITY</Badge>
      <h1 className="font-display text-xl font-bold leading-snug text-ink">
        {data.headline}
      </h1>
      <p className="text-sm leading-relaxed text-slate-500">
        {data.market_question}
      </p>

      <div className="w-full border-t border-slate-100 pt-4">
        <SnapshotBar asOf={data.as_of} permalink={data.permalink} compact />
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={copyCitation}
          className="btn-primary mt-2 w-full"
        >
          Copy citation
        </motion.button>
      </div>
    </motion.aside>
  );
}
