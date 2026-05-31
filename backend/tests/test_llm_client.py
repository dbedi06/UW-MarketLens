"""Tests for the shared OpenRouter client."""
from __future__ import annotations

import json

import httpx
import pytest

from app.llm_client import (
    DEFAULT_MODEL, OpenRouterError, call_chat, has_openrouter_key,
)


def _ok_response(text: str = "hello") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "test",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        },
    )


def test_has_openrouter_key_reads_env(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert has_openrouter_key() is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert has_openrouter_key() is True


def test_call_chat_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError, match="not set"):
        call_chat([{"role": "user", "content": "hi"}])


def test_call_chat_returns_message_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: _ok_response("the answer")),
    )
    out = call_chat([{"role": "user", "content": "hi"}], client=client)
    assert out == "the answer"


def test_call_chat_raises_on_non_200(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(429, json={"error": "rate limited"}),
        ),
    )
    with pytest.raises(OpenRouterError, match="429"):
        call_chat([{"role": "user", "content": "hi"}], client=client)


def test_call_chat_attaches_bearer_auth_and_default_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    captured: dict = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization", "")
        captured["referer"] = request.headers.get("HTTP-Referer", "")
        captured["title"] = request.headers.get("X-Title", "")
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)

    assert captured["url"].endswith("/api/v1/chat/completions")
    assert captured["url"].startswith("https://openrouter.ai/")
    assert captured["auth"] == "Bearer secret-key"
    assert captured["referer"]  # non-empty (analytics referer)
    assert captured["title"] == "UW MarketLens"
    assert captured["body"]["model"] == DEFAULT_MODEL


def test_call_chat_json_mode_adds_response_format(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], json_mode=True, client=client)
    assert captured["body"].get("response_format") == {"type": "json_object"}


def test_call_chat_no_json_mode_omits_response_format(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)
    assert "response_format" not in captured["body"]


def test_call_chat_explicit_model_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_MODEL", "env-model")
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat(
        [{"role": "user", "content": "hi"}],
        model="explicit-model",
        client=client,
    )
    assert captured["body"]["model"] == "explicit-model"


def test_call_chat_raises_on_malformed_response_shape(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"unexpected": "shape"}),
        ),
    )
    with pytest.raises(OpenRouterError, match="choices"):
        call_chat([{"role": "user", "content": "hi"}], client=client)
