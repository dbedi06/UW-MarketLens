"""
GET /api/snapshot/{id} — PILLAR 2.

Returns the frozen reliability report for a snapshot id. Because the mock data
is deterministic in (url, as_of), resolving the id back to its (url, as_of)
and recomputing yields byte-identical output every time — which is exactly
what makes a citation reproducible.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import MarketScore
from .. import mock

router = APIRouter(prefix="/api", tags=["snapshot"])


@router.get("/snapshot/{sid}", response_model=MarketScore)
def snapshot(sid: str) -> MarketScore:
    resolved = mock.resolve_snapshot(sid)
    if resolved is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown snapshot id. Re-run the lookup to regenerate it "
                   "(deterministic — same URL and date yield the same snapshot).",
        )
    url, as_of = resolved
    return mock.make_market_score(url, as_of)
