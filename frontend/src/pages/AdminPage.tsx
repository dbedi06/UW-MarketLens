// Proposal §2.3 — the human-in-the-loop view. Approve an LLM tag suggestion
// as-is, or override the departments. Demonstrates AI + human oversight.

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "react-router-dom";
import type { PendingTag } from "../types";
import {
  ApiError,
  getAdminToken,
  getPendingTags,
  setAdminToken,
  verifyTag,
} from "../api";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import { fadeUp, stagger } from "../lib/motion";
import { toast } from "../ui/Toast";

const ALL_DEPTS = ["POLS", "ECON", "INFO", "EVANS"];

export default function AdminPage() {
  const [params, setParams] = useSearchParams();
  const [tags, setTags] = useState<PendingTag[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const [pwInput, setPwInput] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<string[]>([]);

  function load() {
    setErr(null);
    getPendingTags()
      .then((ts) => {
        setTags(ts);
        setLocked(false);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          setLocked(true);
        } else {
          setErr(e instanceof Error ? e.message : "Failed to load");
        }
      });
  }

  // Capture ?key= from the address (secret-in-the-URL), persist it,
  // and strip it from the bar so it isn't left lying in history.
  useEffect(() => {
    const key = params.get("key");
    if (key) {
      setAdminToken(key);
      params.delete("key");
      setParams(params, { replace: true });
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function unlock() {
    setAdminToken(pwInput.trim());
    setPwInput("");
    load();
  }

  function replace(u: PendingTag) {
    setTags((ts) => ts.map((t) => (t.market_url === u.market_url ? u : t)));
  }

  async function approve(t: PendingTag) {
    replace({ ...t, verified: true });
    try {
      replace(await verifyTag(t.market_url, "approve"));
      toast("Tag approved");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Verify failed");
    }
  }

  async function saveOverride(t: PendingTag) {
    setEditing(null);
    replace({ ...t, verified: true, suggested_departments: draft });
    try {
      replace(await verifyTag(t.market_url, "override", draft));
      toast("Tag overridden");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Override failed");
    }
  }

  return (
    <PageShell wide>
      <motion.div variants={fadeUp}>
        <SectionHeading
          eyebrow="Curation"
          title="Tag verification"
          sub="The LLM tagger (S5) proposes UW department tags. Approve as-is, or override. (Proposal §2.3.)"
        />
      </motion.div>
      {err && <p className="text-sm text-bad">{err}</p>}

      {locked && (
        <div className="card mx-auto mt-4 max-w-md p-6 text-center">
          <p className="font-medium text-ink">This area is restricted</p>
          <p className="caption mt-1">
            Enter the admin token to review tags.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              type="password"
              value={pwInput}
              onChange={(e) => setPwInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && unlock()}
              placeholder="Admin token"
              className="field flex-1 font-mono text-[13px]"
              autoFocus
            />
            <Button onClick={unlock}>Unlock</Button>
          </div>
          {getAdminToken() && (
            <p className="caption mt-3 text-bad">
              That token was rejected. Try again.
            </p>
          )}
        </div>
      )}

      {!locked && tags.length === 0 && !err && (
        <div className="card p-10 text-center">
          <p className="text-sm italic text-ink/55">
            No tags are pending review right now.
          </p>
          <p className="caption mt-2">
            The S5 LLM tagger emits suggestions as new markets are scored.
            Score a market on the home page, then return here to verify the
            tags it produced.
          </p>
        </div>
      )}

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="space-y-3"
      >
        {tags.map((t) => (
          <motion.div
            key={t.market_url}
            variants={fadeUp}
            className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <div className="font-medium text-ink">{t.market_question}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {editing === t.market_url ? (
                  ALL_DEPTS.map((d) => {
                    const on = draft.includes(d);
                    return (
                      <button
                        key={d}
                        onClick={() =>
                          setDraft((ds) =>
                            on ? ds.filter((x) => x !== d) : [...ds, d],
                          )
                        }
                        className={`rounded-sm border px-2.5 py-1 font-mono
                          text-[11px] uppercase tracking-wide transition-colors ${
                          on
                            ? "border-brand-600 text-brand-700"
                            : "border-line text-ink/40 hover:text-ink"
                        }`}
                      >
                        {d}
                      </button>
                    );
                  })
                ) : (
                  <>
                    {t.suggested_departments.map((d) => (
                      <Badge key={d} tone="brand">{d}</Badge>
                    ))}
                    <Badge tone="neutral">
                      applicability {t.course_applicability}
                    </Badge>
                  </>
                )}
              </div>
            </div>
            <div className="flex flex-shrink-0 gap-2">
              {t.verified && editing !== t.market_url ? (
                <Badge tone="gold">Verified</Badge>
              ) : editing === t.market_url ? (
                <>
                  <Button onClick={() => saveOverride(t)}>Save</Button>
                  <Button variant="ghost" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                </>
              ) : (
                <>
                  <Button onClick={() => approve(t)}>Approve</Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setEditing(t.market_url);
                      setDraft(t.suggested_departments);
                    }}
                  >
                    Override
                  </Button>
                </>
              )}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </PageShell>
  );
}
