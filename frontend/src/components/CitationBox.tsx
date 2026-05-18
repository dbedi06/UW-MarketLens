// Shows APA + MLA citations and the reliability-flag warning a reader sees
// when a cited market falls below the integrity threshold.

import type { Citation } from "../types";

export default function CitationBox({ citation }: { citation: Citation }) {
  const isOk = citation.reliability_flag.startsWith("RELIABLE");
  return (
    <div className="card">
      <h2>Academic Citation</h2>
      <div className="citation">
        <div className="style-label">APA</div>
        <p>{citation.apa}</p>
        <div className="style-label">MLA</div>
        <p>{citation.mla}</p>
        <span className={`flag ${isOk ? "ok" : "warn"}`}>
          {citation.reliability_flag}
        </span>
      </div>
    </div>
  );
}
