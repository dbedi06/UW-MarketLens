"""
Admin verification — proposal §2.3 (human-in-the-loop over the LLM tagger).

GET  /api/admin/pending-tags  -> tags awaiting review
POST /api/admin/verify        -> approve as-is, or override the departments

State is an in-memory overlay on the mock tagger output (resets on restart;
fine for a demo). Real S0 would persist this to a table.
"""

from typing import List, Dict
from fastapi import APIRouter, HTTPException
from ..schemas import PendingTag, VerifyRequest
from .. import mock

router = APIRouter(prefix="/api/admin", tags=["admin"])

# market_url -> {"verified": bool, "departments": [...]}
_OVERLAY: Dict[str, dict] = {}


def _apply_overlay(tag: PendingTag) -> PendingTag:
    o = _OVERLAY.get(tag.market_url)
    if not o:
        return tag
    return tag.model_copy(update={
        "verified": o["verified"],
        "suggested_departments": o.get("departments", tag.suggested_departments),
    })


@router.get("/pending-tags", response_model=List[PendingTag])
def pending_tags() -> List[PendingTag]:
    return [_apply_overlay(t) for t in mock.make_pending_tags()]


@router.post("/verify", response_model=PendingTag)
def verify(req: VerifyRequest) -> PendingTag:
    base = next(
        (t for t in mock.make_pending_tags() if t.market_url == req.market_url),
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
