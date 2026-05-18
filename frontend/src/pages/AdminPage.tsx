// Proposal §2.3 — the human-in-the-loop view. Approve an LLM tag suggestion
// as-is, or override the departments. Demonstrates AI + human oversight.

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { PendingTag } from "../types";
import { getPendingTags, verifyTag } from "../api";
import PageShell from "../ui/PageShell";
import SectionHeading from "../ui/SectionHeading";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import { fadeUp, stagger } from "../lib/motion";
import { toast } from "../ui/Toast";

const ALL_DEPTS = ["POLS", "ECON", "INFO", "EVANS"];

export default function AdminPage() {
  const [tags, setTags] = useState<PendingTag[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<string[]>([]);

  useEffect(() => {
    getPendingTags().then(setTags).catch((e) => setErr(e.message));
  }, []);

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
                        className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                          on
                            ? "bg-brand-600 text-white"
                            : "bg-slate-100 text-slate-500"
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
                <Badge tone="gold">Verified ✓</Badge>
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
