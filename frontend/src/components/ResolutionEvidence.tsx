// Surfaces the actual NewsAPI snippets the LLM-as-judge weighed when
// it produced the resolution verdict. PISAN's framing: "when LLM-as-
// judge says UNVERIFIABLE, surface the actual snippets that were
// considered" — closes the "why, not the number" pillar honestly for
// the resolution leg.
//
// Hidden when there are no snippets (S4 fallback path, no API keys,
// or no articles returned by NewsAPI).

import { motion } from "framer-motion";
import type { ResolutionVerdict } from "../types";
import { fadeUp } from "../lib/motion";
import SectionHeading from "../ui/SectionHeading";

const VERDICT_TONE: Record<string, string> = {
  HIGH: "text-good",
  MEDIUM: "text-warn",
  LOW: "text-bad",
  UNVERIFIABLE: "text-ink/55",
};

export default function ResolutionEvidence({
  resolution,
}: {
  resolution: ResolutionVerdict;
}) {
  const snippets = resolution.supporting_snippets ?? [];
  if (snippets.length === 0) {
    return null;
  }

  const verdictTone = VERDICT_TONE[resolution.verdict] ?? "text-ink";

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Resolution evidence"
        title="What the LLM-as-judge actually saw"
        sub="The S4 resolution checker gave Claude the snippets below — title plus description from NewsAPI — and asked for a verdict. Read them yourself to audit the call."
      />

      <div className="mt-4 flex items-center gap-3 border-b border-line pb-3">
        <span className="caption">Verdict</span>
        <span
          className={`font-sans text-sm font-extrabold tracking-tight
            ${verdictTone}`}
        >
          {resolution.verdict}
        </span>
        <span className="text-ink/30">·</span>
        <span className="caption">{snippets.length} snippet{snippets.length === 1 ? "" : "s"} considered</span>
      </div>

      <ul className="mt-4 space-y-4">
        {snippets.map((s, i) => (
          <li
            key={s.url || i}
            className="border-l-2 border-line pl-4 hover:border-brand-600"
          >
            {s.title && (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block font-sans text-sm font-bold leading-snug
                  tracking-tight text-ink underline-offset-4 hover:underline"
              >
                {s.title}
              </a>
            )}
            {s.description && (
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink/65">
                {s.description}
              </p>
            )}
            {s.url && (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1.5 inline-block font-mono text-[11px]
                  text-ink/40 hover:text-ink"
              >
                {s.url}
              </a>
            )}
          </li>
        ))}
      </ul>

      <p className="caption mt-4 italic">
        Snippets reproduced verbatim from NewsAPI. If the coverage is
        thin or biased, this panel makes that visible rather than hiding
        it.
      </p>
    </motion.div>
  );
}
