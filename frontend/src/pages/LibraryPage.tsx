import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import type { LibraryEntry } from "../types";
import { getLibrary } from "../api";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Badge, { bandTone } from "../ui/Badge";
import { fadeUp, stagger } from "../lib/motion";

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
      <motion.div variants={fadeUp}>
        <SectionHeading
          eyebrow="UW market library"
          title="Find a citable market for your course"
          sub="Markets tagged to UW departments by the LLM tagger (mock). Open one for the full reliability report."
        />
      </motion.div>

      <motion.div variants={fadeUp} className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search market questions…"
          className="field sm:max-w-sm"
        />
        <div className="flex flex-wrap gap-2">
          {DEPTS.map((d) => (
            <button
              key={d}
              onClick={() => setDept(d)}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                d === dept
                  ? "bg-brand-600 text-white shadow-lift"
                  : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-600/40"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </motion.div>

      {err && <p className="text-sm text-bad">Library failed to load: {err}</p>}

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        {sorted.map((r) => (
          <motion.button
            key={r.market_url}
            variants={fadeUp}
            whileHover={{ y: -3 }}
            onClick={() => nav(`/market?url=${encodeURIComponent(r.market_url)}`)}
            className="card group p-5 text-left transition hover:shadow-lift"
          >
            <div className="flex items-start justify-between gap-3">
              <Badge tone={bandTone(r.band)}>{r.reliability_score}</Badge>
              {r.verified && <Badge tone="gold">✓ verified</Badge>}
            </div>
            <p className="mt-3 font-medium leading-snug text-ink line-clamp-3">
              {r.market_question}
            </p>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {r.departments.join(" · ")}
              </span>
              <span className="text-sm font-semibold text-brand-600
                opacity-0 transition group-hover:opacity-100">
                View report →
              </span>
            </div>
          </motion.button>
        ))}
        {sorted.length === 0 && !err && (
          <div className="col-span-full rounded-2xl border border-dashed
            border-slate-300 p-12 text-center text-slate-400">
            No markets match this filter.
          </div>
        )}
      </motion.div>

      <button
        onClick={() => setSortDesc((s) => !s)}
        className="mt-5 text-sm font-medium text-slate-500 hover:text-brand-600"
      >
        Sort by score: {sortDesc ? "highest first ▼" : "lowest first ▲"}
      </button>
    </PageShell>
  );
}
