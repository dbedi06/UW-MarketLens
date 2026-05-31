"""Market-level scorer plumbing for labeled evaluation.

The labeled-eval script (`scripts/eval_on_labeled.py`) accepts a
`--scorer pkg.mod:fn` callable that maps a Polymarket URL to a single
float anomaly score. This module exposes that callable plus a shared
detector singleton so labeled eval and the live route train one model
instead of two.

Training: real-corpus-first
---------------------------
If `app/anomaly/data/trained_model.pkl` exists, `get_detector()` loads
the real-trained detector from disk in <1s. Otherwise it falls back to
a fresh synthetic-stream fit (the v0.8 behavior). Build the pickle via
`python -m scripts.train_from_corpus` after running
`build_real_corpus.py` to populate `app/anomaly/data/corpus/`.

The pickle is committed; rebuilding only needed when the feature
contract or the corpus changes meaningfully.
"""
from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np

from .features import (
    BASE_FEATURE_NAMES,
    FULL_FEATURE_NAMES_WITH_NETWORK,
    feature_matrix_streams_with_network,
    from_trades_with_network,
)
from .model import IsoForestDetector
from .streams import clean_streams_with_network
from ..ingestion import fetch_market
from ..ingestion.polymarket import RawMarket, RawTrade

logger = logging.getLogger(__name__)

_TRAIN_M = 80
_TRAIN_W = 30
_TRAIN_SEED = 7
_REF_M = 40
_REF_W = 30
_REF_SEED = 8  # disjoint from training seed
_TOP_K = 3

# Path conventions for the real-trained model artifact.
DATA_DIR = Path(__file__).parent / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MODEL_PATH = DATA_DIR / "trained_model.pkl"

_DETECTOR: IsoForestDetector | None = None


def _train_synthetic() -> IsoForestDetector:
    """Original synthetic-stream training path (v0.8 default).
    Kept as fallback when no pickled real-trained model is present."""
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
    ref_market_stats = []
    for m in np.unique(mid_r):
        ws = ref_window_scores[mid_r == m]
        k = min(_TOP_K, ws.shape[0])
        ref_market_stats.append(float(np.mean(np.sort(ws)[-k:])))
    det._reference_scores = np.sort(np.array(ref_market_stats, dtype=float))
    det._network_medians = np.median(X_net, axis=0)
    det._trained_on = "synthetic"
    return det


def _load_corpus_market(path: Path) -> RawMarket:
    """Rebuild a `RawMarket` dataclass from a JSON snapshot saved by
    `build_real_corpus.py`. Datetime fields are stored as ISO strings;
    we parse them back. Trades nested as dicts → rebuilt as RawTrade."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    def _parse_dt(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    trades: list[RawTrade] = []
    for t in raw.get("trades", []) or []:
        ts = _parse_dt(t.get("timestamp"))
        if ts is None:
            continue
        trades.append(RawTrade(
            trade_id=str(t.get("trade_id", "")),
            token_id=str(t.get("token_id", "")),
            price=float(t.get("price", 0.0)),
            size=float(t.get("size", 0.0)),
            side=str(t.get("side", "BUY")),
            timestamp=ts,
            maker_address=str(t.get("maker_address", "") or ""),
            taker_address=str(t.get("taker_address", "") or ""),
        ))

    return RawMarket(
        market_url=raw.get("market_url", ""),
        condition_id=raw.get("condition_id", ""),
        question_id=raw.get("question_id", ""),
        question=raw.get("question", ""),
        token_ids=raw.get("token_ids") or [],
        volume_usd=float(raw.get("volume_usd", 0.0)),
        liquidity_usd=float(raw.get("liquidity_usd", 0.0)),
        unique_traders=int(raw.get("unique_traders", 0)),
        yes_price=float(raw.get("yes_price", 0.5)),
        spread=float(raw.get("spread", 0.0)),
        end_date=_parse_dt(raw.get("end_date")),
        resolved=bool(raw.get("resolved", False)),
        resolution=raw.get("resolution"),
        trades=trades,
        fetched_at=_parse_dt(raw.get("fetched_at")) or datetime.now(),
    )


def train_from_corpus(
    corpus_dir: Path = CORPUS_DIR,
    *,
    n_estimators: int = 200,
    contamination: float = 0.05,
    seed: int = _TRAIN_SEED,
) -> IsoForestDetector:
    """Fit an IsoForestDetector on the per-market feature matrices
    derived from the real Polymarket corpus.

    The corpus is whatever's on disk under `corpus_dir`. Each market
    contributes its per-window rows via `from_trades_with_network`; we
    concatenate them, train one detector, then compute a per-market
    reference distribution + per-column network medians (used at
    scoring time the same way the synthetic-trained model used them).

    Returns the fitted detector with `_reference_scores`,
    `_network_medians`, and `_trained_on = "real-corpus"` attached.
    Raises `ValueError` if the corpus is empty or has no scorable
    markets (need ≥3 windows each).
    """
    market_paths = sorted(corpus_dir.glob("*.json"))
    if not market_paths:
        raise ValueError(
            f"No corpus JSONs in {corpus_dir}. Run "
            f"`python -m scripts.build_real_corpus` first."
        )

    all_base: list[np.ndarray] = []
    all_net: list[np.ndarray] = []
    all_mid: list[np.ndarray] = []
    all_widx: list[np.ndarray] = []
    per_market_meta: list[tuple[str, int]] = []  # (condition_id, n_windows)

    next_mid = 0
    for path in market_paths:
        try:
            market = _load_corpus_market(path)
            if not market.trades:
                continue
            X_base, X_net, mid, widx = from_trades_with_network(market)
            if X_base.shape[0] < 3:
                continue
            # Renumber market_ids so they're globally unique across
            # corpus markets (from_trades_with_network always returns 0).
            all_base.append(X_base)
            all_net.append(X_net)
            all_mid.append(np.full(X_base.shape[0], next_mid, dtype=np.int64))
            all_widx.append(widx)
            per_market_meta.append((market.condition_id, X_base.shape[0]))
            next_mid += 1
        except Exception as exc:
            logger.warning("skipped %s: %s", path.name, exc)

    if not all_base:
        raise ValueError(
            "Corpus has no scorable markets (need ≥3 windows per market). "
            "Re-run build_real_corpus with --min-trades larger."
        )

    X_base = np.vstack(all_base)
    X_net = np.vstack(all_net)
    mid = np.concatenate(all_mid)
    widx = np.concatenate(all_widx)

    # Network NaN imputation BEFORE training — same policy as scoring
    # uses: per-column median across markets that have data. Markets
    # without on-chain takers contribute NaN rows; we keep them in
    # training but with imputed network values so the IsoForest doesn't
    # see NaNs.
    if np.isnan(X_net).any():
        col_medians = np.nanmedian(X_net, axis=0)
        # Fallback to zeros if a whole column is NaN (no on-chain data
        # across the entire corpus — unlikely but safe).
        col_medians = np.where(np.isnan(col_medians), 0.0, col_medians)
        nan_mask = np.isnan(X_net)
        X_net = np.where(nan_mask, col_medians[None, :], X_net)

    F = feature_matrix_streams_with_network(X_base, X_net, mid, widx)

    det = IsoForestDetector(n_estimators=n_estimators,
                            contamination=contamination,
                            seed=seed)
    det.fit(F)

    # Reference distribution: same per-market top-K reduction as
    # synthetic path, but using the corpus markets themselves as the
    # reference. Since we trained on them, their scores are typically
    # near the inlier side — that's fine for percentile lookup
    # because real anomalies score higher than the inlier mass.
    per_window = det.score(F)
    ref_market_stats: list[float] = []
    for m in np.unique(mid):
        ws = per_window[mid == m]
        k = min(_TOP_K, ws.shape[0])
        ref_market_stats.append(float(np.mean(np.sort(ws)[-k:])))
    det._reference_scores = np.sort(np.array(ref_market_stats, dtype=float))

    det._network_medians = np.median(X_net, axis=0)
    det._trained_on = "real-corpus"
    det._corpus_n_markets = len(per_market_meta)
    det._corpus_n_windows = int(X_base.shape[0])
    logger.info(
        "Trained on real corpus: %d markets, %d total windows",
        det._corpus_n_markets, det._corpus_n_windows,
    )
    return det


def save_detector(det: IsoForestDetector, path: Path = MODEL_PATH) -> None:
    """Pickle the fitted detector + its calibration artifacts to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(det, f)


def _load_detector(path: Path) -> IsoForestDetector | None:
    """Load a pickled detector; return None on any failure (caller
    falls back to fresh synthetic training)."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            return pickle.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load pickled detector at %s: %s", path, exc)
        return None


def get_detector() -> IsoForestDetector:
    """Return the cached detector. Resolution order:
      1. In-process cache (already loaded once).
      2. Pickled real-trained model at `MODEL_PATH` (preferred).
      3. Fresh synthetic-stream fit (fallback).

    Calibration artifacts attached to the detector regardless of
    training source:
      * `_reference_scores`: sorted per-market top-K scores from the
        training distribution; used by `percentile_from_reference`
        to make subscores cross-market comparable.
      * `_network_medians`: per-column median of training-set network
        features; used to impute when a real market has no wallet
        data.
      * `_trained_on`: either "real-corpus" or "synthetic" so the UI
        can disclose honestly which path produced this model.
    """
    global _DETECTOR
    if _DETECTOR is not None:
        return _DETECTOR

    pickled = _load_detector(MODEL_PATH)
    if pickled is not None:
        logger.info(
            "Loaded real-trained detector from %s (trained_on=%s)",
            MODEL_PATH,
            getattr(pickled, "_trained_on", "unknown"),
        )
        _DETECTOR = pickled
        return _DETECTOR

    logger.info("No pickled model at %s; falling back to synthetic", MODEL_PATH)
    _DETECTOR = _train_synthetic()
    return _DETECTOR


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
