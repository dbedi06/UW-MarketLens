// PILLAR 2 — the reproducibility strip. The permalink always re-renders this
// exact report, so a paper's citation stays verifiable after the market moves.

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
      <div className="border-t border-line pt-4">
        <div className="caption">Snapshot · {asOf}</div>
        <p className="mt-1 text-xs leading-relaxed text-ink/55">
          This permalink always renders this exact verdict.
        </p>
        <button
          onClick={copy}
          className="btn-ghost mt-3 w-full text-xs"
        >
          Copy permalink
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-y
      border-line py-3">
      <span className="text-sm text-ink/70">
        <span className="caption mr-2">Snapshot {asOf}</span>
        This link always shows this exact verdict.
      </span>
      <code className="font-mono text-xs text-brand-700">{fullLink}</code>
      <button onClick={copy} className="btn-ghost ml-auto text-xs">
        Copy permalink
      </button>
    </div>
  );
}
