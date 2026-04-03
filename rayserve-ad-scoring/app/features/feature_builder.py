"""Feature assembly for ad scoring requests."""

from typing import List

import numpy as np


class FeatureBuilder:
    """Simulates feature assembly combining user, content, and context signals.

    In production this would call a feature store (e.g. Feast / Tecton).
    Here it returns deterministic pseudo-random features seeded on the
    input IDs so that the same request always produces the same vector.
    """

    @staticmethod
    def feature_names() -> List[str]:
        """Canonical ordered list of features the scoring models expect."""
        return [
            # User features
            "user_age",
            "user_click_rate_7d",
            "user_impression_count_7d",
            "user_avg_session_sec",
            # Content features
            "ad_category_id",
            "ad_embedding_norm",
            "ad_historical_ctr",
            # Context features
            "hour_of_day",
            "day_of_week",
            "device_type",
            "page_position",
        ]

    @staticmethod
    def build(user_id: str, content_id: str) -> np.ndarray:
        """Assemble a feature vector for the given user/content pair.

        Returns:
            Array of shape ``(1, num_features)``.
        """
        seed = hash((user_id, content_id)) % (2**32)
        rng = np.random.default_rng(seed=seed)
        return rng.standard_normal((1, len(FeatureBuilder.feature_names())))
