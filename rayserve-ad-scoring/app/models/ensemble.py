"""Ensemble ad-scoring ingress — Ray Serve deployment.

This mirrors a production ad decisioning pipeline where an ingress deployment
assembles features, fans out to one or more model deployments (here just
XGBoostScorer, but the pattern extends to multiple signals), applies business
logic to fuse the scores, and returns a serving decision.
"""

import logging
import time

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from ray import serve
except ModuleNotFoundError:  # pragma: no cover – allow unit tests without Ray

    class _ServeFallback:
        @staticmethod
        def deployment(**kwargs):
            """No-op decorator when Ray is not installed."""
            return lambda cls: cls

        @staticmethod
        def ingress(fast_app):
            """No-op ingress decorator; attaches the app to the class."""
            def wrapper(cls):
                cls.app = fast_app
                return cls
            return wrapper

    serve = _ServeFallback()

from app.features.feature_builder import FeatureBuilder
from app.middleware.metrics import record_score_request

logger = logging.getLogger(__name__)

app = FastAPI()

# Module-level reference to the active EnsembleScorer instance.  Populated by
# __init__ so the free-standing FastAPI route function can delegate to it.
# In production Ray Serve, @serve.ingress handles this binding automatically.
_instance: "EnsembleScorer | None" = None


# -- request / response schemas ----------------------------------------------

class ScoreRequest(BaseModel):
    user_id: str
    content_id: str


class ScoreResponse(BaseModel):
    user_id: str
    content_id: str
    score: float
    tier: str
    latency_ms: float


# -- HTTP endpoint (free-standing so FastAPI sees a clean signature) ----------

@app.post("/score", response_model=ScoreResponse)
async def score_endpoint(request: ScoreRequest) -> ScoreResponse:
    """Forward to the active EnsembleScorer instance."""
    assert _instance is not None, "EnsembleScorer has not been initialised"
    return await _instance._handle_score(request)


# -- deployment ---------------------------------------------------------------

@serve.deployment(
    num_replicas=1,
    max_concurrent_queries=20,
    ray_actor_options={"num_cpus": 0.5},
)
@serve.ingress(app)
class EnsembleScorer:
    """Top-level Ray Serve ingress that orchestrates ad scoring."""

    def __init__(self, scorer_handle=None) -> None:
        global _instance
        self.scorer = scorer_handle
        _instance = self

    # -- business logic -------------------------------------------------------

    @staticmethod
    def _classify_tier(score: float) -> str:
        if score > 0.7:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

    # -- core scoring logic ---------------------------------------------------

    async def _handle_score(self, request: ScoreRequest) -> ScoreResponse:
        start = time.perf_counter()

        features = FeatureBuilder.build(request.user_id, request.content_id)

        # In Ray Serve the handle is a DeploymentHandle and .score.remote()
        # returns an asyncio future.  For unit tests the handle is a plain
        # XGBoostScorer so we call .score() directly.
        scorer_result = self.scorer.score(features)

        # Support both sync returns and Ray ObjectRefs / coroutines.
        if hasattr(scorer_result, "__await__"):
            score_value: float = await scorer_result  # type: ignore[misc]
        else:
            score_value = scorer_result

        elapsed_s = time.perf_counter() - start
        elapsed_ms = elapsed_s * 1000
        tier = self._classify_tier(score_value)

        record_score_request(
            tier=tier,
            latency_s=elapsed_s,
            model_name="xgboost",
        )

        logger.info(
            "EnsembleScorer: user=%s content=%s score=%.4f tier=%s latency=%.2fms",
            request.user_id,
            request.content_id,
            score_value,
            tier,
            elapsed_ms,
        )

        return ScoreResponse(
            user_id=request.user_id,
            content_id=request.content_id,
            score=score_value,
            tier=tier,
            latency_ms=round(elapsed_ms, 2),
        )
