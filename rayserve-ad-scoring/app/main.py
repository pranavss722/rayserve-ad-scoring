"""Ray Serve entry point for the ad-scoring pipeline.

Wires together the three deployments and exposes them on their respective
HTTP routes:

    /score    — EnsembleScorer (ingress → XGBoostScorer)
    /metrics  — MetricsEndpoint (Prometheus scrape target)

Usage
-----
With a running Ray cluster::

    python -m app.main

Or via the declarative config::

    serve run config/serve_config.yaml
"""

import logging
import signal
import threading

try:
    from ray import serve

    _RAY_AVAILABLE = True
except ModuleNotFoundError:
    _RAY_AVAILABLE = False

from app.middleware.metrics import MetricsEndpoint
from app.models.ensemble import EnsembleScorer
from app.models.xgboost_scorer import XGBoostScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


def build_applications():
    """Bind deployment graphs and return the two top-level applications.

    When Ray is not installed (e.g. during unit tests) this falls back to
    plain Python object instantiation so the wiring can still be verified.
    """
    if _RAY_AVAILABLE:
        scorer_handle = XGBoostScorer.bind()  # type: ignore[attr-defined]
        scorer_app = EnsembleScorer.bind(scorer_handle=scorer_handle)  # type: ignore[attr-defined]
        metrics_app = MetricsEndpoint.bind()  # type: ignore[attr-defined]
    else:
        scorer_instance = XGBoostScorer()
        scorer_app = EnsembleScorer(scorer_handle=scorer_instance)
        metrics_app = MetricsEndpoint()

    return scorer_app, metrics_app


scorer_app, metrics_app = build_applications()


def main() -> None:
    """Deploy both applications with ``serve.run``."""
    if not _RAY_AVAILABLE:
        logger.error(
            "Ray is not installed — cannot start Ray Serve. "
            "Install with: pip install 'ray[serve]'"
        )
        return

    serve.run(scorer_app, name="ad-scorer", route_prefix="/score")
    serve.run(metrics_app, name="ad-metrics", route_prefix="/metrics")

    print()
    print("Ad-scoring pipeline deployed:")
    print("  POST /score    — EnsembleScorer → XGBoostScorer")
    print("  GET  /metrics  — Prometheus metrics endpoint")
    print()

    # Block until SIGINT / SIGTERM so the container stays alive.
    shutdown = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: shutdown.set())
    signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
    shutdown.wait()


if __name__ == "__main__":
    main()
