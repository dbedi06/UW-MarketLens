# UW MarketLens — Backend (PLACEHOLDER)

FastAPI backend returning **deterministic mock data**. All fake data lives in
`app/mock.py` — that is the single file replaced when real sections (S1–S7) land.

## Run

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API.

## Endpoints

| Method | Path           | Body                          | Returns        |
|--------|----------------|-------------------------------|----------------|
| GET    | `/health`      | —                             | liveness       |
| POST   | `/api/score`   | `{ "url": "..." }`            | `MarketScore`  |
| GET    | `/api/library` | —                             | `LibraryEntry[]` |
| POST   | `/api/citation`| `{ "url": "...", "style": "APA" }` | `Citation` |

Schemas in `app/schemas.py` are **placeholders** — finalized in S0.
