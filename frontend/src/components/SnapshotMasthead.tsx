// PILLAR 2 identity: frames the snapshot as a sealed, reproducible record,
// led by the live OG share card.

import { motion } from "framer-motion";
import { fadeUp } from "../lib/motion";
import { ogImageUrl } from "../api";
import { toast } from "../ui/Toast";

export default function SnapshotMasthead({
  id,
  asOf,
}: {
  id: string;
  asOf: string;
}) {
  const link = `${window.location.origin}/snapshot/${id}`;

  function copy() {
    navigator.clipboard.writeText(link);
    toast("Permalink copied");
  }

  return (
    <motion.section
      variants={fadeUp}
      className="mb-8 overflow-hidden rounded-xl border border-line"
    >
      <div className="block-purple flex flex-wrap items-end justify-between
        gap-4 px-6 py-5">
        <div>
          <div className="font-mono text-[11px] font-medium uppercase
            tracking-[0.14em] text-gold">
            Reproducible snapshot
          </div>
          <div className="mt-1 font-sans text-3xl font-extrabold
            tracking-tight text-paper">
            As of {asOf}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 rounded-md border
            border-gold/40 px-3 py-1.5 font-mono text-xs text-gold">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <rect x="4" y="11" width="16" height="10" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
            {id}
          </span>
          <button
            onClick={copy}
            className="rounded-md bg-gold px-4 py-1.5 font-mono text-xs
              font-bold uppercase tracking-wide text-brand-900
              hover:brightness-105"
          >
            Copy permalink
          </button>
        </div>
      </div>

      <div className="bg-ink/[0.03] p-4 sm:p-6">
        <img
          src={ogImageUrl(id)}
          alt="Sealed reliability snapshot card"
          width={1200}
          height={630}
          className="block aspect-[1200/630] w-full rounded-lg border
            border-line"
        />
        <p className="mt-3 text-center font-mono text-xs text-ink/45">
          This is the citable record. The link always renders this exact
          view, byte for byte.
        </p>
      </div>
    </motion.section>
  );
}
