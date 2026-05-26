"""Market-level scorer plumbing for labeled evaluation.

The labeled-eval script (`scripts/eval_on_labeled.py`) accepts a
`--scorer pkg.mod:fn` callable that maps a Polymarket URL to a single
float anomaly score. This module exposes that callable plus a shared
detector singleton so labeled eval and the live route train one model
instead of two.

Honest caveats:
  * The detector is trained on SYNTHETIC streams with synthetic network
    features. The labeled eval is the only end-to-end cross-check that
    the synthetic feature distributions transfer to real markets.
  * Per-market reduction is `mean(top-3 window scores)` — robust to
    one-window noise but less aggressive than `max`. This is a design
    choice, not theoretically optimal.
"""
from __future__ import annotations

import numpy as np

from .features import (
    FULL_FEATURE_NAMES_WITH_NETWORK,
    feature_matrix_streams_with_network,
    from_trades_with_network,
)
from .model import IsoForestDetector
from .streams import clean_streams_with_network
from ..ingestion import fetch_market

_TRAIN_M = 80
_TRAIN_W = 30
_TRAIN_SEED = 7
_REF_M = 40
_REF_W = 30
_REF_SEED = 8  # disjoint from training seed
_TOP_K = 3

_DETECTOR: IsoForestDetector | None = None


def get_detector() -> IsoForestDetector:
    """Lazy-fit a single IsoForestDetector on synthetic streams with
    network features. Cached at module level; the live route and the
    labeled-eval scorer share the same model so behavior is identical.

    Two calibration artifacts are attached to the detector singleton:
      * `_reference_scores`: sorted array of detector scores on a
        disjoint held-out clean block. Used to convert a market's
        score statistic into a cross-market-comparable percentile
        (fixes B1: within-market normalization collapsed to ~50).
      * `_network_medians`: per-column median of the training network
        block. Used as the imputation value when a real market has
        no wallet addresses (fixes B5: zero-imputation looked like
        a sybil ring on the topology axes).
    """
    global _DETECTOR
    if _DETECTOR is not None:
        return _DETECTOR
    X_base, X_net, mid, widx = clean_streams_with_network(
        n_markets=_TRAIN_M, w_per_market=_TRAIN_W, seed=_TRAIN_SEED,
    )
    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
    det = IsoForestDetector(n_estimators=200, contamination=0.05,
                            seed=_TRAIN_SEED)
    det.fit(F)

    # Reference distribution: score a fresh clean block; sorted scores
    # become the empirical CDF for percentile lookup at scoring time.
    Xb_r, Xn_r, mid_r, widx_r = clean_streams_with_network(
        n_markets=_REF_M, w_per_market=_REF_W, seed=_REF_SEED,
    )
    F_ref = feature_matrix_streams_with_network(Xb_r, Xn_r, mid_r, widx_r)
    ref_window_scores = det.score(F_ref)
    # Reduce per-market the same way the live route will: mean of top-K.
    ref_market_stats = []
    for m in np.unique(mid_r):
        ws = ref_window_scores[mid_r == m]
        k = min(_TOP_K, ws.shape[0])
        ref_market_stats.append(float(np.mean(np.sort(ws)[-k:])))
    det._reference_scores = np.sort(np.array(ref_market_stats, dtype=float))

    # Network feature medians for honest imputation.
    det._network_medians = np.median(X_net, axis=0)

    _DETECTOR = det
    return det


def reset_detector() -> None:
    """Tests use this to force a fresh fit on `tmp_path` cache state."""
    global _DETECTOR
    _DETECTOR = None


def percentile_from_reference(stat: float, reference: np.ndarray) -> float:
    """Empirical CDF of `stat` against a sorted reference array. Returns
    a value in [0, 1] where 1 means "more anomalous than all of reference."
    """
    if reference.size == 0:
        return 0.5
    # Number of reference values strictly less than stat → percentile.
    idx = int(np.searchsorted(reference, stat, side="right"))
    return float(idx) / float(reference.size)


def score_market_url(url: str) -> float:
    """Return a single anomaly score for a Polymarket market URL.

    `fetch_market` is cache-first; if the cache is cold and
    `MARKETLENS_POLYMARKET_LIVE` is not set this raises
    `IngestionUnavailable` (the labeled-eval caller logs and continues).

    Score reduction: `mean(top-3 per-window scores)`. If we have fewer
    than 3 windows, we mean over what we have. If `from_trades_with_network`
    returned NaN network features (no wallet addresses), we fall back to
    a degraded score that the eval reports separately.
    """
    market = fetch_market(url)
    X_base, X_net, mid, widx = from_trades_with_network(market)
    if X_base.shape[0] == 0:
        return float("nan")

    det = get_detector()
    # B5 fix: impute NaN network features with the training-set median
    # per column instead of zero. Zero pushed markets to the low corner
    # of the network feature space, which looked like a sybil ring;
    # the median is a "no signal" choice.
    if np.isnan(X_net).any():
        medians = det._network_medians
        X_net = np.where(np.isnan(X_net), medians[None, :], X_net)

    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
    per_window = det.score(F)
    k = min(_TOP_K, per_window.shape[0])
    top_k = np.sort(per_window)[-k:]
    return float(np.mean(top_k))


__all__ = ["score_market_url", "get_detector", "reset_detector"]
