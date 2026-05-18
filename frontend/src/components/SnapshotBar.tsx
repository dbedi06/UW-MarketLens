// PILLAR 2 — the reproducibility strip. The permalink always re-renders this
// exact report, so a paper's citation stays verifiable after the market moves.

import { motion } from "framer-motion";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";

export default function SnapshotBar({
  asOf,
  permalink,
}: {
  asOf: string;
  permalink: string;
}) {
  const fullLink = `${window.location.origin}${permalink}`;

  async function copy() {
    await navigator.clipboard.writeText(fullLink);
    toast("Permalink copied");
  }

  return (
    <motion.div
      variants={fadeUp}
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl
        border border-brand-600/15 bg-brand-600/[0.06] px-5 py-3.5"
    >
      <span className="text-sm text-slate-600">
        📌 Snapshot{" "}
        <strong className="text-brand-700">as of {asOf}</strong> — this link
        always shows this exact verdict.
      </span>
      <code className="rounded-lg bg-white px-2.5 py-1 font-mono text-xs
        text-brand-700 ring-1 ring-slate-200">
        {fullLink}
      </code>
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={copy}
        className="btn-ghost ml-auto"
      >
        Copy permalink
      </motion.button>
    </motion.div>
  );
}
