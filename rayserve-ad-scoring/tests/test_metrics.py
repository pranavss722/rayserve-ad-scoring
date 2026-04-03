"""Tests for Prometheus metrics instrumentation."""

import prometheus_client
import pytest
from starlette.testclient import TestClient

from app.middleware.metrics import (
    AD_SCORE_LATENCY_SECONDS,
    AD_SCORE_REQUESTS_TOTAL,
    MODEL_REPLICA_HITS_TOTAL,
    MetricsEndpoint,
    record_score_request,
)
from app.models.ensemble import EnsembleScorer
from app.models.xgboost_scorer import XGBoostScorer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_collectors():
    """Clear all collector sample caches between tests.

    We cannot unregister/re-register Prometheus collectors within a process,
    but we *can* reset the underlying metric values so each test starts from
    a known state.
    """
    # Reset counters.
    for tier in ("high", "medium", "low"):
        AD_SCORE_REQUESTS_TOTAL.labels(tier=tier)._value.set(0)
    for child in MODEL_REPLICA_HITS_TOTAL._metrics.values():
        child._value.set(0)
    # Reset label-free histogram (sum + bucket accumulators).
    AD_SCORE_LATENCY_SECONDS._sum.set(0)
    for bucket in AD_SCORE_LATENCY_SECONDS._buckets:
        bucket.set(0)
    yield


@pytest.fixture(scope="module")
def scorer():
    return XGBoostScorer()


@pytest.fixture(scope="module")
def ensemble(scorer):
    return EnsembleScorer(scorer_handle=scorer)


@pytest.fixture(scope="module")
def client(ensemble):
    return TestClient(ensemble.app)


# ---------------------------------------------------------------------------
# Metric object tests
# ---------------------------------------------------------------------------

class TestMetricDefinitions:
    """Verify metric types, names, and labels."""

    def test_requests_counter_name(self):
        # prometheus_client strips the _total suffix; full name is in describe().
        assert AD_SCORE_REQUESTS_TOTAL._name == "ad_score_requests"

    def test_requests_counter_has_tier_label(self):
        assert "tier" in AD_SCORE_REQUESTS_TOTAL._labelnames

    def test_latency_histogram_name(self):
        assert AD_SCORE_LATENCY_SECONDS._name == "ad_score_latency_seconds"

    def test_latency_histogram_buckets(self):
        expected = (0.010, 0.025, 0.050, 0.100, 0.250, 0.500)
        # Prometheus adds +Inf; the user-specified upper bounds live in
        # _upper_bounds on each child, but we can check the declared buckets
        # via the metric's _kwargs.
        assert AD_SCORE_LATENCY_SECONDS._kwargs["buckets"] == expected

    def test_replica_hits_counter_name(self):
        assert MODEL_REPLICA_HITS_TOTAL._name == "model_replica_hits"

    def test_replica_hits_has_model_name_label(self):
        assert "model_name" in MODEL_REPLICA_HITS_TOTAL._labelnames


# ---------------------------------------------------------------------------
# record_score_request helper
# ---------------------------------------------------------------------------

class TestRecordScoreRequest:
    """Verify the convenience function updates all three metrics."""

    def test_increments_request_counter(self):
        record_score_request(tier="high", latency_s=0.05, model_name="xgboost")
        assert AD_SCORE_REQUESTS_TOTAL.labels(tier="high")._value.get() == 1.0

    def test_observes_latency(self):
        record_score_request(tier="low", latency_s=0.123, model_name="xgboost")
        # Sum should reflect the observed value.
        assert AD_SCORE_LATENCY_SECONDS._sum.get() == pytest.approx(0.123)

    def test_increments_replica_hits(self):
        record_score_request(tier="medium", latency_s=0.01, model_name="xgboost")
        assert MODEL_REPLICA_HITS_TOTAL.labels(model_name="xgboost")._value.get() == 1.0

    def test_multiple_calls_accumulate(self):
        record_score_request(tier="high", latency_s=0.01, model_name="xgboost")
        record_score_request(tier="high", latency_s=0.02, model_name="xgboost")
        assert AD_SCORE_REQUESTS_TOTAL.labels(tier="high")._value.get() == 2.0


# ---------------------------------------------------------------------------
# MetricsEndpoint deployment
# ---------------------------------------------------------------------------

class TestMetricsEndpoint:
    """Verify the /metrics HTTP endpoint."""

    def test_returns_prometheus_text(self):
        endpoint = MetricsEndpoint()
        client = TestClient(endpoint.app)
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "ad_score_requests_total" in body
        assert "ad_score_latency_seconds" in body
        assert "model_replica_hits_total" in body

    def test_content_type(self):
        endpoint = MetricsEndpoint()
        client = TestClient(endpoint.app)
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Integration: ensemble records metrics
# ---------------------------------------------------------------------------

class TestEnsembleMetricsIntegration:
    """After a /score request the Prometheus counters should be bumped."""

    def test_score_request_records_metrics(self, client):
        # Reset before our request.
        for t in ("high", "medium", "low"):
            AD_SCORE_REQUESTS_TOTAL.labels(tier=t)._value.set(0)
        MODEL_REPLICA_HITS_TOTAL.labels(model_name="xgboost")._value.set(0)

        client.post("/score", json={"user_id": "u1", "content_id": "c1"})

        total = sum(
            AD_SCORE_REQUESTS_TOTAL.labels(tier=t)._value.get()
            for t in ("high", "medium", "low")
        )
        assert total == 1.0
        assert MODEL_REPLICA_HITS_TOTAL.labels(model_name="xgboost")._value.get() == 1.0
