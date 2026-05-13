"""
Regression tests for BTCAAAAA-423: UX Fixes in MetricsDisplayPanel and BacktestConfigPanel.

Issue: BTCAAAAA-423
Component: src/optimizer_v3/ui/metrics_display_panel.py, src/strategy_builder/ui/backtest_config_panel.py

Fixes applied:
  1. _switch_to_metrics_tab() now prefers 'Metrics' tab (not 'AI Recommendations').
  2. Tab order in backtest_config_panel: Config | Live Output | Trades | AI Recommendations | Metrics | Compare.
  3. _find_main_window() walks the full Qt parent chain past BacktestConfigDialog.
  4. _refresh_strategy_builder_ui() calls blocks_panel.refresh_from_orchestrator().
"""

from __future__ import annotations

import inspect
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-423"),
    pytest.mark.regression,
]


class TestSwitchToMetricsTabStructural:
    """Structural checks for _switch_to_metrics_tab preferring Metrics over AI Recommendations."""

    def test_switch_to_metrics_tab_method_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_switch_to_metrics_tab")

    def test_switch_checks_metric_before_ai(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        metric_pos = src.find("'metric'")
        ai_pos = src.find("'ai'")
        assert metric_pos != -1, "'metric' check not found"
        assert ai_pos != -1, "'ai' fallback not found"
        assert metric_pos < ai_pos, "'metric' check must precede 'ai' fallback"


class TestTabOrderStructural:
    """Structural checks for tab order in BacktestConfigPanel."""

    def test_ai_recommendations_before_metrics_in_source(self):
        source_path = pathlib.Path("src/strategy_builder/ui/backtest_config_panel.py")
        source = source_path.read_text()
        ai_pos = source.find("AI Recommendations")
        metrics_pos = source.find('"💹 Metrics"')
        assert ai_pos != -1, "AI Recommendations tab not found"
        assert metrics_pos != -1, "Metrics tab not found"
        assert ai_pos < metrics_pos, "AI Recommendations addTab must appear before Metrics"

    def test_signal_connections_present(self):
        source = pathlib.Path("src/strategy_builder/ui/backtest_config_panel.py").read_text()
        assert "metrics_updated" in source
        assert "send_approved" in source
        assert "recommendations_generated" in source
        assert "_on_ai_request_approved" in source
        assert "display_recommendations" in source


class TestFindMainWindowStructural:
    """Structural checks for _find_main_window walking the full parent chain."""

    def test_find_main_window_method_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_find_main_window")

    def test_find_main_window_uses_blocks_panel_check(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._find_main_window)
        assert "blocks_panel" in src

    def test_refresh_uses_refresh_from_orchestrator(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._refresh_strategy_builder_ui)
        assert "refresh_from_orchestrator" in src
