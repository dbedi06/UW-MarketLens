"""
POST /api/live/score — opt-in live anomaly scoring on real Polymarket data.

This is the *additive* counterpart to `/api/score` (mock). The frontend
defaults to live; this route runs the full S1 → S3 → S4 → S5 → S6 → S7
chain via `app.composite.make_market_score`.

Previously the route inlined its own scoring + composite logic, which
(a) duplicated everything composite.py already does and (b) hardcoded
tags to ["ECON"] and used `mock.make_citation` instead of S6's real
generator — leaving S5/S6/S7 as dead code. This wrapper fixes that.

Error handling preserved from the previous inline implementation:

  - IngestionUnavailable      → 503 (cache miss + LIVE flag unset)
  - "No Gamma event" / ...    → 404 (market doesn't exist on Polymarket)
  - Other ValueError          → 422 (data present but unscorable, e.g.
                                     <4 trade windows)
  - httpx.HTTPStatusError     → 502 (upstream Polymarket misbehaved)
  - everything else           → bubble up as 500 (with traceback in logs)
"""

from __future__ import annotations

import logging
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Request

from ..schemas import ScoreRequest, MarketScore
from ..ingestion import IngestionUnavailable
from .. import composite

router = APIRouter(prefix="/api/live", tags=["score-live"])
logger = logging.getLogger(__name__)


# ── shared render path (used by route + snapshot dispatch) ─────────────────

def render_live_snapshot(url: str, as_of: str) -> MarketScore:
    """Run the full live pipeline for `url` and emit a MarketScore.

    Used by both `POST /api/live/score` and `GET /api/snapshot/{id}` when
    the snapshot was originally produced by the live route. Raises
    `IngestionUnavailable`, `ValueError`, or `httpx.HTTPStatusError`
    — the route handler maps each to a friendly HTTP status.
    """
    return composite.make_market_score(url, as_of)


# ── route ────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=MarketScore)
def live_score(req: ScoreRequest, request: Request) -> MarketScore:
    url = req.url.strip()
    if "polymarket.com" not in url:
        raise HTTPException(status_code=400,
                            detail="Expected a polymarket.com URL")

    as_of = (req.as_of or date.today().isoformat())
    try:
        return render_live_snapshot(url, as_of)
    except IngestionUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=(f"No cached snapshot for this market and live fetch "
                    f"is disabled. Set MARKETLENS_POLYMARKET_LIVE=1 to "
                    f"allow Polymarket calls, or seed the cache via "
                    f"`python -m scripts.fetch_market --url ...`. "
                    f"({exc})"),
        )
    except ValueError as exc:
        # Distinguish "market does not exist on Polymarket" (404) from
        # "market exists but has insufficient data to score" (422). Both
        # arrive as ValueError today — the message is the discriminator.
        msg = str(exc)
        if "No Gamma event" in msg or "has no markets" in msg:
            raise HTTPException(
                status_code=404,
                detail=(f"This market doesn't appear to exist on Polymarket. "
                        f"Verify the URL by opening it in a browser. ({msg})"),
            )
        raise HTTPException(status_code=422, detail=msg)
    except httpx.HTTPStatusError as exc:
        # Upstream Polymarket returned an error (e.g., 401 for a malformed
        # token id, 404 for an unknown slug, 5xx during outage). Surface a
        # 502 with the upstream code rather than crashing into a 500.
        failed_url = str(exc.request.url) if exc.request else "<unknown>"
        logger.warning(
            "live: upstream Polymarket error %d on %s (event=%s)",
            exc.response.status_code, failed_url, url,
        )
        raise HTTPException(
            status_code=502,
            detail=(f"Polymarket returned {exc.response.status_code} for "
                    f"the upstream call to {failed_url}. The market URL "
                    f"may be valid but the API may have changed shape. "
                    f"Switch to Mock mode to keep browsing."),
        )
