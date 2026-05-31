"""Tests for app.citation_gen — S6 pure-function citation generator."""
from __future__ import annotations

from app.citation_gen import (
    CitationOutput, _bibtex_key, _clean_question, _reliability_flag,
    make_citation,
)


def test_reliability_flag_bands():
    assert "RELIABLE" in _reliability_flag(90)
    assert "RELIABLE" in _reliability_flag(70)
    assert "USE WITH CAUTION" in _reliability_flag(50)
    assert "USE WITH CAUTION" in _reliability_flag(40)
    assert "NOT RECOMMENDED" in _reliability_flag(30)
    assert "NOT RECOMMENDED" in _reliability_flag(0)


def test_bibtex_key_deterministic():
    """Same permalink → same BibTeX key. Different permalinks differ."""
    a = _bibtex_key("/snapshot/abc123")
    b = _bibtex_key("/snapshot/abc123")
    c = _bibtex_key("/snapshot/def456")
    assert a == b
    assert a != c
    assert a.startswith("marketlens_")
    assert len(a) == len("marketlens_") + 8  # 8 hex chars


def test_clean_question_adds_question_mark():
    assert _clean_question("Will it rain") == "Will it rain?"
    assert _clean_question("Will it rain?") == "Will it rain?"
    assert _clean_question("  Will   it   rain  ") == "Will it rain?"


def test_make_citation_full_shape():
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will the Fed cut rates in 2025?",
        as_of="2026-05-30",
        permalink="/snapshot/abc12345",
        score=82,
    )
    assert isinstance(out, CitationOutput)
    # APA includes question, date, URL, permalink, flag
    assert "Will the Fed cut rates in 2025?" in out.apa
    assert "2026-05-30" in out.apa
    assert "https://polymarket.com/event/test" in out.apa
    assert "/snapshot/abc12345" in out.apa
    assert "RELIABLE" in out.apa
    # MLA includes the same anchors
    assert "Will the Fed cut rates in 2025?" in out.mla
    assert "/snapshot/abc12345" in out.mla
    # BibTeX has the deterministic key prefix and proper structure
    assert out.bibtex.startswith("@misc{marketlens_")
    assert out.bibtex.endswith("}")
    assert "title  =" in out.bibtex
    assert "author = {Polymarket}" in out.bibtex
    # Reliability flag matches the score band
    assert "RELIABLE" in out.reliability_flag


def test_make_citation_low_score_embeds_not_recommended():
    """A low score should make the citation visibly warn the reader."""
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will pigs fly?",
        as_of="2026-05-30",
        permalink="/snapshot/xyz",
        score=15,
    )
    assert "NOT RECOMMENDED" in out.apa
    assert "NOT RECOMMENDED" in out.mla
    assert "NOT RECOMMENDED" in out.bibtex
    assert "NOT RECOMMENDED" in out.reliability_flag


def test_bibtex_escapes_braces_in_question():
    """A question containing literal braces would otherwise corrupt the
    BibTeX entry."""
    out = make_citation(
        url="https://polymarket.com/event/test",
        question="Will the {brace} survive escaping?",
        as_of="2026-05-30",
        permalink="/snapshot/test",
        score=70,
    )
    assert r"\{brace\}" in out.bibtex
