// Home-page carousel of UW-relevant markets sourced from the library.
//
// PISAN line 76: "the home page only shows recent lookups from
// localStorage; add a 'Featured UW-relevant markets' carousel sourced from
// the library so a first-time visitor can click into a real example without
// having to find a Polymarket URL."
//
// Approach: fetch a small slice of the library (top-N by reliability_score)
// and render as a compact horizontal card row. Empty / error states are
// soft — the carousel just doesn't appear, so a backend outage never
// breaks the Home page.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { LibraryEntry } from "../types";
import { getLibrary } from "../api";
import Badge, { bandTone } from "../ui/Badge";

const MAX_CARDS = 4;

// Department label → short pill text for the card chip.
const DEPT_LABEL: Record<string, string> = {
  POLS: "Political Science",
  ECON: "Economics",
  INFO: "Informatics",
  EVANS: "Evans (Public Policy)",
};

function deptText(depts: string[]): string {
  if (!depts.length) return "Unfiled";
  const head = depts[0];
  return DEPT_LABEL[head] ?? head;
}

export default function FeaturedMarkets() {
  const [rows, setRows] = useState<LibraryEntry[] | null>(null);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getLibrary()
      .then((all) => {
        if (cancelled) return;
        // Prefer verified entries first, then sort by reliability_score so
        // the home page shows the most-defensible examples up front.
        const ranked = [...all]
          .sort((a, b) => {
            if (a.verified !== b.verified) return a.verified ? -1 : 1;
            return b.reliability_score - a.reliability_score;
          })
          .slice(0, MAX_CARDS);
        setRows(ranked);
      })
      .catch(() => {
        if (!cancelled) setErrored(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Soft-hide on error — better to lose the carousel than break Home.
  if (errored || (rows && rows.length === 0)) return null;

  return (
    <section
      aria-labelledby="featured-heading"
      className="mx-auto max-w-content px-5 sm:px-8 lg:px-14 py-14"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <div className="caption mb-1">Featured</div>
          <h2
            id="featured-heading"
            className="font-sans text-2xl font-extrabold tracking-tight text-ink"
          >
            UW-relevant markets to start with
          </h2>
        </div>
        <Link
          to="/library"
          className="font-mono text-xs font-medium uppercase
            tracking-wider text-brand-600 hover:text-brand-700
            hover:underline underline-offset-4"
        >
          Browse the full library →
        </Link>
      </div>

      <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(rows ?? Array.from({ length: MAX_CARDS })).map((row, i) =>
          row ? (
            <li key={row.market_url}>
              <Link
                to={`/market?url=${encodeURIComponent(row.market_url)}`}
                className="card flex h-full flex-col gap-4 p-5
                  transition-colors hover:border-brand-600"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="caption truncate" title={deptText(row.departments)}>
                    {deptText(row.departments)}
                  </span>
                  <Badge tone={bandTone(row.band)}>{row.band}</Badge>
                </div>
                <p className="line-clamp-3 text-sm font-medium text-ink">
                  {row.market_question}
                </p>
                <div className="mt-auto flex items-baseline justify-between gap-2 border-t border-line pt-3">
                  <span className="caption">Score</span>
                  <span className="font-mono text-lg font-bold tabular-nums text-ink">
                    {row.reliability_score}
                    <span className="text-ink/30"> / 100</span>
                  </span>
                </div>
              </Link>
            </li>
          ) : (
            <li
              key={`skeleton-${i}`}
              className="card h-44 animate-pulse bg-panel"
              aria-hidden
            />
          ),
        )}
      </ul>
    </section>
  );
}
