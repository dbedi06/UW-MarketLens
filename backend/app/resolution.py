from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2/everything"
DEFAULT_TIMEOUT_S = 15.0
MAX_SOURCES = 3


class ClaudePayload(BaseModel):
    verdict: Literal["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"]
    reasoning: str
    supporting_sources: list[str]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


@dataclass
class ResolutionAssessment:
    verdict: Literal["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"]
    reasoning: str
    supporting_sources: list[str]
    confidence: float
    resolution_quality: int
    used_fallback: bool
    # PISAN-flagged honesty fix: surface the actual NewsAPI snippets
    # the LLM was given, so a reader can audit the evidence behind
    # the verdict. Each entry: {title, description, url}.
    supporting_snippets: list[dict[str, str]] = field(default_factory=list)
    # Which LLM produced this verdict — surfaces in the UI as
    # "Model: deepseek/deepseek-v4-pro" so users can see when a
    # fallback fired. Empty for fallback-assessment cases (no LLM
    # ever ran).
    model_used: str = ""
    model_was_fallback: bool = False


def has_resolution_keys() -> bool:
    return bool(
        os.environ.get("NEWS_API_KEY")
        and os.environ.get("OPENROUTER_API_KEY")
    )


def _fallback_assessment(reason: str) -> ResolutionAssessment:
    return ResolutionAssessment(
        verdict="UNVERIFIABLE",
        reasoning=reason,
        supporting_sources=[],
        confidence=0.0,
        resolution_quality=0,
        used_fallback=True,
    )


def _build_prompt(question: str, resolved: bool, snippets: list[str]) -> str:
    resolved_hint = (
        "The market is already resolved according to the supplied metadata."
        if resolved
        else "The market is not yet resolved according to the supplied metadata."
    )
    snippets_block = "\n".join(f"- {snippet}" for snippet in snippets[:5]) or "- No article snippets were returned."
    return (
        "You are evaluating whether a prediction-market resolution is well-supported "
        "by independent reporting.\n"
        "Return ONLY valid JSON with these keys: verdict, reasoning, supporting_sources, confidence.\n"
        "verdict must be one of HIGH, MEDIUM, LOW, UNVERIFIABLE.\n"
        "reasoning should be a concise plain-language explanation.\n"
        "supporting_sources should be a list of URLs from the articles, or an empty list.\n"
        "confidence should be a number between 0 and 1.\n\n"
        f"Question: {question}\n"
        f"Metadata: {resolved_hint}\n"
        f"Independent reporting snippets:\n{snippets_block}\n"
    )


def _clean_sources(sources: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for src in sources:
        src = src.strip()
        if not src or not (src.startswith("http://") or src.startswith("https://")):
            continue
        if src not in seen:
            seen.add(src)
            out.append(src)
    return out[:MAX_SOURCES]


def _quality_from_payload(payload: ClaudePayload) -> int:
    return max(0, min(100, int(round(payload.confidence * 100))))


def _extract_articles(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    articles = payload.get("articles")
    if not isinstance(articles, list):
        return []
    out: list[dict[str, str]] = []
    for article in articles[:MAX_SOURCES]:
        if not isinstance(article, dict):
            continue
        title = str(article.get("title") or "").strip()
        description = str(article.get("description") or "").strip()
        url = str(article.get("url") or "").strip()
        if not url:
            continue
        out.append({"title": title, "description": description, "url": url})
    return out


def _snippets_from_articles(articles: list[dict[str, str]]) -> list[str]:
    snippets: list[str] = []
    for article in articles:
        title = article.get("title") or ""
        description = article.get("description") or ""
        if title and description:
            snippets.append(f"{title} — {description}")
        elif title:
            snippets.append(title)
        elif description:
            snippets.append(description)
    return snippets


def fetch_news_articles(question: str, client: httpx.Client | None = None) -> list[dict[str, str]]:
    if not os.environ.get("NEWS_API_KEY"):
        return []

    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    close_client = client is None
    try:
        response = http_client.get(
            NEWS_API_BASE,
            params={
                "q": question,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 3,
                "apiKey": os.environ["NEWS_API_KEY"],
            },
        )
        response.raise_for_status()
        payload = response.json()
        return _extract_articles(payload)
    except Exception:
        return []
    finally:
        if close_client:
            http_client.close()


def call_llm(
    question: str,
    snippets: list[str],
    *,
    resolved: bool = False,
    client: httpx.Client | None = None,
) -> tuple[ClaudePayload, str, bool]:
    """Run the LLM-as-judge prompt through OpenRouter and parse the
    structured JSON response. Returns (payload, model_used,
    used_fallback) so callers can surface which model ran. The class
    is still called `ClaudePayload` for backward-compat but the call
    is provider-agnostic."""
    from .llm_client import call_chat

    prompt = _build_prompt(question, resolved, snippets)
    resp = call_chat(
        [{"role": "user", "content": prompt}],
        max_tokens=512,
        json_mode=True,
        client=client,
    )
    parsed = json.loads(resp.content)
    return ClaudePayload.model_validate(parsed), resp.model, resp.used_fallback


# Back-compat alias for any external caller that still imports the
# old function name. New code should call `call_llm`.
call_claude = call_llm


def resolve_market(
    question: str,
    *,
    resolved: bool = False,
    client: httpx.Client | None = None,
) -> ResolutionAssessment:
    if not has_resolution_keys():
        return _fallback_assessment(
            "Resolution checking is not configured; NEWS_API_KEY and ANTHROPIC_API_KEY are required."
        )

    try:
        articles = fetch_news_articles(question, client=client)
        snippets = _snippets_from_articles(articles)
        if not snippets:
            return _fallback_assessment("No independent reporting snippets were available for verification.")

        payload, model_used, model_was_fallback = call_llm(
            question, snippets, resolved=resolved, client=client,
        )
        sources = _clean_sources(payload.supporting_sources)
        reasoning = payload.reasoning.strip() or "No reasoning was returned by the checker."
        return ResolutionAssessment(
            verdict=payload.verdict,
            reasoning=reasoning,
            supporting_sources=sources,
            confidence=float(payload.confidence),
            resolution_quality=_quality_from_payload(payload),
            used_fallback=False,
            supporting_snippets=articles,
            model_used=model_used,
            model_was_fallback=model_was_fallback,
        )
    except Exception as exc:
        # Without this log the live route silently returns
        # resolution_quality=0 whenever OpenRouter, NewsAPI, or JSON
        # parsing throws — and the production deploy has no way to
        # diagnose why. Log the full exception so Render logs surface
        # the real failure ("OpenRouter HTTP 401: ...", "expecting
        # value: line 1 column 1", etc.).
        logger.exception("resolve_market failed (%s); returning UNVERIFIABLE", exc)
        return _fallback_assessment(
            f"Resolution checking failed ({type(exc).__name__}); falling back to UNVERIFIABLE."
        )
