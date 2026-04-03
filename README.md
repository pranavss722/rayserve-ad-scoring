# rayserve-ad-scoring

> Real-time multi-model ad scoring pipeline built on Ray Serve

![Python](https://img.shields.io/badge/python-3.11-blue) ![Ray](https://img.shields.io/badge/ray-serve-orange) ![XGBoost](https://img.shields.io/badge/model-xgboost-green) ![Prometheus](https://img.shields.io/badge/metrics-prometheus-red) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview

A production-style real-time ad relevance scoring service built on [Ray Serve](https://docs.ray.io/en/latest/serve/index.html). It accepts a user/content pair, assembles features from a simulated online feature store, runs an XGBoost click-probability model, applies business-logic tier bucketing, and returns a scored ad decision — all behind an autoscaling HTTP deployment with Prometheus observability baked in.

This architecture maps directly to production ad scoring at streaming scale. Each component (feature assembly, model inference, decisioning) is an independent Ray Serve deployment that scales horizontally. Because Ray Serve multiplexes requests across replicas with async concurrency, the pipeline sustains thousands of QPS on commodity hardware while keeping p99 latency under 50ms.

---

## Architecture
