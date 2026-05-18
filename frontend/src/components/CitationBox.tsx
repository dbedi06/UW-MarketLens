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
      <h2 className="text-xl font-semibold">Academic citation</h2>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
          {(["APA", "MLA", "BibTeX"] as Style[]).map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`relative rounded-lg px-3.5 py-1.5 text-sm font-medium
                transition ${
                  s === style ? "text-brand-700" : "text-slate-500 hover:text-ink"
                }`}
            >
              {s === style && (
                <motion.span
                  layoutId="cite-tab"
                  className="absolute inset-0 rounded-lg bg-white shadow-soft"
                />
              )}
              <span className="relative">{s}</span>
            </button>
          ))}
        </div>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={copy}
          className="btn-primary"
        >
          Copy
        </motion.button>
      </div>
      <pre className="mt-3 whitespace-pre-wrap break-words rounded-xl
        bg-ink p-4 font-mono text-[13px] leading-relaxed text-slate-200">
        {text}
      </pre>
      <div className="mt-3">
        <Badge tone={isOk ? "good" : "warn"}>{citation.reliability_flag}</Badge>
      </div>
    </motion.div>
  );
}
