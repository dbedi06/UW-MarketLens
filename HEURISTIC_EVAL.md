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
| 1    |    61    | Yes |       Cold-start blank screen (~14s) with no spinner; tab title never updates to market name | H1, H4 |
| 2    | 28       | Yes |       No in-UI confirmation that copy succeeded after clicking Copy APA Citation             | H1 |
| 3    | 198      | Yes |       Browse section not signposted from results; filter label disappears on input; no course tag on result cards                                                     | H6, H1, H3 |
| 4    | 112      | Yes |       Snapshot URL is behind primary share button; snapshot vs permalink terminology mismatch 
                                           | H6, H2 |
| 5 | 49          | Yes |       Subscores in fixed order not sorted by value; requires scanning to find worst subscore
                                           | H8 |

### Reviewer C — Rogagoja

| Task | Time (s) | Completed? | Notes | Heuristic(s) |
| ---- | -------- | ---------- | ----- | ------------ |
| 1 |   |   |   |   |
| 2 |   |   |   |   |
| 3 |   |   |   |   |
| 4 |   |   |   |   |
| 5 |   |   |   |   |

## Consolidated findings

After all three reviewers finish, merge findings here. One row per
distinct issue. **Severity** = highest reviewer-rating; **N
reviewers** = how many found it (this is the meaningful number,
not a SUS score).

| Issue | Where | Severity | N reviewers | Heuristic | Proposed fix |
| ----- | ----- | -------- | ----------- | --------- | ------------ |
|       |       |          |             |           |              |

## Headline result (for AboutPage)

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
