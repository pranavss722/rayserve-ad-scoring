"""Tests for EnsembleScorer and FeatureBuilder.

All tests run against plain Python objects — no Ray cluster required.
"""

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.features.feature_builder import FeatureBuilder
from app.models.ensemble import EnsembleScorer
from app.models.xgboost_scorer import XGBoostScorer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scorer():
    """A real XGBoostScorer instance (no Ray handle indirection)."""
    return XGBoostScorer()


@pytest.fixture(scope="module")
def ensemble(scorer):
    """EnsembleScorer wired to a plain scorer for unit testing."""
    return EnsembleScorer(scorer_handle=scorer)


@pytest.fixture(scope="module")
def client(ensemble):
    """Starlette/FastAPI test client for the ensemble's ASGI app."""
    return TestClient(ensemble.app)


# ---------------------------------------------------------------------------
# Tier classification (pure business logic)
# ---------------------------------------------------------------------------

class TestEnsembleTierLogic:
    """Verify the business-logic tier bucketing with exact spec values."""

    def test_score_0_8_is_high(self, ensemble):
        assert ensemble._classify_tier(0.8) == "high"

    def test_score_0_5_is_medium(self, ensemble):
        assert ensemble._classify_tier(0.5) == "medium"

    def test_score_0_2_is_low(self, ensemble):
        assert ensemble._classify_tier(0.2) == "low"

    def test_high_boundary(self, ensemble):
        """Scores strictly above 0.7 are 'high'."""
        assert ensemble._classify_tier(0.71) == "high"
        assert ensemble._classify_tier(1.0) == "high"

    def test_medium_boundary(self, ensemble):
        """0.7 itself falls into 'medium' (not strictly > 0.7)."""
        assert ensemble._classify_tier(0.7) == "medium"
        assert ensemble._classify_tier(0.4) == "medium"

    def test_low_boundary(self, ensemble):
        """Scores below 0.4 are 'low'."""
        assert ensemble._classify_tier(0.39) == "low"
        assert ensemble._classify_tier(0.0) == "low"


# ---------------------------------------------------------------------------
# FeatureBuilder
# ---------------------------------------------------------------------------

class TestFeatureBuilder:
    """Verify feature assembly contract."""

    def test_build_returns_correct_column_count(self):
        """build() array width must equal the number of declared features."""
        features = FeatureBuilder.build("u1", "c1")
        assert features.shape[1] == len(FeatureBuilder.feature_names())

    def test_build_returns_single_row(self):
        features = FeatureBuilder.build("u1", "c1")
        assert features.shape[0] == 1

    def test_build_returns_ndarray(self):
        features = FeatureBuilder.build("u1", "c1")
        assert isinstance(features, np.ndarray)

    def test_feature_names_length_matches_array(self):
        """feature_names() length must exactly match the array width."""
        names = FeatureBuilder.feature_names()
        array = FeatureBuilder.build("any_user", "any_content")
        assert len(names) == array.shape[1]

    def test_build_is_deterministic(self):
        """Same inputs must always produce the same feature vector."""
        a = FeatureBuilder.build("u42", "ad-100")
        b = FeatureBuilder.build("u42", "ad-100")
        np.testing.assert_array_equal(a, b)

    def test_build_varies_by_input(self):
        """Different inputs must produce different feature vectors."""
        a = FeatureBuilder.build("u1", "c1")
        b = FeatureBuilder.build("u2", "c2")
        assert not np.array_equal(a, b)


# ---------------------------------------------------------------------------
# Endpoint integration (still no Ray — uses Starlette TestClient)
# ---------------------------------------------------------------------------

class TestEnsembleEndpoint:
    """Integration-style tests hitting the FastAPI endpoint."""

    def test_valid_request(self, client):
        resp = client.post("/score", json={
            "user_id": "u123",
            "content_id": "c456",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "u123"
        assert body["content_id"] == "c456"
        assert 0.0 <= body["score"] <= 1.0
        assert body["tier"] in ("high", "medium", "low")
        assert isinstance(body["latency_ms"], float)

    def test_missing_user_id(self, client):
        resp = client.post("/score", json={"content_id": "c456"})
        assert resp.status_code == 422

    def test_missing_content_id(self, client):
        resp = client.post("/score", json={"user_id": "u123"})
        assert resp.status_code == 422

    def test_deterministic_scoring(self, client):
        payload = {"user_id": "u999", "content_id": "c999"}
        r1 = client.post("/score", json=payload).json()
        r2 = client.post("/score", json=payload).json()
        assert r1["score"] == r2["score"]
        assert r1["tier"] == r2["tier"]

    def test_response_tier_consistent_with_score(self, client):
        """The returned tier must match _classify_tier applied to the score."""
        resp = client.post("/score", json={
            "user_id": "u-tier-check",
            "content_id": "c-tier-check",
        }).json()
        score = resp["score"]
        if score > 0.7:
            assert resp["tier"] == "high"
        elif score >= 0.4:
            assert resp["tier"] == "medium"
        else:
            assert resp["tier"] == "low"
