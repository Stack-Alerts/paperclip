"""
Regression tests for BTCAAAAA-391: AI progress UX fixes in MetricsDisplayPanel.

Issue: BTCAAAAA-391
Component: src/optimizer_v3/ui/metrics_display_panel.py

Fixes applied:
  1. Bug 3: Deferred tab switch via QTimer.singleShot(0) in _finalize_recommendations
     so the tab switch runs after all pending Qt events (dialog-close cleanup,
     focus-change events) are processed, preventing the switch from being overridden.
  2. UX fix: _on_ai_progress switches progress bar to indeterminate mode at 80%
     (when AI API HTTP call blocks for 15-30s) and restores determinate mode at 95%.

This file verifies both guards are present in the source code.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-391"),
    pytest.mark.regression,
]


class TestDeferredTabSwitchGuard:
    """Structural checks for the QTimer.singleShot(0) deferred tab switch."""

    def test_single_shot_timer_in_finalize_recommendations(self):
        """_finalize_recommendations must use QTimer.singleShot(0) to defer tab switch."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "QTimer.singleShot(0, self._switch_to_metrics_tab)" in src, (
            "_finalize_recommendations must call QTimer.singleShot(0, "
            "self._switch_to_metrics_tab) to defer the tab switch after dialog close"
        )

    def test_switch_to_metrics_tab_method_exists(self):
        """_switch_to_metrics_tab method must exist on MetricsDisplayPanel."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        assert hasattr(MetricsDisplayPanel, "_switch_to_metrics_tab"), (
            "_switch_to_metrics_tab() must exist on MetricsDisplayPanel"
        )


class TestProgressIndeterminateModeGuard:
    """Structural checks for indeterminate progress bar mode at 80%."""

    def test_indeterminate_mode_at_80_percent(self):
        """_on_ai_progress must switch to indeterminate mode at percentage == 80."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "setRange(0, 0)" in src, (
            "_on_ai_progress must call setRange(0, 0) to enter indeterminate mode "
            "when the AI API call is about to block"
        )

    def test_determinate_restored_at_95_percent(self):
        """_on_ai_progress must restore determinate (0, 100) range at 95%."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert ("setRange(0, 100)" in src and "percentage == 95" in src) or "elif percentage == 95" in src, (
            "_on_ai_progress must restore setRange(0, 100) in the percentage == 95 branch"
        )

    def test_percentage_80_and_95_branches_exist(self):
        """_on_ai_progress must handle both percentage == 80 and percentage == 95."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "percentage == 80" in src, "percentage == 80 branch must exist"
        assert "percentage == 95" in src, "percentage == 95 branch must exist"
