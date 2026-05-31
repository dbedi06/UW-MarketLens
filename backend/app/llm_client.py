"""Shared OpenRouter chat-completions client.

UW MarketLens used to call Anthropic's Claude API directly from
`resolution.py` (S4) and `tagger.py` (S5). Claude is too expensive
for a class demo where every /api/live/score request fires two LLM
calls. OpenRouter exposes a single OpenAI-compatible endpoint that
routes to hundreds of models — including free-tier models with no
card on file.

This module is the only place that talks to OpenRouter. S4 and S5
both call `call_chat(messages, json_mode=...)` and get back a string
of response text; the prompt shape and parsing live in the callers.

Env vars
--------
  OPENROUTER_API_KEY  required for any live call
  OPENROUTER_MODEL    optional; falls back to DEFAULT_MODEL below
  OPENROUTER_PROVIDER optional; comma-separated allowlist of provider
                      slugs. When set, OpenRouter will ONLY route to
                      these providers (no fallback to others). Use
                      this to pin a model to its cheapest source —
                      e.g. DeepSeek V4 Pro is ~$0.44/M input via
                      `deepseek` but ~5x that via `fireworks`. Set
                      `OPENROUTER_PROVIDER=deepseek` to enforce.

Default model: `meta-llama/llama-3.3-70b-instruct:free`. Free tier,
strong JSON-output reliability. If free-tier rate limits become a
problem, drop in a paid pennies-per-call model via the env var:

  $env:OPENROUTER_MODEL = "deepseek/deepseek-v4-pro"             # ~$0.44/M in, $0.87/M out
  $env:OPENROUTER_PROVIDER = "deepseek"                          # pin to cheap provider
  $env:OPENROUTER_MODEL = "google/gemini-flash-1.5-8b"           # ~$0.04 / 1M tokens
  $env:OPENROUTER_MODEL = "openai/gpt-4o-mini"                   # ~$0.15 / 1M tokens
  $env:OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"          # if you have credit
"""

from __future__ import annotations

import json as _json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_FALLBACK_MODEL = "google/gemini-flash-1.5-8b"
DEFAULT_TIMEOUT_S = 30.0
MAX_RETRIES = 2  # additional attempts on transient failure (3 total)
RETRY_BACKOFF_S = 0.8

# Optional analytics headers OpenRouter uses for their leaderboards.
# Harmless if missing; useful for the team to see traffic in the
# OpenRouter dashboard.
_REFERER = "https://marketlens-web.onrender.com"
_TITLE = "UW MarketLens"

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter call fails (network error, non-200
    response, missing key). Callers in resolution.py + tagger.py
    catch this and fall through to their documented fallback paths."""


@dataclass
class LlmResponse:
    """Output of `call_chat`. Carries both the text content and the
    model that produced it so callers can surface "model used: X" in
    the UI (matters because the primary model may have failed and we
    fell back to a cheaper one)."""
    content: str
    model: str
    used_fallback: bool = False


def has_openrouter_key() -> bool:
    """True iff OPENROUTER_API_KEY is set. Use this to decide between
    a live LLM call and the fallback path without raising."""
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def _resolve_model(model: str | None) -> str:
    if model:
        return model
    return os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL


def _resolve_provider_block() -> dict | None:
    """If `OPENROUTER_PROVIDER` is set, return the `provider` request-
    body block that pins OpenRouter to those providers with no
    fallback. Comma-separated values support multi-provider
    allowlists (e.g. "deepseek,deepinfra"). Returns None when the
    env var is unset so the request body omits the field and
    OpenRouter routes normally."""
    raw = os.environ.get("OPENROUTER_PROVIDER")
    if not raw:
        return None
    providers = [p.strip() for p in raw.split(",") if p.strip()]
    if not providers:
        return None
    # `order` + `allow_fallbacks: false` is the documented OpenRouter
    # pattern for "only these providers, fail if none available."
    # Critical for cost control: DeepSeek V4 Pro is ~$0.44/M input
    # via the `deepseek` provider but several times that via
    # Fireworks / Together / etc. Without this, OpenRouter may
    # silently route to a more expensive provider during DeepSeek
    # rate-limit spikes.
    return {
        "order": providers,
        "allow_fallbacks": False,
    }


def _single_attempt(
    http_client: httpx.Client,
    api_key: str,
    body: dict[str, Any],
) -> str:
    """One HTTP POST. Returns the message content or raises
    OpenRouterError. Callers handle retry / fallback policy."""
    try:
        response = http_client.post(
            OPENROUTER_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": _REFERER,
                "X-Title": _TITLE,
                "Content-Type": "application/json",
            },
            json=body,
        )
    except httpx.HTTPError as exc:
        raise OpenRouterError(f"OpenRouter network error: {exc}") from exc

    if response.status_code != 200:
        raise OpenRouterError(
            f"OpenRouter HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )

    try:
        payload = response.json()
    except _json.JSONDecodeError as exc:
        raise OpenRouterError(
            f"OpenRouter returned non-JSON body: {exc}"
        ) from exc

    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        raise OpenRouterError(
            f"OpenRouter response missing 'choices': {str(payload)[:300]}"
        )
    first = choices[0]
    if not isinstance(first, dict):
        raise OpenRouterError("OpenRouter response 'choices[0]' not a dict")
    message = first.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise OpenRouterError(
            "OpenRouter response missing 'choices[0].message.content'"
        )
    return content


def call_chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 512,
    json_mode: bool = False,
    client: httpx.Client | None = None,
) -> LlmResponse:
    """POST a chat-completions request to OpenRouter with retry +
    fallback. Returns an `LlmResponse` carrying the content, the
    model that actually produced it, and whether the fallback fired.

    Retry policy
    ------------
    The primary model is tried up to MAX_RETRIES+1 times with a brief
    backoff between attempts. Common DeepSeek-via-OpenRouter symptoms
    (5xx, "no instances available", transient network errors) are
    typically transient — retrying once or twice usually clears them.

    Fallback policy
    ---------------
    If the primary model still fails after retries, we make one
    attempt against the fallback model (`OPENROUTER_FALLBACK_MODEL`
    env var, defaults to `google/gemini-flash-1.5-8b`). The fallback
    request is sent without the provider pin (different provider
    space) so it has a clean chance to succeed even if the primary
    provider is down. `used_fallback=True` on the response so the UI
    can surface "Model used: X (fallback)".

    Parameters
    ----------
    messages
        OpenAI-format message list. e.g.
        `[{"role": "system", "content": "..."},
          {"role": "user", "content": "..."}]`.
    model
        Override the env-var/default model on a per-call basis. Tests
        use this; production should set OPENROUTER_MODEL once.
    max_tokens
        Cap on output length. Defaults to 512.
    json_mode
        When True, sends `response_format: {"type": "json_object"}`.
        Most modern models honor this; ones that don't simply ignore
        the field.

    Returns
    -------
    LlmResponse
        `.content` is the assistant's message text. `.model` is the
        model that produced it (primary or fallback). `.used_fallback`
        is True iff the primary failed and the fallback succeeded.

    Raises
    ------
    OpenRouterError
        Both primary and fallback failed, OR the API key is missing.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not set")

    primary_model = _resolve_model(model)
    provider_block = _resolve_provider_block()
    fallback_model = (
        os.environ.get("OPENROUTER_FALLBACK_MODEL") or DEFAULT_FALLBACK_MODEL
    )

    def _body_for(target_model: str, *, with_provider: bool) -> dict:
        body: dict[str, Any] = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if with_provider and provider_block is not None:
            body["provider"] = provider_block
        return body

    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    close_client = client is None
    try:
        # Primary with retry
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                content = _single_attempt(
                    http_client, api_key,
                    _body_for(primary_model, with_provider=True),
                )
                return LlmResponse(
                    content=content,
                    model=primary_model,
                    used_fallback=False,
                )
            except OpenRouterError as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "OpenRouter primary attempt %d/%d failed (%s); "
                        "retrying after %.1fs",
                        attempt + 1, MAX_RETRIES + 1, exc,
                        RETRY_BACKOFF_S,
                    )
                    time.sleep(RETRY_BACKOFF_S)

        # Fallback (single attempt, no provider pin — different
        # provider space than the primary)
        if fallback_model and fallback_model != primary_model:
            logger.warning(
                "OpenRouter primary %s exhausted retries (%s); "
                "trying fallback %s",
                primary_model, last_exc, fallback_model,
            )
            try:
                content = _single_attempt(
                    http_client, api_key,
                    _body_for(fallback_model, with_provider=False),
                )
                return LlmResponse(
                    content=content,
                    model=fallback_model,
                    used_fallback=True,
                )
            except OpenRouterError as exc:
                # Propagate the fallback's error since it's most recent
                raise OpenRouterError(
                    f"OpenRouter primary ({primary_model}) and fallback "
                    f"({fallback_model}) both failed. Primary: {last_exc}. "
                    f"Fallback: {exc}"
                ) from exc

        # No fallback configured (or equal to primary) — surface the
        # primary failure
        assert last_exc is not None
        raise last_exc
    finally:
        if close_client:
            http_client.close()
