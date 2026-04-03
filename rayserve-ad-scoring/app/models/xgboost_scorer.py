"""XGBoost ad relevance scorer — Ray Serve deployment.

This module mirrors a production pattern where an XGBoost binary classifier
scores ad click probability in real time.  In production the model would be
loaded from an artifact store (e.g. MLflow / S3); here we train a lightweight
model on synthetic data at startup so the deployment is fully self-contained.
"""

import logging
import time

import numpy as np
from xgboost import XGBClassifier

try:
    from ray import serve
except ModuleNotFoundError:  # pragma: no cover – allow unit tests without Ray
    from unittest.mock import MagicMock as _MagicMock

    class _ServeFallback:
        @staticmethod
        def deployment(**kwargs):
            """No-op decorator when Ray is not installed."""
            return lambda cls: cls

    serve = _ServeFallback()

from app.features.feature_builder import FeatureBuilder

logger = logging.getLogger(__name__)

_NUM_FEATURES = len(FeatureBuilder.feature_names())
_SYNTHETIC_ROWS = 10_000


def _generate_synthetic_data() -> tuple[np.ndarray, np.ndarray]:
    """Create synthetic training data matching the feature schema."""
    rng = np.random.default_rng(seed=42)
    X = rng.standard_normal((_SYNTHETIC_ROWS, _NUM_FEATURES))
    # Simple synthetic label: positive when weighted sum > 0
    weights = rng.standard_normal(_NUM_FEATURES)
    y = (X @ weights > 0).astype(int)
    return X, y


@serve.deployment(
    num_replicas=2,
    max_concurrent_queries=10,
    ray_actor_options={"num_cpus": 0.5},
)
class XGBoostScorer:
    """Ray Serve deployment that scores ad click probability with XGBoost."""

    def __init__(self) -> None:
        X, y = _generate_synthetic_data()
        self.model = XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            eval_metric="logloss",
        )
        self.model.fit(X, y)
        logger.info("XGBoostScorer: model trained on %d rows", _SYNTHETIC_ROWS)

    def score(self, features: np.ndarray) -> float:
        """Return click probability for a single feature vector.

        Args:
            features: Array of shape ``(1, num_features)``.

        Returns:
            Click probability in [0, 1].

        Raises:
            ValueError: If ``features`` has the wrong number of columns.
        """
        if features.shape[1] != _NUM_FEATURES:
            raise ValueError(
                f"Expected {_NUM_FEATURES} features, got {features.shape[1]}"
            )

        start = time.perf_counter()
        proba = self.model.predict_proba(features)[0, 1]
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("XGBoostScorer inference: %.2f ms", elapsed_ms)

        return float(proba)
