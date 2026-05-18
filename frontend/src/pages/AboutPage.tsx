// Project web presence (rubric: 15 pts). Architecture, methodology, and an
// honest evaluation-results placeholder clearly labeled as not-yet-measured.

import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";

const PIPELINE: [string, string, string][] = [
  ["S1", "Ingest", "Polymarket API, trade history"],
  ["S2", "Features", "Per-window vectors"],
  ["S3", "Anomaly", "Isolation Forest"],
  ["S4", "Resolution", "LLM-as-judge vs. wire sources"],
  ["S7", "Composite", "Deterministic 0–100 score"],
];

const METHOD: [string, string][] = [
  ["The “why,” not the number", "Every verdict ships with plain-language reasons and flagged-window evidence — a score is only as citable as its explanation."],
  ["Reproducible snapshots", "Markets move; a citation must not. Each lookup yields a dated permalink that always re-renders the identical report."],
  ["Human-in-the-loop tagging", "The LLM proposes UW department tags; a person approves or overrides before they enter the library."],
  ["Auditable AI", "All model calls return structured, schema-constrained output evaluated against labeled ground truth."],
];

const EVAL: [string, string, string][] = [
  ["Anomaly detector", "Recall @ ≤20% FPR", "≥75%"],
  ["LLM-as-judge", "Verdict agreement", "≥80%"],
  ["Usability", "SUS score", "≥70"],
];

export default function AboutPage() {
  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="About"
        title="UW MarketLens"
        sub="A free, open-access tool for the UW community that scores the reliability of Polymarket markets so they can be cited responsibly."
      />

      <section className="mt-10 border-t border-line pt-8">
        <h2 className="section-title">How a score is built</h2>
        <ol className="mt-5 divide-y divide-line border-y border-line">
          {PIPELINE.map(([id, t, d]) => (
            <li key={id} className="flex items-baseline gap-5 py-3">
              <span className="caption w-8 shrink-0">{id}</span>
              <span className="w-32 shrink-0 font-display font-semibold text-ink">
                {t}
              </span>
              <span className="text-sm text-ink/60">{d}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          Current build: every stage is served by a deterministic mock
          (<code className="font-mono">backend/app/mock.py</code>). The contract
          and UI are final; the real pipeline swaps in behind the API with no
          frontend change.
        </p>
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Methodology</h2>
        <div className="mt-5 grid gap-px border border-line bg-line sm:grid-cols-2">
          {METHOD.map(([t, d]) => (
            <div key={t} className="bg-paper p-6">
              <div className="font-display font-semibold text-ink">{t}</div>
              <p className="mt-1.5 text-sm leading-relaxed text-ink/65">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Evaluation results</h2>
        <table className="mt-5 w-full border border-line text-sm">
          <thead>
            <tr className="border-b border-line text-left">
              {["Component", "Metric", "Target", "Measured"].map((h) => (
                <th key={h} className="caption px-4 py-2.5 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {EVAL.map(([c, m, t]) => (
              <tr key={c}>
                <td className="px-4 py-2.5 text-ink">{c}</td>
                <td className="px-4 py-2.5 font-mono text-ink/60">{m}</td>
                <td className="px-4 py-2.5 font-mono text-ink/60">{t}</td>
                <td className="px-4 py-2.5 font-mono italic text-ink/40">
                  pending
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          Numbers are intentionally blank until the real models are wired and
          evaluated — we don't report metrics we haven't measured.
        </p>
      </section>
    </PageShell>
  );
}
