"""
GET /api/snapshot/{id} — PILLAR 2.

Returns the frozen reliability report for a snapshot id. Mock snapshots
are deterministic in (url, as_of) so re-rendering yields byte-identical
output. Live snapshots re-run the S1→S2→S3 chain against the ingestion
cache; if the cache is cold (e.g., after Render dyno sleep) we surface
that as a 503 rather than silently substituting mock data — that
substitution was the B2 bug.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import MarketScore
from ..ingestion import IngestionUnavailable
from .. import mock
from . import live

router = APIRouter(prefix="/api", tags=["snapshot"])


@router.get("/snapshot/{sid}", response_model=MarketScore)
def snapshot(sid: str) -> MarketScore:
    full = mock.resolve_snapshot_full(sid)
    if full is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown snapshot id. Re-run the lookup to regenerate it "
                   "(deterministic for mock; live re-runs the S1→S2→S3 chain).",
        )
    url, as_of, source = full
    if source == "live":
        try:
            return live.render_live_snapshot(url, as_of)
        except IngestionUnavailable as exc:
            raise HTTPException(
                status_code=503,
                detail=(f"Live snapshot but ingestion cache is cold. "
                        f"Re-fetch the original market to warm the cache, "
                        f"then revisit this permalink. ({exc})"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    return mock.make_market_score(url, as_of)
