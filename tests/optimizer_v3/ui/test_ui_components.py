"""
Smoke Tests for Optimizer V3 UI Components

Minimal import-level smoke tests that verify components load without errors.
Replaces the prior file that referenced PerformanceMetrics/ConfigSnapshot
(removed in production code) and used PyQt6 (production uses PyQt5).

These tests do NOT instantiate QWidgets (which require a running QApplication
and display server), so they are safe to run in CI headless environments.

Sprint: 1.6 (BTCAAAAA-245 — Task 4: fix stale test file)
"""

import importlib
import pytest


class TestModuleImports:
    """Verify all optimizer_v3 UI modules import without errors."""

    def test_metrics_display_panel_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.metrics_display_panel")
        assert hasattr(mod, "MetricsDisplayPanel")

    def test_live_output_panel_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.live_output_panel")
        assert mod is not None

    def test_trades_panel_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.trades_panel")
        assert mod is not None

    def test_compare_view_panel_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.compare_view_panel")
        assert mod is not None

    def test_optimizer_controls_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.optimizer_controls")
        assert mod is not None

    def test_recommendation_worker_imports(self):
        mod = importlib.import_module("src.optimizer_v3.ui.recommendation_worker")
        assert mod is not None


class TestMetricsDisplayPanelAttributes:
    """Verify MetricsDisplayPanel exposes expected public interface."""

    def test_class_has_apply_single_recommendation(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_apply_single_recommendation")

    def test_class_has_apply_selected_recommendations(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_apply_selected_recommendations")

    def test_class_has_add_recheck_config(self):
        """ADD_RECHECK handler method must be present (BTCAAAAA-245 Task 2)."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_add_recheck_config"), \
            "_add_recheck_config not found — was ADD_RECHECK handler implemented?"

    def test_class_has_add_timing_config(self):
        """ADD_TIMING handler method must be present (BTCAAAAA-245 Task 2)."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_add_timing_config"), \
            "_add_timing_config not found — was ADD_TIMING handler implemented?"

    def test_no_action_type_attribute_in_recommendation(self):
        """IntegratedRecommendation should use .type not .action_type (BTCAAAAA-245 Task 1)."""
        from src.optimizer_v3.core.intelligent_recommendation_engine import IntegratedRecommendation
        rec = IntegratedRecommendation(type="ADD_BLOCK", primary=True)
        # .type must exist
        assert rec.type == "ADD_BLOCK"
        # .action_type must NOT exist (old field — was a bug)
        assert not hasattr(rec, "action_type"), \
            "IntegratedRecommendation still has 'action_type' attribute — bug not fixed"
