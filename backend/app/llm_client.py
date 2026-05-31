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

Default model: `meta-llama/llama-3.3-70b-instruct:free`. Free tier,
strong JSON-output reliability. If free-tier rate limits become a
problem, drop in a paid pennies-per-call model via the env var:

  $env:OPENROUTER_MODEL = "google/gemini-flash-1.5-8b"           # ~$0.04 / 1M tokens
  $env:OPENROUTER_MODEL = "openai/gpt-4o-mini"                   # ~$0.15 / 1M tokens
  $env:OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"          # if you have credit
"""

from __future__ import annotations

import json as _json
import os
from typing import Any

import httpx

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_TIMEOUT_S = 30.0

# Optional analytics headers OpenRouter uses for their leaderboards.
# Harmless if missing; useful for the team to see traffic in the
# OpenRouter dashboard.
_REFERER = "https://marketlens-web.onrender.com"
_TITLE = "UW MarketLens"


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter call fails (network error, non-200
    response, missing key). Callers in resolution.py + tagger.py
    catch this and fall through to their documented fallback paths."""


def has_openrouter_key() -> bool:
    """True iff OPENROUTER_API_KEY is set. Use this to decide between
    a live LLM call and the fallback path without raising."""
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def _resolve_model(model: str | None) -> str:
    if model:
        return model
    return os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL


def call_chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 512,
    json_mode: bool = False,
    client: httpx.Client | None = None,
) -> str:
    """POST a chat-completions request to OpenRouter; return the text
    of the first choice's message content.

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
        Cap on output length. Defaults to 512 (covers S4 + S5 with
        room to spare).
    json_mode
        When True, sends `response_format: {"type": "json_object"}`
        in the request body. Most modern models honor this and emit
        valid JSON without surrounding prose. Models that don't
        recognize the field simply ignore it; the caller still gets
        a string and parses it itself.

    Returns
    -------
    str
        The content of `choices[0].message.content`. Empty string if
        the response shape is unexpected (caller should guard).

    Raises
    ------
    OpenRouterError
        Missing API key, network failure, non-200 response, or a
        response body that doesn't include the expected fields.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not set")

    body: dict[str, Any] = {
        "model": _resolve_model(model),
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    close_client = client is None
    try:
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
    finally:
        if close_client:
            http_client.close()
