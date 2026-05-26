"""IsolationForest detectors.

`IsoForestDetector` — single IF, wrapped in a RobustScaler so the
engineered features (which span very different magnitudes) don't smear
the tree splits.

`BaggedIsoForest` — average of K IFs trained on different random
feature subsets and different bootstrap row samples. Reduces seed-level
score variance and is the standard production tweak when a single IF is
unstable on small / correlated feature sets.

`score()` returns higher = more anomalous (sklearn's `decision_function`
uses the inverse convention). `pick_threshold()` chooses a cut on a
held-out clean validation set so realized FPR ≤ target.
"""

from __future__ import annotations
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


class IsoForestDetector:
    name = "IsolationForest"

    def __init__(self, *, n_estimators: int = 200, contamination: float = 0.05,
                 seed: int = 0):
        self.seed = seed
        self.scaler = RobustScaler()
        self._model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=seed,
            n_jobs=1,
        )

    def fit(self, X_clean: np.ndarray) -> "IsoForestDetector":
        self.scaler.fit(X_clean)
        self._model.fit(self.scaler.transform(X_clean))
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return -self._model.decision_function(self.scaler.transform(X))

    def pick_threshold(self, X_val_clean: np.ndarray, *,
                       fpr_target: float = 0.20) -> float:
        scores = self.score(X_val_clean)
        return float(np.quantile(scores, 1.0 - fpr_target))


class BaggedIsoForest:
    """K IsolationForests on different random feature subsets + bootstrap
    row samples. Score = mean of per-member z-normalized scores so members
    contribute on the same scale."""

    name = "BaggedIsoForest"

    def __init__(self, *, k: int = 5, n_estimators: int = 200,
                 contamination: float = 0.05, feature_frac: float = 0.7,
                 seed: int = 0):
        if k < 1:
            raise ValueError("k must be >= 1")
        if not 0.0 < feature_frac <= 1.0:
            raise ValueError("feature_frac must be in (0, 1]")
        self.seed = seed
        self.k = k
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.feature_frac = feature_frac
        self._members: list[tuple[IsolationForest, RobustScaler, np.ndarray]] = []
        self._score_mean: np.ndarray | None = None  # per-member calibration
        self._score_std: np.ndarray | None = None

    def fit(self, X_clean: np.ndarray) -> "BaggedIsoForest":
        rng = np.random.default_rng(self.seed)
        n, d = X_clean.shape
        n_feat = max(2, int(round(self.feature_frac * d)))
        means: list[float] = []
        stds: list[float] = []
        for i in range(self.k):
            cols = np.sort(rng.choice(d, size=n_feat, replace=False))
            rows = rng.integers(0, n, size=n)  # bootstrap
            scaler = RobustScaler().fit(X_clean[rows][:, cols])
            model = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=self.seed + i,
                n_jobs=1,
            )
            model.fit(scaler.transform(X_clean[rows][:, cols]))
            self._members.append((model, scaler, cols))
            # Calibration on the *full* clean set so members are comparable.
            s = -model.decision_function(scaler.transform(X_clean[:, cols]))
            means.append(float(s.mean()))
            stds.append(float(s.std() + 1e-9))
        self._score_mean = np.asarray(means)
        self._score_std = np.asarray(stds)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        if not self._members:
            raise RuntimeError("BaggedIsoForest not fitted")
        per = np.zeros((self.k, X.shape[0]), dtype=float)
        for i, (model, scaler, cols) in enumerate(self._members):
            s = -model.decision_function(scaler.transform(X[:, cols]))
            per[i] = (s - self._score_mean[i]) / self._score_std[i]
        return per.mean(axis=0)

    def pick_threshold(self, X_val_clean: np.ndarray, *,
                       fpr_target: float = 0.20) -> float:
        s = self.score(X_val_clean)
        return float(np.quantile(s, 1.0 - fpr_target))
