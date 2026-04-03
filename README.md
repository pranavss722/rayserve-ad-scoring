# rayserve-ad-scoring

> Real-time multi-model ad scoring pipeline built on Ray Serve

![Python](https://img.shields.io/badge/python-3.11-blue) ![Ray](https://img.shields.io/badge/ray-serve-orange) ![XGBoost](https://img.shields.io/badge/model-xgboost-green) ![Prometheus](https://img.shields.io/badge/metrics-prometheus-red) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview

A production-style real-time ad relevance scoring service built on [Ray Serve](https://docs.ray.io/en/latest/serve/index.html). It accepts a user/content pair, assembles features from a simulated online feature store, runs an XGBoost click-probability model, applies business-logic tier bucketing, and returns a scored ad decision — all behind an autoscaling HTTP deployment with Prometheus observability baked in.

This architecture maps directly to production ad scoring at streaming scale. Each component (feature assembly, model inference, decisioning) is an independent Ray Serve deployment that scales horizontally. Because Ray Serve multiplexes requests across replicas with async concurrency, the pipeline sustains thousands of QPS on commodity hardware while keeping p99 latency under 50ms.

---

## Architecture

HTTP POST /score
│
▼
┌─────────────────┐
│  EnsembleScorer │  ← Ingress deployment (FastAPI)
│  (decisioning)  │    Accepts JSON, returns tier + score
└────────┬────────┘
│
├─ 1. Assemble features
▼
┌─────────────────┐
│  FeatureBuilder │  ← Stateless utility
│  (feature store)│    Simulates Feast / DynamoDB online read
└────────┬────────┘
│
├─ 2. Score
▼
┌─────────────────┐
│  XGBoostScorer  │  ← Model deployment (2 replicas)
│  (click model)  │    Returns P(click) ∈ [0, 1]
└────────┬────────┘
│
├─ 3. Classify tier
▼
high / medium / low
| Layer | Module | Role |
|-------|--------|------|
| FeatureBuilder | `app/features/feature_builder.py` | Assembles an 11-dimensional feature vector from user and content IDs. In production this calls a Feast/DynamoDB online store. |
| XGBoostScorer | `app/models/xgboost_scorer.py` | Ray Serve deployment running an XGBClassifier. Returns click probability in [0, 1]. |
| EnsembleScorer | `app/models/ensemble.py` | Top-level ingress. Fans out to XGBoostScorer, applies tier logic (>0.7 high, 0.4–0.7 medium, <0.4 low), records Prometheus metrics. |
| MetricsEndpoint | `app/middleware/metrics.py` | Separate deployment exposing `/metrics` for Prometheus scraping. |

---

## Why Ray Serve

- **Autoscaling** — EnsembleScorer scales 1–4 replicas based on in-flight request queue depth, configured declaratively in `config/serve_config.yaml`
- **Multi-model composition** — XGBoostScorer and MetricsEndpoint are independent deployments with separate resource allocations; adding a second model is one `.bind()` call
- **Zero-downtime rollout** — `serve run config/serve_config.yaml` performs a rolling update; new replicas pass health checks before old ones drain

---

## Quickstart
```bash
# 1. Install dependencies (Python 3.11 recommended — Ray requires ≤ 3.12)
pip install -r requirements.txt

# 2. Start a local Ray cluster
ray start --head

# 3. Deploy the pipeline
python -m app.main

# 4. Score an ad request
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

# 5. Scrape Prometheus metrics
curl http://localhost:8000/metrics
```

---

## Production Patterns

### Autoscaling

`config/serve_config.yaml` defines autoscaling for EnsembleScorer:
```yaml
autoscaling_config:
  min_replicas: 1
  max_replicas: 4
  target_num_ongoing_requests_per_replica: 5
```

XGBoostScorer runs at a fixed 2 replicas since inference is CPU-bound and predictable.

### Prometheus Observability

Three metrics are recorded on every `/score` request:

| Metric | Type | Labels |
|--------|------|--------|
| `ad_score_requests_total` | Counter | `tier` (high/medium/low) |
| `ad_score_latency_seconds` | Histogram | buckets: 10ms, 25ms, 50ms, 100ms, 250ms, 500ms |
| `model_replica_hits_total` | Counter | `model_name` |

### Docker + Railway Deploy
```bash
# Build and run locally
docker build -t rayserve-ad-scoring .
docker run -p 8000:8000 rayserve-ad-scoring

# Deploy to Railway
railway up
```

---

## Tests

**44 tests, zero Ray dependency in the test suite.**

All tests run against plain Python objects using pytest — no Ray cluster required. The `@serve.deployment` decorator falls back to a no-op when Ray is not installed, so CI works on any Python 3.11 environment.
```bash
pytest tests/ -v
```

---

## Stack

| Tool | Role |
|------|------|
| Ray Serve | Distributed model serving, autoscaling, multi-model composition |
| XGBoost | Click probability model (binary classifier) |
| FastAPI | HTTP ingress layer |
| Prometheus | Request metrics, latency histograms, replica hit counters |
| Docker | Containerized deployment |
| Railway | Cloud hosting |

---

## Project Structure

rayserve-ad-scoring/
├── app/
│   ├── features/
│   │   └── feature_builder.py   # Simulates Feast/DynamoDB online store
│   ├── models/
│   │   ├── xgboost_scorer.py    # XGBoost Ray Serve deployment
│   │   └── ensemble.py          # Multi-model ingress router
│   ├── middleware/
│   │   └── metrics.py           # Prometheus metrics + /metrics endpoint
│   └── main.py                  # Ray Serve entry point
├── tests/                       # 44 tests, no Ray dependency
├── config/
│   └── serve_config.yaml        # Declarative autoscaling config
├── Dockerfile
└── railway.toml

---
