"""
GET /api/library — list of UW-relevant markets, optionally filtered.

Today the list is a fixed sample. Later it is auto-populated by the S5 LLM
tagger + admin verification; the endpoint shape (and the ?q=/?dept= filters)
stays the same.
"""

from typing import List, Optional
from fastapi import APIRouter, Query
from ..schemas import LibraryEntry
from .. import mock

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/library", response_model=List[LibraryEntry])
def library(
    q: Optional[str] = Query(None, description="Search in the market question"),
    dept: Optional[str] = Query(None, description="Filter by department code"),
) -> List[LibraryEntry]:
    rows = mock.make_library()
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r.market_question.lower()]
    if dept:
        rows = [r for r in rows if dept.upper() in r.departments]
    return rows
