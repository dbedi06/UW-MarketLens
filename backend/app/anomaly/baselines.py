"""Trivial baselines for the S3 eval.

We compare IsolationForest against the simplest possible threshold rules so
we can show — or honestly report we can't show — that IF earns its place.
Each baseline has the same `fit / score / pick_threshold` interface as
IsoForestDetector. They operate on the **base** features (raw scale), not
the engineered matrix; the engineered features exist for the model.

  VolumeZScore         flags top-tail volume         (single feature)
  VolatilityZScore     flags top-tail price_volatility
  CombinedSimpleRule   takes the max z-score of the two above (a soft OR)
"""

from __future__ import annotations
import numpy as np


_VOL, _PV = 0, 3  # base-feature column indices


class _ZScoreDetector:
    """Robust z-score on one base column (median / MAD), score = |z|."""

    def __init__(self, col: int, *, name: str):
        self._col = col
        self.name = name
        self._med = 0.0
        self._mad = 1.0

    def fit(self, X_base_clean: np.ndarray) -> "_ZScoreDetector":
        col = X_base_clean[:, self._col]
        self._med = float(np.median(col))
        mad = float(np.median(np.abs(col - self._med)))
        # 1.4826 makes MAD a consistent estimator of stddev under normality.
        self._mad = max(mad * 1.4826, 1e-9)
        return self

    def score(self, X_base: np.ndarray) -> np.ndarray:
        return np.abs((X_base[:, self._col] - self._med) / self._mad)

    def pick_threshold(self, X_val_clean: np.ndarray, *,
                       fpr_target: float = 0.20) -> float:
        s = self.score(X_val_clean)
        return float(np.quantile(s, 1.0 - fpr_target))


class VolumeZScore(_ZScoreDetector):
    def __init__(self) -> None:
        super().__init__(_VOL, name="VolumeZScore")


class VolatilityZScore(_ZScoreDetector):
    def __init__(self) -> None:
        super().__init__(_PV, name="VolatilityZScore")


class CombinedSimpleRule:
    """Soft-OR of the two z-score baselines: score = max of the two."""

    name = "CombinedSimpleRule"

    def __init__(self) -> None:
        self._a = VolumeZScore()
        self._b = VolatilityZScore()

    def fit(self, X_base_clean: np.ndarray) -> "CombinedSimpleRule":
        self._a.fit(X_base_clean)
        self._b.fit(X_base_clean)
        return self

    def score(self, X_base: np.ndarray) -> np.ndarray:
        return np.maximum(self._a.score(X_base), self._b.score(X_base))

    def pick_threshold(self, X_val_clean: np.ndarray, *,
                       fpr_target: float = 0.20) -> float:
        s = self.score(X_val_clean)
        return float(np.quantile(s, 1.0 - fpr_target))


def all_baselines() -> list:
    return [VolumeZScore(), VolatilityZScore(), CombinedSimpleRule()]


# ---- Per-market relative baselines (stream-aware) -----------------------
# These mirror what a real surveillance system does: z-score against each
# market's own trailing history, not against a global pool. The score is
# the |trailing z| on a single base feature. Honest sibling of the global
# baselines above so we can show whether per-market context helps.

from .features import _rolling_z  # noqa: E402


class _StreamZScoreDetector:
    """Operates on streams: (X_base, market_id, window_index). Fit is a
    no-op (rolling baseline is per-row by construction); score computes
    |trailing z| against the same market's prior `history` windows."""

    def __init__(self, col: int, *, name: str, history: int = 20):
        self._col = col
        self._history = history
        self.name = name

    def fit(self, streams: tuple[np.ndarray, np.ndarray, np.ndarray]
            ) -> "_StreamZScoreDetector":
        return self  # rolling baseline is data-local, no global stats

    def score(self, streams: tuple[np.ndarray, np.ndarray, np.ndarray]
              ) -> np.ndarray:
        X, mid, widx = streams
        n = X.shape[0]
        out = np.zeros(n, dtype=float)
        for m in np.unique(mid):
            rows = np.where(mid == m)[0]
            order = rows[np.argsort(widx[rows])]
            z = _rolling_z(X[order, self._col], self._history)
            out[order] = np.abs(z)
        return out

    def pick_threshold(self, streams_val_clean, *, fpr_target: float = 0.20
                       ) -> float:
        s = self.score(streams_val_clean)
        return float(np.quantile(s, 1.0 - fpr_target))


class RelativeVolumeZ(_StreamZScoreDetector):
    def __init__(self) -> None:
        super().__init__(_VOL, name="RelativeVolumeZ")


class RelativeVolatilityZ(_StreamZScoreDetector):
    def __init__(self) -> None:
        super().__init__(_PV, name="RelativeVolatilityZ")


class RelativeCombined:
    """Soft-OR of the two relative z-scores."""

    name = "RelativeCombined"

    def __init__(self) -> None:
        self._a = RelativeVolumeZ()
        self._b = RelativeVolatilityZ()

    def fit(self, streams):
        # B6: actually propagate fit to children so future stateful
        # baselines aren't silently dropped.
        self._a.fit(streams)
        self._b.fit(streams)
        return self

    def score(self, streams) -> np.ndarray:
        return np.maximum(self._a.score(streams), self._b.score(streams))

    def pick_threshold(self, streams_val_clean, *, fpr_target: float = 0.20
                       ) -> float:
        s = self.score(streams_val_clean)
        return float(np.quantile(s, 1.0 - fpr_target))


def all_stream_baselines() -> list:
    return [RelativeVolumeZ(), RelativeVolatilityZ(), RelativeCombined()]
