# UW Course Tagger — Rubric (committed)

**Status:** v1, locked 2026-05-30. Loaded at import time by
`app/tagger.py` and substituted into the Claude few-shot prompt.

Edit this file rather than the prompt string in `tagger.py`. Changes
take effect on the next process restart (or on first call if the
detector singleton hasn't been touched).

## Departments

Use the **code**, not the label:

| Code | Department | Scope |
|------|------------|-------|
| `POLS`  | Political Science | elections, policy, geopolitics, legislation |
| `ECON`  | Economics | interest rates, GDP, inflation, trade, markets |
| `INFO`  | Information School | tech companies, AI, social media, data |
| `EVANS` | Evans School of Public Policy | public policy, government spending, regulation |

A question may belong to **zero, one, or two** departments. Most
questions are best tagged with one or two; three is rarely
appropriate; four is almost never.

## Course-applicability score

`course_applicability` is a 0–100 integer answering: *how useful is
this market as a classroom example or research data point?*

| Band | Interpretation |
|------|----------------|
| **90–100** | Textbook example of the field, rich data, clear outcome |
| **70–89**  | Relevant and usable, minor caveats |
| **40–69**  | Tangentially related or low data quality |
| **0–39**   | Not useful for coursework |

## Rules

1. Return only departments that **genuinely apply**. Don't pad.
2. If no department applies (pop-culture, sports, entertainment),
   return an empty list and a score below 40.
3. A market about a *single company* leans toward the company's
   primary domain (e.g., OpenAI → `INFO`; ExxonMobil regulatory
   action → `EVANS`).
4. A market that crosses domains gets multiple tags. Example: "Will
   the Fed cut rates before July?" → `ECON` (the rate decision) +
   `EVANS` (the Fed as a public-policy actor).
5. Geopolitical markets (war, treaty, NATO) get `POLS`. Add `EVANS`
   only if there's a clear US-government-policy angle.
6. AI-capability markets ("Will GPT-5 release in 2024?") get `INFO`.
   Add `ECON` only if the market is specifically about market
   reception (price, adoption, share).
7. Sports outcomes default to `[]` unless the market is about a
   policy decision affecting sport (e.g., college NIL regulation).
8. Resolution should be **factually verifiable** to score above 70.
   Vague or subjective resolutions cap the score in the 40–69 band.
9. Markets with very low expected activity (obscure outcomes,
   short windows) cap below 70 regardless of department fit.

## Few-shot examples

These four examples are sent to Claude as the in-context training
set. Order matters — keep them in the order below.

| Question | Tags | Score |
|----------|------|-------|
| Will the Federal Reserve cut interest rates before July 2025? | `ECON`, `EVANS` | 92 |
| Will Donald Trump win the 2024 US presidential election? | `POLS`, `EVANS` | 88 |
| Will GPT-5 be released before the end of 2024? | `INFO` | 74 |
| Will Lionel Messi score in the Champions League final? | `[]` | 12 |

## Versioning

Bump the version header (and add a `## Changelog` entry) when:

- Changing the department set
- Re-balancing the score bands
- Replacing or reordering the few-shot examples

Backward-compatibility for committed evaluation runs depends on
tagging rubric stability. Old runs against v1 must remain
reproducible.
