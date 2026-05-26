"""S3 — synthetic anomaly detection (Isolation Forest).

Self-contained ML module. Behind a clean boundary; not wired into the API
yet (S2/S7 will swap mock.make_market_score over once real features land).
Eval is reported as a lower-bound capability check on synthetic data with
Wilson 95% CIs, per Section D of the implementation plan.
"""

from .features import (
    BASE_FEATURE_NAMES,
    ENGINEERED_FEATURE_NAMES,
    RELATIVE_FEATURE_NAMES,
    FEATURE_NAMES,
    FULL_FEATURE_NAMES,
    feature_matrix,
    feature_matrix_streams,
    clean_windows,
)
from .streams import clean_streams
from .model import IsoForestDetector, BaggedIsoForest

__all__ = [
    "BASE_FEATURE_NAMES",
    "ENGINEERED_FEATURE_NAMES",
    "RELATIVE_FEATURE_NAMES",
    "FEATURE_NAMES",
    "FULL_FEATURE_NAMES",
    "feature_matrix",
    "feature_matrix_streams",
    "clean_windows",
    "clean_streams",
    "IsoForestDetector",
    "BaggedIsoForest",
]
