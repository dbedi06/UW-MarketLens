from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

NEWS_API_BASE = "https://newsapi.org/v2/everything"
CLAUDE_API_BASE = "https://api.anthropic.com/v1/messages"
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
    # Claude was given, so a reader can audit the evidence behind the
    # verdict rather than trusting the verdict + URL list alone. Each
    # entry: {title, description, url}.
    supporting_snippets: list[dict[str, str]] = field(default_factory=list)


def has_resolution_keys() -> bool:
    return bool(os.environ.get("NEWS_API_KEY") and os.environ.get("ANTHROPIC_API_KEY"))


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


def call_claude(question: str, snippets: list[str], *, resolved: bool = False, client: httpx.Client | None = None) -> ClaudePayload:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    prompt = _build_prompt(question, resolved, snippets)
    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    close_client = client is None
    try:
        response = http_client.post(
            CLAUDE_API_BASE,
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20240620"),
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("content")
        if isinstance(text, list):
            text = "".join(item.get("text", "") for item in text if isinstance(item, dict))
        if not isinstance(text, str):
            raise ValueError("Claude response missing text content")
        parsed = json.loads(text)
        return ClaudePayload.model_validate(parsed)
    finally:
        if close_client:
            http_client.close()


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

        payload = call_claude(question, snippets, resolved=resolved, client=client)
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
        )
    except Exception:
        return _fallback_assessment("Resolution checking failed; falling back to UNVERIFIABLE.")
