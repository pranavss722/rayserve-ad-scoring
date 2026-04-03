"""Prometheus metrics for the ad-scoring pipeline.

Exports three metrics and a convenience function ``record_score_request``
that the EnsembleScorer calls on every request.  A lightweight
``MetricsEndpoint`` Ray Serve deployment exposes ``/metrics`` for scraping.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest

try:
    from ray import serve
except ModuleNotFoundError:  # pragma: no cover – allow unit tests without Ray

    class _ServeFallback:
        @staticmethod
        def deployment(**kwargs):
            return lambda cls: cls

        @staticmethod
        def ingress(fast_app):
            def wrapper(cls):
                cls.app = fast_app
                return cls
            return wrapper

    serve = _ServeFallback()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

AD_SCORE_REQUESTS_TOTAL = Counter(
    "ad_score_requests_total",
    "Total ad-score requests by decision tier",
    labelnames=("tier",),
)

_LATENCY_BUCKETS = (0.010, 0.025, 0.050, 0.100, 0.250, 0.500)

AD_SCORE_LATENCY_SECONDS = Histogram(
    "ad_score_latency_seconds",
    "End-to-end ad-score latency in seconds",
    buckets=_LATENCY_BUCKETS,
)

MODEL_REPLICA_HITS_TOTAL = Counter(
    "model_replica_hits_total",
    "Inference calls per model",
    labelnames=("model_name",),
)


# ---------------------------------------------------------------------------
# Convenience recorder
# ---------------------------------------------------------------------------

def record_score_request(
    *,
    tier: str,
    latency_s: float,
    model_name: str,
) -> None:
    """Update all three metrics after a scoring request."""
    AD_SCORE_REQUESTS_TOTAL.labels(tier=tier).inc()
    AD_SCORE_LATENCY_SECONDS.observe(latency_s)
    MODEL_REPLICA_HITS_TOTAL.labels(model_name=model_name).inc()


# ---------------------------------------------------------------------------
# /metrics endpoint deployment
# ---------------------------------------------------------------------------

metrics_app = FastAPI()


@metrics_app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint() -> PlainTextResponse:
    """Return Prometheus text exposition format."""
    return PlainTextResponse(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 0.1},
)
@serve.ingress(metrics_app)
class MetricsEndpoint:
    """Ray Serve deployment that exposes Prometheus metrics for scraping."""
