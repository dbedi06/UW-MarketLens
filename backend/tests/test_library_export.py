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
