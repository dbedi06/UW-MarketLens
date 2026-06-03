# Changelog

Notable changes per tagged release. Newest first. Tags created
retroactively from the commits where each section landed; the project
shipped iteratively, not in a single big bang.

## v0.9.1-mock-library-real — 2026-06-02

Cleanup of a timing artifact from the project's mock-only origin.
`backend/app/mock.py:_SAMPLE_URLS` was authored before Live mode
existed, when every code path on the site produced deterministic
mock data and the URLs were illustrative placeholders. When Live
mode shipped (`/api/live/score`) and later affordances were added
(`FeaturedMarkets` carousel, course-pack workflow, CSV export,
HomePage "Open sample report" button, ComparePage defaults,
HEURISTIC_EVAL Task 1), they all assumed real Polymarket events
under the hood. The seed never got swapped over, so each of those
affordances 404'd in Live mode against the legacy placeholders.
Caught during the Track 4 heuristic-eval dry-run.

Two paths to fix: (a) replace the placeholders with verified-real
Polymarket events so both modes work, or (b) hide the Live-mode
affordances when the underlying URLs aren't real. Picked (a) —
the Featured carousel + course-pack workflow are the UW Community
Impact narrative; they should demonstrate real markets, not the
mock testbed.

- Replaced `_SAMPLE_URLS` with five verified-real events probed
  end-to-end against `/api/live/score` on 2026-06-02:
  `fed-decision-in-june-825` (ECON, 70 HIGH),
  `us-x-iran-permanent-peace-deal-by` (POLS, 50 MEDIUM),
  `us-enacts-ai-safety-bill-before-2027` (INFO+EVANS, 42 MEDIUM),
  `world-cup-winner` (multi-outcome, picks France favourite at ~17%,
  81 HIGH), and
  `which-company-has-best-ai-model-end-of-june` (INFO, 61 MEDIUM).
- **PISAN line 14 fix.** Mock-mode library tagging switched from
  random-hash (`depts = [_DEPARTMENTS[seed % 4]]`) to keyword-based
  via `tagger._fallback(question)` — the same code path the live
  tagger falls back to when the OpenRouter key is unavailable.
  Side benefit: keyword lists extended with current-events
  coverage (POLS: iran/israel/russia/ukraine/china/trump/putin/
  mayor/governor/prime minister; EVANS: bill/enacts/law/ban/court/
  ruling), which also improves Live-mode no-key degradation for
  arbitrary URLs. Determinism contract preserved: same (url,
  as_of) → same question text → same depts.
- New `backend/scripts/refresh_library_seed.py` queries Gamma for
  the current top-volume active events, classifies each title via
  keyword fallback (mirrors `tagger.py:_fallback`), and emits a
  paste-ready `_SAMPLE_URLS` block. Maintenance tool so the seed
  doesn't go stale silently — next person re-runs the script when
  markets resolve out.
- Frontend `SAMPLE` constants updated in lockstep:
  `HomePage.tsx` → World Cup;
  `ComparePage.tsx` → Fed Decision vs World Cup.
- `HEURISTIC_EVAL.md` Task 1 sample URL updated.
- Test fixtures (`tests/fixtures/polymarket/gamma_event_fed_rates.json`,
  `tests/test_ingestion.py`) intentionally still reference the old
  fabricated slug — those are pure URL-parsing assertions against a
  mocked Gamma response and never hit real Polymarket. The slug name
  is a fixture identifier; the test contract is "given this URL
  shape, parse it correctly," not "this URL exists."

211 tests still passing. No semver bump because the public API
didn't change; this is a data-quality fix.

## v0.9-real-trained — 2026-05-31

The S3 anomaly detector no longer trains on synthetic-only data. A
54-market real Polymarket corpus is fitted into a committed
`trained_model.pkl` (~1.3 MB). The reference distribution used for
percentile-converting raw scores now reflects real-market score
ranges (-0.123 .. 0.262) instead of the synthetic -0.055 .. 0.066.
Real markets now produce subscores that genuinely vary based on
what the model thinks of them, not collapsed to ~50 by a
mis-calibrated reference.

- New `scripts/build_real_corpus.py` fetches top-N resolved Polymarket
  events via Gamma + Data API + (optional) Polygon enrichment, saves
  each as a JSON snapshot under `app/anomaly/data/corpus/`. Resumable
  (skips condition_ids already on disk). Filters thin markets
  (`--min-trades 50` by default).
- New `app/anomaly/scoring.py:train_from_corpus()` loads every JSON
  in the corpus, runs each through `from_trades_with_network`,
  concatenates the per-market feature blocks, fits the IsoForest,
  computes the per-market top-K reference distribution + per-column
  network medians (used for NaN imputation at scoring time), and
  pickles the result.
- New `scripts/train_from_corpus.py` runs the above and saves to
  `app/anomaly/data/trained_model.pkl`.
- `get_detector()` now resolves: in-process cache → pickle on disk →
  synthetic fallback. Attaches `_trained_on` so callers can disclose
  whether a score came from the real or synthetic path.
- New `scripts/discover_labeled_candidates.py` is ready for the team
  to run once `NEWS_API_KEY` is available: queries NewsAPI for
  manipulation/controversy reporting, extracts referenced Polymarket
  URLs (with a fuzzy slug-fallback when no URL is in the article),
  pairs with mundane corpus samples, and appends `LK-candidate-v2`
  rows to `labeled_cases.yaml` for team verification under rubric v1.
- 6 new tests in `test_corpus_training.py` (JSON round-trip, trainer
  produces calibrated detector, pickle round-trip, get_detector
  resolution order). 211 total passing.
- MODEL_STATUS.md updated: rating moves from 4.5/10 → ~5.5/10. Full
  6/10 still gated on the team-verified labeled set + the actual
  ROC-AUC number that comes out of running eval_on_labeled against
  it. Documented in Push_To_Six.html.
- AboutPage evaluation table now lists the real-trained corpus row
  honestly; labeled-eval AUC remains "pending" since labels still
  need team curation.

Honest note: the real-trained model gives scores that visibly differ
from synthetic (delta ~0.05 on the fed-rates market in local
smoke), but until labels exist we cannot say "this lift is in the
right direction." That measurement is the next push.

## v0.8.1-llm-reliability — 2026-05-31

Three additions on top of v0.8 to harden the OpenRouter integration
for production use of expensive-via-wrong-provider models like
DeepSeek V4 Pro:

- **Provider pinning.** New `OPENROUTER_PROVIDER` env var (comma-
  separated allowlist). When set, requests carry
  `provider: {order: [...], allow_fallbacks: false}` so OpenRouter
  never silently routes to a more expensive provider (DeepSeek V4
  Pro is ~$0.44/M via the `deepseek` provider but ~5x via
  Fireworks). Critical for cost control.
- **Retry + automatic model fallback.** Primary model is tried up
  to 3 times with brief backoff (transient errors clear). If all
  retries fail, one shot at `OPENROUTER_FALLBACK_MODEL` (default
  `google/gemini-flash-1.5-8b`), provider pin removed for the
  fallback request so it has a clean path even when the pinned
  provider is down.
- **Surface which model produced each verdict.** `call_chat` returns
  an `LlmResponse(content, model, used_fallback)` instead of a bare
  string. `ResolutionAssessment` + `TagResult` carry the model name
  and a `model_was_fallback` flag. Plumbed through the schema and
  the frontend — the resolution evidence panel shows
  `model: deepseek/deepseek-v4-pro`, or `(fallback)` in amber when
  the secondary fired.

7 new tests in `test_llm_client.py`. Suite at 205 passing.

## v0.8-openrouter — 2026-05-31

Cost fix: every `/api/live/score` request fires two LLM calls (S4
resolution + S5 tagger). Claude direct-API costs were not sustainable
for a class demo. Swapped both call sites to OpenRouter — an
OpenAI-compatible gateway routing to hundreds of models, including
free-tier ones. Default model is now `meta-llama/llama-3.3-70b-instruct:free`
(no card on file). Team can override via `OPENROUTER_MODEL` env var
to any model in the OpenRouter catalog, including Claude itself
(`anthropic/claude-3.5-sonnet`) for anyone with existing credit.

- New `backend/app/llm_client.py` is the single place that talks to
  OpenRouter. Bearer-auth, OpenAI-format messages, optional
  `response_format: {"type": "json_object"}` for JSON-mode-aware
  models, OpenRouter analytics headers (`HTTP-Referer`, `X-Title`).
- `resolution.py` and `tagger.py` are now thin wrappers around
  `llm_client.call_chat`. The fallback paths (UNVERIFIABLE / keyword
  tags) are unchanged — graceful degradation when the key is unset
  or the call fails.
- Env var renamed: `ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY`.
  Tests retargeted accordingly. The `render.yaml` declares
  `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `NEWS_API_KEY` as
  `sync: false` so the team pastes them once in the dashboard.
- 9 new tests in `test_llm_client.py`. Suite at 198 passing.

Honest caveats documented in README + `MODEL_STATUS.md`: free-tier
models can rate-limit during peak hours; output quality is plausibly
lower than Claude Sonnet for the LLM-as-judge case; OpenRouter
sees our prompts (their privacy policy applies).

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
