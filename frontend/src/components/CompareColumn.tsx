// One market's compact card in the comparison view.

import type { MarketScore } from "../types";
import Badge, { bandTone } from "../ui/Badge";
import { toast } from "../ui/Toast";

const BAND_COLOR: Record<string, string> = {
  HIGH: "#1f7a4d",
  MEDIUM: "#9a6a14",
  LOW: "#b3261e",
};

export default function CompareColumn({ data }: { data: MarketScore }) {
  function copyPermalink() {
    navigator.clipboard.writeText(`${window.location.origin}${data.permalink}`);
    toast("Permalink copied");
  }

  return (
    <div className="card p-6">
      <div className="flex items-baseline justify-between gap-3">
        <span
          className="numeral text-5xl"
          style={{ color: BAND_COLOR[data.band] ?? "#4B2E83" }}
        >
          {data.reliability_score}
        </span>
        <Badge tone={bandTone(data.band)}>{data.band}</Badge>
      </div>

      <h2 className="mt-3 font-sans text-base font-extrabold leading-snug
        tracking-tight text-ink">
        {data.market_question}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-ink/60">
        {data.headline}
      </p>

      <div className="mt-4 caption">
        {data.tags.departments.join(" · ")} · resolution {data.resolution.verdict}
      </div>

      <button
        onClick={copyPermalink}
        className="btn-ghost mt-5 w-full text-xs"
      >
        Copy permalink
      </button>
    </div>
  );
}
