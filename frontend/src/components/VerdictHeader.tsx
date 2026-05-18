// The verdict at a glance: animated gauge + plain-language headline.

import { motion } from "framer-motion";
import type { MarketScore } from "../types";
import { fadeUp } from "../lib/motion";
import ScoreGauge from "../ui/ScoreGauge";
import Badge, { bandTone } from "../ui/Badge";

export default function VerdictHeader({ data }: { data: MarketScore }) {
  return (
    <motion.div
      variants={fadeUp}
      className="card overflow-hidden p-7
        bg-gradient-to-br from-white to-slate-50"
    >
      <div className="flex flex-col items-center gap-7 sm:flex-row sm:items-center">
        <ScoreGauge score={data.reliability_score} band={data.band} />
        <div className="min-w-0 flex-1 text-center sm:text-left">
          <Badge tone={bandTone(data.band)}>{data.band} RELIABILITY</Badge>
          <h2 className="mt-3 text-2xl font-bold leading-snug text-ink">
            {data.headline}
          </h2>
          <p className="mt-2 text-[15px] text-slate-600">
            {data.market_question}
          </p>
          <p className="mt-3 text-xs text-slate-400">
            Reliability snapshot as of{" "}
            <span className="font-semibold text-slate-600">{data.as_of}</span>
          </p>
        </div>
      </div>
    </motion.div>
  );
}
