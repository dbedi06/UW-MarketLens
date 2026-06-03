// Passive scoring-mode status pill. Reads from `useScoringMode` and renders
// a small "Live" / "Mock" indicator. Not a control — the actual toggle lives
// in NavBar. PISAN line 75: "casual user can't easily tell whether the report
// they're looking at is real or mock"; this is the at-a-glance answer on
// pages where the question matters (Home lookup).
//
// Colour choice: amber for Live mirrors `SourceBadge` in `MarketReport.tsx`,
// not green. Amber says "real data, treat with the usual caveats" — the
// detector is real-trained on the cold path, the LLM verdict is heuristic.
// Green would imply "verified accurate," which is overclaiming for a 6/10
// system. Matching `SourceBadge` also makes the two pills read
// as the same status language (preset on Home vs. actual on the report)
// instead of unrelated UI.
//
// On a MarketReport, the per-report `SourceBadge` is more authoritative —
// it reflects the actual `MarketScore.source` from the response, not the
// global preference. The two can differ if the user toggled mid-flow.

import { useScoringMode } from "../lib/scoringMode";

export default function ModeBadge({ className = "" }: { className?: string }) {
  const { mode } = useScoringMode();
  const isLive = mode === "live";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5
        text-[10px] font-bold uppercase tracking-wider ${
          isLive
            ? "border-warn/40 bg-warn/10 text-warn"
            : "border-line bg-panel text-ink/55"
        } ${className}`}
      title={
        isLive
          ? "Live mode — lookups hit the real S1→S7 chain on Polymarket data."
          : "Mock mode — lookups return deterministic placeholder data."
      }
    >
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full ${
          isLive ? "bg-warn" : "bg-ink/30"
        }`}
      />
      {isLive ? "Live" : "Mock"}
    </span>
  );
}
