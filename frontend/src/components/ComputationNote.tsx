// Auditability disclosure. The formula here mirrors backend/app/mock.py
// make_market_score exactly; update both together when the real S7 lands.

export default function ComputationNote() {
  return (
    <details
      id="how-computed"
      className="card group p-6 [&_summary::-webkit-details-marker]:hidden"
    >
      <summary className="flex cursor-pointer items-center justify-between
        gap-3 list-none">
        <span className="section-title text-lg">How is this score computed?</span>
        <span className="caption transition-transform
          group-open:rotate-90">view</span>
      </summary>
      <div className="mt-4 space-y-3 text-sm leading-relaxed text-ink/70">
        <p>
          The reliability score is a deterministic composite of three
          subscores: liquidity health, trading-pattern integrity, and
          resolution quality.
        </p>
        <p className="font-mono text-[13px] text-ink">
          score = round( mean(liquidity, anomaly, resolution) )
        </p>
        <p>
          Bands: <strong>HIGH</strong> for 70 and above,{" "}
          <strong>MEDIUM</strong> for 40 to 69, <strong>LOW</strong> for
          below 40.
        </p>
        <p className="text-ink/50">
          Placeholder weighting: this build uses an equal-weighted mean of
          mock subscores. The real composite (statistical anomaly model,
          LLM-as-judge resolution, liquidity rules) replaces it later with no
          change to this report's shape.
        </p>
      </div>
    </details>
  );
}
