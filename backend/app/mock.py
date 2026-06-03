"""
Deterministic mock data — the offline / "Mock mode" fallback.

Status (as of S7 wiring)
------------------------
S1-S7 are now real and the live route (`/api/live/score`) goes through
`app.composite.make_market_score`. The frontend defaults to Live mode.
This module is still useful for:

  - `/api/score`                — Mock-mode toggle in the nav. Always
                                  responds even when Polymarket is down,
                                  the cache is cold, or API keys are
                                  missing. Useful for demos.
  - `/api/library`              — Mock-only today. The library page
                                  always shows mock data regardless of
                                  the frontend Live/Mock toggle (the
                                  page subtitle says so).
  - `/api/admin/pending-tags`   — Mock placeholder for the S5 tagger
                                  human-review queue.
  - `mock.register_snapshot` /  — Shared snapshot registry. Live snapshots
    `mock.resolve_snapshot_full`  use this too so the snapshot route can
                                  dispatch to live vs mock.

Determinism contract
--------------------
The same (url, as_of) always yields byte-identical output. We hash the
pair into a seed and derive every value from it, so a snapshot permalink
reopened next month renders the same number — Pillar 2 of the project
(a citation must be reproducible). This is the property that makes the
mock route safe as a fallback.

Field-by-field this is "real Pydantic models populated with placeholder
data" — the *shape* is the same shape `composite.make_market_score`
returns. That's why the frontend doesn't care which path served the
request beyond the `source` badge.

Future: when the live route has been validated end-to-end on real
markets with real labels, the project can swap `/api/score` to delegate
to `composite.make_market_score` and reduce this file to only the
library + admin mocks. Not yet.
"""

import hashlib
from datetime import date
from .schemas import (
    MarketScore, Subscores, AnomalyResult, ResolutionVerdict, Tags, Citation,
    LibraryEntry, ReasonItem, MarketMeta, AnomalyPoint, PendingTag,
)
# Mock library reuses the live tagger's keyword fallback to derive
# departments from question content rather than from the URL hash —
# PISAN line 14's hash-tagging critique. Importing the private
# `_fallback` is deliberate cross-module code reuse; the alternative
# (duplicating the keyword list here) would drift over time.
from .tagger import _fallback as _tagger_keyword_fallback

_DEPT_LABEL = {
    "POLS": "Political Science",
    "ECON": "Economics",
    "INFO": "Information School",
    "EVANS": "Evans School of Public Policy",
}


def _seed(url: str, as_of: str) -> int:
    return int(hashlib.sha256(f"{url}|{as_of}".encode()).hexdigest(), 16)


def _pct(seed: int, salt: int) -> int:
    return (seed // (salt + 1)) % 101


def _band(score: int) -> str:
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"


def _sev(value: int) -> str:
    return "good" if value >= 70 else "warn" if value >= 40 else "bad"


def _today() -> str:
    return date.today().isoformat()


def _question_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1].split("?")[0]
    words = slug.replace("-", " ").strip()
    return words.capitalize() + "?" if words else "Untitled market?"


def snapshot_id(url: str, as_of: str) -> str:
    return hashlib.sha256(f"{url}|{as_of}".encode()).hexdigest()[:12]


# Snapshot registry: id -> (url, as_of, source). Populated whenever a score
# is built. In-memory (resets on restart) — acceptable for mock because data
# is deterministic; for live, a cold cache after dyno wake means the snapshot
# route returns 503 (not silently-different data). Real S0/persistence would
# back this with a table.
SnapshotSource = str  # "mock" | "live"
_SNAPSHOTS: dict[str, tuple[str, str, SnapshotSource]] = {}


def register_snapshot(sid: str, url: str, as_of: str, source: str) -> None:
    """Record (url, as_of, source) for a snapshot id. Source must be 'live'
    or 'mock'; the snapshot route dispatches on it (B2 fix)."""
    if source not in {"live", "mock"}:
        raise ValueError(f"source must be 'live' or 'mock', got {source!r}")
    _SNAPSHOTS[sid] = (url, as_of, source)


def resolve_snapshot(sid: str) -> tuple[str, str] | None:
    """Back-compat: returns (url, as_of) without source. New callers should
    use `resolve_snapshot_full` so they can dispatch on origin."""
    row = _SNAPSHOTS.get(sid)
    return (row[0], row[1]) if row else None


def resolve_snapshot_full(sid: str) -> tuple[str, str, str] | None:
    return _SNAPSHOTS.get(sid)


# ---- The "why" (Pillar 1) -------------------------------------------------

def _reasons(seed: int, liquidity: int, anomaly_sub: int, resolution_sub: int,
             meta: MarketMeta) -> list[ReasonItem]:
    """Plain-language reasons. Numbers are deterministic from the seed so the
    sentence always matches the chart and scores."""
    price_swing = round(0.10 + (seed % 35) / 100, 2)  # 0.10–0.44
    swing_minutes = 8 + seed % 40

    liq = ReasonItem(
        factor="liquidity",
        severity=_sev(liquidity),
        headline=(
            "Healthy liquidity" if liquidity >= 70
            else "Thin liquidity" if liquidity < 40
            else "Moderate liquidity"
        ),
        detail=(
            f"${meta.liquidity_usd:,} of liquidity across {meta.unique_traders} "
            f"unique traders and ${meta.volume_usd:,} total volume. "
            + ("Deep enough that prices reflect broad consensus."
               if liquidity >= 70 else
               "Few traders means a single actor can move the price, so treat "
               "the implied probability with caution.")
        ),
    )
    ano = ReasonItem(
        factor="anomaly",
        severity=_sev(anomaly_sub),
        headline=(
            "No unusual trading detected" if anomaly_sub >= 70
            else "Suspicious trading pattern" if anomaly_sub < 40
            else "Minor trading irregularities"
        ),
        detail=(
            "Trade windows fall within normal market behavior."
            if anomaly_sub >= 70 else
            f"The model flagged a window where the price moved {price_swing:.2f} "
            f"in {swing_minutes} minutes on below-average volume. See the "
            f"highlighted span in the chart."
        ),
    )
    res = ReasonItem(
        factor="resolution",
        severity=_sev(resolution_sub),
        headline=(
            "Resolution well-corroborated" if resolution_sub >= 70
            else "Resolution unverifiable" if resolution_sub < 40
            else "Resolution partially corroborated"
        ),
        detail=(
            "The official resolution is corroborated by multiple independent "
            "wire sources (AP, Reuters)."
            if resolution_sub >= 70 else
            "The resolution statement could not be matched against independent "
            "reporting, so cite the outcome with an explicit caveat."
        ),
    )
    return [liq, ano, res]


def _headline(score: int, reasons: list[ReasonItem]) -> str:
    worst = min(reasons, key=lambda r: {"bad": 0, "warn": 1, "good": 2}[r.severity])
    verdict = (
        "Reliable to cite" if score >= 70
        else "Use with caution" if score >= 40
        else "Not recommended for citation"
    )
    return f"{verdict}: {worst.headline.lower()} drives most of the assessment."


# ---- Market metadata & anomaly series (Pillar 1 evidence) -----------------

def _meta(seed: int) -> MarketMeta:
    return MarketMeta(
        volume_usd=5_000 + (seed % 900) * 1_000,
        liquidity_usd=1_000 + (seed % 200) * 500,
        unique_traders=20 + seed % 600,
        end_date=f"2026-{1 + seed % 12:02d}-{1 + seed % 28:02d}",
        resolved=seed % 3 == 0,
    )


def _anomaly_series(seed: int) -> list[AnomalyPoint]:
    """~30-point price walk with one contiguous flagged window."""
    points: list[AnomalyPoint] = []
    price = 0.30 + (seed % 40) / 100
    flag_start = 8 + seed % 12
    flag_len = 3 + seed % 4
    for i in range(30):
        step = (((seed >> i) % 11) - 5) / 100  # deterministic -0.05..0.05
        in_flag = flag_start <= i < flag_start + flag_len
        if in_flag:
            step *= 4  # exaggerated move during the suspicious window
        price = max(0.02, min(0.98, round(price + step, 3)))
        anomaly_value = round(abs(step) * (3 if in_flag else 1), 3)
        points.append(AnomalyPoint(
            window_index=i, price=price,
            anomaly_value=anomaly_value, flagged=in_flag,
        ))
    return points


# ---- Citation (Pillar 2) --------------------------------------------------

def make_citation(url: str, as_of: str, permalink: str, score: int,
                   style: str = "APA") -> Citation:
    q = _question_from_url(url)
    flag = (
        "RELIABLE (score ≥ 70)" if score >= 70
        else "USE WITH CAUTION: reliability below integrity threshold"
    )
    apa = (
        f'Polymarket. (n.d.). {q} [Prediction market]. UW MarketLens '
        f'reliability snapshot {as_of}. Retrieved from {url} '
        f'(snapshot: {permalink})'
    )
    mla = (
        f'"{q}" Polymarket, {url}. UW MarketLens reliability snapshot, '
        f'{as_of}, {permalink}.'
    )
    bibtex = (
        "@misc{marketlens,\n"
        f"  title  = {{{q}}},\n"
        "  author = {{Polymarket}},\n"
        f"  note   = {{UW MarketLens reliability snapshot {as_of}}},\n"
        f"  url    = {{{permalink}}}\n"
        "}"
    )
    return Citation(apa=apa, mla=mla, bibtex=bibtex, reliability_flag=flag)


# ---- Composite (PLACEHOLDER — real version is S7) -------------------------

def make_market_score(url: str, as_of: str | None = None) -> MarketScore:
    as_of = as_of or _today()
    seed = _seed(url, as_of)
    liquidity = _pct(seed, 2)
    anomaly_sub = _pct(seed, 3)
    resolution_sub = _pct(seed, 4)
    overall = round((liquidity + anomaly_sub + resolution_sub) / 3)

    meta = _meta(seed)
    series = _anomaly_series(seed)
    reasons = _reasons(seed, liquidity, anomaly_sub, resolution_sub, meta)
    sid = snapshot_id(url, as_of)
    permalink = f"/snapshot/{sid}"
    register_snapshot(sid, url, as_of, "mock")

    verdict_pool = ["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"]
    # Derive departments from the slugified question via the live
    # tagger's keyword fallback. Same (url, as_of) → same question
    # text → same depts, so the determinism contract is preserved.
    # Empty list when the question hits no UW keyword (honest
    # "untagged" — e.g. a generic sports event).
    depts = _tagger_keyword_fallback(_question_from_url(url)).departments

    return MarketScore(
        market_url=url,
        market_question=_question_from_url(url),
        reliability_score=overall,
        band=_band(overall),
        headline=_headline(overall, reasons),
        reasons=reasons,
        meta=meta,
        anomaly_series=series,
        subscores=Subscores(
            liquidity_health=liquidity,
            anomaly=anomaly_sub,
            resolution_quality=resolution_sub,
        ),
        anomaly=AnomalyResult(
            score=round((100 - anomaly_sub) / 100, 3),
            flagged_windows=sum(1 for p in series if p.flagged),
            top_features=["volume_spike", "spread_widening", "trader_concentration"][: 1 + seed % 3],
            trained_on="synthetic",
        ),
        resolution=ResolutionVerdict(
            verdict=verdict_pool[seed % 4],
            reasoning="PLACEHOLDER reasoning, replaced by S4 LLM-as-judge output.",
            supporting_sources=["https://apnews.com/", "https://reuters.com/"][: 1 + seed % 2],
        ),
        tags=Tags(departments=depts, course_applicability=_pct(seed, 5)),
        citation=make_citation(url, as_of, permalink, overall),
        as_of=as_of,
        snapshot_id=sid,
        permalink=permalink,
        source="mock",
    )


def make_library() -> list[LibraryEntry]:
    entries = []
    for u in _SAMPLE_URLS:
        ms = make_market_score(u)
        entries.append(LibraryEntry(
            market_url=ms.market_url,
            market_question=ms.market_question,
            reliability_score=ms.reliability_score,
            band=ms.band,
            departments=ms.tags.departments,
            verified=_seed(u, ms.as_of) % 2 == 0,
        ))
    return entries


def make_pending_tags() -> list[PendingTag]:
    out = []
    for u in _SAMPLE_URLS:
        ms = make_market_score(u)
        out.append(PendingTag(
            market_url=ms.market_url,
            market_question=ms.market_question,
            suggested_departments=ms.tags.departments,
            course_applicability=ms.tags.course_applicability,
            verified=False,
        ))
    return out


# Verified-real Polymarket event slugs (probed via Gamma + tested
# against /api/live/score on 2026-06-02). Refresh via
# `backend/scripts/refresh_library_seed.py` when these markets resolve
# out of the demo window.
#
# Per-line dept annotations describe what `tagger._fallback`
# (mock-mode path) and the S5 LLM (live-mode path) should both pick
# up from each market's slugified question text. Library tagging is
# now content-based, not hash-based — see `make_market_score()` above
# for the wire-up.
#
# Earlier seed lists carried illustrative placeholders from when this
# module was the only data path on the site (pre-Live-mode). The slugs
# were fine for deterministic-mock-data purposes — that's the whole
# point of `mock.py` — but they leaked into the Featured carousel,
# course-pack workflow, and "Open sample report" button after Live
# mode shipped, all of which assume real Polymarket events. This list
# is the honest replacement now that both modes share the seed.
_SAMPLE_URLS = [
    # ECON — Fed rate decisions, the canonical UW econ teaching market.
    "https://polymarket.com/event/fed-decision-in-june-825",
    # POLS — geopolitics, Iran peace agreement.
    "https://polymarket.com/event/us-x-iran-permanent-peace-deal-by",
    # INFO + EVANS — AI regulation crossover (LLM tagger lands either way).
    "https://polymarket.com/event/us-enacts-ai-safety-bill-before-2027",
    # POLS + ECON — multi-outcome event; favourite-pick logic surfaces
    # the highest-traded outcome (currently "Will France win?" at ~17%).
    "https://polymarket.com/event/world-cup-winner",
    # INFO — frontier AI benchmarks, tech-industry-relevant.
    "https://polymarket.com/event/which-company-has-best-ai-model-end-of-june",
]

DEPT_LABEL = _DEPT_LABEL
