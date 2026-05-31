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

# Optional — override the model. Default is meta-llama/llama-3.3-70b-instruct:free.
$env:OPENROUTER_MODEL = "deepseek/deepseek-v4-pro"   # ~$0.44/M in, $0.87/M out

# When using a model where a specific provider is way cheaper than
# OpenRouter's fallback providers (DeepSeek V4 Pro: $0.44/M via the
# `deepseek` provider, ~5x via Fireworks), pin the provider so the
# request never silently routes to the expensive one.
$env:OPENROUTER_PROVIDER = "deepseek"

# Optional — when the primary model + retries all fail, the client
# falls back to this. Default is google/gemini-flash-1.5-8b (cheap,
# reliable, served by Google directly). Set to "" to disable fallback.
$env:OPENROUTER_FALLBACK_MODEL = "google/gemini-flash-1.5-8b"
```

**Reliability behavior:**

- Primary model is tried up to 3 times with brief backoff for
  transient errors (5xx, "no instances available", network blips).
- If all primary attempts fail, one shot at the fallback model
  (provider pin removed for the fallback — different provider space).
- If both fail, the caller catches the error and degrades to
  rule-based fallback tags or `UNVERIFIABLE` resolution.
- The frontend surfaces which model produced each verdict via a
  small "model: deepseek/deepseek-v4-pro" badge next to the resolution
  verdict; if the fallback fired, it says "(fallback)" in amber.

**Cost notes:**

- `meta-llama/llama-3.3-70b-instruct:free` — $0, free tier (default)
- `google/gemini-flash-1.5-8b` — ~$0.16 / 1000 requests
- `deepseek/deepseek-v4-pro` (pin to `deepseek`) — ~$1.04 / 1000 requests
- `openai/gpt-4o-mini` — ~$0.60 / 1000 requests
- `anthropic/claude-3.5-sonnet` — ~$13 / 1000 requests (reference)

If `OPENROUTER_API_KEY` is missing, both S4 (resolution) and S5
(tagger) fall back gracefully — `/api/live/score` still responds
cleanly with `verdict=UNVERIFIABLE` and rule-based keyword tags
instead of failing the request. If `NEWS_API_KEY` is missing, S4
falls back regardless of the OpenRouter key (no evidence to weigh).

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
