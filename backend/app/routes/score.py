"""
POST /api/score  — given a market URL, return a deterministic mock MarketScore.

This is the explicit fallback route used by the frontend Mock toggle.
The frontend defaults to live mode and uses `/api/live/score` for the real
Polymarket scoring pipeline. The handler is deliberately thin: validate input
(FastAPI does this via the ScoreRequest model), then delegate to
mock.make_market_score.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import ScoreRequest, MarketScore
from .. import mock

router = APIRouter(prefix="/api", tags=["score"])


@router.post("/score", response_model=MarketScore)
def score(req: ScoreRequest) -> MarketScore:
    url = req.url.strip()
    if "polymarket.com" not in url:
        # Mock route does a light sanity check; the live route's S1
        # ingestion does full slug parsing + Gamma lookup.
        raise HTTPException(status_code=400, detail="Expected a polymarket.com URL")
    return mock.make_market_score(url, req.as_of)
