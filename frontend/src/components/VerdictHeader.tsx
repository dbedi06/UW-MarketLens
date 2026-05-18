// The first thing a student sees: the plain-language verdict, not just a number.

import type { MarketScore } from "../types";

export default function VerdictHeader({ data }: { data: MarketScore }) {
  return (
    <div className={`verdict band-bg-${data.band}`}>
      <div className="verdict-score">
        <span className="num">{data.reliability_score}</span>
        <span className="den">/100</span>
      </div>
      <div className="verdict-body">
        <div className="verdict-band">{data.band} RELIABILITY</div>
        <h2>{data.headline}</h2>
        <p className="verdict-q">{data.market_question}</p>
        <p className="verdict-asof">
          Reliability snapshot as of <strong>{data.as_of}</strong>
        </p>
      </div>
    </div>
  );
}
