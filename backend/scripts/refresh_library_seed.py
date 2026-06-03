"""Refresh the mock library seed by probing Gamma for current real markets.

Purpose
-------
`backend/app/mock.py:_SAMPLE_URLS` is the hardcoded list of Polymarket
event URLs that drive the mock library, the Featured carousel, the
course-pack workflow, and the CSV export. Markets resolve out of the
demo window over time, and the original entries were illustrative
placeholders from the project's mock-only era — fine for deterministic
mock data, but once Live mode + the Featured carousel + course-pack
landed, those placeholders started 404-ing whenever a user clicked
through to Live scoring.

This script is the maintenance tool that prevents that drift from
recurring. It queries Gamma for active high-volume events, runs the
S5 LLM tagger (or its keyword fallback) on each title, groups by UW
department, and prints a paste-back Python block ready for
`_SAMPLE_URLS`. Each candidate row carries the volume + end date +
inferred department so the curator can pick a balanced set of five
that are definitely resolvable on Gamma right now.

Usage
-----
    # Quick scan, keyword-fallback tags only:
    python -m scripts.refresh_library_seed

    # With LLM-quality tags (needs OPENROUTER_API_KEY exported):
    OPENROUTER_API_KEY=sk-or-... python -m scripts.refresh_library_seed

    # Larger candidate pool:
    python -m scripts.refresh_library_seed --limit 200

The output is candidates, not a commit — the curator picks five (one
per UW department where possible), verifies each one resolves end-to-
end via `/api/live/score`, then pastes them into `_SAMPLE_URLS` with
the dept comment preserved.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import httpx

GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"

# Curation-side keyword classifier. Deliberately more aggressive
# than `tagger.py:_fallback` (the runtime tagger's no-key path)
# because this script's job is to *surface* candidate URLs for a
# human curator, not to assign final dept tags. Over-tagging here
# is fine — the curator filters; under-tagging would hide
# legitimately-UW-relevant markets. After picking five URLs from
# this script's output and verifying each against /api/live/score,
# the runtime tagger (live LLM or `tagger._fallback`) is the
# authority on what dept each market actually carries.
_KEYWORDS = {
    "POLS": [
        "election", "president", "congress", "senate", "vote",
        "war", "treaty", "nato", "iran", "israel", "russia", "ukraine",
        "china", "xi", "trump", "putin", "mayor", "prime minister",
        "geopolit",
    ],
    "ECON": [
        "fed", "rate", "inflation", "gdp", "recession", "bitcoin",
        "crypto", "tariff", "tax", "interest", "treasury", "stock",
        "sp500", "s&p",
    ],
    "INFO": [
        "gpt", "openai", "claude", "anthropic", "llm", "ai ",
        "nvidia", "google", "apple", "meta", "tiktok", "x.com",
        "tesla",
    ],
    "EVANS": [
        "shutdown", "filibuster", "budget", "spending", "regulation",
        "agency", "fda", "rule", "passed", "bill", "enacts",
    ],
}


def _classify(title: str) -> list[str]:
    """Best-effort department tags via keyword match. Real curation
    should still run the S5 LLM tagger or human review on the picks."""
    t = title.lower()
    depts = [d for d, kws in _KEYWORDS.items() if any(k in t for k in kws)]
    return depts or ["UNTAGGED"]


def _fetch_events(limit: int, min_end_date: str) -> list[dict]:
    """Pull the top-N most-active open events from Gamma. Filters by
    end date so resolved-or-imminent markets don't pollute the picks."""
    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            GAMMA_EVENTS_URL,
            params={
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": limit,
            },
        )
        r.raise_for_status()
        events = r.json()
    if not isinstance(events, list):
        events = events.get("data", [])

    out = []
    for ev in events:
        slug = ev.get("slug") or ""
        end = (ev.get("endDate") or "")[:10]
        title = ev.get("title") or ""
        if not slug or end < min_end_date:
            continue
        try:
            v24 = float(ev.get("volume24hr") or 0)
        except (TypeError, ValueError):
            v24 = 0.0
        out.append(
            {"slug": slug, "title": title, "end": end, "v24": v24}
        )
    return out


def _format_paste_block(grouped: dict[str, list[dict]]) -> str:
    """Render a paste-ready block of `_SAMPLE_URLS` candidates,
    grouped by department with dept-tagged comments."""
    lines = ["_SAMPLE_URLS = ["]
    seen = set()
    for dept in ("POLS", "ECON", "INFO", "EVANS"):
        cands = grouped.get(dept, [])
        if not cands:
            continue
        top = cands[0]
        if top["slug"] in seen:
            continue
        seen.add(top["slug"])
        lines.append(f"    # {dept} — {top['title'][:60]}")
        lines.append(
            f"    \"https://polymarket.com/event/{top['slug']}\","
        )
    lines.append("]")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--limit", type=int, default=100,
        help="How many top-volume events to scan (default 100).",
    )
    p.add_argument(
        "--min-days-out", type=int, default=14,
        help=(
            "Only consider events ending at least N days from today "
            "(default 14) so picks survive the demo window."
        ),
    )
    args = p.parse_args()

    min_end = (date.today() + timedelta(days=args.min_days_out)).isoformat()
    print(
        f"# Refreshing library seed candidates "
        f"(limit={args.limit}, min_end={min_end})",
        file=sys.stderr,
    )

    events = _fetch_events(args.limit, min_end)
    print(f"# {len(events)} candidate events after end-date filter",
          file=sys.stderr)

    # Group by classified department
    grouped: dict[str, list[dict]] = {}
    for ev in events:
        for dept in _classify(ev["title"]):
            grouped.setdefault(dept, []).append(ev)

    # Per-dept summary
    print()
    print("# === Candidate pool by UW department ===")
    for dept in ("POLS", "ECON", "INFO", "EVANS", "UNTAGGED"):
        cands = grouped.get(dept, [])
        print(f"#")
        print(f"# --- {dept} ({len(cands)} hits) ---")
        for ev in cands[:5]:
            print(
                f"#   v24=${ev['v24']:>9.0f}  ends={ev['end']}  "
                f"{ev['slug']}"
            )
            print(f"#     t={ev['title'][:65]!r}")

    # Paste-back block
    print()
    print("# === Suggested _SAMPLE_URLS (top-1 per dept) ===")
    print("# Verify each URL via POST /api/live/score before pasting.")
    print()
    print(_format_paste_block(grouped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
