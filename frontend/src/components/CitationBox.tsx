// PILLAR 2 deliverable — tabbed citation with one-click copy + toast. The
// strings already embed the as-of date and snapshot permalink (backend-side).

import { useState } from "react";
import { motion } from "framer-motion";
import type { Citation } from "../types";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";
import Badge from "../ui/Badge";

type Style = "APA" | "MLA" | "BibTeX";

export default function CitationBox({ citation }: { citation: Citation }) {
  const [style, setStyle] = useState<Style>("APA");
  const text =
    style === "APA" ? citation.apa : style === "MLA" ? citation.mla : citation.bibtex;
  const isOk = citation.reliability_flag.startsWith("RELIABLE");

  async function copy() {
    await navigator.clipboard.writeText(text);
    toast(`${style} citation copied`);
  }

  return (
    <motion.div variants={fadeUp} className="card p-6">
      <h2 className="section-title">Academic citation</h2>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-5">
          {(["APA", "MLA", "BibTeX"] as Style[]).map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`border-b-2 pb-1 font-mono text-xs transition-colors ${
                s === style
                  ? "border-brand-600 text-ink"
                  : "border-transparent text-ink/45 hover:text-ink"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <button onClick={copy} className="btn-ghost text-xs">
          Copy
        </button>
      </div>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words
        border border-line bg-ink/[0.03] p-4 font-mono text-[13px]
        leading-relaxed text-ink/80">
        {text}
      </pre>
      <div className="mt-3">
        <Badge tone={isOk ? "good" : "warn"}>{citation.reliability_flag}</Badge>
      </div>
    </motion.div>
  );
}
