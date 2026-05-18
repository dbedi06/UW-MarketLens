"""
Deterministic mock data — THE SWAP-OUT POINT.

Everything fake lives here. When real sections land (S1 ingestion, S3 anomaly,
S4/S5 LLM, S6 citation, S7 composite score), the route handlers call those
modules instead of these functions and this file is deleted. Nothing in the
frontend or the route signatures changes.

"Deterministic" means: the same URL always produces the same numbers. We hash
the URL and derive every value from that hash, so a demo is stable and
repeatable instead of random each refresh.
"""

import hashlib
from .schemas import (
    MarketScore, Subscores, AnomalyResult, ResolutionVerdict,
    Tags, Citation, LibraryEntry,
)

_DEPARTMENTS = ["POLS", "ECON", "INFO", "EVANS"]


def _seed(url: str) -> int:
    """Stable integer seed from the URL (sha256 → int)."""
    return int(hashlib.sha256(url.encode()).hexdigest(), 16)


def _pct(seed: int, salt: int) -> int:
    """Derive a stable 0–100 value from the seed and a salt."""
    return (seed // (salt + 1)) % 101


def _band(score: int) -> str:
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"


def _question_from_url(url: str) -> str:
    """Fake a readable question from the URL slug."""
    slug = url.rstrip("/").split("/")[-1].split("?")[0]
    words = slug.replace("-", " ").strip()
    return words.capitalize() + "?" if words else "Untitled market?"


def make_citation(url: str, style: str = "APA") -> Citation:
    """PLACEHOLDER citation — real version is S6."""
    q = _question_from_url(url)
    seed = _seed(url)
    score = _pct(seed, 1)
    flag = (
        "RELIABLE (score ≥ 70)" if score >= 70
        else "USE WITH CAUTION — reliability below integrity threshold"
    )
    apa = f'Polymarket. (n.d.). {q} Retrieved from {url}'
    mla = f'"{q}" Polymarket, {url}.'
    return Citation(apa=apa, mla=mla, reliability_flag=flag)


def make_market_score(url: str) -> MarketScore:
    """PLACEHOLDER composite — real version is S7 combining S3/S4/liquidity."""
    seed = _seed(url)
    liquidity = _pct(seed, 2)
    anomaly_sub = _pct(seed, 3)
    resolution_sub = _pct(seed, 4)
    # simple average stands in for the real deterministic composite (S7)
    overall = round((liquidity + anomaly_sub + resolution_sub) / 3)

    verdict_pool = ["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"]
    verdict = verdict_pool[seed % 4]
    depts = [_DEPARTMENTS[seed % 4]]
    if seed % 3 == 0:
        depts.append(_DEPARTMENTS[(seed + 1) % 4])

    return MarketScore(
        market_url=url,
        market_question=_question_from_url(url),
        reliability_score=overall,
        band=_band(overall),
        subscores=Subscores(
            liquidity_health=liquidity,
            anomaly=anomaly_sub,
            resolution_quality=resolution_sub,
        ),
        anomaly=AnomalyResult(
            score=round((100 - anomaly_sub) / 100, 3),
            flagged_windows=seed % 5,
            top_features=["volume_spike", "spread_widening", "trader_concentration"][: 1 + seed % 3],
        ),
        resolution=ResolutionVerdict(
            verdict=verdict,
            reasoning="PLACEHOLDER reasoning — replaced by S4 LLM-as-judge output.",
            supporting_sources=["https://apnews.com/", "https://reuters.com/"][: 1 + seed % 2],
        ),
        tags=Tags(departments=depts, course_applicability=_pct(seed, 5)),
        citation=make_citation(url),
    )


def make_library() -> list[LibraryEntry]:
    """PLACEHOLDER library — real version is auto-populated by S5 tagger."""
    sample_urls = [
        "https://polymarket.com/event/will-the-fed-cut-rates-in-2025",
        "https://polymarket.com/event/us-presidential-election-popular-vote",
        "https://polymarket.com/event/will-gpt-5-release-this-year",
        "https://polymarket.com/event/wa-state-ballot-measure-passes",
        "https://polymarket.com/event/global-temperature-record-2025",
    ]
    entries = []
    for u in sample_urls:
        ms = make_market_score(u)
        entries.append(
            LibraryEntry(
                market_url=ms.market_url,
                market_question=ms.market_question,
                reliability_score=ms.reliability_score,
                band=ms.band,
                departments=ms.tags.departments,
                verified=_seed(u) % 2 == 0,
            )
        )
    return entries
