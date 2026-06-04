import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { LibraryEntry } from "../types";
import { getLibrary, libraryCsvUrl } from "../api";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Badge, { bandTone } from "../ui/Badge";

const DEPTS = ["ALL", "POLS", "ECON", "INFO", "EVANS"];

// Course codes the backend knows about (mirror of
// backend/app/data/uw_courses.json). Used for autocomplete suggestions
// in the course-pack mode input.
const KNOWN_COURSES = [
  "POLS270", "POLS353", "POLS427",
  "ECON200", "ECON201", "ECON301", "ECON482",
  "INFO200", "INFO340", "INFO462",
  "EVANS547", "EVANS582",
];

export default function LibraryPage() {
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();

  // Course mode is active when ?course=POLS270 is in the URL. The
  // dept tabs hide while a course filter is in effect.
  const courseParam = (params.get("course") || "").toUpperCase();
  const [coursePackMode, setCoursePackMode] = useState(!!courseParam);
  const [courseInput, setCourseInput] = useState(courseParam);

  const [rows, setRows] = useState<LibraryEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("ALL");
  const [sortDesc, setSortDesc] = useState(true);

  useEffect(() => {
    const course = coursePackMode && courseParam ? courseParam : undefined;
    getLibrary(
      q || undefined,
      course ? undefined : (dept === "ALL" ? undefined : dept),
      course,
    )
      .then((r) => {
        setRows(r);
        setErr(null);
      })
      .catch((e) => setErr(e.message));
  }, [q, dept, coursePackMode, courseParam]);

  const sorted = useMemo(
    () =>
      [...rows].sort((a, b) =>
        sortDesc
          ? b.reliability_score - a.reliability_score
          : a.reliability_score - b.reliability_score,
      ),
    [rows, sortDesc],
  );

  function applyCourse() {
    const code = courseInput.trim().toUpperCase().replace(/\s+/g, "");
    if (!code) return;
    setParams({ course: code }, { replace: true });
    setCoursePackMode(true);
  }

  function clearCourse() {
    const p = new URLSearchParams(params);
    p.delete("course");
    setParams(p, { replace: true });
    setCourseInput("");
    setCoursePackMode(false);
  }

  return (
    <PageShell wide>
      <SectionHeading
        eyebrow="UW market library"
        title="Find a citable market for your course"
        sub="Markets tagged to UW departments by the LLM tagger. Open one for the full reliability report — or switch to course-pack mode to see only what fits a specific UW course."
      />

      {/* Mode toggle */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-b border-line pb-4">
        <button
          onClick={() => {
            setCoursePackMode(false);
            clearCourse();
          }}
          className={`border-b-2 pb-0.5 font-mono text-xs uppercase
            tracking-wider transition-colors ${
            !coursePackMode
              ? "border-brand-600 text-ink"
              : "border-transparent text-ink/45 hover:text-ink"
          }`}
        >
          Department filter
        </button>
        <button
          onClick={() => setCoursePackMode(true)}
          className={`border-b-2 pb-0.5 font-mono text-xs uppercase
            tracking-wider transition-colors ${
            coursePackMode
              ? "border-brand-600 text-ink"
              : "border-transparent text-ink/45 hover:text-ink"
          }`}
        >
          Course-pack mode
        </button>
        <span className="ml-auto">
          <a
            href={libraryCsvUrl(
              q || undefined,
              coursePackMode ? undefined : (dept === "ALL" ? undefined : dept),
              coursePackMode && courseParam ? courseParam : undefined,
            )}
            download="marketlens_library.csv"
            className="font-mono text-xs font-medium uppercase tracking-wider
              text-brand-600 hover:text-brand-700 hover:underline
              underline-offset-4"
          >
            Download CSV ↓
          </a>
        </span>
      </div>

      {coursePackMode ? (
        <div className="mt-6 flex flex-col gap-4 border-y border-line py-4
          sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
            <label className="caption shrink-0">UW course code</label>
            <input
              list="ml-course-codes"
              value={courseInput}
              onChange={(e) => setCourseInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applyCourse()}
              placeholder="e.g. POLS270, INFO200"
              className="field font-mono text-[13px] sm:max-w-xs"
            />
            <datalist id="ml-course-codes">
              {KNOWN_COURSES.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            <button onClick={applyCourse} className="btn-primary px-5 py-2">
              Apply
            </button>
            {courseParam && (
              <button onClick={clearCourse} className="caption hover:text-ink">
                Clear ({courseParam})
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-4 border-y border-line py-4
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
      )}

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
              <span className="numeral w-24 shrink-0 text-center text-5xl text-brand-600">
                {r.reliability_score}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-sans text-base font-extrabold
                  leading-snug tracking-tight text-ink">
                  {r.market_question}
                </span>
                <span className="caption mt-1.5 block">
                  {r.departments.length > 0
                    ? r.departments.join(" · ")
                    : "Untagged"}
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
          <li className="py-16 text-center">
            <p className="text-sm italic text-ink/55">
              {coursePackMode && courseParam
                ? `No markets tagged for ${courseParam}.`
                : "No markets match this filter."}
            </p>
            <p className="caption mt-2">
              {coursePackMode && courseParam
                ? "Try another course code, or switch to the department filter."
                : q || dept !== "ALL"
                  ? "Try a different department or a broader search term."
                  : "The library may be loading, or the backend may be cold-starting (~30s on free tier)."}
            </p>
            {(q || dept !== "ALL" || (coursePackMode && courseParam)) && (
              <button
                onClick={() => {
                  setQ("");
                  setDept("ALL");
                  clearCourse();
                }}
                className="mt-4 font-mono text-xs font-medium uppercase
                  tracking-wider text-brand-600 hover:text-brand-700
                  hover:underline underline-offset-4"
              >
                Reset filters
              </button>
            )}
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
