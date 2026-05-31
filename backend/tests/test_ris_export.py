"""Tests for the RIS citation format addition (S6 extension)."""
from __future__ import annotations

from app.citation_gen import make_citation


def test_ris_field_present_in_output():
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will the Fed cut rates in 2025?",
        as_of="2026-05-30",
        permalink="/snapshot/abc12345",
        score=82,
    )
    assert out.ris != ""


def test_ris_starts_with_ty_and_ends_with_er():
    """RIS records start with TY and end with ER (end of record)."""
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will the Fed cut rates in 2025?",
        as_of="2026-05-30",
        permalink="/snapshot/abc12345",
        score=82,
    )
    lines = [l for l in out.ris.splitlines() if l.strip()]
    assert lines[0].startswith("TY  - ")
    assert lines[-1].startswith("ER  - ")


def test_ris_contains_required_fields():
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will the Fed cut rates in 2025?",
        as_of="2026-05-30",
        permalink="/snapshot/abc12345",
        score=82,
    )
    ris = out.ris
    # Tags we always emit
    for tag in ("TY  - ", "T1  - ", "AU  - ", "PY  - ", "UR  - ",
                "N1  - ", "ER  - "):
        assert tag in ris, f"Missing {tag!r} in RIS output"
    # Year is derived from the as_of date
    assert "PY  - 2026" in ris
    # URL appears in UR
    assert "https://polymarket.com/event/test" in ris
    # Question appears in T1
    assert "Will the Fed cut rates in 2025?" in ris
    # Reliability flag is preserved verbatim
    assert "RELIABLE" in ris


def test_ris_low_score_embeds_not_recommended():
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will pigs fly?",
        as_of="2026-05-30",
        permalink="/snapshot/xyz",
        score=15,
    )
    assert "NOT RECOMMENDED" in out.ris
