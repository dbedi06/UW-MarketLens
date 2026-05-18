// PILLAR 2 — the reproducibility strip. The permalink always re-renders this
// exact report, so a paper's citation stays verifiable after the market moves.

import { useState } from "react";

export default function SnapshotBar({
  asOf,
  permalink,
}: {
  asOf: string;
  permalink: string;
}) {
  const [copied, setCopied] = useState(false);
  const fullLink = `${window.location.origin}${permalink}`;

  async function copy() {
    await navigator.clipboard.writeText(fullLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="snapshot-bar">
      <span>
        📌 Reliability snapshot <strong>as of {asOf}</strong> — this link always
        shows this exact verdict.
      </span>
      <code className="snap-link">{fullLink}</code>
      <button className="copy-btn" onClick={copy}>
        {copied ? "Copied ✓" : "Copy permalink"}
      </button>
    </div>
  );
}
