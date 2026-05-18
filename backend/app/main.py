"""
FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for the auto-generated interactive API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import score, library, citation

app = FastAPI(
    title="UW MarketLens API",
    description="Prediction-market reliability platform — PLACEHOLDER backend (mock data).",
    version="0.1.0",
)

# CORS: the Vite dev server runs on a different origin (port 5173). Browsers
# block cross-origin requests unless the server explicitly allows them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Simple liveness check — handy for deploy/CI later."""
    return {"status": "ok", "mode": "mock"}


app.include_router(score.router)
app.include_router(library.router)
app.include_router(citation.router)
