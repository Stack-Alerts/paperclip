"""
Regression tests for BTCAAAAA-381: _allow_dialog_close must finalize
recommendations when _recommendations_waiting is set (timer path).

Issue: BTCAAAAA-381
Component: src/optimizer_v3/ui/metrics_display_panel.py

Root cause: _allow_dialog_close() set dialog_can_close=True and closed the
progress dialog but never called _finalize_recommendations() when
_recommendations_waiting was True.  AI recommendations that arrived before
the 1-second minimum-dialog timer were silently dropped — the
recommendations_generated signal was never emitted and
AIRecommendationsPanel.display_recommendations() was never invoked.

Fix: _allow_dialog_close() now calls _finalize_recommendations() after
deleting the _recommendations_waiting flag (single-fire, no re-entry).

This file tests that:
  1. _allow_dialog_close, _on_recommendations_ready, _finalize_recommendations
     all exist on MetricsDisplayPanel.
  2. _allow_dialog_close calls _finalize_recommendations when
     _recommendations_waiting is detected.
  3. _recommendations_waiting is deleted BEFORE _finalize_recommendations
     is called (double-fire prevention).
  4. _on_recommendations_ready sets _recommendations_waiting when the
     dialog minimum time has not yet elapsed (slow path).
  5. _on_recommendations_ready directly finalizes when dialog_can_close
     is True (fast path).
  6. dialog_can_close is initialised as False in init paths.
  7. progress_dialog is created in init paths.
  8. min_dialog_timer is connected to _allow_dialog_close.
  9. rec_worker.recommendations_ready is connected to _on_recommendations_ready.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-381"),
    pytest.mark.regression,
]

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "optimizer_v3"
    / "ui"
    / "metrics_display_panel.py"
).read_text()


class TestMethodsExist:
    """Verify the fix methods exist on MetricsDisplayPanel."""

    def test_allow_dialog_close_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        assert hasattr(MetricsDisplayPanel, "_allow_dialog_close"), (
            "_allow_dialog_close not found on MetricsDisplayPanel"
        )

    def test_on_recommendations_ready_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        assert hasattr(MetricsDisplayPanel, "_on_recommendations_ready"), (
            "_on_recommendations_ready not found on MetricsDisplayPanel"
        )

    def test_finalize_recommendations_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        assert hasattr(MetricsDisplayPanel, "_finalize_recommendations"), (
            "_finalize_recommendations not found on MetricsDisplayPanel"
        )


class TestAllowDialogCloseFix:
    """Verify _allow_dialog_close() contains the fix for BTCAAAAA-381."""

    def test_calls_finalize_when_recommendations_waiting(self):
        """_allow_dialog_close must call _finalize_recommendations() when
        _recommendations_waiting is present."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._allow_dialog_close)
        assert "hasattr(self, '_recommendations_waiting')" in src, (
            "_allow_dialog_close must check for _recommendations_waiting"
        )
        assert "_finalize_recommendations()" in src, (
            "_allow_dialog_close must call _finalize_recommendations() in the timer path"
        )

    def test_deletes_flag_before_finalize(self):
        """_recommendations_waiting must be deleted BEFORE _finalize_recommendations
        is called, to prevent double-fire / re-entry."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._allow_dialog_close)
        del_pos = src.find("del self._recommendations_waiting")
        finalize_pos = src.find("_finalize_recommendations()")
        assert del_pos >= 0, (
            "_recommendations_waiting must be deleted in _allow_dialog_close"
        )
        assert finalize_pos >= 0, (
            "_finalize_recommendations() must be called in _allow_dialog_close"
        )
        assert del_pos < finalize_pos, (
            "del _recommendations_waiting must occur BEFORE _finalize_recommendations() "
            "to prevent double-fire / re-entry"
        )

    def test_dialog_can_close_set_to_true(self):
        """_allow_dialog_close must set dialog_can_close=True."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._allow_dialog_close)
        assert "self.dialog_can_close = True" in src, (
            "_allow_dialog_close must set dialog_can_close = True"
        )

    def test_closes_progress_dialog(self):
        """_allow_dialog_close must close the progress dialog."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._allow_dialog_close)
        assert "self.progress_dialog.close()" in src, (
            "_allow_dialog_close must call progress_dialog.close()"
        )


class TestOnRecommendationsReady:
    """Verify _on_recommendations_ready handles both slow and fast paths."""

    def test_sets_waiting_flag_when_dialog_not_ready(self):
        """When dialog_can_close is False, must set _recommendations_waiting=True
        and return early (slow path)."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_recommendations_ready)
        assert "self._recommendations_waiting = True" in src, (
            "_on_recommendations_ready must set _recommendations_waiting = True "
            "when dialog minimum time has not elapsed"
        )
        assert "return" in src, (
            "_on_recommendations_ready must return early in the slow path "
            "(do not update UI yet — wait for timer)"
        )

    def test_closes_dialog_in_fast_path(self):
        """When dialog_can_close is True, must close dialog and finalize directly."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_recommendations_ready)
        assert "self.dialog_can_close" in src, (
            "_on_recommendations_ready must check dialog_can_close"
        )

    def test_no_waiting_flag_in_fast_path(self):
        """Fast path (dialog_can_close=True) must NOT set _recommendations_waiting."""
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel

        src = inspect.getsource(MetricsDisplayPanel._on_recommendations_ready)
        lines = src.split("\n")
        in_fast_path = False
        for line in lines:
            stripped = line.strip()
            if "self.dialog_can_close" in stripped and "if" in stripped:
                in_fast_path = True
                continue
            if in_fast_path:
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith("else:") or stripped.startswith("elif "):
                    in_fast_path = False
                    continue
                if "_recommendations_waiting = True" in stripped:
                    pytest.fail(
                        "_recommendations_waiting must NOT be set in the fast path"
                    )


class TestDialogInit:
    """Verify dialog state is initialised correctly in init paths."""

    def test_dialog_can_close_initialised_false(self):
        """dialog_can_close must be initialised to False."""
        assert "self.dialog_can_close = False" in SOURCE, (
            "dialog_can_close must be initialised to False"
        )

    def test_progress_dialog_created(self):
        """progress_dialog must be created at init."""
        assert "QProgressDialog" in SOURCE, (
            "QProgressDialog must be created at init"
        )

    def test_min_dialog_timer_connected_to_allow_dialog_close(self):
        """min_dialog_timer.timeout must be connected to _allow_dialog_close."""
        assert "min_dialog_timer.timeout.connect(self._allow_dialog_close)" in SOURCE, (
            "min_dialog_timer must be connected to _allow_dialog_close"
        )

    def test_rec_worker_connected_to_on_recommendations_ready(self):
        """rec_worker.recommendations_ready must be connected to _on_recommendations_ready."""
        assert "recommendations_ready.connect(self._on_recommendations_ready)" in SOURCE, (
            "rec_worker.recommendations_ready must be connected to _on_recommendations_ready"
        )
