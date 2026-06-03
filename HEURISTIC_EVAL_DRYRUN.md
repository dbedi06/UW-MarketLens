# Heuristic Evaluation — Dry-Run Pre-Flight Notes

> Read before running the `HEURISTIC_EVAL.md` protocol. I traced
> each of the five scripted tasks through the live deploy + code
> on 2026-06-02 to flag any task that would waste reviewer time.
> One catastrophic finding plus a few small things to know.

## Severity-4 blocker — RESOLVED in this same session

> Fixed in the same session that flagged it. Task 1 now uses the
> verified-real `world-cup-winner` slug and the underlying mock
> library was reseeded with five verified-real Polymarket events
> across UW departments. The original placeholder slugs came from
> the project's pre-Live-mode era — fine as mock data, became a
> problem when Live-mode affordances assumed real events. Notes
> below preserved as a record of what got caught and fixed.

### Original finding — Task 1's sample URL didn't resolve on Polymarket

The protocol's Task 1 instruction reads:

> *"A colleague sent you this Polymarket URL:
> `https://polymarket.com/event/will-the-fed-cut-rates-in-2025`."*

That market **does not exist** on Polymarket. Probed via the
production API on 2026-06-02:

```
POST https://marketlens-api.onrender.com/api/live/score
{"url":"https://polymarket.com/event/will-the-fed-cut-rates-in-2025"}

→ HTTP 404
  "This market doesn't appear to exist on Polymarket.
   (No Gamma event found for slug: 'will-the-fed-cut-rates-in-2025')"
```

Every reviewer would 404 immediately. This also cascades:

- **HomePage's `SAMPLE` constant** at
  `frontend/src/pages/HomePage.tsx:6` is the same broken URL. The
  "Open sample report →" button fails the same way.
- **Mock library** still references the slug. Reviewers in Task 3
  who click "Will the fed cut rates in 2025?" from the
  POLS270-filtered list also 404.
- **Tasks 2, 4, 5** all assume "the same market" from Task 1, so
  they cascade-fail too.

### Recommended replacement: `world-cup-winner`

Probed on the same deploy, 2026-06-02:

```
POST https://marketlens-api.onrender.com/api/live/score
{"url":"https://polymarket.com/event/world-cup-winner"}

→ HTTP 200
  question:  "Will France win the 2026 FIFA World Cup?"
  score:     81 HIGH
  source:    live
  verdict:   UNVERIFIABLE  (future market, expected — composite drops
                            the resolution leg and reweights to ~47/53)
  model_used: deepseek/deepseek-v4-pro
  snapshot:  /snapshot/f37b7cb5e630
```

This is a stable real market, scored end-to-end with a real LLM
verdict surfaced, with a snapshot permalink that resolves. Good
demonstration target for all five tasks.

**Action before reviewers start:**

1. Update the protocol's Task 1 URL to
   `https://polymarket.com/event/world-cup-winner` (single edit
   in `HEURISTIC_EVAL.md` line 41).
2. Optionally also fix `HomePage.tsx`'s `SAMPLE` constant and
   `backend/app/mock.py`'s `_SAMPLE_URLS` so the broken
   `will-the-fed-cut-rates-in-2025` slug doesn't appear in the
   Library or as the default-typed URL on Home. That's a separate
   ~5 min cleanup, *not* part of the heuristic eval itself —
   reviewers can spot it as a finding instead.

## Tasks 2, 3, 4, 5 — no blockers, just notes

### Task 2 — Copy APA citation

**Works as described.** `CitationBox` ([frontend/src/components/CitationBox.tsx](frontend/src/components/CitationBox.tsx))
defaults to the APA tab; the "Copy" button is labeled exactly
"Copy"; clipboard receives `citation.apa`; a toast confirms.
Reviewers should complete in well under 30s.

**Minor note for reviewer awareness:** there's also a
"Download .ris" button next to Copy. Don't let reviewers get
confused — Task 2 specifies clipboard, so "Copy" is the
correct affordance.

### Task 3 — Find a market for POLS 270

**Works as described.** Verified via:

```
GET /api/library?course=POLS270 → 3 markets, all tagged POLS
```

The flow: Library page → click "Course-pack mode" tab → type
`POLS270` (autocomplete suggests known codes) → click "Apply" →
list filters to POLS-tagged markets. Backend `_filter_rows`
normalises whitespace, so `POLS 270` (with space) also works.

**Note:** "Course-pack mode" is a tab toggle, not a checkbox.
Reviewers used to settings-style UI might miss it on first
glance. That's exactly the kind of finding the heuristic eval is
designed to surface; don't pre-empt it — log it if it comes up.

### Task 4 — Share a snapshot permalink

**Works as described.** `SnapshotBar` ([frontend/src/components/SnapshotBar.tsx](frontend/src/components/SnapshotBar.tsx))
renders both compact (sticky sidebar) and full (inline)
variants. Both have a "Copy permalink" button that writes
`${origin}${permalink}` to clipboard with a toast confirmation.

**Note:** the compact form only says "Copy permalink" without
showing the URL; reviewers in the sidebar context can't
preview the link before copying. Possible severity-1 or -2
finding to log.

### Task 5 — Understand why the score is what it is

**Works as described.** Two complementary surfaces:

- `WhyPanel` ([frontend/src/components/WhyPanel.tsx](frontend/src/components/WhyPanel.tsx))
  renders three reason cards (liquidity, anomaly, resolution)
  with severity-coloured left rail (red/amber/green) and a
  plain-language detail line each. The worst factor visually
  jumps out via the red rail.
- `SubscoreBars` quantifies each: numeric value out of 100, bar
  width proportional, colour matched.

For the World Cup market specifically, reviewers should be able
to say "Resolution is N/A because the market hasn't resolved yet
— composite reweights liquidity + anomaly" or similar. The N/A
framing is in the reason detail text; verify reviewers actually
read it rather than fixating on the literal 0/100.

## Recommended pre-eval checklist

Before each reviewer starts, the coordinator should:

1. ✅ Update `HEURISTIC_EVAL.md` Task 1 URL to
   `polymarket.com/event/world-cup-winner` (until Polymarket
   re-lists a Fed-rate market — could swap back at that point).
2. ✅ Confirm the live deploy is awake (Render free tier sleeps
   after 15 min idle). Hit any URL on the site first to wake the
   backend; otherwise reviewer Task-1 cold-start time-on-task
   reads as "30s clicking around" not "1s of UI confusion."
3. ✅ Confirm OpenRouter is still returning a verdict — if
   `resolution.model_used` comes back empty, the heuristic eval
   surfaces an LLM outage as a Task-5 finding when it shouldn't.

## Optional separate cleanup task

If anyone has 5 minutes, replace `will-the-fed-cut-rates-in-2025`
in:

- `frontend/src/pages/HomePage.tsx:6` — `SAMPLE` constant + the
  default `useState(SAMPLE)` placeholder. Suggested replacement:
  the same World Cup URL.
- `backend/app/mock.py:_SAMPLE_URLS` — the broken slug pollutes
  the mock library, which then pollutes the Featured carousel
  and POLS270 results.

That's *not* a heuristic-eval task — it's a "fix a stale fixture"
task. Doing it before the eval makes Task 3 cleaner; doing it
after is fine too.
