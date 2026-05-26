# Labeling protocol — read before adding rows

The case file `labeled_cases.yaml` ships **empty** on purpose. An
earlier draft seeded 10 candidate rows with evidence URLs the author
had not verified resolve — that draft was removed because feeding
unverified entries into the labeled-eval script produces a number
that *looks* measured but isn't. The pipeline (loader, eval script,
shared scorer) is in place; only the data is pending.

## How to add a row (team workflow)

For each candidate market:

1. Open the Polymarket URL and confirm the market exists and is
   **resolved** (rubric inclusion criterion 1).
2. Confirm activity ≥ ~200 USDC across ≥ ~20 unique wallets across
   the market's lifetime (rubric criterion 2).
3. **For `controversial` entries**: produce a `evidence_url` that
   you have personally opened and that meets the rubric's evidence
   standards (established outlet, governance post, or credible on-
   chain trace — *not* opinion). Prefer an archive.org snapshot so
   the link stays stable. If you cannot find evidence that meets the
   standard, the market is **dropped**, not downgraded to `mundane`.
4. **For `mundane` entries**: best-effort search for manipulation
   discussion; if nothing surfaces, accept and add.
5. Record your initials in `labeler` so Cohen's κ can compute when a
   second labeler covers the same market.

## Target

Per rubric v1: 20–40 total entries, roughly balanced. Below ~20 the
labeled eval will set `low_n_warning: true` in
`last_labeled_eval.json` — that flag is the script's way of telling
you the ROC-AUC is directional, not headline-worthy.

## After adding rows

```powershell
# warm the ingestion cache against the new URLs (one time)
$env:MARKETLENS_POLYMARKET_LIVE = "1"
python -m scripts.seed_labeled_cache

# score every case with the shared detector
python -m scripts.eval_on_labeled --scorer app.anomaly.scoring:score_market_url
```

The output drops to `app/anomaly/last_labeled_eval.json`.
