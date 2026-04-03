"""Tests for XGBoostScorer.

All tests run against plain Python objects — no Ray cluster required.
"""

import numpy as np
import pytest

from app.features.feature_builder import FeatureBuilder
from app.models.xgboost_scorer import XGBoostScorer


@pytest.fixture(scope="module")
def scorer():
    """Train once per module — the model is deterministic and expensive-ish."""
    return scorer_instance


# Module-level instance so the fixture is truly shared (scope="module"
# fixtures cannot use autouse on a class).
scorer_instance = XGBoostScorer()


@pytest.fixture()
def random_features():
    """A single random feature row matching the expected schema width."""
    return np.random.rand(1, len(FeatureBuilder.feature_names()))


@pytest.fixture()
def fixed_features():
    """A deterministic feature row for reproducibility checks."""
    return np.ones((1, len(FeatureBuilder.feature_names())))


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestXGBoostScorerInit:
    """Verify the model trains correctly at construction time."""

    def test_model_is_trained_on_init(self, scorer):
        """XGBClassifier should be fitted and stored on the instance."""
        assert scorer.model is not None

    def test_model_is_xgb_classifier(self, scorer):
        from xgboost import XGBClassifier
        assert isinstance(scorer.model, XGBClassifier)

    def test_model_has_learned_classes(self, scorer):
        """After training, the model must know both binary classes."""
        assert list(scorer.model.classes_) == [0, 1]


# ---------------------------------------------------------------------------
# Scoring contract
# ---------------------------------------------------------------------------

class TestXGBoostScorerScore:
    """Verify .score() return value, bounds, and error handling."""

    def test_score_returns_float(self, scorer, random_features):
        result = scorer.score(random_features)
        assert isinstance(result, float)

    def test_score_between_zero_and_one(self, scorer, random_features):
        result = scorer.score(random_features)
        assert 0.0 <= result <= 1.0

    def test_score_bounds_across_many_inputs(self, scorer):
        """Spot-check 50 random vectors — all scores must be in [0, 1]."""
        rng = np.random.default_rng(seed=99)
        n_features = len(FeatureBuilder.feature_names())
        for _ in range(50):
            features = rng.standard_normal((1, n_features))
            s = scorer.score(features)
            assert 0.0 <= s <= 1.0

    def test_score_expects_correct_feature_count(self, scorer):
        wrong_shape = np.random.rand(1, 3)
        with pytest.raises(ValueError, match="Expected .* features, got 3"):
            scorer.score(wrong_shape)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestXGBoostScorerDeterminism:
    """The scorer must produce identical outputs for identical inputs."""

    def test_deterministic_for_same_input(self, scorer, fixed_features):
        a = scorer.score(fixed_features)
        b = scorer.score(fixed_features)
        assert a == b

    def test_deterministic_across_calls(self, scorer):
        """Two separately constructed feature arrays with equal values
        must yield the exact same score."""
        n = len(FeatureBuilder.feature_names())
        f1 = np.full((1, n), 0.5)
        f2 = np.full((1, n), 0.5)
        assert scorer.score(f1) == scorer.score(f2)
