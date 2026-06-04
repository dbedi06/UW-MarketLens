"""
Admin verification — proposal §2.3 (human-in-the-loop over the LLM tagger).

GET  /api/admin/pending-tags  -> tags awaiting review
POST /api/admin/verify        -> approve as-is, or override the departments

State is an in-memory overlay on the mock tagger output (resets on restart;
fine for a demo). Real S0 would persist this to a table.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from ..schemas import PendingTag, VerifyRequest
from .. import composite, mock

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)

# market_url -> {"verified": bool, "departments": [...]}
_OVERLAY: Dict[str, dict] = {}


def require_admin(
    x_admin_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> None:
    """Shared-secret gate for the mutating admin endpoints. Reads the
    token from the `X-Admin-Token` header (sent by the frontend) or a
    `?token=` query param (secret-in-the-address). Enforced only when
    `ADMIN_TOKEN` is set in the environment — unset means open, which
    keeps local dev + the test suite working without config. Set it
    in the Render dashboard to lock production.

    Not real auth (one shared secret, no users/sessions) but it does
    actually 401 the endpoints — demo-grade, honestly so.
    """
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected:
        logger.warning("ADMIN_TOKEN not set; admin endpoints are open.")
        return
    if (x_admin_token or token) != expected:
        raise HTTPException(status_code=401, detail="Admin token required")


def _pending_tags() -> List[PendingTag]:
    """The tag-review queue. Scores each curated market through the
    real pipeline when live is available (real questions + real
    departments), per-URL mock fallback so one failing market can't
    break the page. Mirrors `routes.library._library_rows`."""
    if not composite.has_live_pipeline():
        return mock.make_pending_tags()
    out: List[PendingTag] = []
    for url in mock.library_urls():
        try:
            ms = composite.make_market_score(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("admin: live score failed for %s (%s); "
                           "mock fallback.", url, exc)
            ms = mock.make_market_score(url, register=False)
        out.append(mock.pending_tag_from_score(ms))
    return out


def _apply_overlay(tag: PendingTag) -> PendingTag:
    o = _OVERLAY.get(tag.market_url)
    if not o:
        return tag
    return tag.model_copy(update={
        "verified": o["verified"],
        "suggested_departments": o.get("departments", tag.suggested_departments),
    })


@router.get("/pending-tags", response_model=List[PendingTag],
            dependencies=[Depends(require_admin)])
def pending_tags() -> List[PendingTag]:
    return [_apply_overlay(t) for t in _pending_tags()]


@router.post("/verify", response_model=PendingTag,
             dependencies=[Depends(require_admin)])
def verify(req: VerifyRequest) -> PendingTag:
    base = next(
        (t for t in _pending_tags() if t.market_url == req.market_url),
        None,
    )
    if base is None:
        raise HTTPException(status_code=404, detail="Unknown market_url")
    if req.action == "override" and not req.departments:
        raise HTTPException(
            status_code=400, detail="override requires a departments list"
        )
    _OVERLAY[req.market_url] = {
        "verified": True,
        "departments": req.departments if req.action == "override"
        else base.suggested_departments,
    }
    return _apply_overlay(base)


@router.get("/calibration-report")
def calibration_report() -> Any:
    # Serve the committed, precomputed report only. Never generate on
    # the request path: live generation fires ~36 LLM calls (12 cases
    # x self-consistency), takes 45s+, times out behind Render's proxy,
    # and — because self-consistency samples at temperature — produces
    # a different chart every load. The report is built offline via
    # `python -m scripts.calibration_report` and committed, so the
    # endpoint is instant and stable.
    report_path = Path(__file__).resolve().parents[1] / "anomaly" / "calibration_report.json"
    if report_path.exists():
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    raise HTTPException(
        status_code=503,
        detail=(
            "Calibration report not generated. Run "
            "`python -m scripts.calibration_report` and commit "
            "app/anomaly/calibration_report.json."
        ),
    )
