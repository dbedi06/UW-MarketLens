// Proposal §2.3 — the human-in-the-loop view. Shows what the LLM tagger
// suggested and lets a team member approve it or override the departments
// with one click. Demonstrates the AI doing ongoing work + human oversight.

import { useEffect, useState } from "react";
import type { PendingTag } from "../types";
import { getPendingTags, verifyTag } from "../api";

const ALL_DEPTS = ["POLS", "ECON", "INFO", "EVANS"];

export default function AdminPage() {
  const [tags, setTags] = useState<PendingTag[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<string[]>([]);

  useEffect(() => {
    getPendingTags().then(setTags).catch((e) => setErr(e.message));
  }, []);

  function replace(updated: PendingTag) {
    setTags((ts) => ts.map((t) => (t.market_url === updated.market_url ? updated : t)));
  }

  async function approve(t: PendingTag) {
    replace({ ...t, verified: true }); // optimistic
    try {
      replace(await verifyTag(t.market_url, "approve"));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Verify failed");
    }
  }

  async function saveOverride(t: PendingTag) {
    setEditing(null);
    replace({ ...t, verified: true, suggested_departments: draft });
    try {
      replace(await verifyTag(t.market_url, "override", draft));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Override failed");
    }
  }

  return (
    <div>
      <h2 className="page-title">Tag verification</h2>
      <p className="question">
        The LLM tagger (S5) proposes UW department tags for newly ingested
        markets. Approve a suggestion as-is, or override the departments. This
        is the curation step from proposal §2.3.
      </p>
      {err && <p className="error">{err}</p>}

      {tags.map((t) => (
        <div className="card admin-row" key={t.market_url}>
          <div className="admin-main">
            <div className="admin-q">{t.market_question}</div>
            <div className="admin-meta">
              {editing === t.market_url ? (
                <div className="chips">
                  {ALL_DEPTS.map((d) => {
                    const on = draft.includes(d);
                    return (
                      <button
                        key={d}
                        className={on ? "chip-btn active" : "chip-btn"}
                        onClick={() =>
                          setDraft((ds) =>
                            on ? ds.filter((x) => x !== d) : [...ds, d],
                          )
                        }
                      >
                        {d}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <>
                  {t.suggested_departments.map((d) => (
                    <span className="chip" key={d}>{d}</span>
                  ))}
                  <span className="chip">applicability {t.course_applicability}</span>
                </>
              )}
            </div>
          </div>
          <div className="admin-actions">
            {t.verified && editing !== t.market_url ? (
              <span className="flag ok">Verified ✓</span>
            ) : editing === t.market_url ? (
              <>
                <button className="copy-btn" onClick={() => saveOverride(t)}>
                  Save
                </button>
                <button className="chip-btn" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button className="copy-btn" onClick={() => approve(t)}>
                  Approve
                </button>
                <button
                  className="chip-btn"
                  onClick={() => {
                    setEditing(t.market_url);
                    setDraft(t.suggested_departments);
                  }}
                >
                  Override
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
