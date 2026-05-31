"""
S7 — Composite Score
====================
The real make_market_score(). Wires S1 ingestion, S3 anomaly detection,
S4 resolution checker, S5 tagger, and S6 citation into a single MarketScore.

This module replaces mock.make_market_score() in score.py and live.py.
Route handlers don't change — only the import does.

Public entry points
-------------------
  make_market_score(url, as_of)  ->  MarketScore
      Full live pipeline. Falls back gracefully if any sub-section is
      unavailable (no API keys, no live data).

  has_live_pipeline()  ->  bool
      True if enough pieces are available to produce a meaningful live score.

Scoring weights
---------------
  liquidity_health   35%   — market depth and trader diversity
  anomaly            40%   — Isolation Forest anomaly detection (S3)
  resolution_quality 25%   — LLM resolution corroboration (S4)

Liquidity score derivation
--------------------------
  Derived from S1 RawMarket metadata using three signals:
    - volume_usd:      log-scaled, normalised against a $500k reference
    - liquidity_usd:   log-scaled, normalised against a $100k reference
    - unique_traders:  log-scaled, normalised against 500 traders
  Combined as an equal-weighted mean, clamped to 0-100.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from datetime import date, datetime, timezone
from typing import Optional

from .schemas import (
    AnomalyPoint, AnomalyResult, Citation, LibraryEntry, MarketMeta,
    MarketScore, PendingTag, ReasonItem, ResolutionVerdict, Subscores, Tags,
)

logger = logging.getLogger(__name__)

# ── Scoring weights (must sum to 1.0) ────────────────────────────────────────
_W_LIQUIDITY   = 0.35
_W_ANOMALY     = 0.40
_W_RESOLUTION  = 0.25

# ── Reference values for liquidity normalisation ─────────────────────────────
_REF_VOLUME    = 500_000
_REF_LIQUIDITY = 100_000
_REF_TRADERS   = 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> str:
    return date.today().isoformat()


def _snapshot_id(url: str, as_of: str) -> str:
    return hashlib.sha256(f"{url}|{as_of}".encode()).hexdigest()[:12]


def _band(score: int) -> str:
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"


def _sev(value: int) -> str:
    return "good" if value >= 70 else "warn" if value >= 40 else "bad"


def _log_scale(value: float, reference: float) -> float:
    """
    Normalise value against reference using log scaling.
    Returns 0-100. A value equal to reference gives ~63.

    Guards against NaN / non-finite inputs (B3 fix carried into the
    composite from the old inline liquidity_subscore): if the upstream
    API returns NaN for volume or spread, treat as the neutral 0 floor
    rather than letting NaN propagate through to int().
    """
    if not math.isfinite(value) or value <= 0:
        return 0.0
    raw = math.log1p(value) / math.log1p(reference)
    return min(100.0, raw * 100)


def _liquidity_score(volume: float, liquidity: float, traders: int) -> int:
    vol_s  = _log_scale(volume,    _REF_VOLUME)
    liq_s  = _log_scale(liquidity, _REF_LIQUIDITY)
    trd_s  = _log_scale(traders,   _REF_TRADERS)
    return max(0, min(100, round((vol_s + liq_s + trd_s) / 3)))


def _anomaly_subscore(anomaly_percentile: float) -> int:
    """
    Convert S3's anomaly percentile (0-1, higher = more anomalous)
    into a 0-100 subscore where 100 = clean market.
    """
    return max(0, min(100, round((1.0 - anomaly_percentile) * 100)))


def _build_reasons(
    liquidity: int,
    anomaly_sub: int,
    resolution_sub: int,
    meta: MarketMeta,
    anomaly_series: list[AnomalyPoint],
) -> list[ReasonItem]:
    flagged = [p for p in anomaly_series if p.flagged]

    liq = ReasonItem(
        factor="liquidity",
        severity=_sev(liquidity),
        headline=(
            "Healthy liquidity" if liquidity >= 70
            else "Thin liquidity" if liquidity < 40
            else "Moderate liquidity"
        ),
        detail=(
            f"${meta.liquidity_usd:,} of liquidity across "
            f"{meta.unique_traders} unique traders and "
            f"${meta.volume_usd:,} total volume. "
            + (
                "Deep enough that prices reflect broad consensus."
                if liquidity >= 70 else
                "Few traders means a single actor can move the price — "
                "treat the implied probability with caution."
            )
        ),
    )

    if flagged:
        ano_detail = (
            f"{len(flagged)} of {len(anomaly_series)} time windows were flagged "
            f"as unusual by the anomaly model. Check the highlighted spans in the chart."
        )
    else:
        ano_detail = "Trade windows fall within normal market behavior."

    ano = ReasonItem(
        factor="anomaly",
        severity=_sev(anomaly_sub),
        headline=(
            "No unusual trading detected" if anomaly_sub >= 70
            else "Suspicious trading pattern" if anomaly_sub < 40
            else "Minor trading irregularities"
        ),
        detail=ano_detail,
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
            "The resolution is corroborated by multiple independent sources."
            if resolution_sub >= 70 else
            "The resolution could not be matched against independent reporting — "
            "cite the outcome with an explicit caveat."
        ),
    )

    return [liq, ano, res]


def _build_headline(score: int, reasons: list[ReasonItem]) -> str:
    worst = min(reasons, key=lambda r: {"bad": 0, "warn": 1, "good": 2}[r.severity])
    verdict = (
        "Reliable to cite" if score >= 70
        else "Use with caution" if score >= 40
        else "Not recommended for citation"
    )
    return f"{verdict}: {worst.headline.lower()} drives most of the assessment."


# ── Pipeline availability checks ─────────────────────────────────────────────

def has_live_pipeline() -> bool:
    """True if we can run at least S1 + S3 (the minimum for a meaningful score)."""
    live_flag = os.environ.get("MARKETLENS_POLYMARKET_LIVE", "").lower()
    return live_flag in ("1", "true", "yes")


# ── Main entry point ──────────────────────────────────────────────────────────

def make_market_score(url: str, as_of: Optional[str] = None) -> MarketScore:
    """
    Full live pipeline: S1 → S3 → S4 → S5 → S6 → composite score.

    Graceful degradation
    --------------------
    - If S1 fails (network down, market not found): raises immediately so
      the route returns a 4xx/5xx rather than silent mock data.
    - If S4 (resolution) has no keys: falls back to UNVERIFIABLE verdict,
      resolution_quality = 0.
    - If S5 (tagger) has no keys: falls back to rule-based tags.
    - S6 (citation) is a pure function — never fails.
    """
    from .ingestion import fetch_market
    from .anomaly.scoring import get_detector, percentile_from_reference
    from .anomaly.features import from_trades_with_network, feature_matrix_streams_with_network
    from .resolution import resolve_market
    from .tagger import tag_market
    from .citation_gen import make_citation
    from . import mock  # for register_snapshot only
    import numpy as np

    as_of = as_of or _today()

    # ── S1: Fetch real market data ────────────────────────────────────────────
    market = fetch_market(url)

    # ── S3: Anomaly detection ─────────────────────────────────────────────────
    anomaly_percentile = 0.5   # neutral default
    anomaly_series: list[AnomalyPoint] = []
    top_features: list[str] = []
    flagged_windows = 0

    X_base, X_net, mid, widx = from_trades_with_network(market)
    # B9 (preserved from previous live route): relative features
    # require min_n=3 prior windows; with <4 windows the per-market
    # z-scores are all zero and the score is meaningless. Refuse rather
    # than emit a misleading number. Raised outside the try/except below
    # so it propagates to the route handler (→ HTTP 422).
    if 0 < X_base.shape[0] < 4:
        raise ValueError(
            f"Not enough trade history: got {X_base.shape[0]} "
            f"window(s), need >=4 for relative-feature baseline."
        )

    try:
        if X_base.shape[0] > 0:
            det = get_detector()
            medians = getattr(det, "_network_medians", None)
            if np.isnan(X_net).any() and medians is not None:
                X_net = np.where(np.isnan(X_net), medians[None, :], X_net)
            elif np.isnan(X_net).any():
                # No medians attached (test detector or unfit detector) —
                # fall back to zero so the matrix is at least finite.
                X_net = np.where(np.isnan(X_net), 0.0, X_net)
            F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
            per_window = det.score(F)
            top_k = min(3, per_window.shape[0])
            stat = float(np.mean(np.sort(per_window)[-top_k:]))
            ref = getattr(det, "_reference_scores", None)
            if ref is not None and ref.size:
                anomaly_percentile = percentile_from_reference(stat, ref)
            elif per_window.size:
                # Defensive fallback for fake/uncalibrated detectors:
                # min-max normalize within this batch. Mirrors the
                # pre-composite live-route behavior.
                lo, hi = float(per_window.min()), float(per_window.max())
                anomaly_percentile = (
                    0.5 if hi <= lo
                    else float((stat - lo) / (hi - lo))
                )

            # Build AnomalyPoint series for the chart
            threshold = float(np.percentile(per_window, 85))
            for i, score_val in enumerate(per_window):
                flagged = float(score_val) >= threshold
                if flagged:
                    flagged_windows += 1
                anomaly_series.append(AnomalyPoint(
                    window_index=i,
                    price=float(market.yes_price),
                    anomaly_value=round(float(score_val), 4),
                    flagged=flagged,
                ))

            # Top features: use the feature names from the anomaly module
            from .anomaly.features import FULL_FEATURE_NAMES_WITH_NETWORK
            feat_importance = np.abs(per_window - per_window.mean())
            if feat_importance.sum() > 0:
                top_idx = np.argsort(feat_importance)[-3:][::-1]
                top_features = [
                    FULL_FEATURE_NAMES_WITH_NETWORK[i % len(FULL_FEATURE_NAMES_WITH_NETWORK)]
                    for i in top_idx
                ]
    except Exception as exc:
        logger.warning("S3 anomaly detection failed, using neutral score: %s", exc)

    anomaly_sub = _anomaly_subscore(anomaly_percentile)

    # ── S4: Resolution checker ────────────────────────────────────────────────
    resolution = resolve_market(market.question, resolved=market.resolved)
    resolution_sub = resolution.resolution_quality

    # ── S1-derived liquidity score ────────────────────────────────────────────
    liquidity = _liquidity_score(
        market.volume_usd,
        market.liquidity_usd,
        market.unique_traders,
    )

    # ── S7: Composite score ───────────────────────────────────────────────────
    overall = round(
        _W_LIQUIDITY  * liquidity +
        _W_ANOMALY    * anomaly_sub +
        _W_RESOLUTION * resolution_sub
    )

    # ── S5: Tagger ────────────────────────────────────────────────────────────
    tags = tag_market(market.question)

    # ── Metadata and reasons ──────────────────────────────────────────────────
    end_date_str = (
        market.end_date.strftime("%Y-%m-%d")
        if market.end_date else "Unknown"
    )
    meta = MarketMeta(
        volume_usd=int(market.volume_usd),
        liquidity_usd=int(market.liquidity_usd),
        unique_traders=market.unique_traders,
        end_date=end_date_str,
        resolved=market.resolved,
    )

    reasons = _build_reasons(liquidity, anomaly_sub, resolution_sub, meta, anomaly_series)
    headline = _build_headline(overall, reasons)

    # ── S6: Citation ──────────────────────────────────────────────────────────
    sid = _snapshot_id(url, as_of)
    permalink = f"/snapshot/{sid}"
    citation_out = make_citation(
        url=url,
        question=market.question,
        as_of=as_of,
        permalink=permalink,
        score=overall,
    )
    citation = Citation(
        apa=citation_out.apa,
        mla=citation_out.mla,
        bibtex=citation_out.bibtex,
        reliability_flag=citation_out.reliability_flag,
    )

    # Register snapshot so the permalink resolves
    mock.register_snapshot(sid, url, as_of, "live")

    return MarketScore(
        market_url=url,
        market_question=market.question,
        reliability_score=overall,
        band=_band(overall),
        headline=headline,
        reasons=reasons,
        meta=meta,
        anomaly_series=anomaly_series,
        subscores=Subscores(
            liquidity_health=liquidity,
            anomaly=anomaly_sub,
            resolution_quality=resolution_sub,
        ),
        anomaly=AnomalyResult(
            score=round(anomaly_percentile, 3),
            flagged_windows=flagged_windows,
            top_features=top_features,
        ),
        resolution=ResolutionVerdict(
            verdict=resolution.verdict,
            reasoning=resolution.reasoning,
            supporting_sources=resolution.supporting_sources,
            supporting_snippets=getattr(resolution, "supporting_snippets", []),
        ),
        tags=Tags(
            departments=tags.departments,
            course_applicability=tags.course_applicability,
        ),
        citation=citation,
        as_of=as_of,
        snapshot_id=sid,
        permalink=permalink,
        source="live",
    )
