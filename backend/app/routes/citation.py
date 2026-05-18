"""
POST /api/citation — academic citation (APA/MLA) with a reliability flag.

Standalone so the citation generator (S6) can be developed independently of
scoring. Same thin-handler pattern.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import CitationRequest, Citation
from .. import mock

router = APIRouter(prefix="/api", tags=["citation"])


@router.post("/citation", response_model=Citation)
def citation(req: CitationRequest) -> Citation:
    url = req.url.strip()
    if "polymarket.com" not in url:
        raise HTTPException(status_code=400, detail="Expected a polymarket.com URL")
    # Derive from the full score so the citation's reliability flag and the
    # snapshot permalink always agree with the rest of the report.
    return mock.make_market_score(url).citation
