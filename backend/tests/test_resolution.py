from __future__ import annotations

import httpx
import pytest

from app.resolution import resolve_market


def _response(payload, status_code=200):
    return httpx.Response(status_code, json=payload)


def test_resolve_market_returns_assessment_from_llm(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "news-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")

    def handler(request):
        if request.url.host == "newsapi.org" and request.url.path == "/v2/everything":
            return _response(
                {
                    "articles": [
                        {
                            "title": "Wire source backs outcome",
                            "description": "Independent reporting confirms the result.",
                            "url": "https://example.com/article-one",
                        }
                    ]
                }
            )
        if request.url.host == "api.anthropic.com" and request.url.path == "/v1/messages":
            return _response(
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"verdict":"HIGH","reasoning":"Independent reporting corroborates the outcome.",'
                                '"supporting_sources":["https://example.com/article-one"],"confidence":0.8}'
                            ),
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request: {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assessment = resolve_market("Will the Fed cut rates in 2025?", client=client)

    assert assessment.verdict == "HIGH"
    assert assessment.reasoning == "Independent reporting corroborates the outcome."
    assert assessment.supporting_sources == ["https://example.com/article-one"]
    assert assessment.confidence == pytest.approx(0.8)
    assert assessment.resolution_quality == 80
    assert assessment.used_fallback is False


def test_resolve_market_falls_back_when_keys_missing(monkeypatch):
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assessment = resolve_market("Will the Fed cut rates in 2025?")

    assert assessment.verdict == "UNVERIFIABLE"
    assert assessment.used_fallback is True
    assert assessment.supporting_sources == []
    assert assessment.confidence == 0.0
    assert assessment.resolution_quality == 0


def test_resolve_market_falls_back_on_bad_llm_payload(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "news-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")

    def handler(request):
        if request.url.host == "newsapi.org" and request.url.path == "/v2/everything":
            return _response(
                {
                    "articles": [
                        {
                            "title": "Wire source backs outcome",
                            "description": "Independent reporting confirms the result.",
                            "url": "https://example.com/article-one",
                        }
                    ]
                }
            )
        if request.url.host == "api.anthropic.com" and request.url.path == "/v1/messages":
            return _response(
                {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"verdict":"NOT_A_REAL_VERDICT","reasoning":"broken","confidence":1.0}',
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request: {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assessment = resolve_market("Will the Fed cut rates in 2025?", client=client)

    assert assessment.verdict == "UNVERIFIABLE"
    assert assessment.used_fallback is True
