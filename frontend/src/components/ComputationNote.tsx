// Auditability disclosure. Formula + weights mirror backend/app/composite.py
// (S7). When the weights change there, update this note in lockstep.

export default function ComputationNote() {
  return (
    <details
      id="how-computed"
      className="card group p-6 [&_summary::-webkit-details-marker]:hidden"
    >
      <summary
        className="flex cursor-pointer items-center justify-between
        gap-3 list-none"
      >
        <span className="section-title text-lg">
          How is this score computed?
        </span>
        <span
          className="caption transition-transform
          group-open:rotate-90"
        >
          view
        </span>
      </summary>
      <div className="mt-4 space-y-3 text-sm leading-relaxed text-ink/70">
        <p>
          The reliability score is a weighted composite of three subscores:
          liquidity health (from market depth + trader diversity),
          trading-pattern integrity (from the S3 Isolation Forest), and
          resolution quality (from the S4 LLM-as-judge over independent
          reporting).
        </p>
        <p className="font-mono text-[13px] text-ink">
          score = round( 0.35 · liquidity + 0.40 · anomaly + 0.25 · resolution )
        </p>
        <p>
          Bands: <strong>HIGH</strong> for 70 and above, <strong>MEDIUM</strong>{" "}
          for 40 to 69, <strong>LOW</strong> for below 40.
        </p>
        <p className="text-ink/50">
          Weights are uncalibrated — they reflect the current best guess at the
          relative importance of each leg, not a result from a tuning
          experiment. The canonical implementation lives in{" "}
          <code className="font-mono">backend/app/composite.py</code>; the
          model's honest rating (currently ~6.0/10 with a low-N caveat) and the
          path to improve it are documented in{" "}
          <code className="font-mono">backend/app/anomaly/MODEL_STATUS.md</code>
          .
        </p>
      </div>
    </details>
  );
}
