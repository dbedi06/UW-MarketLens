"""
POST /api/citation — academic citation (APA/MLA/BibTeX) with reliability flag.

Generates the citation via S6 (`app/citation_gen.py`, a pure function).
Score and metadata still come from the mock path for speed — this endpoint
is "give me a citation for this URL now," not "run the full live pipeline
just to format a string." For a score-anchored citation, the full live
report at `POST /api/live/score` already includes the same fields, computed
from real data.
"""

from fastapi import APIRouter, HTTPException
from ..schemas import CitationRequest, Citation
from ..citation_gen import make_citation
from .. import mock

router = APIRouter(prefix="/api", tags=["citation"])


@router.post("/citation", response_model=Citation)
def citation(req: CitationRequest) -> Citation:
    url = req.url.strip()
    if "polymarket.com" not in url:
        raise HTTPException(status_code=400, detail="Expected a polymarket.com URL")

    # Score + metadata from the mock path (deterministic, fast). The
    # citation strings themselves come from S6's real generator so a
    # paper that cites a snapshot sees BibTeX + reliability flag in the
    # same format the live pipeline emits.
    ms = mock.make_market_score(url)
    out = make_citation(
        url=url,
        question=ms.market_question,
        as_of=ms.as_of,
        permalink=ms.permalink,
        score=ms.reliability_score,
    )
    return Citation(
        apa=out.apa,
        mla=out.mla,
        bibtex=out.bibtex,
        reliability_flag=out.reliability_flag,
    )
