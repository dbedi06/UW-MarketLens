"""Discover candidate labeled cases for the S3 labeled-eval by mining
NewsAPI for manipulation/controversy coverage of Polymarket markets.

What it does
------------
1. Query NewsAPI for ~12 manipulation-related search terms.
2. For each article, try to extract a `polymarket.com/event/<slug>` URL
   from the title/description/content.
3. For URLs we can directly extract: stage as `controversial` candidates
   with the article URL as `evidence_url`.
4. For ones we can't: try Gamma's slug search using the article headline
   tokens. Tag those as `slug_inferred=true` so the team knows the
   match might be wrong.
5. Sample mundane candidates from the local corpus (built via
   `build_real_corpus.py`) — markets the team is unlikely to have read
   reporting on.
6. Append all candidates to `labeled_cases.yaml` with `labeler:
   LK-candidate-v2`. Existing entries are preserved; the team
   verifies these against rubric v1 before any number is quoted.

We do not fabricate evidence URLs. Every `evidence_url` produced by
this script points at a real NewsAPI article. Whether the article
actually describes the inferred market is for the team to confirm.

Usage
-----
    $env:NEWS_API_KEY = "<key>"
    python -m scripts.discover_labeled_candidates \
        --max-controversial 8 --max-mundane 6
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.anomaly.labeled import DEFAULT_CASES_PATH  # noqa: E402
from app.anomaly.scoring import CORPUS_DIR  # noqa: E402
from app.ingestion.polymarket import GAMMA_BASE  # noqa: E402

NEWS_API_BASE = "https://newsapi.org/v2/everything"
POLYMARKET_URL_RE = re.compile(
    r"https?://(?:www\.)?polymarket\.com/event/([a-z0-9-]+)",
    re.IGNORECASE,
)

# Search terms — focused enough to surface real manipulation reporting
# without drowning in adjacent "Polymarket reaches $X volume" puff.
_QUERIES = [
    "polymarket manipulation",
    "polymarket wash trade",
    "polymarket suspicious trading",
    "polymarket sybil",
    "polymarket whale manipulation",
    "polymarket controversy",
    "polymarket coordinated",
    "polymarket spoofing",
    "polymarket fraud",
    "polymarket wallet cluster",
    "polymarket fake volume",
    "polymarket pump",
]


def _fetch_articles_for_query(
    client: httpx.Client, q: str, *, page_size: int = 10,
) -> list[dict]:
    """One NewsAPI query → up to `page_size` articles. On any failure
    returns []."""
    try:
        r = client.get(
            NEWS_API_BASE,
            params={
                "q": q,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": page_size,
                "apiKey": os.environ["NEWS_API_KEY"],
            },
            timeout=20.0,
        )
        r.raise_for_status()
        return r.json().get("articles", []) or []
    except Exception as exc:
        print(f"[warn] query {q!r} failed: {exc}", file=sys.stderr)
        return []


def _extract_polymarket_url(article: dict) -> str | None:
    """Find a polymarket.com/event/... URL in any field of the article."""
    blobs = [
        article.get("title") or "",
        article.get("description") or "",
        article.get("content") or "",
        article.get("url") or "",
    ]
    for blob in blobs:
        m = POLYMARKET_URL_RE.search(blob)
        if m:
            slug = m.group(1).lower()
            return f"https://polymarket.com/event/{slug}"
    return None


def _gamma_slug_search(
    client: httpx.Client, headline: str,
) -> tuple[str | None, bool]:
    """Fuzzy fallback: send a few headline words to Gamma /events?slug=.
    Polymarket's slug-search matches by prefix. Returns (url,
    slug_inferred). Best-effort — when fuzzy match fails returns
    (None, True)."""
    # Strip punctuation, take 3-4 most-content-y words
    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", headline)]
    tokens = [t for t in tokens if len(t) > 3 and t not in (
        "polymarket", "market", "wallet", "trader", "trade", "this", "that",
        "with", "from", "have", "will", "what", "when", "where", "which",
        "into", "after", "before", "during",
    )][:4]
    if not tokens:
        return None, True
    slug = "-".join(tokens)
    try:
        r = client.get(
            f"{GAMMA_BASE}/events",
            params={"slug": slug, "limit": 1},
            timeout=10.0,
        )
        r.raise_for_status()
        events = r.json()
        if isinstance(events, list) and events:
            ev_slug = events[0].get("slug", "")
            if ev_slug:
                return f"https://polymarket.com/event/{ev_slug}", True
    except Exception:
        pass
    return None, True


def _load_corpus_market_urls() -> list[tuple[str, str]]:
    """Return [(market_url, question), ...] from the corpus directory.
    Used for sampling mundane candidates."""
    out = []
    for p in sorted(CORPUS_DIR.glob("*.json")):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            url = raw.get("market_url", "")
            q = raw.get("question", "")
            if url:
                out.append((url, q))
        except Exception:
            continue
    return out


def _load_existing_cases(path: Path) -> dict:
    """Read the labeled-cases YAML, return the parsed object. Creates
    a stub if the file is missing."""
    if not path.exists():
        return {"schema_version": 1, "rubric_version": "v1", "cases": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {
        "schema_version": 1, "rubric_version": "v1", "cases": [],
    }


def _existing_urls(blob: dict) -> set[str]:
    return {c.get("market_url", "") for c in (blob.get("cases") or [])}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-controversial", type=int, default=8)
    p.add_argument("--max-mundane", type=int, default=6)
    p.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    args = p.parse_args()

    if not os.environ.get("NEWS_API_KEY"):
        print("[error] NEWS_API_KEY not set. Get a free key at "
              "https://newsapi.org and export it.", file=sys.stderr)
        return 2

    blob = _load_existing_cases(args.cases)
    already = _existing_urls(blob)
    today = date.today().isoformat()

    # ── Controversial candidates ──────────────────────────────────────
    print(f"[search] running {len(_QUERIES)} NewsAPI queries...")
    all_articles: list[dict] = []
    with httpx.Client() as client:
        for q in _QUERIES:
            articles = _fetch_articles_for_query(client, q)
            for a in articles:
                a["_query"] = q
            all_articles.extend(articles)

    print(f"[search] got {len(all_articles)} articles total")

    controversial: list[dict] = []
    inferred_count = 0
    seen_articles: set[str] = set()
    with httpx.Client() as client:
        for article in all_articles:
            art_url = (article.get("url") or "").strip()
            if not art_url or art_url in seen_articles:
                continue
            seen_articles.add(art_url)

            market_url = _extract_polymarket_url(article)
            slug_inferred = False
            if market_url is None:
                # Try the fuzzy slug fallback
                market_url, slug_inferred = _gamma_slug_search(
                    client, article.get("title") or "",
                )
                if market_url is None:
                    continue
                inferred_count += 1

            if market_url in already:
                continue
            already.add(market_url)

            note = article.get("title") or ""
            if slug_inferred:
                note = f"{note} [slug_inferred from headline]"
            controversial.append({
                "market_url":      market_url,
                "label":           "controversial",
                "evidence_url":    art_url,
                "notes":           (note + " — flagged by NewsAPI query "
                                    f"{article.get('_query')!r}; review "
                                    f"the article URL before quoting"),
                "date_documented": today,
                "labeler":         "LK-candidate-v2",
                "rubric_version":  "v1",
            })
            if len(controversial) >= args.max_controversial:
                break

    # ── Mundane candidates from the corpus ────────────────────────────
    print(f"[mundane] sampling from corpus...")
    corpus = _load_corpus_market_urls()
    # Exclude any URL already in cases or in the controversial list
    controversial_urls = {c["market_url"] for c in controversial}
    mundane: list[dict] = []
    for url, question in corpus:
        if url in already or url in controversial_urls:
            continue
        # We don't run an inverse news query (cost) — the team should
        # spot-check these for unexpected controversy.
        mundane.append({
            "market_url":      url,
            "label":           "mundane",
            "evidence_url":    None,
            "notes":           (f"{question} — sampled from training corpus; "
                                "no manipulation reporting surfaced in the "
                                "candidate query. Team: best-effort search "
                                "for controversy before accepting"),
            "date_documented": today,
            "labeler":         "LK-candidate-v2",
            "rubric_version":  "v1",
        })
        if len(mundane) >= args.max_mundane:
            break

    new_cases = controversial + mundane
    if not new_cases:
        print("[done] no new candidates discovered.")
        return 0

    # Append + write back. YAML output: we re-serialize the whole file
    # so the schema_version header is preserved.
    blob.setdefault("cases", []).extend(new_cases)
    args.cases.write_text(
        yaml.safe_dump(blob, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"[done] appended {len(controversial)} controversial "
          f"({inferred_count} slug-inferred) + {len(mundane)} mundane "
          f"candidates to {args.cases}")
    print("[next] team verifies under rubric v1 before any number "
          "from eval_on_labeled gets quoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
