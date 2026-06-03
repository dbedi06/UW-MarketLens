# UW MarketLens — Remaining Work

> Everything left to take the codebase from "5.5/10 honest, AUC
> pending" to "submission-ready, AUC published." Excludes
> presentation, demo, slides, write-up, and in-class work — those are
> deliverables the team handles separately. This document is only
> the code + data + docs that need to land in the repo.

> **2026-06-02 note:** A separate audit during the Track 4 dry-run
> caught that `backend/app/mock.py:_SAMPLE_URLS` (the mock library
> seed) held illustrative placeholder slugs from the project's
> mock-only era. The Featured carousel, course-pack workflow, CSV
> export, "Open sample report" button, ComparePage defaults, and
> HEURISTIC_EVAL Task 1 — all of which landed after Live mode and
> assume real Polymarket events — were 404'ing in Live mode as a
> result. Reseeded with five verified-real events across UW
> departments + added `backend/scripts/refresh_library_seed.py` so
> the seed can be re-curated cleanly when markets resolve out.
> Distinct from Track 1's labeled-cases problem (that one was
> real fabrication of verification data).

## Estimated total

**~8 hours of focused work, parallelisable across three teammates
to ~3.5 hours wall-clock.** Single calendar day if everyone's
online together.

The biggest lever is the labeled set: ~2.5 hours of careful review
unlocks the headline ROC-AUC number, the S4 verdict-agreement
metric, and the confidence-calibration chart all at once. Without
it the honest rating stays parked at 5.5/10. Front-load it.

---

## Track 1 — Clean up the labeled set (the 6/10 gate)

> The current `backend/app/anomaly/data/labeled_cases.yaml` has 10
> fabricated rows: 9 of the 10 Polymarket URLs return *"No Gamma
> event found"* (the slugs are invented), and the notes contain
> measurements that can't exist (e.g. *"10+ wallets from same IP
> subnet"* — Polymarket exposes no IP data). Push_To_Six explicitly
> says the labeled file is *"empty pending team verification under
> rubric v1"* — that contract was broken. Reset and redo honestly.

### Step 1 — Reset (15 min, one person)

- Delete every row from `backend/app/anomaly/data/labeled_cases.yaml`
  except the schema header. File ends at `cases: []`.
- Commit message should explicitly say *"fabricated rows removed,
  pending real verification under rubric v1"* so the history shows
  the reset was deliberate.

### Step 2 — Seed real candidates (15 min, one person)

- Export `NEWS_API_KEY` and `MARKETLENS_POLYMARKET_LIVE=1`.
- `python -m scripts.discover_labeled_candidates --dry-run` first
  to preview the candidate pool without writing.
- If the preview looks sensible, re-run without `--dry-run` to
  append ~30 unverified candidates tagged `LK-candidate-v2` to the
  yaml. Each candidate row carries `evidence_url`,
  `slug_inferred`, and the NewsAPI snippet that surfaced it.

### Step 3 — Three-way verification under rubric v1 (~2 hours team-wall, parallelisable)

Three reviewers, ~7 candidates primaried each, plus a 4-case
overlap pool everyone codes independently for Cohen's κ
inter-rater agreement (PISAN line 92 — "thin validation"
critique). Per candidate:

1. **Open the Polymarket URL in a browser.** Confirm the market
   actually exists. If the slug returns 404, the candidate is
   invalid — mark `rejected: slug-404` and move on. Do not invent.
2. **Read the evidence article.** For `controversial` candidates,
   does the article actually describe manipulation, anomalous
   trading, or a documented dispute? For `mundane` candidates, can
   you confirm absence of controversy (no news hits searching the
   market's question + keywords like "manipulation" / "dispute" /
   "wash trade")?
3. **Apply rubric v1** (see
   `backend/app/anomaly/data/labeling_rubric.md`): does the
   evidence meet the rubric's criteria for the assigned label, or
   not?
4. **Write the verified row** with honest notes. Reference the
   article URL. Do not include claims that can only be measured by
   running the detector (e.g. anomaly subscores) — the eval will
   produce those.

Target: **≥20 verified rows** with at least 5 of each class to
preserve balance. Anything below that and `eval_on_labeled.py`
will emit `low_n_warning: true` on the result.

### Step 4 — Compute κ + run the eval (~45 min, one person)

- For the 4-case overlap pool, compute pairwise Cohen's κ across
  the three reviewers. Even a single κ value materially answers
  PISAN's "report agreement with CI" critique.
- `python -m scripts.eval_on_labeled --scorer app.anomaly.scoring:score_market_url`
- Output lands in `backend/app/anomaly/last_labeled_eval.json`
  with ROC-AUC + bootstrap CI. Read the actual number.
- Paste the AUC + κ into the AboutPage evaluation table row,
  replacing *"pending — labeling protocol drafted"*. Be honest
  with the CI width — a wide CI on n=20 is the truth.

---

## Track 2 — Code items PISAN-Suggest.md explicitly named

> PISAN's two named UI items that haven't shipped. Both are small
> and visible — high signal-to-effort for the project-web-presence
> rubric.

### "Live / Mock" indicator on every page (~30 min)

PISAN line 75 verbatim: *"Add a small 'Live | Mock' indicator on
every page (not just nav). Right now `MarketScore.source` is in
the schema but a casual user can't easily tell whether the report
they're looking at is real or mock."*

- `MarketScore.source` already exists in the schema; no backend
  work required.
- Add a small badge component (top-right corner of `PageShell` or
  inside `NavBar`) that reads the source from the current report
  context. Green pill for Live, amber for Mock.
- On pages without a report (Library, About, etc.), the badge
  should reflect the global Mock-toggle state from NavBar, not
  per-report state.

### Featured UW-relevant markets carousel on Home (~1 hour)

PISAN line 76 verbatim: *"The home page only shows recent lookups
from `localStorage`; add a 'Featured UW-relevant markets' carousel
sourced from the library so a first-time visitor can click into a
real example without having to find a Polymarket URL."*

- Backend: no work — the library endpoint already surfaces the
  data and the course-pack filter (S5 tags + `uw_courses.json`)
  already does the relevance mapping.
- Frontend: add a `FeaturedMarkets` component on HomePage that
  fetches `/api/library?course=POLS270` (or rotates through 3-4
  UW department slugs) and renders the top 3-5 with thumbnail
  card + question + band pill. Each card links to
  `/market?url=...`.

---

## Track 3 — Confidence calibration (PISAN line 94, depends on labels)

> PISAN: *"Add a confidence calibration check: do high-confidence
> verdicts actually correlate with verified resolutions? With the
> labeled corpus this is a 30-line script and a chart in the About
> page."*

Blocked until Track 1 finishes (no labels = nothing to correlate
against). Once labels exist:

- New script: `backend/scripts/calibration_report.py`. For every
  labeled case, run `resolve_market(case.question)` (the S4 path),
  collect `(confidence, verdict)`, compare verdict to the human
  label. Bin confidences into 5 buckets (0–0.2, 0.2–0.4, ...).
  For each bucket, compute accuracy = (verdicts matching label) /
  bucket size. Write to JSON.
- Frontend: small bar chart on AboutPage under the evaluation
  table — x-axis confidence bucket, y-axis accuracy, with the
  diagonal "perfectly calibrated" reference line. ~2 hours
  including the small component.
- Honest framing: with n=20 labels, the per-bucket counts will be
  tiny (3-5 each). Call it a *calibration sanity check, not a
  reliability diagram* in the prose.

---

## Track 4 — Heuristic Evaluation execution (S11, ~2 hours)

> Protocol already exists in `HEURISTIC_EVAL.md`. Three reviewers,
> five scripted tasks, ~30 min each on the live deploy, plus 30 min
> consolidation.

- Each reviewer independently runs the 5 tasks on
  `marketlens-web.onrender.com` with a timer, fills in their
  worksheet block in `HEURISTIC_EVAL.md`.
- After all three are done, merge findings into the consolidated
  table. Duplicates (issues found by multiple reviewers) get
  highest severity rating.
- Paste the headline result (e.g. *"3 severity-2 issues, 0
  severity-3+, all resolved before submission"*) into AboutPage's
  Usability row, replacing *"pending — protocol in
  HEURISTIC_EVAL.md"*.

---

## Track 5 — Operational housekeeping

### Rotate the leaked OpenRouter key (~5 min — STILL PENDING, user action)

The current OpenRouter key appeared in a screenshot earlier in
development and is in the conversation transcript. Rotate it on
OpenRouter, paste the new key into the Render dashboard for
`marketlens-api`, trigger a manual redeploy.

**Step-by-step:**

1. OpenRouter dashboard → Keys → "Create new key" → name it (e.g.
   `marketlens-prod-v2`) → copy the new `sk-or-v1-...` value.
2. Render dashboard → `marketlens-api` service → Environment →
   edit `OPENROUTER_API_KEY` → paste new value → Save Changes.
3. Render will auto-redeploy. Wait ~2 min for the build.
4. Verify: `curl -X POST https://marketlens-api.onrender.com/api/live/score
   -H "Content-Type: application/json"
   -d '{"url":"https://polymarket.com/event/world-cup-winner"}'`
   — response should still contain
   `"model_used": "deepseek/deepseek-v4-pro"`.
5. Back in OpenRouter dashboard → Keys → delete the old leaked
   key. Both keys are valid during rotation; deleting the old one
   invalidates the leaked credential.

### Standardise git identities (~5 min — DONE in v0.9.1 via .mailmap)

PISAN line 67: *"The shared email `bob452305@gmail.com` across
`Rogagoja`, `rogagoja`, and `Leonikot` GitHub authors will confuse
`git shortlog`. Standardize on one identity per teammate."*

Addressed by committing `.mailmap` at repo root. `git shortlog
-sne --all` now reports:

- `46  Rogagoja <rogagoja@gmail.com>` (collapses bob452305 +
  Leonikot + lowercase rogagoja + dbedi06-misattribution-with-
  bob into one identity)
- `12  dbedi06 <dilshanbedi@gmail.com>` (Dilshan's actual commits)
- `5   Lewi <lewiale@uw.edu>` (UW academic identity, unifies his
  two emails)
- `1   Yusuf Pisan <pisan@uw.edu>` (professor, unchanged)

No history rewrite; works for any future viewer of the repo with
no per-developer setup. Going forward, anyone making commits
should still set their own `git config user.email` correctly so
`.mailmap` doesn't have to grow.

### Verify the deepinfra provider switch took effect (~5 min — DONE 2026-06-02)

The Render env var `OPENROUTER_PROVIDER=deepinfra` is verified
live. Probed `POST /api/live/score` on `world-cup-winner` and got:

```
model_used: 'deepseek/deepseek-v4-pro'
model_was_fallback: False
```

Provider pin + key + fallback routing all healthy.

---

## Track 6 — Documentation refresh after the AUC lands

> All of these touch files that explicitly cite the 5.5/10 rating
> or claim labels are pending. Once the real AUC exists they need
> to reflect it honestly. ~45 minutes total.

- **`UW_MarketLens_Push_To_Six.html`** — the Phase B section
  literally describes the labeled-eval AUC as the gating item.
  Add the published number with bootstrap CI.
- **`backend/app/anomaly/MODEL_STATUS.md`** — honest rating
  refresh. If the real AUC came in above 0.65, rating moves to
  6/10. If below, rating stays at 5.5/10 with the new measurement
  as evidence; do not adjust the rating up to flatter the number.
- **`UW_MarketLens_Implementation_Plan.html`** — Section F PISAN
  table flips a few more rows from "Outstanding" / "Blocked" to
  "Addressed." Bottom-callout rating updates to match
  MODEL_STATUS.
- **`CHANGELOG.md`** — single entry for the labeled-eval landing,
  the heuristic eval, the calibration chart, the two PISAN UI
  items. One commit per logical bundle, not one mega-commit.

---

## What's NOT on this list

Intentional exclusions, to be clear about scope:

- **Email / Slack band-change alerts** (PISAN line 85) — needs
  user-account state the project doesn't model. Out of scope.
- **External SUS testing with non-team users** — replaced by the
  Heuristic Evaluation per the genre-of-research discussion
  (HEURISTIC_EVAL.md).
- **Polymarket-equivalent of a CFTC fine ledger** — doesn't exist
  publicly; documented as a real-system gap in the Implementation
  Plan Section E.
- **Order-book / depth-history features** — Polymarket's public
  CLOB doesn't expose the granularity required; same Section E.
- **Time-cross-validation on real data** — needs months of cached
  trade history we don't have on free tier.

---

## Ready-to-ship definition

Code-side, the project is **submission-ready** when:

1. `labeled_cases.yaml` has ≥20 honest rows, no fabricated entries
2. `last_labeled_eval.json` carries a real AUC with bootstrap CI
3. AboutPage evaluation table has measured values in every row
   that isn't structurally out of scope
4. Heuristic Eval findings consolidated and the headline lands on
   AboutPage
5. Live/Mock indicator visible on every page
6. Featured markets carousel renders on Home
7. Confidence calibration chart renders on About
8. OpenRouter key rotated; deepinfra provider verified live
9. Git identities deduplicated
10. Push_To_Six / MODEL_STATUS / Implementation Plan / CHANGELOG
    all reflect the real AUC

Everything above this line is what the codebase needs. Demo
preparation, slides, the written report, peer review, and the
in-class presentation are not in this document — they're the
team's deliverables.
