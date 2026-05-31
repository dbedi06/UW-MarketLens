# UW MarketLens

AI-Powered Prediction Market Reliability Platform — DYOP project.

**Live demo:** https://marketlens-web.onrender.com  
**API:** https://marketlens-api.onrender.com — see `/docs` for the interactive schema, `/health` for liveness.

> **Free-tier note.** Both services sleep after 15 minutes of inactivity;
> the first request after a sleep takes ~30–60 seconds to wake the dyno.
> Subsequent requests are fast.

> **Status: real pipeline live.** Frontend defaults to **Live** mode,
> which runs the full chain — S1 Polymarket ingestion → S2 features →
> S3 Isolation Forest → S4 LLM resolution checker → S5 LLM course
> tagger → S6 citation → S7 weighted composite (35% liquidity / 40%
> anomaly / 25% resolution). The deterministic mock at
> `backend/app/mock.py` is still available behind a Mock toggle in the
> nav. See `UW_MarketLens_Implementation_Plan.html` for the section
> breakdown and `backend/app/anomaly/MODEL_STATUS.md` for the honest
> ML rating (currently ~4.5/10, with the upgrade path in
> `UW_MarketLens_Push_To_Six.html`).

## Run locally (two terminals)

**Terminal 1 — backend (http://localhost:8000):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend (http://localhost:5173):**

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Multi-page app: **Home** (lookup) → **Market
detail** (plain-language "why", anomaly chart with the flagged window shaded,
subscores, market facts, copy-able APA/MLA/BibTeX citation, and a dated
**snapshot permalink** that always re-renders the identical report) →
**Library** (search + department filters) → **Admin** (approve/override LLM
tags) → **About** (architecture + methodology). Interactive API docs:
http://localhost:8000/docs

For live scoring, load `backend/.env` and set `MARKETLENS_POLYMARKET_LIVE=1`
before starting the backend. See `backend/README.md` for full live env setup.

You can also use the included `Makefile`:

```bash
make backend-dev
make frontend-dev
make test
```

## Layout

| Path                          | What                                                                                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/schemas.py`      | Pydantic contract (S0)                                                                                                                 |
| `backend/app/ingestion/`      | S1 Polymarket adapter (Gamma + CLOB, on-disk cache)                                                                                    |
| `backend/app/anomaly/`        | S2 features + S3 Isolation Forest + labeled-eval                                                                                       |
| `backend/app/resolution.py`   | S4 LLM resolution checker (OpenRouter + NewsAPI)                                                                                       |
| `backend/app/tagger.py`       | S5 course tagger (OpenRouter few-shot + `data/tagging_rubric.md`)                                                                      |
| `backend/app/citation_gen.py` | S6 pure-function APA/MLA/BibTeX generator                                                                                              |
| `backend/app/composite.py`    | S7 weighted composite — the live `make_market_score`                                                                                   |
| `backend/app/mock.py`         | Deterministic mock — still backs `/api/score` and `/api/citation`                                                                      |
| `backend/app/routes/`         | Thin handlers — `/api/score`, `/api/live/score`, `/api/library`, `/api/citation`, `/api/snapshot/{id}`, `/api/admin/*`, `/api/og/{id}` |
| `frontend/src/types.ts`       | TS mirror of the schema                                                                                                                |
| `frontend/src/api.ts`         | Backend URL lives here only                                                                                                            |
| `frontend/src/components/`    | MarketReport, AnomalyChart, SubscoreBars, CitationBox, etc.                                                                            |
