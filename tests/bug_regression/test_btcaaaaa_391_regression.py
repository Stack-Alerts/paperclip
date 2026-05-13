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

    def test_finalize_updates_performance_table(self):
        """_finalize_recommendations must call _update_performance_table."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "self._update_performance_table()" in src, (
            "_finalize_recommendations must call _update_performance_table() "
            "to refresh table with new recommendations"
        )

    def test_finalize_updates_risk_table(self):
        """_finalize_recommendations must call _update_risk_table."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "self._update_risk_table()" in src, (
            "_finalize_recommendations must call _update_risk_table() "
            "to refresh risk table with new recommendations"
        )

    def test_finalize_updates_status_label(self):
        """_finalize_recommendations must update the status label text."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "self.status_label.setText(" in src, (
            "_finalize_recommendations must call setText on status_label "
            "to inform the user how many AI recommendations were generated"
        )

    def test_finalize_populates_ai_recommendations_panel(self):
        """_finalize_recommendations must populate the AI Recommendations Panel."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "self._populate_ai_recommendations_panel()" in src, (
            "_finalize_recommendations must call _populate_ai_recommendations_panel() "
            "to push full preview data to the AI Recommendations Panel"
        )

    def test_finalize_emits_recommendations_generated_signal(self):
        """_finalize_recommendations must emit recommendations_generated signal."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._finalize_recommendations)
        assert "self.recommendations_generated.emit(" in src, (
            "_finalize_recommendations must emit recommendations_generated signal "
            "with batch recommendations to wire to AIRecommendationsPanel"
        )

    def test_switch_to_metrics_tab_has_error_handling(self):
        """_switch_to_metrics_tab must have try/except error handling."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        assert "try:" in src, (
            "_switch_to_metrics_tab must wrap logic in try/except to gracefully "
            "handle errors during tab navigation"
        )
        assert "except Exception" in src, (
            "_switch_to_metrics_tab must catch Exception to prevent crashes "
            "if tab widget parent traversal fails"
        )

    def test_switch_to_metrics_tab_searches_parent_hierarchy(self):
        """_switch_to_metrics_tab must traverse parent hierarchy to find QTabWidget."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        assert "isinstance(parent, QTabWidget)" in src, (
            "_switch_to_metrics_tab must check isinstance(parent, QTabWidget) "
            "to locate the tab widget container in the parent hierarchy"
        )
        assert "parent.setCurrentIndex(i)" in src, (
            "_switch_to_metrics_tab must call setCurrentIndex on the tab widget "
            "to switch to the Metrics tab"
        )

    def test_switch_to_metrics_tab_prefers_metrics_tab(self):
        """_switch_to_metrics_tab must prefer the 'Metrics' tab over fallback."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._switch_to_metrics_tab)
        assert "'metric' in tab_text" in src, (
            "_switch_to_metrics_tab must check for 'metric' in tab_text "
            "as the primary tab target"
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
        assert (
            "setRange(0, 100)" in src and "percentage == 95" in src
        ) or "elif percentage == 95" in src, (
            "_on_ai_progress must restore setRange(0, 100) in the percentage == 95 branch"
        )

    def test_percentage_80_and_95_branches_exist(self):
        """_on_ai_progress must handle both percentage == 80 and percentage == 95."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "percentage == 80" in src, "percentage == 80 branch must exist"
        assert "percentage == 95" in src, "percentage == 95 branch must exist"

    def test_on_ai_progress_early_return_when_no_dialog(self):
        """_on_ai_progress must early-return when progress_dialog does not exist."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "hasattr(self, 'progress_dialog')" in src, (
            "_on_ai_progress must check hasattr(self, 'progress_dialog') "
            "and return early if the dialog has been destroyed"
        )

    def test_on_ai_progress_percentage_100_branch(self):
        """_on_ai_progress must snap to 100% on completion."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "percentage == 100" in src, (
            "_on_ai_progress must handle percentage == 100 "
            "to snap the progress bar to completion"
        )
        assert "setValue(percentage)" in src, (
            "_on_ai_progress must call setValue(percentage) to update the bar value"
        )

    def test_on_ai_progress_normal_progress_branch(self):
        """_on_ai_progress must handle normal progress updates (percentage >= 0)."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "percentage >= 0" in src, (
            "_on_ai_progress must have a percentage >= 0 branch "
            "for regular progress updates between 0-79%"
        )

    def test_on_ai_progress_updates_label_text(self):
        """_on_ai_progress must call setLabelText with the progress message."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_ai_progress)
        assert "self.progress_dialog.setLabelText(message)" in src, (
            "_on_ai_progress must call setLabelText(message) to update "
            "the progress dialog label with the current step description"
        )
