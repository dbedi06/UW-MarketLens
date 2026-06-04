# UW MarketLens — Heuristic Evaluation

You're testing the site as a stand-in for a usability study. Each
reviewer runs the same 5 tasks, writes what they found, then we merge.

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

| Task | Done? | Time | Notes                                                                                                                                                                          |
| ---- | ----- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | Yes   | 3s   | Everything worked well, it didn't take much time to load for me.                                                                                                               |
| 2    | Yes   | 0s   | Copying happened immediately and flawlessly.                                                                                                                                   |
| 3    | Yes   | 7s   | Easy to do + didn't have any load time.                                                                                                                                        |
| 4    | Yes   | 0s   | Just had to click a button, smooth.                                                                                                                                            |
| 5    | Yes   | 0s   | The liquidity is deep enough that prices reflect broad consensus. 7 of 44 time windows were flagged as unusual by the anomaly model. No resolution since market is still open. |

### Reviewer B — Leo

| Task | Done? | Time          | Notes                                                                 |
| :--: | :---: | :------------ | :-------------------------------------------------------------------- |
|  1   |  Yes  | ~60s          | Score and band clear once loaded; first request was slow (dyno wake). |
|  2   |  Yes  | immediate     | APA tab is the default, "Copy" button obvious.                        |
|  3   |  Yes  | 5s + 20s load | Course-pack mode easy to find; market load felt a touch slow.         |
|  4   |  Yes  | immediate     | "Copy permalink" button right where expected.                         |
|  5   |  Yes  | immediate     | Reasons panel reads clearly; subscore bars make the driver obvious.   |

### Consolidated headline

n=2 reviewers. All 5 tasks completed by both, no blockers.

## After everyone's done

One person pastes the headline into AboutPage's evaluation row.
Suggested format:

> _"Heuristic evaluation, n=2 reviewers, 5 tasks. X tasks completed
> by all reviewers. Y issues surfaced (Z fixed before submission).
> No reviewer was unable to complete a task."_

Replace X / Y / Z with whatever your merged findings actually say.
That's it.
