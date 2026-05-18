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
      className="card accent-rail flex flex-col gap-5 p-7"
    >
      <div className="flex flex-col items-center gap-3">
        <ScoreGauge score={data.reliability_score} band={data.band} />
        <Badge tone={bandTone(data.band)}>{data.band} reliability</Badge>
      </div>
      <div className="border-t border-line pt-4">
        <h1 className="font-display text-xl font-semibold leading-snug text-ink">
          {data.headline}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink/55">
          {data.market_question}
        </p>
      </div>

      <div>
        <button onClick={copyCitation} className="btn-primary w-full">
          Copy citation
        </button>
        <SnapshotBar asOf={data.as_of} permalink={data.permalink} compact />
      </div>
    </motion.aside>
  );
}
