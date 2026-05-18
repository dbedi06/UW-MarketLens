// The decision-support summary. Lives in the sticky left rail so the verdict,
// score, snapshot link and a copy-citation action stay in view while the
// evidence scrolls. Folds in what VerdictHeader used to show.

import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";
import { toMarkdown } from "../lib/report";
import ScoreGauge from "../ui/ScoreGauge";
import Badge from "../ui/Badge";
import SnapshotBar from "./SnapshotBar";

export default function ReportSummary({ data }: { data: MarketScore }) {
  async function copyCitation() {
    await navigator.clipboard.writeText(data.citation.apa);
    toast("APA citation copied");
  }
  async function copyMarkdown() {
    await navigator.clipboard.writeText(toMarkdown(data));
    toast("Markdown report copied");
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
          <h1 className="font-sans text-xl font-extrabold tracking-tight text-ink">
            {data.headline}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-ink/55">
            {data.market_question}
          </p>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-2">
          <button onClick={copyCitation} className="btn-primary">
            Copy citation
          </button>
          <button onClick={copyMarkdown} className="btn-ghost">
            Copy Markdown
          </button>
        </div>
        <SnapshotBar asOf={data.as_of} permalink={data.permalink} compact />

        <a
          href="#how-computed"
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border
            border-line px-2 py-0.5 font-mono text-[11px] font-medium
            uppercase tracking-wide text-ink/55 hover:text-ink"
        >
          Placeholder model · how computed
        </a>
      </div>
    </motion.aside>
  );
}
