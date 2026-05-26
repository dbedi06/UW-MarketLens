"""
FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

Then open http://localhost:8000/docs for the auto-generated interactive API.
"""

import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import score, library, citation, snapshot, admin, og, live

logger = logging.getLogger(__name__)

app = FastAPI(
    title="UW MarketLens API",
    description="Prediction-market reliability platform — PLACEHOLDER backend (mock data).",
    version="0.1.0",
)

# CORS: the Vite dev server runs on a different origin (port 5173). Browsers
# block cross-origin requests unless the server explicitly allows them. In
# production, set FRONTEND_ORIGIN to the deployed static-site URL (Render does
# this automatically via render.yaml).
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_frontend_origin = os.environ.get("FRONTEND_ORIGIN")
if _frontend_origin:
    _allowed_origins.append(_frontend_origin.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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
app.include_router(snapshot.router)
app.include_router(admin.router)
app.include_router(og.router)
app.include_router(live.router)


@app.on_event("startup")
def _prefit_detector() -> None:
    """B7 fix: pay the IsoForest training cost at boot, not on first
    /api/live/score request. Render dyno wakes every 15 min idle; without
    this hook the first user after each wake waits 5-10s through training.
    Wrapped in try/except so a fit failure doesn't block API boot."""
    from .anomaly import scoring as anomaly_scoring
    t0 = time.perf_counter()
    try:
        anomaly_scoring.get_detector()
        logger.info("startup: pre-fit anomaly detector in %.2fs",
                    time.perf_counter() - t0)
    except Exception as exc:  # noqa: BLE001
        # Don't crash the API on a detector training failure — the live
        # route will retry the fit on first request.
        logger.exception("startup: detector pre-fit failed: %s", exc)
