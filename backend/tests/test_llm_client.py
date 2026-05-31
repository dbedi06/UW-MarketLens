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
    assert out.content == "the answer"
    assert out.model == DEFAULT_MODEL
    assert out.used_fallback is False


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


# ── Provider pinning ───────────────────────────────────────────────────────

def test_provider_env_var_adds_provider_block_to_request(monkeypatch):
    """OPENROUTER_PROVIDER=deepseek must inject a `provider` field that
    pins to that provider with no fallback (the cost-control feature)."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_PROVIDER", "deepseek")
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)

    prov = captured["body"].get("provider")
    assert prov is not None
    # Modern OpenRouter pin syntax: `only` replaces the older
    # `order + allow_fallbacks: false` pair which started returning
    # hard 404s under transient conditions. Same cost guarantee.
    assert prov.get("only") == ["deepseek"]
    assert "order" not in prov
    assert "allow_fallbacks" not in prov


def test_provider_env_var_unset_omits_provider_block(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("OPENROUTER_PROVIDER", raising=False)
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)
    assert "provider" not in captured["body"]


def test_provider_env_var_supports_comma_list(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_PROVIDER", "deepseek, deepinfra")
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _ok_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)
    assert captured["body"]["provider"]["only"] == ["deepseek", "deepinfra"]


# ── Retry + fallback ───────────────────────────────────────────────────────

def test_call_chat_retries_on_transient_error_then_succeeds(monkeypatch):
    """A 503 on the first attempt, 200 on the retry: must return the
    retry's content without firing the fallback."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr("app.llm_client.RETRY_BACKOFF_S", 0.0)
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(503, json={"error": "no instances"})
        return _ok_response("recovered")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = call_chat([{"role": "user", "content": "hi"}], client=client)
    assert out.content == "recovered"
    assert out.used_fallback is False
    assert attempts["n"] == 2  # one retry


def test_call_chat_falls_back_when_primary_exhausts_retries(monkeypatch):
    """All primary attempts fail → fallback model gets one try and
    succeeds → response carries the fallback model id + used_fallback=True."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_MODEL", "primary/x")
    monkeypatch.setenv("OPENROUTER_FALLBACK_MODEL", "fallback/y")
    monkeypatch.setattr("app.llm_client.RETRY_BACKOFF_S", 0.0)
    seen_models: list[str] = []

    def handler(request):
        body = json.loads(request.content)
        model = body.get("model")
        seen_models.append(model)
        if model == "primary/x":
            return httpx.Response(500, json={"error": "boom"})
        return _ok_response(f"hello from {model}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = call_chat([{"role": "user", "content": "hi"}], client=client)
    assert out.content == "hello from fallback/y"
    assert out.model == "fallback/y"
    assert out.used_fallback is True
    # 3 primary attempts (1 + 2 retries) then 1 fallback attempt
    assert seen_models == ["primary/x"] * 3 + ["fallback/y"]


def test_call_chat_raises_when_both_primary_and_fallback_fail(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_MODEL", "primary/x")
    monkeypatch.setenv("OPENROUTER_FALLBACK_MODEL", "fallback/y")
    monkeypatch.setattr("app.llm_client.RETRY_BACKOFF_S", 0.0)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(500, json={"error": "boom"}),
        ),
    )
    with pytest.raises(OpenRouterError, match="both failed"):
        call_chat([{"role": "user", "content": "hi"}], client=client)


def test_fallback_request_omits_provider_pin(monkeypatch):
    """The provider pin applies to the primary model only — the
    fallback may not be served by the pinned provider, so the
    fallback attempt must be unpinned to have a chance."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/v4-pro")
    monkeypatch.setenv("OPENROUTER_PROVIDER", "deepseek")
    monkeypatch.setenv("OPENROUTER_FALLBACK_MODEL", "google/gemini-flash")
    monkeypatch.setattr("app.llm_client.RETRY_BACKOFF_S", 0.0)
    bodies: list[dict] = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        if body["model"] == "deepseek/v4-pro":
            return httpx.Response(500, json={"error": "boom"})
        return _ok_response("ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    call_chat([{"role": "user", "content": "hi"}], client=client)
    primary_bodies = [b for b in bodies if b["model"] == "deepseek/v4-pro"]
    fallback_bodies = [b for b in bodies if b["model"] == "google/gemini-flash"]
    # Every primary attempt carries the provider pin
    assert all("provider" in b for b in primary_bodies)
    # Fallback attempt is unpinned
    assert all("provider" not in b for b in fallback_bodies)
