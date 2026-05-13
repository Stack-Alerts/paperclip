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

    def test_switch_falls_back_to_ai_recommendations(self):
        """_switch_to_metrics_tab must fall back to 'ai'/'rec' tab when Metrics tab is absent."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        assert "'ai'" in src or "'rec'" in src, "Fallback to AI/Recommendations tab must exist"

    def test_switch_logs_warning_when_no_tabwidget(self):
        """_switch_to_metrics_tab must log a warning when no QTabWidget is found."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        assert "warning" in src.lower() or "WARNING" in src, (
            "Must log warning when tab widget not found"
        )


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

    def test_all_six_tab_titles_present(self):
        """All six expected tab titles must appear in backtest_config_panel.py source."""
        source = pathlib.Path("src/strategy_builder/ui/backtest_config_panel.py").read_text()
        for keyword in ["Config", "Live Output", "Trades", "AI Recommendations", "Metrics", "Compare"]:
            assert keyword in source, f"Tab '{keyword}' not found in source"


class TestFindMainWindowStructural:
    """Structural checks for _find_main_window walking the full parent chain."""

    def test_find_main_window_method_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_find_main_window")

    def test_find_main_window_uses_blocks_panel_check(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._find_main_window)
        assert "blocks_panel" in src

    def test_find_main_window_walks_parent_chain(self):
        """_find_main_window must use a while loop with widget.parent(), not just self.window()."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._find_main_window)
        assert "parent()" in src, "Must walk Qt parent chain via widget.parent()"

    def test_find_main_window_returns_none_as_fallback(self):
        """_find_main_window must return None when no blocks_panel ancestor exists."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._find_main_window)
        assert "return None" in src, "Must return None when main window not found"

    def test_refresh_uses_refresh_from_orchestrator(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._refresh_strategy_builder_ui)
        assert "refresh_from_orchestrator" in src

    def test_refresh_handles_none_main_window(self):
        """_refresh_strategy_builder_ui must guard against main_window being None."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        src = inspect.getsource(MetricsDisplayPanel._refresh_strategy_builder_ui)
        assert "main_window is None" in src or "MainWindow not found" in src, (
            "Must guard against None main_window"
        )
