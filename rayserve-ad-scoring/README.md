# rayserve-ad-scoring

**Real-time multi-model ad scoring pipeline built on Ray Serve**

![Python 3.11](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![Ray Serve](https://img.shields.io/badge/Ray_Serve-2.x-028CF0?logo=ray&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-3.x-FF6600)
![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

A production-style ad relevance scoring service that accepts a user/content pair over HTTP, assembles an 11-dimensional feature vector, runs an XGBoost click-probability model, applies business-logic tier bucketing (high / medium / low), and returns a scored decision -- all behind autoscaling Ray Serve deployments with Prometheus observability baked in.

This architecture maps directly to how ad decisioning works at Hulu/ESPN/Disney+ scale: each component (feature assembly, model inference, decisioning) is an independent Ray Serve deployment that scales horizontally. Ray Serve multiplexes requests across replicas with async concurrency, sustaining thousands of QPS on commodity hardware while keeping p99 latency under 200ms. The pipeline is declaratively configured, zero-downtime deployable, and fully observable out of the box.

## Architecture

```
                         HTTP POST /score
                               |
                               v
                    +---------------------+
                    |   EnsembleScorer    |  Ingress (FastAPI)
                    |   route: /score     |  Accepts JSON, returns tier + score
                    +---------------------+
                          |           |
            1. Assemble   |           |  2. Score
               features   |           |
                          v           v
                  +--------------+  +------------------+
                  | FeatureBuilder|  |  XGBoostScorer   |
                  | (stateless)  |  |  (2 replicas)    |
                  +--------------+  +------------------+
                  Combines user,    XGBClassifier returns
                  content, context  P(click) in [0, 1]
                  signals (11 dims)
                          |           |
                          +-----+-----+
                                |
                       3. Classify tier
                                |
                                v
                    +---------------------+
                    |  > 0.7  -->  high   |
                    |  0.4-0.7 -> medium  |
                    |  < 0.4  -->  low    |
                    +---------------------+
                                |
                                v
                    { user_id, content_id,
                      score, tier, latency_ms }
```

| Layer | Module | Role |
|-------|--------|------|
| **EnsembleScorer** | `app/models/ensemble.py` | Top-level ingress. Orchestrates feature assembly, model scoring, tier classification, and metrics recording. |
| **FeatureBuilder** | `app/features/feature_builder.py` | Assembles an 11-dimensional feature vector from user and content IDs. In production this calls a feature store (Feast, Tecton). |
| **XGBoostScorer** | `app/models/xgboost_scorer.py` | Ray Serve deployment running an XGBClassifier trained on synthetic data at startup. Returns click probability in [0, 1]. |
| **MetricsEndpoint** | `app/middleware/metrics.py` | Separate deployment exposing `/metrics` for Prometheus scraping. |

## Why Ray Serve

- **Autoscaling per deployment** -- Each model and ingress scales independently based on in-flight request queues. The EnsembleScorer scales 1-4 replicas while XGBoostScorer holds steady at 2, matching real workload profiles where ingress is I/O-bound and inference is CPU-bound.
- **Multi-model composition** -- Ray Serve's deployment graph wires models together with typed handles and async fan-out. Adding a second model (e.g. a lightweight logistic regression for cold-start users) is one `.bind()` call, not a rewrite.
- **Zero-downtime rollout** -- `serve run config/serve_config.yaml` performs a rolling update: new replicas start and pass health checks before old replicas drain. Model updates, feature schema changes, and autoscaling tweaks all follow the same declarative path.

## Local quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy the pipeline (starts Ray head node automatically)
python -m app.main

# Score an ad request
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u42", "content_id": "ad-1001"}'

# Example response:
# {
#   "user_id": "u42",
#   "content_id": "ad-1001",
#   "score": 0.6234,
#   "tier": "medium",
#   "latency_ms": 1.87
# }

# Scrape Prometheus metrics
curl http://localhost:8000/metrics
```

## Production patterns

### Autoscaling config

`config/serve_config.yaml` defines per-deployment scaling:

```yaml
autoscaling_config:
  min_replicas: 1
  max_replicas: 4
  target_num_ongoing_requests_per_replica: 5
```

Ray Serve's autoscaler monitors the in-flight request queue per replica and scales between bounds to maintain the target concurrency. Apply changes without downtime:

```bash
serve run config/serve_config.yaml
```

### Prometheus metrics

Three metrics are recorded on every `/score` request:

| Metric | Type | Labels |
|--------|------|--------|
| `ad_score_requests_total` | Counter | `tier` (high / medium / low) |
| `ad_score_latency_seconds` | Histogram | buckets: 10ms, 25ms, 50ms, 100ms, 250ms, 500ms |
| `model_replica_hits_total` | Counter | `model_name` |

Point Prometheus at `http://<host>:8000/metrics` to scrape. These feed dashboards for throughput, latency percentiles, and per-model utilization.

### Dockerfile + Railway deploy

```bash
# Build and run locally
docker build -t rayserve-ad-scoring .
docker run -p 8000:8000 rayserve-ad-scoring

# Deploy to Railway
railway up
```

The included `railway.toml` sets the start command, `PORT=8000`, and `PYTHONUNBUFFERED=1` for container deployment.

## Tests

**44 tests, zero Ray dependency in test suite.**

All tests run against plain Python objects using pytest and Starlette's `TestClient` -- no Ray cluster required. The test suite covers model initialization, scoring contracts, tier classification, feature builder shape invariants, endpoint integration, and Prometheus metric recording.

```bash
pytest tests/ -v
```

## Stack

| Component | Role |
|-----------|------|
| **Ray Serve** | Autoscaling model serving and HTTP ingress |
| **XGBoost** | Ad click-probability model (XGBClassifier) |
| **FastAPI** | HTTP endpoint layer via `@serve.ingress` |
| **Prometheus** | Metrics collection (request count, latency, model hits) |
| **Docker** | Container packaging with `python:3.11-slim` |
| **Railway** | One-command cloud deployment |

---

Built as a companion project to explore Ray Serve's multi-model serving patterns for real-time ad decisioning at streaming scale.
