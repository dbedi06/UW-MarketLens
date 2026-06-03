"""Tests for /api/library.csv + course-pack filter."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_library_csv_returns_csv_with_header():
    with TestClient(app) as client:
        r = client.get("/api/library.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.text
    first = body.splitlines()[0]
    # Header row matches expected schema columns
    expected = "market_url,market_question,reliability_score,band,departments,verified"
    assert first == expected
    # At least one data row
    assert len(body.splitlines()) > 1


def test_library_csv_respects_dept_filter():
    with TestClient(app) as client:
        r = client.get("/api/library.csv?dept=ECON")
    assert r.status_code == 200
    rows = r.text.splitlines()[1:]  # skip header
    assert len(rows) > 0
    # Every data row's departments column contains ECON
    for row in rows:
        cols = row.split(",")
        # departments is column 4 (0-indexed) joined by ";"
        assert "ECON" in cols[4]


def test_library_course_filter_known_code():
    """POLS270 is in the committed uw_courses.json, mapped to POLS."""
    with TestClient(app) as client:
        r = client.get("/api/library?course=POLS270")
    assert r.status_code == 200
    rows = r.json()
    # All returned rows are POLS-tagged
    for row in rows:
        assert "POLS" in row["departments"]


def test_library_course_filter_normalizes_whitespace():
    """`POLS 270` (with space) must resolve same as `POLS270`."""
    with TestClient(app) as client:
        r1 = client.get("/api/library?course=POLS270")
        r2 = client.get("/api/library?course=POLS%20270")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()


def test_library_course_filter_unknown_code_returns_404():
    with TestClient(app) as client:
        r = client.get("/api/library?course=NONSENSE999")
    assert r.status_code == 404
    assert "isn't in the UW courses map" in r.json()["detail"]


def test_library_csv_with_course_filter():
    with TestClient(app) as client:
        r = client.get("/api/library.csv?course=INFO200")
    assert r.status_code == 200
    rows = r.text.splitlines()[1:]
    for row in rows:
        assert "INFO" in row.split(",")[4]


def test_mock_library_dept_tagging_is_content_based():
    """Lock PISAN line 14's fix against regression.

    Before v0.9.1 the mock library assigned departments by hashing
    `(url, as_of)` modulo 4 — random tagging. The fix routes through
    `tagger._fallback(question)` so depts derive from the slugified
    question text. This test asserts the four content→dept matches
    that should hold for the committed `_SAMPLE_URLS`. If anyone
    reverts the mock-tagger wiring or removes a keyword the URLs
    depend on, this fails loudly.

    The World Cup row intentionally has no UW-dept-mapping keyword
    and tags as `[]` ("Untagged" in the frontend) — that's the
    honest outcome, not a bug.
    """
    from app.mock import make_library

    by_question = {entry.market_question: entry for entry in make_library()}
    expectations = {
        "Fed decision in june 825?": "ECON",
        "Us x iran permanent peace deal by?": "POLS",
        "Us enacts ai safety bill before 2027?": "INFO",
        "Which company has best ai model end of june?": "INFO",
    }
    for question, dept in expectations.items():
        assert question in by_question, (
            f"Mock library missing expected seeded question {question!r} — "
            f"the _SAMPLE_URLS slug list may have drifted from this test."
        )
        assert dept in by_question[question].departments, (
            f"Mock library entry for {question!r} expected to include "
            f"{dept!r} in departments, got {by_question[question].departments}. "
            f"PISAN line 14 regression: content-based dept tagging broke."
        )

    # AI safety bill is the canonical double-tag (INFO + EVANS).
    ai_bill_entry = by_question["Us enacts ai safety bill before 2027?"]
    assert "EVANS" in ai_bill_entry.departments

    # World Cup is honestly untagged — no UW dept fits a sports event.
    world_cup_entry = by_question["World cup winner?"]
    assert world_cup_entry.departments == [], (
        f"World Cup row expected empty departments (no UW dept fits), "
        f"got {world_cup_entry.departments}. If the keyword list now "
        f"matches 'world cup' to some dept, update this assertion."
    )
