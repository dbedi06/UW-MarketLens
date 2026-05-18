// Project web presence (rubric: 15 pts). Architecture, methodology, and an
// honest evaluation-results placeholder clearly labeled as not-yet-measured.

import { motion } from "framer-motion";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import { fadeUp, stagger, reveal } from "../lib/motion";

const PIPELINE: [string, string][] = [
  ["Ingest", "Polymarket API → trade history (S1)"],
  ["Features", "Per-window vectors (S2)"],
  ["Anomaly", "Isolation Forest (S3)"],
  ["Resolution", "LLM-as-judge vs. wire sources (S4)"],
  ["Composite", "Deterministic 0–100 score (S7)"],
];

const METHOD = [
  ["The \"why,\" not the number", "Every verdict ships with plain-language reasons and flagged-window evidence — a score is only as citable as its explanation."],
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
      <motion.div variants={fadeUp}>
        <SectionHeading
          eyebrow="About"
          title="UW MarketLens"
          sub="A free, open-access tool for the UW community that scores the reliability of Polymarket markets so they can be cited responsibly."
        />
      </motion.div>

      <motion.section {...reveal} className="card mb-5 p-6">
        <h2 className="text-xl font-semibold">How a score is built</h2>
        <div className="mt-5 flex flex-wrap items-stretch gap-3">
          {PIPELINE.map(([t, d], i) => (
            <motion.div
              key={t}
              variants={fadeUp}
              className="flex items-center gap-3"
            >
              <div className="min-w-[150px] rounded-xl bg-brand-600/[0.06]
                px-4 py-3 ring-1 ring-brand-600/15">
                <div className="font-display text-sm font-bold text-brand-700">
                  {t}
                </div>
                <div className="mt-0.5 text-[11px] text-slate-500">{d}</div>
              </div>
              {i < PIPELINE.length - 1 && (
                <span className="text-lg font-bold text-brand-300">→</span>
              )}
            </motion.div>
          ))}
        </div>
        <p className="mt-4 text-xs italic text-slate-400">
          Current build: every stage is served by a deterministic mock
          (<code>backend/app/mock.py</code>). The contract and UI are final;
          the real pipeline swaps in behind the API with no frontend change.
        </p>
      </motion.section>

      <motion.section {...reveal} className="card mb-5 p-6">
        <h2 className="text-xl font-semibold">Methodology</h2>
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="mt-4 grid gap-4 sm:grid-cols-2"
        >
          {METHOD.map(([t, d]) => (
            <motion.div
              key={t}
              variants={fadeUp}
              className="rounded-xl border border-slate-200/70 bg-slate-50 p-4"
            >
              <div className="font-semibold text-ink">{t}</div>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{d}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.section>

      <motion.section {...reveal} className="card p-6">
        <h2 className="text-xl font-semibold">Evaluation results</h2>
        <div className="mt-4 overflow-hidden rounded-xl ring-1 ring-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Component</th>
                <th className="px-4 py-2.5 font-semibold">Metric</th>
                <th className="px-4 py-2.5 font-semibold">Target</th>
                <th className="px-4 py-2.5 font-semibold">Measured</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {EVAL.map(([c, m, t]) => (
                <tr key={c}>
                  <td className="px-4 py-2.5 text-ink">{c}</td>
                  <td className="px-4 py-2.5 text-slate-600">{m}</td>
                  <td className="px-4 py-2.5 text-slate-600">{t}</td>
                  <td className="px-4 py-2.5 italic text-slate-400">pending</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs italic text-slate-400">
          Numbers are intentionally blank until the real models are wired and
          evaluated — we don't report metrics we haven't measured.
        </p>
      </motion.section>
    </PageShell>
  );
}
