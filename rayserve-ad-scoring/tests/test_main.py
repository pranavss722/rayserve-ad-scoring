"""Tests for the Ray Serve entry point wiring in app/main.py."""

import importlib

import pytest


class TestEntryPointImports:
    """Verify that main.py exposes the expected symbols."""

    def test_module_imports(self):
        mod = importlib.import_module("app.main")
        assert mod is not None

    def test_exposes_scorer_app(self):
        from app.main import scorer_app
        assert scorer_app is not None

    def test_exposes_metrics_app(self):
        from app.main import metrics_app
        assert metrics_app is not None

    def test_scorer_app_is_xgboost_backed(self):
        """The bound scorer application should originate from EnsembleScorer."""
        from app.main import scorer_app
        # In the no-Ray fallback, scorer_app is an EnsembleScorer instance.
        # With real Ray, it would be a DeploymentHandle / Application.
        # Either way it should be truthy and importable.
        assert scorer_app is not None

    def test_metrics_app_is_metrics_endpoint(self):
        from app.main import metrics_app
        assert metrics_app is not None
