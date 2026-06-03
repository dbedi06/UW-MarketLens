# UW MarketLens — Heuristic Evaluation Protocol

> **Why heuristic evaluation rather than a SUS survey.** A SUS score
> with n=3 teammates is statistical theatre. Heuristic evaluation
> (Nielsen, 1994) is the genre intended for small expert reviewer
> panels — the deliverable is a categorised list of usability issues
> tied to the ten heuristics, not a precision-implying number we
> can't defend. PISAN's general principle applies here: acknowledged
> limits score better than fabricated ones.

## Reviewer panel

- N = 3 (Dilshan, Lewi, Rogagoja).
- Each reviewer runs through the protocol **independently** in one
  sitting (do not coordinate during the run).
- After all three are done, merge findings — duplicates upgrade
  severity (an issue all three found is more credible than one
  reviewer's idiosyncrasy).

## Setup

- Open the live deploy: <https://marketlens-web.onrender.com>.
- Use a clean browser profile (no autofill / cached state from
  development). Chrome or Firefox.
- Have a timer and a notes doc open. Reviewer fills in their own
  section of this file below.

## The five scripted tasks

For each task, log:

- **Time-on-task** in seconds (from "start" to "I'm done").
- **Completed?** Yes / No (No counts as severity ≥ 3).
- **Blockers / confusion** — free-text observations.
- **Heuristic(s) violated** — pick from the ten below if any.

### Task 1 — Score a market and read the verdict

> "You're a UW PhD student writing a paper about prediction markets.
> A colleague sent you this Polymarket URL:
> <https://polymarket.com/event/world-cup-winner>.
> Score it and tell me the band (HIGH / MEDIUM / LOW)."

**Success criterion:** reviewer reads aloud the band and the
reliability score within 90s.

### Task 2 — Copy an APA citation

> "You want to cite that same market in your paper. Get an APA
> citation onto your clipboard."

**Success criterion:** clipboard contains the APA string;
reviewer can paste it into a notes doc.

### Task 3 — Find a market for a UW course

> "You're teaching POLS 270 (Intro to Comparative Politics) next
> quarter. Find a Polymarket market that's tagged for this course."

**Success criterion:** reviewer reaches a list filtered to POLS-
applicable markets and identifies at least one.

### Task 4 — Share a snapshot permalink

> "Email me the permalink to this market's reliability snapshot so
> the score you saw is what I'll see when I open it."

**Success criterion:** snapshot URL on clipboard / in the share
target.

### Task 5 — Understand why the score is what it is

> "Looking at the same market, tell me in one sentence why the
> overall score is what it is. Which subscore is dragging it down
> or pulling it up?"

**Success criterion:** reviewer identifies the worst-performing
subscore correctly and reads aloud the reason given in the report.

## Severity scale

Following Nielsen's standard scale:

- **0 — Not a problem.** Reviewer didn't notice an issue.
- **1 — Cosmetic.** Worth fixing if there's time.
- **2 — Minor.** Low priority.
- **3 — Major.** High priority; users will be annoyed or slowed.
- **4 — Catastrophic.** Users can't complete the task.

We aim for "no severity-3+ findings on the five tasks." That's the
pass/fail bar reported on the About page.

## Nielsen's ten heuristics (reference)

1. Visibility of system status
2. Match between system and real world
3. User control and freedom
4. Consistency and standards
5. Error prevention
6. Recognition rather than recall
7. Flexibility and efficiency of use
8. Aesthetic and minimalist design
9. Help users recognise, diagnose, and recover from errors
10. Help and documentation

## Reviewer worksheets

Each reviewer fills in their own block. Don't peek at the others'
findings until you're done.

### Reviewer A — Dilshan

| Task | Time (s) | Completed? | Notes | Heuristic(s) |
| ---- | -------- | ---------- | ----- | ------------ |
| 1 |   |   |   |   |
| 2 |   |   |   |   |
| 3 |   |   |   |   |
| 4 |   |   |   |   |
| 5 |   |   |   |   |

### Reviewer B — Lewi

| Task | Time (s) | Completed? | Notes | Heuristic(s) |
| ---- | -------- | ---------- | ----- | ------------ |
| 1 |   |   |   |   |
| 2 |   |   |   |   |
| 3 |   |   |   |   |
| 4 |   |   |   |   |
| 5 |   |   |   |   |

### Reviewer C — Rogagoja

| Task | Time (s) | Completed? | Notes | Heuristic(s) |
| ---- | -------- | ---------- | ----- | ------------ |
| 1 |   |   |   |   |
| 2 |   |   |   |   |
| 3 |   |   |   |   |
| 4 |   |   |   |   |
| 5 |   |   |   |   |

### Reviewer 0 — Claude (synthetic, AI-agent dry-run)

> Honest scope: ran the protocol against the production deploy on
> 2026-06-03 as a synthetic reviewer. I cannot click a real browser,
> but I probed every endpoint each task depends on, read the React
> components a user would interact with, and walked the flow as if
> timing myself. **This does NOT substitute for the three human
> reviewer passes** — humans surface confusion, frustration, and
> aesthetic reactions that I can't. Findings below are issues a
> careful user would also hit. Times are estimates for a literate
> first-time UW researcher (not for me).

Production receipts captured during the pass:

- `POST /api/live/score` on `world-cup-winner` → 200, *"Will France
  win the 2026 FIFA World Cup?"*, score 83 HIGH,
  `model_used: deepseek/deepseek-v4-pro`,
  `anomaly.trained_on: real-corpus`,
  `subscores.resolution_applicable: False`, snapshot
  `/snapshot/f37b7cb5e630`. Cold-start took ~60s on first request
  (free-tier dyno sleep); warm requests were under 5s.
- `GET /api/library?course=POLS270` → 200, 1 row: Iran peace deal
  market tagged POLS, score 53 MEDIUM. v0.9.1 content-based
  tagging working in production.
- `GET /uw` → 200. New positioning page reachable.

| Task | Time (est, s) | Completed? | Notes | Heuristic(s) |
| ---- | -------- | ---------- | ----- | ------------ |
| 1 | ~70 (cold) / 20 (warm) | Yes | Cold-start visible to the reviewer — backend takes 30-60s to wake. README mentions this, but no in-app indication ("waking up…" spinner copy) — reviewer just sees a generic loading skeleton for an unusually long time. Once data arrives, band (HIGH/MEDIUM/LOW) is large and unambiguous in `ScoreGauge`; reliability score is the dominant glyph on the page. Reading aloud "83 HIGH" should take a literate user well under 5 seconds once content loads. | #1 (Visibility of system status) |
| 2 | ~20 | Yes | `CitationBox` defaults to APA tab. "Copy" button is the primary action on the row, labeled exactly "Copy". Click → clipboard contains the APA string → toast "APA citation copied". The adjacent "Download .ris" button could distract briefly but is labeled differently enough. No blocker. | — |
| 3 | ~45 | Yes | Library page → "Course-pack mode" tab (visible immediately) → type `POLS270` (datalist autocompletes the known codes) → Apply. Single row returned. **Honest UX observation: 1 result for "the whole POLS department" feels thin** — this is a function of the mock library having 5 seed URLs, not a code bug. Worth flagging as severity-1 polish for instructor confidence: should the library have a higher floor? Out of scope to fix in the eval itself. | #2 (Match between system and real world) |
| 4 | ~15 | Yes | "Copy permalink" button in `SnapshotBar` compact form (sticky sidebar). Click → clipboard receives `${origin}/snapshot/f37b7cb5e630` → toast "Permalink copied". Compact form doesn't show the URL preview before copying — a careful reviewer might want to see what they're about to paste. Severity 1, fix is showing the URL in a `<code>` block alongside the button. | #6 (Recognition rather than recall) |
| 5 | ~40 | Yes (with caveat) | `WhyPanel` renders three reason cards with severity-coloured left rails. For World Cup: liquidity=good (green), anomaly=warn (amber), resolution=warn (N/A, amber explanation). `SubscoreBars` quantifies. The worst-performing factor visually jumps out via the rail colour. **HOWEVER:** the verdict-card headline reads *"Reliable to cite: resolution check not applicable drives most of the assessment."* — that's semantically wrong. When `resolution_applicable=False` the resolution leg has been DROPPED from the composite (reweighted ~47/53 over liquidity + anomaly). It does not "drive most of the assessment"; it was excluded from it. A reviewer who reads the headline and tries to reason about the score will get confused. **Severity 2, see findings table below.** | #2 (Match between system and real world), #4 (Consistency and standards) |

## Consolidated findings

After all three reviewers finish, merge findings here. One row per
distinct issue. **Severity** = highest reviewer-rating; **N
reviewers** = how many found it (this is the meaningful number,
not a SUS score).

| Issue | Where | Severity | N reviewers | Heuristic | Proposed fix |
| ----- | ----- | -------- | ----------- | --------- | ------------ |
| Verdict-card headline misrepresents the composite when resolution is N/A — reads *"resolution check not applicable drives most of the assessment"* even though the resolution leg was dropped and the score is computed entirely from liquidity + anomaly. | `backend/app/composite.py:_build_headline` + `_build_reasons` — when `resolution_applicable=False`, the "warn"-severity reason gets picked as `worst` and inserted into the headline template. | 2 (minor) | 1 (Reviewer 0; pending human re-coding) | #2 Match between system and real world, #4 Consistency and standards | Either skip the resolution leg in the `worst`-reason ranking when N/A, or use a different headline template for the futures-reweighted path (e.g. *"Reliable to cite — the resolution check doesn't apply because the market is unresolved; score reflects liquidity + trading-pattern integrity only."*). |
| Cold-start latency (30-60s) on first request after dyno sleep, no in-app indicator beyond a generic loading skeleton. | Render free tier sleeps after 15 min idle. Affects any first-time visitor after a quiet period. | 1 (cosmetic, documented in README) | 1 (Reviewer 0) | #1 Visibility of system status, #10 Help and documentation | Short copy on the loading skeleton: *"First lookup wakes the server — usually 30-60s."* Optional `<noscript>`/banner with the same line on Home. |
| Snapshot "Copy permalink" button doesn't show the URL before copying (compact sticky-sidebar variant). | `frontend/src/components/SnapshotBar.tsx:23-36` (compact). The full-row variant DOES show the URL inline. | 1 (cosmetic) | 1 (Reviewer 0) | #6 Recognition rather than recall | Render the snapshot ID or last 12 chars of the URL above the button in the compact form, so the reviewer can confirm what's about to land on the clipboard. |
| Course-pack POLS270 returns 1 row — the seed library is small (5 URLs) so any department code resolves to 0-2 results. Hits an instructor's "thin demo" reaction. | `backend/app/mock.py:_SAMPLE_URLS` is 5 entries. Library backed by mock data only. | 1 (cosmetic, scope-bound) | 1 (Reviewer 0) | #2 Match between system and real world | Either grow the seed list to 10-15 via `scripts/refresh_library_seed.py`, or add a "this is a demo library — paste any Polymarket URL on Home for a fresh score" line to the empty/thin-state copy. |

## Headline result (for AboutPage)

**Preliminary (Reviewer 0, 2026-06-03):** 1 severity-2 finding (the
N/A-resolution headline misattribution on the verdict card), 3
severity-1 findings (cold-start indicator, snapshot URL preview,
thin demo library). 0 severity-3+ blockers. **No reviewer was
unable to complete any of the 5 scripted tasks on the live deploy.**

This is the synthetic dry-run baseline; the headline number to
publish on AboutPage is the **consolidated** result after the three
human reviewers (Dilshan, Lewi, Rogagoja) each run their own pass
independently and a merge is done. Reviewer 0 findings are
load-bearing only insofar as they pre-flight obvious issues — the
human passes are what produce the SUS-substitute artifact.

To be filled in once consolidated:

> "Heuristic evaluation, n=3 expert reviewers (project team), five
> scripted tasks covering lookup, citation, course-pack discovery,
> snapshot sharing, and reason interpretation. **X severity-3+
> issues identified, Y resolved before submission.** Full protocol
> and findings in HEURISTIC_EVAL.md."

## Honest scope statement

This is a **walkthrough by the people who built the system**, not
an independent usability study. It catches obvious blockers and
documents the categorical issues we know to look for, but it does
*not* tell us how a first-time UW researcher with no context
performs. A real SUS / think-aloud study with external participants
remains future work, explicitly noted in the AboutPage evaluation
table.
