# UW MarketLens — Backend (PLACEHOLDER)

FastAPI backend returning **deterministic mock data**. All fake data lives in
`app/mock.py` — that is the single file replaced when real sections (S1–S7) land.

## Run

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Allow /api/live/score to fetch from Polymarket on cache miss.
# Without this, the live route returns 503 for any URL it hasn't seen.
$env:MARKETLENS_POLYMARKET_LIVE = "1"

uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API.

On Render, `MARKETLENS_POLYMARKET_LIVE=1` is set declaratively in
`render.yaml` for `marketlens-api`. Cached responses live under
`app/ingestion/cache/` and are reused across requests; the directory
is gitkept but its contents are not tracked, so each environment
warms its own cache from real Polymarket calls.

## S4 + S5 LLM calls (resolution + tagger)

Both LLM calls go through **OpenRouter** — an OpenAI-compatible API
gateway that routes to hundreds of models, including free-tier ones.
We switched off Anthropic's direct API because Claude is too
expensive for a class demo where every `/api/live/score` request
fires two LLM calls.

Set these env vars to enable the live S4 + S5 paths:

```powershell
$env:NEWS_API_KEY = "<your-newsapi-key>"
$env:OPENROUTER_API_KEY = "<your-openrouter-key>"
# Optional — override the model. Default is the free Llama 3.3 70B:
$env:OPENROUTER_MODEL = "google/gemini-flash-1.5-8b"   # pennies / 1M tokens
```

If `OPENROUTER_API_KEY` is missing, both S4 (resolution) and S5
(tagger) fall back gracefully — `/api/live/score` still responds
cleanly with `verdict=UNVERIFIABLE` and rule-based keyword tags
instead of failing the request. If `NEWS_API_KEY` is missing, S4
falls back regardless of the OpenRouter key (no evidence to weigh).

Default model: `meta-llama/llama-3.3-70b-instruct:free`. Free-tier
models can hit rate limits during peak hours; if that becomes a
problem in production, point `OPENROUTER_MODEL` at a paid pennies-
per-call model. Anyone with existing Anthropic credit can also use
Claude models through OpenRouter (`anthropic/claude-3.5-sonnet`).

Browse the catalog: <https://openrouter.ai/models>.

## Endpoints

| Method | Path              | Body                               | Returns                                    |
| ------ | ----------------- | ---------------------------------- | ------------------------------------------ |
| GET    | `/health`         | —                                  | liveness                                   |
| POST   | `/api/score`      | `{ "url": "..." }`                 | `MarketScore` (mock)                       |
| POST   | `/api/live/score` | `{ "url": "..." }`                 | `MarketScore` (real Polymarket → S1→S2→S3) |
| GET    | `/api/library`    | —                                  | `LibraryEntry[]`                           |
| POST   | `/api/citation`   | `{ "url": "...", "style": "APA" }` | `Citation`                                 |

The frontend defaults to Live and exposes a Mock toggle in the nav.
`/api/live/score` returns 503 on cache miss when
`MARKETLENS_POLYMARKET_LIVE` is unset, and 422 when the market has
fewer than 3 windows of trade history.

Schemas in `app/schemas.py` are **placeholders** — finalized in S0.

## Labeled evaluation (S3 sanity check)

The anomaly detector has a pre-registered labeled-cases set under
`app/anomaly/data/labeled_cases.yaml` (rubric v1). See
`app/anomaly/MODEL_STATUS.md` for the current honest rating and
`app/anomaly/data/CANDIDATES.md` for the team-review workflow.

To run the end-to-end labeled eval:

```powershell
# 1) warm the ingestion cache (one time, live fetch)
$env:MARKETLENS_POLYMARKET_LIVE = "1"
python -m scripts.seed_labeled_cache

# 2) score every case with the shared detector
python -m scripts.eval_on_labeled --scorer app.anomaly.scoring:score_market_url
```

Output lands in `app/anomaly/last_labeled_eval.json`. The script
flags `low_n_warning: true` while the case set is below 20 entries;
treat the ROC-AUC as directional, not headline, until that flag is
clear.
