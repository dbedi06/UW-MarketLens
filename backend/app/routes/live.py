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

import httpx
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
    detector, resolution_assessment,
) -> MarketScore:
    """Translate real per-window scores into the existing MarketScore
    Pydantic shape. Subscores other than anomaly remain placeholders
    until S4/S5/composite land — clearly marked in `reasons`.

    B1 fix: anomaly_subscore is now a percentile against the detector's
    reference distribution (a held-out clean block scored at training
    time), not a within-market normalization. This makes the subscore
    actually vary across markets instead of collapsing to ~50.
    """
    if anomaly_scores.size:
        # Per-window display values: percentile of each window's raw score
        # against the per-market-stat reference. Bounded [0, 1].
        ref = getattr(detector, "_reference_scores", None)
        if ref is None or ref.size == 0:
            # Defensive fallback — shouldn't happen with a properly built
            # detector, but if it does, fall back to clipping raw scores
            # to a reasonable absolute range. Better to be conservative
            # than to crash.
            per_window_pct = np.clip(
                (anomaly_scores - anomaly_scores.min())
                / max(1e-9, anomaly_scores.max() - anomaly_scores.min()),
                0.0, 1.0,
            )
        else:
            per_window_pct = np.array([
                anomaly_scoring.percentile_from_reference(s, ref)
                for s in anomaly_scores
            ])

        # Market-level statistic: mean of top-K window scores (matches the
        # labeled-eval scorer in scoring.score_market_url).
        k = min(3, anomaly_scores.shape[0])
        market_stat = float(np.mean(np.sort(anomaly_scores)[-k:]))
        market_pct = (
            anomaly_scoring.percentile_from_reference(market_stat, ref)
            if ref is not None and ref.size else float(np.mean(per_window_pct))
        )
        # Higher percentile = more anomalous; subscore inverts (higher
        # = healthier).
        anomaly_subscore = int(round(100 * (1.0 - market_pct)))

        # Flag windows above the 90th percentile of the per-window
        # distribution (still within-market, fine for display).
        if per_window_pct.size >= 10:
            flag_cutoff = float(np.quantile(per_window_pct, 0.90))
        else:
            # With few windows, flag only those above the per-window 50th
            # percentile of the reference — avoids "flag everything" or
            # "flag nothing" extremes.
            flag_cutoff = 0.5
        flagged = per_window_pct >= flag_cutoff
        norm = per_window_pct  # back-compat: variable name used below
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
    mock.register_snapshot(sid, url, as_of, "live")

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
        source="live",
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
    # B3 fix: guard against NaN / non-finite values from the API.
    vol = market.volume_usd
    if not np.isfinite(vol):
        vol_pts = 30  # neutral fallback
    else:
        vol_pts = min(60, max(0, int(vol / 5000)))     # 0..60
    spread = market.spread
    if not np.isfinite(spread):
        spread_pts = 20  # neutral fallback
    else:
        spread_pts = max(0, min(40, int(40 - spread * 1000)))
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


# ── shared render path (used by route + snapshot dispatch) ─────────────────

def render_live_snapshot(url: str, as_of: str) -> MarketScore:
    """Run the full S1→S2→S3 chain for `url` and emit a MarketScore.

    Used by both `POST /api/live/score` and `GET /api/snapshot/{id}` when
    the snapshot was originally produced by the live route. Raises
    `IngestionUnavailable` on cache miss (caller maps to HTTP 503) and
    `ValueError` on <4 windows (caller maps to HTTP 422).
    """
    market = fetch_market(url)
    X_base, X_net, mid, widx = from_trades_with_network(market)
    # B9 fix: bump from <3 to <4. With 3 windows, _rolling_z's min_n=3
    # requirement leaves the relative axis at zero for every window.
    # At 4 windows the 4th gets a real relative z-score.
    if X_base.shape[0] < 4:
        raise ValueError(
            f"Not enough trade history: got {X_base.shape[0]} window(s), "
            f"need >=4 for relative-feature baseline."
        )

    detector = anomaly_scoring.get_detector()
    # B5 fix: impute NaN network features with the training-set median
    # per column instead of zero. Zero imputation pushed markets to the
    # extreme-low corner of the network feature space, which looked like
    # a sybil ring.
    if np.isnan(X_net).any():
        medians = detector._network_medians
        logger.warning("live: wallet addresses missing for %s; network "
                       "features imputed to training-set median.", url)
        X_net = np.where(np.isnan(X_net), medians[None, :], X_net)

    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
    scores = detector.score(F)
    resolution_assessment = resolve_market(
        market.question or url,
        resolved=bool(market.resolved),
    )
    return _scores_to_marketscore(
        url=url, as_of=as_of, market=market,
        X_base=X_base, widx=widx, anomaly_scores=scores,
        detector=detector,
        resolution_assessment=resolution_assessment,
    )


# ── route ────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=MarketScore)
def live_score(req: ScoreRequest, request: Request) -> MarketScore:
    url = req.url.strip()
    if "polymarket.com" not in url:
        raise HTTPException(status_code=400,
                            detail="Expected a polymarket.com URL")

    as_of = (req.as_of or date.today().isoformat())
    try:
        return render_live_snapshot(url, as_of)
    except IngestionUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=(f"No cached snapshot for this market and live fetch "
                    f"is disabled. Set MARKETLENS_POLYMARKET_LIVE=1 to "
                    f"allow Polymarket calls, or seed the cache via "
                    f"`python -m scripts.fetch_market --url ...`. "
                    f"({exc})"),
        )
    except ValueError as exc:
        # Distinguish "market does not exist on Polymarket" (404) from
        # "market exists but has insufficient data to score" (422). Both
        # arrive as ValueError today — the message is the discriminator.
        msg = str(exc)
        if "No Gamma event" in msg or "has no markets" in msg:
            raise HTTPException(
                status_code=404,
                detail=(f"This market doesn't appear to exist on Polymarket. "
                        f"Verify the URL by opening it in a browser. ({msg})"),
            )
        raise HTTPException(status_code=422, detail=msg)
    except httpx.HTTPStatusError as exc:
        # Upstream Polymarket returned an error (e.g., 401 for a malformed
        # token id, 404 for an unknown slug, 5xx during outage). Surface a
        # 502 with the upstream code rather than crashing into a 500.
        failed_url = str(exc.request.url) if exc.request else "<unknown>"
        logger.warning(
            "live: upstream Polymarket error %d on %s (event=%s)",
            exc.response.status_code, failed_url, url,
        )
        raise HTTPException(
            status_code=502,
            detail=(f"Polymarket returned {exc.response.status_code} for "
                    f"the upstream call to {failed_url}. The market URL "
                    f"may be valid but the API may have changed shape. "
                    f"Switch to Mock mode to keep browsing."),
        )
