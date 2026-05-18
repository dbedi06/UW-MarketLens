// PILLAR 2 — the deliverable a student actually takes away. Style toggle,
// one-click copy, and a prominent reliability flag. The citation strings
// already embed the as-of date and the snapshot permalink (built backend-side
// in mock.make_citation) so what gets pasted into a paper is reproducible.

import { useState } from "react";
import type { Citation } from "../types";

type Style = "APA" | "MLA" | "BibTeX";

export default function CitationBox({ citation }: { citation: Citation }) {
  const [style, setStyle] = useState<Style>("APA");
  const [copied, setCopied] = useState(false);

  const text =
    style === "APA" ? citation.apa : style === "MLA" ? citation.mla : citation.bibtex;
  const isOk = citation.reliability_flag.startsWith("RELIABLE");

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="card">
      <h2>Academic citation</h2>
      <div className="cite-toolbar">
        <div className="cite-tabs">
          {(["APA", "MLA", "BibTeX"] as Style[]).map((s) => (
            <button
              key={s}
              className={s === style ? "cite-tab active" : "cite-tab"}
              onClick={() => setStyle(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <button className="copy-btn" onClick={copy}>
          {copied ? "Copied ✓" : "Copy"}
        </button>
      </div>
      <pre className="citation-text">{text}</pre>
      <span className={`flag ${isOk ? "ok" : "warn"}`}>
        {citation.reliability_flag}
      </span>
    </div>
  );
}
