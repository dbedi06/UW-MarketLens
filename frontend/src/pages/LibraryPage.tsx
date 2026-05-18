import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LibraryEntry } from "../types";
import { getLibrary } from "../api";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Badge, { bandTone } from "../ui/Badge";

const DEPTS = ["ALL", "POLS", "ECON", "INFO", "EVANS"];

export default function LibraryPage() {
  const nav = useNavigate();
  const [rows, setRows] = useState<LibraryEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("ALL");
  const [sortDesc, setSortDesc] = useState(true);

  useEffect(() => {
    getLibrary(q || undefined, dept === "ALL" ? undefined : dept)
      .then(setRows)
      .catch((e) => setErr(e.message));
  }, [q, dept]);

  const sorted = useMemo(
    () =>
      [...rows].sort((a, b) =>
        sortDesc
          ? b.reliability_score - a.reliability_score
          : a.reliability_score - b.reliability_score,
      ),
    [rows, sortDesc],
  );

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="UW market library"
        title="Find a citable market for your course"
        sub="Markets tagged to UW departments by the LLM tagger (mock). Open one for the full reliability report."
      />

      <div className="mt-8 flex flex-col gap-4 border-y border-line py-4
        sm:flex-row sm:items-center sm:justify-between">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search market questions…"
          className="field font-mono text-[13px] sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-5">
          {DEPTS.map((d) => (
            <button
              key={d}
              onClick={() => setDept(d)}
              className={`border-b-2 pb-0.5 font-mono text-xs transition-colors ${
                d === dept
                  ? "border-brand-600 text-ink"
                  : "border-transparent text-ink/45 hover:text-ink"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {err && (
        <p className="mt-4 text-sm text-bad">Library failed to load: {err}</p>
      )}

      <ul className="divide-y-2 divide-ink/10 border-b-2 border-ink">
        {sorted.map((r) => (
          <li key={r.market_url}>
            <button
              onClick={() =>
                nav(`/market?url=${encodeURIComponent(r.market_url)}`)
              }
              className="group flex w-full items-center gap-7 py-6 text-left
                transition-colors hover:bg-ink/[0.03]"
            >
              <span className="numeral w-24 shrink-0 text-5xl text-brand-600">
                {r.reliability_score}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-sans text-base font-extrabold
                  leading-snug tracking-tight text-ink">
                  {r.market_question}
                </span>
                <span className="caption mt-1.5 block">
                  {r.departments.join(" · ")}
                  {r.verified && " · verified"}
                </span>
              </span>
              <span className="hidden shrink-0 sm:block">
                <Badge tone={bandTone(r.band)}>{r.band}</Badge>
              </span>
              <span className="caption shrink-0 opacity-0 transition
                group-hover:opacity-100">
                open
              </span>
            </button>
          </li>
        ))}
        {sorted.length === 0 && !err && (
          <li className="py-16 text-center text-sm italic text-ink/40">
            No markets match this filter.
          </li>
        )}
      </ul>

      <button
        onClick={() => setSortDesc((s) => !s)}
        className="caption mt-5 hover:text-ink"
      >
        Sort by score: {sortDesc ? "highest first" : "lowest first"}
      </button>
    </PageShell>
  );
}
