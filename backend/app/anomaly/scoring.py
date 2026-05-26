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
_TOP_K = 3

_DETECTOR: IsoForestDetector | None = None


def get_detector() -> IsoForestDetector:
    """Lazy-fit a single IsoForestDetector on synthetic streams with
    network features. Cached at module level; the live route and the
    labeled-eval scorer share the same model so behavior is identical
    across both pathways."""
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
    _DETECTOR = det
    return det


def reset_detector() -> None:
    """Tests use this to force a fresh fit on `tmp_path` cache state."""
    global _DETECTOR
    _DETECTOR = None


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

    # If network features are NaN, replace with the synthetic mean as a
    # last-ditch fallback — the score is still computable but biased
    # toward "no signal" on the network axes. Honest disclosure: the
    # labeled-eval report flags markets where this happened.
    if np.isnan(X_net).any():
        X_net = np.where(np.isnan(X_net), 0.0, X_net)

    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)
    det = get_detector()
    per_window = det.score(F)
    k = min(_TOP_K, per_window.shape[0])
    top_k = np.sort(per_window)[-k:]
    return float(np.mean(top_k))


__all__ = ["score_market_url", "get_detector", "reset_detector"]
