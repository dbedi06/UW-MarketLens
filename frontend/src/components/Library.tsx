// Table of UW-relevant markets from GET /api/library.

import { useEffect, useState } from "react";
import type { LibraryEntry } from "../types";
import { getLibrary } from "../api";

const bandColor: Record<string, string> = {
  HIGH: "#2f8a4e",
  MEDIUM: "#b9770e",
  LOW: "#b91c1c",
};

export default function Library() {
  const [rows, setRows] = useState<LibraryEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getLibrary().then(setRows).catch((e) => setErr(e.message));
  }, []);

  if (err) return <p className="error">Library failed to load: {err}</p>;

  return (
    <div className="card">
      <h2>UW Market Library</h2>
      <p className="question">Auto-populated sample (real list comes from the S5 tagger).</p>
      <table>
        <thead>
          <tr>
            <th>Market</th>
            <th>Score</th>
            <th>Departments</th>
            <th>Verified</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.market_url}>
              <td>{r.market_question}</td>
              <td>
                <span className="pill" style={{ background: bandColor[r.band] }}>
                  {r.reliability_score}
                </span>
              </td>
              <td>{r.departments.join(", ")}</td>
              <td>{r.verified ? "✓" : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
