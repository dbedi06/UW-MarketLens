"""
POST /api/score  — given a market URL, return a (mock) MarketScore.

The handler is deliberately thin: validate input (FastAPI does this via the
ScoreRequest model), then delegate to mock.make_market_score. When S7 lands,
only the delegated call changes.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import ScoreRequest, MarketScore
from .. import mock

router = APIRouter(prefix="/api", tags=["score"])


@router.post("/score", response_model=MarketScore)
def score(req: ScoreRequest) -> MarketScore:
    url = req.url.strip()
    if "polymarket.com" not in url:
        # PLACEHOLDER validation — S1 will do real URL parsing.
        raise HTTPException(status_code=400, detail="Expected a polymarket.com URL")
    return mock.make_market_score(url)
