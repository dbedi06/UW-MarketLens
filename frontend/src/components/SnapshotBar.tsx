// PILLAR 2 — the reproducibility strip. The permalink always re-renders this
// exact report, so a paper's citation stays verifiable after the market moves.

import { motion } from "framer-motion";
import { fadeUp } from "../lib/motion";
import { toast } from "../ui/Toast";

export default function SnapshotBar({
  asOf,
  permalink,
  compact = false,
}: {
  asOf: string;
  permalink: string;
  compact?: boolean;
}) {
  const fullLink = `${window.location.origin}${permalink}`;

  async function copy() {
    await navigator.clipboard.writeText(fullLink);
    toast("Permalink copied");
  }

  if (compact) {
    return (
      <div className="rounded-xl border border-brand-600/15
        bg-brand-600/[0.06] p-3">
        <div className="text-xs text-slate-500">
          📌 Snapshot as of{" "}
          <strong className="text-brand-700">{asOf}</strong>
        </div>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={copy}
          className="mt-2 w-full rounded-lg bg-white px-3 py-1.5 text-xs
            font-semibold text-brand-700 ring-1 ring-slate-200
            hover:ring-brand-600/40"
        >
          Copy permalink
        </motion.button>
      </div>
    );
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
