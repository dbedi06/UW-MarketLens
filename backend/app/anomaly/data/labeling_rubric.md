# UW MarketLens — Labeled Cases Rubric (pre-registered)

**Status:** locked v1 (2026-05-19). Changes require a new vN file + a
note in `labeled_cases.yaml` recording which version each row was
labeled against. Pre-registration is a Section D commitment: the rubric
exists before the labels are produced so we can't tune the definitions
to flatter a model.

## Scope

The labeled set is a small (target n=20–40), explicitly imperfect
**sanity check** of the anomaly detector against publicly-documented
Polymarket markets. It does **not** claim to be a representative or
exhaustive ground truth. Section D / Section E document this honestly.

## Labels

Each row carries exactly one of:

- `controversial` — the market is publicly known to have had a
  reliability problem (manipulation accusations, suspicious trading
  flagged in reporting, resolution disputes, sybil-trader incidents,
  inducement/wash-trade discussions). Must have at least one
  publicly-linkable piece of evidence (news article, X/Twitter thread
  from a credible account, Polymarket community post, regulator
  statement, governance vote).
- `mundane` — the market resolved without public controversy:
  reasonable participation, no manipulation discussion surfaced in a
  best-effort search, resolution uncontested.
- (No third "ambiguous" label. Anything we cannot confidently put in
  either bucket is **excluded**, not parked in a middle category. We
  prefer a smaller clean set to a larger noisy one.)

## Inclusion criteria

A market is eligible if:

1. It is **resolved** (so we have a complete trade history and an
   outcome). Open markets are excluded — the score they produce is on a
   moving target.
2. It has enough activity to be analyzable: ≥ ~200 USDC notional
   traded across ≥ ~20 unique wallets over the market's lifetime. Below
   that, baseline metrics are too noisy.
3. It is **single-outcome** (binary or scalar resolution). Avoid
   multi-leg markets in this first pass to keep the eval surface clean.

## Evidence standards (for `controversial`)

The `evidence_url` field must point to at least one of:

- Reporting in established outlets (Bloomberg, FT, WSJ, The Block,
  Decrypt, Reuters, Coindesk).
- A Polymarket governance post or moderator statement.
- An X/Twitter post from an account with ≥ 5k followers that surfaces
  specific on-chain or trade-pattern evidence (not just opinion).
- A Polymarket community Discord/forum thread with multiple
  participants substantively discussing manipulation.

Opinion pieces, single-tweet allegations without evidence, and
reaction memes do **not** qualify.

## Disagreement and escalation

When two labelers disagree:

1. Each labeler logs their rationale in `notes`.
2. A third labeler reviews independently without seeing the first
   two's rationales.
3. Majority wins. If 3 disagree, the row is **dropped**, not labeled.

Per-row labeler identity is recorded in `labeler` so Cohen's κ between
any pair can be computed honestly.

## Anti-patterns (do not label)

- "I think this market looked weird" — needs the evidence URL.
- "The price moved a lot" — price movement alone is not controversy.
- "Whales were involved" — whale presence is not manipulation.
- Markets where the controversy was about the *resolution* (S4's job),
  not the *trading* (S3's job). Resolution disputes belong on the LLM
  resolution checker eval set, not here.

## Class balance

Aim for roughly equal numbers of `controversial` and `mundane` cases.
Better to have 15+15 than 30+0; class imbalance distorts every metric.

## What this gets us (honest framing)

- A real, even if small, signal that S3 outputs correlate with the
  human notion of "this market looked off."
- Numbers reported with Wilson 95% CIs and explicit n.
- A baseline for Cohen's κ when ≥ 2 labelers cover the same rows.

What this does **not** get us:

- Statistical significance at n < 30.
- A guarantee the detector generalizes to unlabeled markets.
- Anything close to regulatory-grade validation.
