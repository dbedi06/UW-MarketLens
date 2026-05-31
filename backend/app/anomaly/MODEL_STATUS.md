# S3 Anomaly Model — Status

A direct snapshot of what the model is, what just changed, and what's
still gating the next half-point on the honest 0-10 rating. No
marketing; if a number is uncertain, this doc says so.

## v0.9 update — trained on real data

**The detector is no longer synthetic-only.** A corpus of 54 resolved
Polymarket markets (~4000 windowed feature rows) lives at
`app/anomaly/data/corpus/` and the IsoForest is now fitted on that
real distribution instead of the hand-picked `Beta(2,8)` synthetic
streams. The fitted model is committed at
`app/anomaly/data/trained_model.pkl` (~1.3 MB); `get_detector()` loads
it on import in <1 s. The synthetic fallback path remains for cases
where the pickle is absent (CI workers without the artifact,
contributors who haven't run the corpus builder).

The reference distribution used for percentile-converting raw
detector scores now reflects real-market score ranges
(`-0.123 .. 0.262` empirically) instead of the synthetic `-0.055 ..
0.066`. Markets that are genuinely high-volatility now score
differently from the trained baseline — a behavioral lift the
synthetic model didn't have.

**Still missing for the full Push-to-Six story:** a verified labeled
set. `labeled_cases.yaml` remains empty pending team curation under
rubric v1. The script `scripts/discover_labeled_candidates.py` is
ready to seed candidates from NewsAPI for team review whenever
someone runs it with `NEWS_API_KEY` set.

## What the model is today

- **Detector**: a single `IsolationForest` (and a `BaggedIsoForest`
  alternative kept for ablations) wrapped in `RobustScaler`. Trained
  on the **real-market corpus** (54 markets, ~4000 windows) when the
  pickle is on disk; falls back to synthetic streams otherwise. The
  live API route and the labeled-eval scorer share the same fitted
  detector via `app.anomaly.scoring.get_detector()`.

- **Features** (column order in `FULL_FEATURE_NAMES_WITH_NETWORK`):
  - **Base (5)**: volume, bid_ask_spread, unique_traders,
    price_volatility, time_to_resolution.
  - **Engineered (4)**: log_volume, vol_per_trader, spread_x_vol,
    traders_per_logvol.
  - **Microstructure (2)**: amihud_proxy, spread_per_logvol — the
    Phase A illiquidity-tightness pair.
  - **Per-market relative (4)**: trailing 20-window z-scores of
    volume, volatility, vol_per_trader, spread. Real surveillance
    systems compare each window to its own market's recent history;
    these are the synthetic analog.
  - **Network (4)**: net_unique_wallets, net_top_trader_hhi,
    net_repeat_counterparty, net_largest_component — built from
    maker/taker addresses on the trade tape.

- **Inputs**: per-window aggregates from `from_trades_with_network`
  for real markets; from `clean_streams_with_network` for synthetic
  training.

- **Evaluation**:
  - **Synthetic eval** (`scripts/eval_anomaly.py`): operating-point
    grid at {0.5%, 1%, 5%, 20%} FPR; Precision@{10, 50, 100};
    ROC-AUC + PR-AUC; Wilson 95% CIs per recall point, bootstrap
    95% CIs across seeds. Patterns: `volume_spike`,
    `coordinated_swing`, `wash_trade_pair`, `coordinated_manip`, and
    the new `sybil_ring` (network-feature lift case).
  - **Labeled eval** (`scripts/eval_on_labeled.py --scorer
    app.anomaly.scoring:score_market_url`): per-case score reduction
    is `mean(top-3 per-window scores)`; reports ROC-AUC with a
    percentile bootstrap CI (1000 iters) and a low-N warning when
    n_scored < 20.

## What changed in this push

- Trader-graph (network) features are now end-to-end:
  - synthetic stream generation emits plausible network feature
    columns per market (heterogeneous baselines);
  - a `sybil_ring` injection pattern perturbs only the network
    columns — the lift case for network-aware detection;
  - `from_trades_with_network` adds the network block at scoring
    time, computed over the same window boundaries as the base
    block;
  - the live route trains on and scores against the wider matrix;
  - the labeled-eval scorer uses the same detector.
- Labeled set seeded with 10 candidate cases (5 controversial / 5
  mundane), tagged `LK-candidate` for team review per `CANDIDATES.md`.
- `eval_on_labeled.py` emits a bootstrap CI on ROC-AUC and a
  `low_n_warning` flag.
- The live route's detector is now lazy-fit once per process via the
  shared singleton, instead of cached on FastAPI app state — same
  behavior, less code, no risk of two detectors disagreeing.

## Honest rating: ~5.5/10 (was 4.5 before v0.9)

A 6/10 framing was drafted earlier; on second look it overstated the
state. Three places it failed to be honest:

- The `sybil_ring` injector perturbs exactly the four network feature
  columns the new code added, leaving base features near-clean. Of
  course the network-aware model "wins" on it — the test is
  tautological by construction. The 0.472 → 0.906 AUC delta is real
  arithmetic on synthetic data the author designed; it is not
  evidence of detection skill on real sybil rings.
- The labeled-cases file was previously seeded with 10 entries whose
  evidence URLs were generated from intuition without verification.
  Those entries were removed; the file ships empty pending team
  verification against rubric v1.
- ~~The detector still trains on 100% synthetic data with hand-picked
  parameter distributions.~~ **Resolved in v0.9** — the detector now
  trains on a 54-market real corpus and the reference distribution
  is computed from it. The synthetic fallback only fires when the
  pickle is missing (CI, fresh contributor).
- **Labeled set still empty.** `labeled_cases.yaml` carries no
  verified rows. Without labels, no ROC-AUC can be computed against
  ground truth — the "did our model actually learn anomalies?"
  question remains open. `discover_labeled_candidates.py` exists to
  seed candidates from NewsAPI; the team has to review them under
  rubric v1 before any number gets quoted. This is the gating item
  for moving past 5.5/10.
- **Counterparty signal recovery (Polygon enrichment).** The Data API
  exposes only the trade initiator (`proxyWallet`). When
  `MARKETLENS_POLYGON_LIVE=1` is also set, `fetch_market` reads the
  Polymarket Exchange contracts' `OrderFilled` events directly from
  Polygon RPC and backfills `taker_address`, giving the network
  features both sides of every (matched) edge. Without the flag,
  trades pass through with `taker_address=""` and the graph stays
  one-sided. The default public RPC prunes historical blocks; for
  full coverage on older trades, set `MARKETLENS_POLYGON_RPC_URL`
  to an archive node (Alchemy/QuickNode free tier covers demo scale).
  See `app/ingestion/README.md` for setup.

What is genuinely real:

- The plumbing — network features through `from_trades_with_network`,
  shared detector singleton across the live route and labeled-eval
  scorer, bootstrap CI + `low_n_warning` in eval reporting. Code is
  correct and tested (198 tests pass).
- **LLM provider**: S4 and S5 now call OpenRouter (default model
  `meta-llama/llama-3.3-70b-instruct:free`) instead of Anthropic
  Claude directly. Cost change, not capability change — the model
  ceiling at ~4.5/10 is unchanged. Free-tier models can
  rate-limit during peak hours; the documented fallback paths
  (UNVERIFIABLE / keyword tags) handle this without crashing.
  See `backend/README.md` for env var setup and overriding the
  model choice.
- The synthetic capability check (operating-point grid, Precision@K,
  Wilson/bootstrap CIs) reports the *shape* of detector behavior
  honestly.
- The labeled-eval pipeline is wired and ready to consume a real
  case list and emit a real number. It just doesn't have one yet.

## What gates the next half-point

See `UW_MarketLens_Push_To_Six.html` (project root) for the full
breakdown. Status:

1. ~~Cached real-market corpus, ≥50 resolved markets, retrain the
   IsoForest on it.~~ **Done in v0.9** (54 markets, 3999 windows,
   pickle committed).
2. **Verified labeled set, N ≥ 20** under rubric v1 — team-produced,
   evidence URLs confirmed to resolve. Run
   `python -m scripts.discover_labeled_candidates` (needs
   `NEWS_API_KEY`) to seed candidates; team verifies before any
   number is quoted.
3. **Run the labeled eval and publish whatever AUC results.** The
   pipeline is in place; needs item #2 first.
4. **Non-circular injection patterns** for the synthetic eval — a
   `sybil_ring` variant that also perturbs base features moderately
   so the lift demo isn't tautological. Optional polish; doesn't
   move the labeled-eval number.

Once items 2 + 3 land we can responsibly claim 6/10 (or whatever the
labeled AUC says — we publish the real number).

## Pointers

- Module roadmap: this file.
- Rubric: `data/labeling_rubric.md` (v1, locked 2026-05-19).
- Candidate label notes: `data/CANDIDATES.md`.
- How to run the labeled eval: `backend/README.md` → "Labeled
  evaluation".
