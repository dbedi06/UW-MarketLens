# UW MarketLens

AI-Powered Prediction Market Reliability Platform — DYOP project.

> **Status: placeholder build.** Backend returns deterministic mock data
> (`backend/app/mock.py`). The real pipeline (S1 ingestion → S3 anomaly →
> S4/S5 LLM → S7 composite) plugs in behind that file with no frontend changes.
> See `UW_MarketLens_Implementation_Plan.html` for the section breakdown.

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

## Layout

| Path | What |
|------|------|
| `backend/app/schemas.py` | PLACEHOLDER Pydantic contract (finalized in S0) |
| `backend/app/mock.py` | All fake data — the single swap-out point |
| `backend/app/routes/` | Thin handlers: `/api/score`, `/api/library`, `/api/citation` |
| `frontend/src/types.ts` | TS mirror of the schema |
| `frontend/src/api.ts` | Backend URL lives here only |
| `frontend/src/components/` | ScoreCard, CitationBox, Library |
