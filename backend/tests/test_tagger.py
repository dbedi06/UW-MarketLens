"""Tests for app.tagger — S5 course tagger.

These exercise the keyword fallback path (no API key required) and the
in-memory cache; the live Claude call is not tested here because it
requires a network + key, and the integration test in test_live_route
covers wiring via monkeypatch.
"""
from __future__ import annotations

import pytest

from app.tagger import (
    DEPARTMENTS, TagResult, clear_cache, has_tagger_key, tag_market,
)


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch):
    """Drop the OPENROUTER_API_KEY for every test so we exercise the
    fallback path deterministically. Each test starts with a clean
    cache."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    clear_cache()
    yield
    clear_cache()


def test_has_tagger_key_false_without_env():
    assert has_tagger_key() is False


def test_fallback_tags_economics_question():
    result = tag_market("Will the Fed cut interest rates in 2025?")
    assert isinstance(result, TagResult)
    assert "ECON" in result.departments
    assert result.used_fallback is True
    assert 0 <= result.course_applicability <= 100


def test_fallback_tags_political_question():
    result = tag_market("Will Donald Trump win the 2024 presidential election?")
    assert "POLS" in result.departments
    assert result.used_fallback is True


def test_fallback_tags_tech_question():
    result = tag_market("Will GPT-5 be released in 2024?")
    assert "INFO" in result.departments
    assert result.used_fallback is True


def test_fallback_off_topic_question_returns_low_score():
    """A pop-culture question should produce 0 departments and a low
    applicability score (per the fallback rule)."""
    result = tag_market("Will Taylor Swift drop a new album?")
    assert result.departments == []
    assert result.course_applicability < 40


def test_departments_validated_against_allowed_set():
    """Whatever path the tagger took, the result must only contain
    departments from the known set."""
    result = tag_market("Will the Fed cut rates?")
    for d in result.departments:
        assert d in DEPARTMENTS


def test_cache_returns_same_object_for_same_question():
    """Same question (case + whitespace insensitive) hits the cache."""
    a = tag_market("Will the Fed cut rates?")
    b = tag_market("  WILL THE FED CUT RATES?  ")
    assert a is b
