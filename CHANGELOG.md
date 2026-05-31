# Changelog

Notable changes per tagged release. Newest first. Tags created
retroactively from the commits where each section landed; the project
shipped iteratively, not in a single big bang.

## v0.7-rubric-pass — 2026-05-30

Closes the named gaps from `PISAN-Suggest.md` that were within reach
without a labelling effort. Estimated rubric movement: 62/85 → 73/85.

- **Track 1 — UI polish.** Proper 404 page, "Open sample report"
  button on home, friendlier empty-state copy on Library and Admin
  with a "Reset filters" affordance.
- **Track 2 — Resolution evidence panel.** S4 now propagates the
  NewsAPI snippets Claude saw alongside the verdict so a reader can
  audit what evidence the LLM weighed.
- **Track 3 — UW community workflows.** CSV download of the library
  (`/api/library.csv`), Zotero/RIS citation export, course-pack mode
  (`/library?course=POLS270`) mapping ~12 UW course codes to
  departments.
- **Track 4 — SHAP per-window explanation.** The dormant Explainer
  is now wired into the composite. Live route response includes
  `anomaly.top_contributions` with the top features for the most-
  flagged window.
- **Track 5 — Milestones honesty.** AboutPage evaluation table no
  longer shows "pending" everywhere; rows reflect what's been
  measured vs what's genuinely pending real labels.
- **Track 6 — Technical polish.** `Makefile` at root for one-command
  test / build / install / smoke. `mock.py` docstring header rewritten
  to reflect current Live-default architecture.

## v0.6-onchain — 2026-05-30

On-chain enrichment recovers trade counterparty signal that the Data
API doesn't expose. `OrderFilled` events on Polymarket's CTF + NegRisk
Exchange contracts are read via Polygon RPC, joined back to Data API
trades by `transactionHash`, and `RawTrade.taker_address` is
backfilled. Both env flags required: `MARKETLENS_POLYMARKET_LIVE=1`
and `MARKETLENS_POLYGON_LIVE=1`. Default public RPC prunes old blocks
(documented); `MARKETLENS_POLYGON_RPC_URL` overrides to an archive
node. 12 new tests (177 total).

## v0.5-data-api-fix — 2026-05-30

Production `/api/live/score` had been returning 502 on every real
Polymarket URL for two weeks. Root cause: `clob.polymarket.com/trades`
requires Level 2 (EIP-712-signed) auth per Polymarket's `llms.txt`
docs and the `py-clob-client` SDK source. Switched trade fetching to
`data-api.polymarket.com/trades` (public, no auth), with the
honestly-documented loss of counterparty signal that Track 6's
on-chain enrichment then partially recovers. 165 tests passing.

## v0.4-composite-wired — 2026-05-30

The live route was a 280-line inline scorer that hardcoded
`["ECON"]` tags and called `mock.make_citation`, leaving S5/S6/S7 as
dead code. This release made `routes/live.py` a thin wrapper around
`composite.make_market_score`, lighting up the real tagger, real
citation generator, and real 35/40/25 weighting end-to-end. Tagging
rubric moved out of the prompt string into a committed
`backend/app/data/tagging_rubric.md`. GitHub Actions workflow added.
Frontend `package.json` pins fixed (`typescript ~5.6.3`,
`vite ^5.4.11`).

## v0.3-s4-s5-s6-s7 — 2026-05-26 (teammate work)

S4 LLM resolution checker (Claude + NewsAPI), S5 course tagger
(Claude few-shot), S6 real citation generator (APA + MLA + BibTeX),
S7 composite score with weighted aggregation. All four modules
shipped as standalone files; integration into the live route came in
v0.4.

## v0.2-bug-fix-pass — 2026-05-26

Five P0 fixes on the live scoring path:

- B1: anomaly subscore stopped collapsing to ~50 for every market —
  swapped within-market min/max normalization for a percentile lookup
  against a held-out clean reference distribution.
- B2: live-route snapshot permalinks now resolve to live data
  (`mock._SNAPSHOTS` carries source; snapshot route dispatches).
- B3: `_liquidity_score` no longer crashes on NaN spread / volume.
- B4: `ttr_days` clipped to training range `[1, 180]` so resolved
  markets stop scoring anomalous purely on the ttr axis.
- B5: NaN network features impute to training-set medians (not zero),
  preventing markets without wallet data from being scored as sybil
  rings.

Plus B6 (banner persists on error), B7 (detector pre-fits on boot),
B8 (`source` field on MarketScore + corner badge), B9 (require >=4
windows for relative-feature baseline).

## v0.1-phase-a — 2026-05-26

Phase A push from honest 2/10 toward 4.5/10 ceiling: network features
(trader-graph: HHI, repeat-counterparty, LCC) wired end-to-end via
`from_trades_with_network`; synthetic streams now emit plausible
network feature columns; `sybil_ring` injection pattern; labeled-
cases YAML + rubric v1; `eval_on_labeled.py` with bootstrap CI;
percentile calibration; live route + Mock-toggle in frontend; honest
write-up in `MODEL_STATUS.md` and `UW_MarketLens_Push_To_Six.html`.

## v0.0-scaffold — Earlier May 2026

Initial scaffolding: FastAPI backend with deterministic mock
(`app/mock.py`), React + Vite + Tailwind frontend with all seven
pages (Home, Market detail, Compare, Library, Admin, About,
Snapshot), Pydantic schemas in lockstep with TypeScript types,
Render Blueprint deployment, dark theme, S1 Polymarket ingestion
module skeleton from Lewi.
