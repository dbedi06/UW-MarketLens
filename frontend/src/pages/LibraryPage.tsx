import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LibraryEntry } from "../types";
import { getLibrary } from "../api";

const DEPTS = ["ALL", "POLS", "ECON", "INFO", "EVANS"];
const bandColor: Record<string, string> = {
  HIGH: "#2f8a4e",
  MEDIUM: "#b9770e",
  LOW: "#b91c1c",
};

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
    <div>
      <h2 className="page-title">UW Market Library</h2>
      <p className="question">
        Markets tagged to UW departments by the LLM tagger (mock). Find a
        citable market for your course, then open it for the full reliability
        report.
      </p>

      <div className="lookup">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search market questions…"
        />
      </div>

      <div className="chips">
        {DEPTS.map((d) => (
          <button
            key={d}
            className={d === dept ? "chip-btn active" : "chip-btn"}
            onClick={() => setDept(d)}
          >
            {d}
          </button>
        ))}
      </div>

      {err && <p className="error">Library failed to load: {err}</p>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Market</th>
              <th
                className="sortable"
                onClick={() => setSortDesc((s) => !s)}
                title="Click to toggle sort"
              >
                Score {sortDesc ? "▼" : "▲"}
              </th>
              <th>Departments</th>
              <th>Verified</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr
                key={r.market_url}
                className="row-click"
                onClick={() =>
                  nav(`/market?url=${encodeURIComponent(r.market_url)}`)
                }
              >
                <td>{r.market_question}</td>
                <td>
                  <span
                    className="pill"
                    style={{ background: bandColor[r.band] }}
                  >
                    {r.reliability_score}
                  </span>
                </td>
                <td>{r.departments.join(", ")}</td>
                <td>{r.verified ? "✓" : "—"}</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-row">
                  No markets match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
