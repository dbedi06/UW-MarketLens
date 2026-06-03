# UW MarketLens — Heuristic Evaluation

You're testing the site as a stand-in for a usability study. Three of
us each run the same 5 tasks, write what we found, then merge.

## How to do it

1. Open <https://marketlens-web.onrender.com> in a normal browser.
   First request takes ~30-60s (server sleeps when idle) — that's
   expected, not a finding.
2. Run the 5 tasks below. Don't peek at the other reviewers' notes
   until you're done.
3. Fill in your row in the table at the bottom. Be honest — "I
   couldn't figure out where to click for 20 seconds" is exactly
   the kind of thing this is for.

## The 5 tasks

**Task 1 — Score a market.** Open this URL:
<https://polymarket.com/event/world-cup-winner>. Use MarketLens to
score it. Read aloud the band (HIGH / MEDIUM / LOW) and the
overall score.

**Task 2 — Copy a citation.** Get the APA citation for that same
market onto your clipboard. Paste it into a notes doc to confirm
it worked.

**Task 3 — Find a market for a UW course.** Pretend you're teaching
POLS 270. Find a market in the library tagged for that course.

**Task 4 — Share a snapshot.** Get the snapshot permalink for the
World Cup market onto your clipboard so you could email it to a
colleague.

**Task 5 — Read the why.** Looking at the same World Cup report,
tell me in one sentence why the score is what it is — which
subscore is dragging it up or down?

## Already-known issues (just so you don't waste time logging them)

- Cold-start takes 30-60s on the first request after the server
  sleeps. README documents it.
- World Cup is a future market, so "Resolution quality" shows
  N/A by design.
- The library currently has 5 seed markets — small set, that's
  the demo state.
- The page title on the World Cup verdict card reads "resolution
  check not applicable drives most" — slightly confusing wording
  but technically true. Known minor copy bug.

## Your worksheet

For each task, fill in:
- Could you complete it? (Yes / No)
- Roughly how long? (eyeball, no need to be precise)
- Anything that confused or annoyed you? (free text)

### Reviewer A — Dilshan

| Task | Done? | Time | What was confusing or annoying |
| ---- | ----- | ---- | ------------------------------ |
| 1    |       |      |                                |
| 2    |       |      |                                |
| 3    |       |      |                                |
| 4    |       |      |                                |
| 5    |       |      |                                |

### Reviewer B — Lewi

| Task | Done? | Time | What was confusing or annoying |
| ---- | ----- | ---- | ------------------------------ |
| 1    |       |      |                                |
| 2    |       |      |                                |
| 3    |       |      |                                |
| 4    |       |      |                                |
| 5    |       |      |                                |

### Reviewer C — Leo

| Task | Done? | Time | What was confusing or annoying |
| ---- | ----- | ---- | ------------------------------ |
| 1    |       |      |                                |
| 2    |       |      |                                |
| 3    |       |      |                                |
| 4    |       |      |                                |
| 5    |       |      |                                |

## After everyone's done

One person pastes the headline into AboutPage's evaluation row.
Suggested format:

> *"Heuristic evaluation, n=3 reviewers, 5 tasks. X tasks completed
> by all reviewers. Y issues surfaced (Z fixed before submission).
> No reviewer was unable to complete a task."*

Replace X / Y / Z with whatever your merged findings actually say.
That's it.
