"""
GET /api/library — list of UW-relevant markets, optionally filtered.

Today the list is a fixed sample. Later it is auto-populated by the S5 LLM
tagger + admin verification; the endpoint shape (and the ?q=/?dept= filters)
stays the same.

Also exposes a CSV variant (`GET /api/library.csv`) and accepts a
`course=POLS270` filter that maps a UW course code to a department via
the committed `app/data/uw_courses.json` table.
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from ..schemas import LibraryEntry
from .. import composite, mock, snapshot_store

router = APIRouter(prefix="/api", tags=["library"])
logger = logging.getLogger(__name__)

# How many user-scored markets to surface on top of the curated seed.
_MAX_RECENT = 15


def _library_rows() -> List[LibraryEntry]:
    """The library list. When the live pipeline is available, score
    each curated market through the real S1→S7 composite so the
    displayed numbers match what a user gets clicking through (and
    so the snapshot they share matches). Per-URL fallback to mock so
    one slow/failing market can't break or hang the whole page.
    Live scores are cached in composite._LIVE_SCORE_CACHE, so only
    the first load after a cold dyno is slow.

    Without the live flag (pure-mock deploy / tests) this is the
    deterministic mock list.
    """
    if not composite.has_live_pipeline():
        return mock.make_library()

    rows: List[LibraryEntry] = []
    seen: set[str] = set()

    # Curated seed — always present, live-scored (cached after first load).
    for url in mock.library_urls():
        try:
            ms = composite.make_market_score(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("library: live score failed for %s (%s); "
                           "falling back to mock row.", url, exc)
            ms = mock.make_market_score(url, register=False)
        rows.append(mock.entry_from_score(ms))
        seen.add(ms.market_url)

    # Markets users have scored, newest first — read straight from the
    # in-process store (no re-scoring). Only real (source="live")
    # markets; mock-toggle scores never leak into the library.
    added = 0
    for ms in snapshot_store.recent():
        if added >= _MAX_RECENT:
            break
        if ms.source == "live" and ms.market_url not in seen:
            rows.append(mock.entry_from_score(ms))
            seen.add(ms.market_url)
            added += 1
    return rows


_COURSE_PATH = Path(__file__).parent.parent / "data" / "uw_courses.json"


def _course_map() -> dict[str, str]:
    """Load the course-code → department map. Cached after first read.
    Returns {} if the file is missing so the rest of the route keeps
    working."""
    if not _COURSE_PATH.exists():
        return {}
    try:
        raw = json.loads(_COURSE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    # Normalize keys to uppercase + no spaces ("POLS 270" → "POLS270").
    # Skip JSON-convention comment keys (start with underscore).
    return {
        str(k).upper().replace(" ", ""): str(v).upper()
        for k, v in raw.items()
        if not str(k).startswith("_")
    }


def _filter_rows(
    rows: List[LibraryEntry],
    q: Optional[str],
    dept: Optional[str],
    course: Optional[str],
) -> List[LibraryEntry]:
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r.market_question.lower()]
    # Course-code filter takes precedence over dept (both can be set
    # via URL; course wins because it's the more specific signal).
    if course:
        cmap = _course_map()
        key = course.upper().replace(" ", "")
        target_dept = cmap.get(key)
        if not target_dept:
            raise HTTPException(
                status_code=404,
                detail=(f"Course code {course!r} isn't in the UW courses "
                        f"map. Known codes: {sorted(cmap.keys()) or 'none'}."),
            )
        rows = [r for r in rows if target_dept in r.departments]
    elif dept:
        rows = [r for r in rows if dept.upper() in r.departments]
    return rows


@router.get("/library", response_model=List[LibraryEntry])
def library(
    q: Optional[str] = Query(None, description="Search in the market question"),
    dept: Optional[str] = Query(None, description="Filter by department code"),
    course: Optional[str] = Query(
        None,
        description=(
            "UW course code (e.g., POLS270, INFO200) — maps to a "
            "department via app/data/uw_courses.json"
        ),
    ),
) -> List[LibraryEntry]:
    rows = _library_rows()
    return _filter_rows(rows, q, dept, course)


@router.get("/library.csv", response_class=StreamingResponse)
def library_csv(
    q: Optional[str] = Query(None),
    dept: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
) -> StreamingResponse:
    """Same filtering as /api/library, returned as CSV with a
    Content-Disposition header so browsers download it. Useful for a
    research-methods instructor who wants a class dataset."""
    rows = _filter_rows(_library_rows(), q, dept, course)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "market_url", "market_question", "reliability_score", "band",
        "departments", "verified",
    ])
    for r in rows:
        writer.writerow([
            r.market_url,
            r.market_question,
            r.reliability_score,
            r.band,
            ";".join(r.departments),
            "true" if r.verified else "false",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="marketlens_library.csv"',
        },
    )
