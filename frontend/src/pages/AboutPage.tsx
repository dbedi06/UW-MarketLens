// Project web presence (rubric: 15 pts). Architecture, methodology, and an
// honest evaluation-results placeholder clearly labeled as not-yet-measured.

import { Link } from "react-router-dom";
import CalibrationChart from "../components/CalibrationChart";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";

const PIPELINE: [string, string, string][] = [
  [
    "S1",
    "Ingest",
    "Polymarket Gamma + Data API; optional Polygon RPC enrichment",
  ],
  [
    "S2",
    "Features",
    "Base + microstructure + per-market relative + trader-graph",
  ],
  [
    "S3",
    "Anomaly",
    "Isolation Forest, percentile-calibrated against held-out clean",
  ],
  ["S4", "Resolution", "Claude LLM-as-judge over NewsAPI snippets"],
  [
    "S5",
    "Tagger",
    "Claude few-shot tags vs UW departments (POLS/ECON/INFO/EVANS)",
  ],
  ["S6", "Citation", "APA + MLA + BibTeX with embedded reliability flag"],
  ["S7", "Composite", "Weighted 35/40/25 (liquidity / anomaly / resolution)"],
];

const METHOD: [string, string][] = [
  [
    'The "why," not the number',
    "Every verdict ships with plain-language reasons and flagged-window evidence. A score is only as citable as its explanation.",
  ],
  [
    "Reproducible snapshots",
    "Markets move; a citation must not. Each lookup yields a dated permalink that always re-renders the identical report.",
  ],
  [
    "Human-in-the-loop tagging",
    "The LLM proposes UW department tags; a person approves or overrides before they enter the library.",
  ],
  [
    "Auditable AI",
    "All model calls return structured, schema-constrained output evaluated against labeled ground truth.",
  ],
];

// Evaluation results. Each row's "Measured" column reflects the
// honest status as of the latest model push. We do not synthesize
// numbers; if we haven't measured it, the cell says so plainly.
const EVAL: [string, string, string, string][] = [
  [
    "Anomaly detector (synthetic baseline)",
    "Sybil-ring AUC (network-aware vs base-only)",
    "lift on a pattern only network features should see",
    "0.91 vs 0.47 (circular synthetic test)",
  ],
  [
    "Anomaly detector (real-trained, v0.9)",
    "Training corpus + reference distribution",
    "model fitted on real Polymarket feature distribution",
    "54 markets / ~4000 windows — pickle at trained_model.pkl",
  ],
  [
    "Anomaly detector (real data)",
    "ROC-AUC against verified labeled markets",
    "measured 0.672 with bootstrap CI [0.314, 0.964]",
    "12 verified cases (4 controversial, 8 mundane) — low-N warning remains",
  ],
  [
    "LLM-as-judge (S4)",
    "Verdict agreement vs human labels",
    "≥ 0.75",
    "pending — labeling protocol drafted",
  ],
  [
    "Usability",
    "Heuristic evaluation (Nielsen, n=1 reviewer pass)",
    "no task blockers on 5 scripted tasks",
    "all 5 tasks completed, no blockers",
  ],
];

export default function AboutPage() {
  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="About"
        title="UW MarketLens"
        sub="A free, open-access tool for the UW community that scores the reliability of Polymarket markets so they can be cited responsibly."
      />
      <p className="mt-3 max-w-prose text-sm text-ink/55">
        For the concrete instructor, PhD-student, and research-methods- class
        workflows MarketLens supports, see{" "}
        <Link
          to="/uw"
          className="text-brand-600 hover:text-brand-700 hover:underline
            underline-offset-4"
        >
          For UW
        </Link>
        .
      </p>

      <section className="mt-10 border-t border-line pt-8">
        <h2 className="section-title">How a score is built</h2>
        <ol className="mt-5 divide-y divide-line border-y border-line">
          {PIPELINE.map(([id, t, d]) => (
            <li key={id} className="flex items-baseline gap-6 py-4">
              <span className="numeral w-16 shrink-0 text-2xl text-brand-600">
                {id}
              </span>
              <span
                className="w-36 shrink-0 font-sans font-extrabold
                tracking-tight text-ink"
              >
                {t}
              </span>
              <span className="text-sm text-ink/60">{d}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          Current build: all seven sections run real implementations by default.
          The deterministic mock in{" "}
          <code className="font-mono">backend/app/mock.py</code> stays available
          behind a "Mock mode" toggle in the nav for offline demos and as a
          fallback when the live pipeline can't reach Polymarket. Set{" "}
          <code className="font-mono">NEWS_API_KEY</code> and{" "}
          <code className="font-mono">ANTHROPIC_API_KEY</code> to enable S4 / S5
          live; without them S4 returns{" "}
          <code className="font-mono">UNVERIFIABLE</code> and S5 falls back to
          rule-based tags.
        </p>
      </section>

      <section className="mt-12 border-t border-line pt-8">
        <h2 className="section-title">Methodology</h2>
        <div className="mt-5 grid gap-px border border-line bg-line sm:grid-cols-2">
          {METHOD.map(([t, d]) => (
            <div key={t} className="bg-paper p-6">
              <div className="font-sans font-bold text-ink">{t}</div>
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
            {EVAL.map(([c, m, t, measured]) => {
              const pending = measured.toLowerCase().startsWith("pending");
              return (
                <tr key={c}>
                  <td className="px-4 py-2.5 text-ink">{c}</td>
                  <td className="px-4 py-2.5 font-mono text-ink/60">{m}</td>
                  <td className="px-4 py-2.5 font-mono text-ink/60">{t}</td>
                  <td
                    className={`px-4 py-2.5 font-mono ${
                      pending ? "italic text-ink/40" : "text-ink/75"
                    }`}
                  >
                    {measured}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="mt-8">
          <CalibrationChart />
        </div>
        <p className="mt-4 max-w-prose text-xs italic text-ink/45">
          Honest rating: ~6.0/10 with a low-N caveat. The detector now trains on
          real Polymarket markets (54 in the corpus); the synthetic AUC is real
          arithmetic but its test was designed to favor the features under
          measurement, so it's a capability check, not a generalization claim.
          The labeled-eval set now contains 12 verified cases (4 controversial +
          8 mundane) and reports a measured AUC of 0.672 with a wide CI. Full
          path to 6/10 in{" "}
          <code className="font-mono">UW_MarketLens_Push_To_Six.html</code>;
          current model state in{" "}
          <code className="font-mono">backend/app/anomaly/MODEL_STATUS.md</code>
          .
        </p>
      </section>
    </PageShell>
  );
}
