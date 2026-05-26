"""Per-alert attribution for the IF model.

Real surveillance systems do not surface a bare anomaly score — analysts
need to know *why* a window scored high (which feature drove it). SHAP is
the standard tool; `shap.TreeExplainer` works on IsolationForest's
underlying decision trees. We invert sign so contributions are in the same
"higher = more anomalous" convention as `IsoForestDetector.score`.

Output is intentionally small (ordered list of (feature, contribution))
so it can be embedded in API responses without bloating payloads.

Honesty: SHAP additivity is approximate for ensemble methods (small
numerical residual). Tests pin the tolerance.
"""

from __future__ import annotations
from typing import Any
import numpy as np
import shap

from .model import IsoForestDetector


class Explainer:
    """Wraps a fitted IsoForestDetector. Lazy-builds the TreeExplainer on
    first use so models that never need attribution don't pay the cost."""

    def __init__(self, detector: IsoForestDetector, feature_names: list[str]):
        if not hasattr(detector, "_model"):
            raise ValueError("detector has no fitted sklearn model")
        self._detector = detector
        self._feature_names = list(feature_names)
        self._tree_explainer: shap.TreeExplainer | None = None

    def _ensure(self) -> shap.TreeExplainer:
        if self._tree_explainer is None:
            # check_additivity=False: IsolationForest's decision_function
            # uses an averaged path-length transform that breaks strict
            # additivity; we still report contributions but document the
            # tolerance in tests.
            self._tree_explainer = shap.TreeExplainer(
                self._detector._model,
                feature_perturbation="tree_path_dependent",
            )
        return self._tree_explainer

    def explain(self, x: np.ndarray, *, top_k: int | None = None
                ) -> dict[str, Any]:
        """Explain a single window (shape (n_features,) or (1, n_features)).
        Returns:
          {
            "score":         model score (higher = more anomalous),
            "contributions": [{"feature": name, "value": x_i,
                               "shap": signed contribution}, ...]
                             sorted by |shap| descending,
          }
        Sign is flipped so positive shap = pushes the window toward "more
        anomalous." Note: shap's additivity for IsolationForest holds in
        the *raw tree output* space (path-length), not in our reported
        score space (which post-processes via score_samples). The
        contributions are still the correct relative ranking of which
        features pushed the window away from the fit distribution; we do
        not report a synthetic additivity number against `score`."""
        if x.ndim == 1:
            x = x[None, :]
        if x.shape[0] != 1:
            raise ValueError("explain() takes a single window")
        if x.shape[1] != len(self._feature_names):
            raise ValueError(
                f"expected {len(self._feature_names)} features, got {x.shape[1]}"
            )

        x_scaled = self._detector.scaler.transform(x)
        expl = self._ensure()
        sv = expl.shap_values(x_scaled, check_additivity=False)[0]
        sv_flipped = (-np.asarray(sv).ravel()).astype(float)

        order = np.argsort(-np.abs(sv_flipped))
        if top_k is not None:
            order = order[:top_k]
        contribs = [
            {
                "feature": self._feature_names[int(i)],
                "value": float(x[0, int(i)]),
                "shap": float(sv_flipped[int(i)]),
            }
            for i in order
        ]
        return {
            "score": float(self._detector.score(x)[0]),
            "contributions": contribs,
        }
