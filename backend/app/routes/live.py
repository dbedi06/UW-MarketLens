"""
POST /api/live/score — opt-in live anomaly scoring on real Polymarket data.

This is the *additive* counterpart to `/api/score` (mock). The frontend
still hits /api/score by default; this route exists so the team can
exercise the full S1 -> S2 -> S3 chain end-to-end on a real market
without disrupting the existing mock contract.

Behavior:
  1. Parse the URL, call `fetch_market(url)` — cache-first.
     - Cache hit  -> proceeds offline.
     - Cache miss + MARKETLENS_POLYMARKET_LIVE not set -> HTTP 503 with a
       friendly message. We do NOT fabricate.
  2. Call `features.from_trades(market)` -> per-window streams tuple.
     If <3 windows, return HTTP 422 ("not enough trade history") — the
     relative-feature pipeline needs prior baseline.
  3. Lazy-fit an `IsoForestDetector` on synthetic streams that now
     include the four trader-graph features
     (`anomaly.scoring.get_detector`). The detector is shared with the
     labeled-eval scorer so the live route and offline eval see the
     same model. Replacing the synthetic training set with a real
     corpus is Phase B (see MODEL_STATUS.md).
  4. Translate the per-window scores into the existing `MarketScore`
     Pydantic shape so the frontend can render this exactly like a
     mock-backed response.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Request

from ..schemas import (
    ScoreRequest, MarketScore, Subscores, AnomalyResult,
    ResolutionVerdict, Tags, Citation, ReasonItem, MarketMeta,
    AnomalyPoint,
)
from ..ingestion import IngestionUnavailable, fetch_market, RawMarket
from ..anomaly.features import (
    from_trades_with_network, feature_matrix_streams_with_network,
)
from ..anomaly import scoring as anomaly_scoring
from .. import mock
from ..resolution import resolve_market

router = APIRouter(prefix="/api/live", tags=["score-live"])
logger = logging.getLogger(__name__)


# ── lazy detector ────────────────────────────────────────────────────────────
# Trains once per process on synthetic streams **including network features**
# (Phase A push). The live route + labeled-eval scorer share one detector
# via `anomaly.scoring.get_detector()` so both paths see the same model.


# ── helpers ──────────────────────────────────────────────────────────────────

def _scores_to_marketscore(
    *, url: str, as_of: str, market: RawMarket,
    X_base: np.ndarray, widx: np.ndarray, anomaly_scores: np.ndarray,
    resolution_assessment,
) -> MarketScore:
    """Translate real per-window scores into the existing MarketScore
    Pydantic shape. Subscores other than anomaly remain placeholders
    until S5/composite land — clearly marked in `reasons`."""
    # Normalize anomaly scores to 0-1, higher=more anomalous, for display
    # parity with the existing anomaly_series.flagged convention.
    if anomaly_scores.size:
        s_lo = float(np.min(anomaly_scores))
        s_hi = float(np.max(anomaly_scores))
        if s_hi > s_lo:
            norm = (anomaly_scores - s_lo) / (s_hi - s_lo)
        else:
            norm = np.zeros_like(anomaly_scores)
        # Flag the top 10% of windows by score (cheap proxy; real
        # threshold selection lives in IsoForestDetector.pick_threshold
        # but needs a clean validation set).
        flag_cutoff = float(np.quantile(norm, 0.90)) if norm.size >= 10 else float(np.max(norm))
        flagged = norm >= flag_cutoff
        anomaly_subscore = int(round(100 * (1.0 - float(np.mean(norm)))))
    else:
        norm = np.zeros(0)
        flagged = np.zeros(0, dtype=bool)
        anomaly_subscore = 50

    anomaly_subscore = max(0, min(100, anomaly_subscore))

    # Build anomaly_series using the YES-token mid prices we approximate
    # from per-window mean trade prices (X_base column 1 is spread, not
    # price — we don't carry mean price through from_trades; reconstruct
    # by re-bucketing trades quickly).
    bucket_means = _mean_prices_per_window(market, widx)
    series: list[AnomalyPoint] = []
    for i, wi in enumerate(widx.tolist()):
        series.append(AnomalyPoint(
            window_index=int(wi),
            price=float(bucket_means[i]),
            anomaly_value=float(norm[i]),
            flagged=bool(flagged[i]),
        ))

    # Liquidity sub-score: cheap heuristic from real volume + spread.
    liquidity = _liquidity_subscore(market)
    resolution_sub = resolution_assessment.resolution_quality

    overall = int(round((liquidity + anomaly_subscore + resolution_sub) / 3))
    band = "HIGH" if overall >= 70 else "MEDIUM" if overall >= 40 else "LOW"

    n_flagged = int(np.sum(flagged))
    reasons = _live_reasons(
        liquidity,
        anomaly_subscore,
        resolution_sub,
        n_flagged,
        market,
        resolution_assessment,
    )
    headline = _live_headline(overall, n_flagged, market)

    sid = mock.snapshot_id(url, as_of)
    permalink = f"/snapshot/{sid}"

    return MarketScore(
        market_url=url,
        market_question=market.question or url,
        reliability_score=overall,
        band=band,
        headline=headline,
        reasons=reasons,
        meta=MarketMeta(
            volume_usd=int(market.volume_usd),
            liquidity_usd=int(market.liquidity_usd),
            unique_traders=int(market.unique_traders),
            end_date=(market.end_date.date().isoformat()
                      if market.end_date else "unknown"),
            resolved=bool(market.resolved),
        ),
        anomaly_series=series,
        subscores=Subscores(
            liquidity_health=liquidity,
            anomaly=anomaly_subscore,
            resolution_quality=resolution_sub,
        ),
        anomaly=AnomalyResult(
            score=round(float(np.mean(norm)) if norm.size else 0.0, 3),
            flagged_windows=n_flagged,
            top_features=["volume", "price_volatility", "unique_traders"],
        ),
        resolution=ResolutionVerdict(
            verdict=resolution_assessment.verdict,
            reasoning=resolution_assessment.reasoning,
            supporting_sources=resolution_assessment.supporting_sources,
        ),
        tags=Tags(departments=["ECON"], course_applicability=60),
        citation=mock.make_citation(url, as_of, permalink, overall),
        as_of=as_of,
        snapshot_id=sid,
        permalink=permalink,
    )


def _mean_prices_per_window(market: RawMarket, widx: np.ndarray) -> np.ndarray:
    from datetime import timedelta
    trades = sorted(market.trades, key=lambda t: t.timestamp)
    if not trades:
        return np.zeros(widx.shape[0])
    t0 = trades[0].timestamp
    width = timedelta(minutes=15)
    by_idx: dict[int, list[float]] = {}
    for t in trades:
        idx = int((t.timestamp - t0) // width)
        by_idx.setdefault(idx, []).append(t.price)
    out = np.zeros(widx.shape[0])
    for i, wi in enumerate(widx.tolist()):
        prices = by_idx.get(int(wi), [])
        out[i] = float(np.mean(prices)) if prices else 0.0
    return out


def _liquidity_subscore(market: RawMarket) -> int:
    # Cheap heuristic: more volume + tighter spread = higher score.
    # Real composite belongs in S7; this keeps the route honest by not
    # pretending the placeholder is anything more than that.
    vol_pts = min(60, int(market.volume_usd / 5000))     # 0..60
    spread_pts = max(0, int(40 - market.spread * 1000))  # 0..40 if spread<0.04
    return max(0, min(100, vol_pts + spread_pts))


def _live_reasons(liquidity: int, anomaly_sub: int, resolution_sub: int,
                  n_flagged: int, market: RawMarket,
                  resolution_assessment) -> list[ReasonItem]:
    def sev(v: int) -> str:
        return "good" if v >= 70 else "warn" if v >= 40 else "bad"

    resolution_detail = (
        "LLM-as-judge is live: NewsAPI and Claude validate the market question "
        "against independent reporting, with a fallback to UNVERIFIABLE when "
        "keys or usable sources are unavailable."
        if not resolution_assessment.used_fallback
        else "Resolution checking fell back to UNVERIFIABLE because the "
             "required NewsAPI/Anthropic inputs were not available."
    )

    return [
        ReasonItem(
            factor="liquidity", severity=sev(liquidity),
            headline=f"${int(market.volume_usd):,} traded, "
                     f"{market.unique_traders} unique wallets",
            detail=("Liquidity sub-score is a placeholder heuristic on real "
                    "volume and spread; composite scoring lands in S7."),
        ),
        ReasonItem(
            factor="anomaly", severity=sev(anomaly_sub),
            headline=f"{n_flagged} window(s) flagged by Isolation Forest",
            detail=("Detector is trained on synthetic streams, not real "
                    "Polymarket history — signal is real but the baseline "
                    "is the synthetic distribution. Phase B will retrain on "
                    "real markets."),
        ),
        ReasonItem(
            factor="resolution", severity=sev(resolution_sub),
            headline=("Market resolved per Gamma" if market.resolved
                      else "Market unresolved"),
            detail=resolution_detail,
        ),
    ]


def _live_headline(overall: int, n_flagged: int, market: RawMarket) -> str:
    band = "High" if overall >= 70 else "Medium" if overall >= 40 else "Low"
    return (f"{band} reliability ({overall}/100); "
            f"{n_flagged} flagged window(s) over {len(market.trades)} trades.")


# ── route ────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=MarketScore)
def live_score(req: ScoreRequest, request: Request) -> MarketScore:
    url = req.url.strip()
    if "polymarket.com" not in url:
        raise HTTPException(status_code=400,
                            detail="Expected a polymarket.com URL")

    try:
        market = fetch_market(url)
    except IngestionUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=(f"No cached snapshot for this market and live fetch "
                    f"is disabled. Set MARKETLENS_POLYMARKET_LIVE=1 to "
                    f"allow Polymarket calls, or seed the cache via "
                    f"`python -m scripts.fetch_market --url ...`. "
                    f"({exc})"),
        )

    X_base, X_net, mid, widx = from_trades_with_network(market)
    if X_base.shape[0] < 3:
        raise HTTPException(
            status_code=422,
            detail=(f"Not enough trade history: got {X_base.shape[0]} "
                    f"window(s), need >=3 for relative-feature baseline."),
        )

    # If addresses are missing, X_net is NaN; impute with zero so the
    # detector can still score, and log so the caller knows the network
    # axes contributed nothing.
    if np.isnan(X_net).any():
        logger.warning("live: wallet addresses missing for %s; network "
                       "features imputed to zero (score is base-only).", url)
        X_net = np.where(np.isnan(X_net), 0.0, X_net)

    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
    detector = anomaly_scoring.get_detector()
    scores = detector.score(F)
    resolution_assessment = resolve_market(
        market.question or url,
        resolved=bool(market.resolved),
    )

    as_of = (req.as_of or date.today().isoformat())
    return _scores_to_marketscore(
        url=url, as_of=as_of, market=market,
        X_base=X_base, widx=widx, anomaly_scores=scores,
        resolution_assessment=resolution_assessment,
    )
