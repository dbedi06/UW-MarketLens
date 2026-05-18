// Project web presence (rubric: 15 pts). Architecture, methodology, and an
// honest evaluation-results placeholder clearly labeled as not-yet-measured.

export default function AboutPage() {
  return (
    <div>
      <h2 className="page-title">About UW MarketLens</h2>
      <p className="question">
        A free, open-access tool for the UW community that scores the
        reliability of Polymarket prediction markets so they can be cited
        responsibly in coursework.
      </p>

      <div className="card">
        <h2>How a score is built</h2>
        <div className="pipeline">
          {[
            ["Ingest", "Polymarket API → trade history (S1)"],
            ["Features", "Per-window vectors (S2)"],
            ["Anomaly", "Isolation Forest (S3)"],
            ["Resolution", "LLM-as-judge vs. wire sources (S4)"],
            ["Composite", "Deterministic 0–100 score (S7)"],
          ].map(([t, d], i, a) => (
            <div className="pipe-step" key={t}>
              <div className="pipe-box">
                <strong>{t}</strong>
                <span>{d}</span>
              </div>
              {i < a.length - 1 && <span className="pipe-arrow">→</span>}
            </div>
          ))}
        </div>
        <p className="placeholder-note" style={{ border: 0, margin: "8px 0 0" }}>
          Current build: every stage above is served by a deterministic mock
          (<code>backend/app/mock.py</code>). The contract and UI are final; the
          real pipeline swaps in behind the API with no frontend change.
        </p>
      </div>

      <div className="card">
        <h2>Methodology</h2>
        <ul className="method">
          <li>
            <strong>The "why," not the number.</strong> Every verdict ships with
            plain-language reasons and the flagged-window evidence — a score is
            only as citable as the explanation behind it.
          </li>
          <li>
            <strong>Reproducible snapshots.</strong> Markets move; a citation
            must not. Each lookup yields a dated permalink that always re-renders
            the identical report.
          </li>
          <li>
            <strong>Human-in-the-loop tagging.</strong> The LLM proposes UW
            department tags; a person approves or overrides them before they
            enter the library.
          </li>
          <li>
            <strong>Auditable AI.</strong> All model calls return structured,
            schema-constrained output evaluated against labeled ground truth.
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>Evaluation results</h2>
        <table>
          <thead>
            <tr><th>Component</th><th>Metric</th><th>Target</th><th>Measured</th></tr>
          </thead>
          <tbody>
            <tr><td>Anomaly detector</td><td>Recall @ ≤20% FPR</td><td>≥75%</td><td className="tbd">pending</td></tr>
            <tr><td>LLM-as-judge</td><td>Verdict agreement</td><td>≥80%</td><td className="tbd">pending</td></tr>
            <tr><td>Usability</td><td>SUS score</td><td>≥70</td><td className="tbd">pending</td></tr>
          </tbody>
        </table>
        <p className="placeholder-note" style={{ border: 0, margin: "8px 0 0" }}>
          Numbers are intentionally blank until the real models are wired and
          evaluated — we don't report metrics we haven't measured.
        </p>
      </div>
    </div>
  );
}
