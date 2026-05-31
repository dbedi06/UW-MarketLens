"""
S5 — LLM Course Tagger
======================
Tags a Polymarket market question with relevant UW departments and a
course applicability score using Claude via few-shot prompting.

Public entry points
-------------------
  tag_market(question)  ->  TagResult
      Call Claude with a few-shot prompt and return department tags
      plus a 0-100 course applicability score.

  has_tagger_key()  ->  bool
      Returns True if ANTHROPIC_API_KEY is set. Callers use this to
      decide whether to call the real tagger or fall back to mock tags.

Design notes
------------
  - Results are cached in memory by question text so repeated lookups
    within one server lifecycle don't burn API calls.
  - The rubric and few-shot examples are committed here, not in a
    separate file, so the tagger is self-contained and auditable.
  - Claude is prompted to return JSON only — no markdown fences,
    no preamble. The parser strips fences defensively just in case.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

import httpx

CLAUDE_API_BASE = "https://api.anthropic.com/v1/messages"
DEFAULT_TIMEOUT_S = 20.0

DEPARTMENTS = ["POLS", "ECON", "INFO", "EVANS"]
DEPT_LABEL = {
    "POLS": "Political Science",
    "ECON": "Economics",
    "INFO": "Information School",
    "EVANS": "Evans School of Public Policy",
}

# ── In-memory cache ───────────────────────────────────────────────────────────
_CACHE: dict[str, "TagResult"] = {}


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class TagResult:
    departments: list[str]          # subset of DEPARTMENTS
    course_applicability: int       # 0-100
    used_fallback: bool = False


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = """You tag Polymarket prediction market questions with UW departments
and a course applicability score.

Departments to choose from (use the code, not the label):
  POLS  — Political Science  (elections, policy, geopolitics, legislation)
  ECON  — Economics          (interest rates, GDP, inflation, trade, markets)
  INFO  — Information School (tech companies, AI, social media, data)
  EVANS — Evans School       (public policy, government spending, regulation)

Rules:
  - Return only the departments that genuinely apply. Most questions get 1-2.
  - course_applicability: 0-100 integer. How useful is this market as a
    classroom example or research data point?
    90-100: textbook example of the field, rich data, clear outcome
    70-89:  relevant and usable, minor caveats
    40-69:  tangentially related or low data quality
    0-39:   not useful for coursework

Return ONLY valid JSON. No markdown, no explanation. Schema:
{"departments": ["CODE", ...], "course_applicability": <int>}"""

_FEW_SHOT = [
    {
        "role": "user",
        "content": "Will the Federal Reserve cut interest rates before July 2025?"
    },
    {
        "role": "assistant",
        "content": '{"departments": ["ECON", "EVANS"], "course_applicability": 92}'
    },
    {
        "role": "user",
        "content": "Will Donald Trump win the 2024 US presidential election?"
    },
    {
        "role": "assistant",
        "content": '{"departments": ["POLS", "EVANS"], "course_applicability": 88}'
    },
    {
        "role": "user",
        "content": "Will GPT-5 be released before the end of 2024?"
    },
    {
        "role": "assistant",
        "content": '{"departments": ["INFO"], "course_applicability": 74}'
    },
    {
        "role": "user",
        "content": "Will Lionel Messi score in the Champions League final?"
    },
    {
        "role": "assistant",
        "content": '{"departments": [], "course_applicability": 12}'
    },
]


def has_tagger_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _fallback(question: str) -> TagResult:
    """
    Rule-based fallback when the API key is absent or the call fails.
    Covers the most common cases so the app still works without keys.
    """
    q = question.lower()
    depts: list[str] = []
    if any(w in q for w in ["election", "president", "congress", "senate", "vote",
                              "legislat", "geopolit", "war", "treaty", "nato"]):
        depts.append("POLS")
    if any(w in q for w in ["rate", "gdp", "inflation", "trade", "tariff",
                              "market", "stock", "fed", "recession", "employ"]):
        depts.append("ECON")
    if any(w in q for w in ["ai", "gpt", "openai", "tech", "google", "apple",
                              "microsoft", "meta", "social media", "data"]):
        depts.append("INFO")
    if any(w in q for w in ["policy", "regulation", "spending", "budget",
                              "government", "agency", "public"]):
        depts.append("EVANS")
    score = 70 if depts else 20
    return TagResult(departments=depts, course_applicability=score, used_fallback=True)


def _parse_response(text: str) -> dict:
    # Strip markdown fences if Claude adds them despite instructions
    text = re.sub(r"```(?:json)?", "", text).strip()
    return json.loads(text)


def tag_market(
    question: str,
    client: httpx.Client | None = None,
) -> TagResult:
    """
    Tag a market question with UW departments and a course applicability score.

    Falls back gracefully if ANTHROPIC_API_KEY is not set or the call fails.
    Results are cached by question text.
    """
    cache_key = question.strip().lower()
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    if not has_tagger_key():
        result = _fallback(question)
        _CACHE[cache_key] = result
        return result

    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S)
    close_client = client is None
    try:
        messages = _FEW_SHOT + [{"role": "user", "content": question}]
        response = http_client.post(
            CLAUDE_API_BASE,
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                "max_tokens": 128,
                "system": _SYSTEM,
                "messages": messages,
            },
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("content", [])
        if isinstance(text, list):
            text = "".join(
                item.get("text", "") for item in text if isinstance(item, dict)
            )
        parsed = _parse_response(text)

        # Validate departments against the allowed set
        raw_depts = parsed.get("departments", [])
        depts = [d for d in raw_depts if d in DEPARTMENTS]
        score = max(0, min(100, int(parsed.get("course_applicability", 50))))

        result = TagResult(departments=depts, course_applicability=score)
        _CACHE[cache_key] = result
        return result

    except Exception:
        result = _fallback(question)
        _CACHE[cache_key] = result
        return result
    finally:
        if close_client:
            http_client.close()


def clear_cache() -> None:
    """Tests use this to reset between cases."""
    _CACHE.clear()
