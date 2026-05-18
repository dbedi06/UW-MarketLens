"""
GET /api/library — list of UW-relevant markets.

Today this is a fixed sample list. Later it is auto-populated by the S5 LLM
tagger + admin verification; the endpoint shape stays the same.
"""

from typing import List
from fastapi import APIRouter
from ..schemas import LibraryEntry
from .. import mock

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/library", response_model=List[LibraryEntry])
def library() -> List[LibraryEntry]:
    return mock.make_library()
