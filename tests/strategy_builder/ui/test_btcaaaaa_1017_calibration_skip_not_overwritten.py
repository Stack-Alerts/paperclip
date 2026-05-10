"""
Real-widget integration test for BTCAAAAA-1017.

Regression guard: the calibration skip message set by _run_auto_calibration()
must NOT be overwritten by the data-cache status setText in _on_run_clicked().

The fix changes lines 2758/2767 in backtest_config_panel.py from
    self.results_text.setText(...)
to
    self.results_text.append(...)

This test uses a real QTextEdit (not MagicMock) so that the setText-vs-append
distinction is actually exercised — MagicMock stubs cannot catch this bug class.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QTextEdit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CALIB_SKIP_MSG = (
    "✓ Calibration already complete for current settings — skipping. "
    "Using cached parameters."
)

CACHE_HIT_PREFIX = "⚡ Cache HIT:"
CACHE_MISS_PREFIX = "🔄 Cache MISS:"


def _make_stub_with_real_results_text(qapp) -> tuple:
    """
    Return (stub, results_text) where results_text is a real QTextEdit.

    Both _run_auto_calibration and _on_run_clicked are bound from the real
    BacktestConfigPanel source without triggering QWidget.__init__.
    """
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    real_widget = QTextEdit()

    stub = MagicMock()
    stub.results_text = real_widget

    # Calibration cache state — mirrors a cache-hit scenario (second run,
    # same settings, so calibration is skipped and skip message is shown).
    stub._calibration_fingerprint = "cached-fp"
    stub._calibration_cache = {"Alpha": 5}

    # _run_auto_calibration uses confluence_spin for nothing, but the method
    # body calls processEvents via QApplication patch — stub it.
    stub.confluence_spin = MagicMock()
    stub.confluence_spin.value.return_value = 3

    # Bind real methods
    stub._run_auto_calibration = types.MethodType(
        BacktestConfigPanel._run_auto_calibration, stub
    )
    stub._on_run_clicked = types.MethodType(
        BacktestConfigPanel._on_run_clicked, stub
    )

    # Attributes required by _on_run_clicked after calibration
    stub.cache_manager = MagicMock()
    stub.trades_panel = MagicMock()
    stub.output_panel = MagicMock()
    stub.run_btn = MagicMock()
    stub.pause_btn = MagicMock()
    stub.stop_btn = MagicMock()
    stub.results_btn = MagicMock()
    stub.live_output_tab_index = 1
    stub.tab_widget = MagicMock()
    stub.get_config = MagicMock(return_value={"timeframe": "15m", "lookback_days": 180})

    # Pass config through unchanged so _run_auto_calibration receives the real dict
    # with the correct blocks list for fingerprint matching.
    stub._repair_if_unreachable.side_effect = lambda cfg: cfg

    return stub, real_widget


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCalibrationSkipNotOverwritten:
    """
    Real-widget regression tests for BTCAAAAA-1017.

    Verifies that the calibration skip message survives the full
    _on_run_clicked sequence unchanged when the data cache is hit or missed.
    """

    def _run_on_run_clicked_with_cache_hit(self, stub, real_widget):
        """
        Simulate: second run with same settings (calibration cache-hit) and
        data cache-hit path.  Drives _run_auto_calibration() then _on_run_clicked().
        """
        config = {"blocks": [{"name": "Alpha"}]}

        # Compute the fingerprint exactly as _run_auto_calibration does so the
        # cache-hit branch is taken on the second call.
        import hashlib
        import json

        fingerprint_payload = {
            "block_names": ["Alpha"],
            "timeframe": "15m",
            "period_days": 180,
            "mode": "production",
        }
        cached_fp = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode()
        ).hexdigest()
        stub._calibration_fingerprint = cached_fp

        # Step 1: calibration — runs the skip branch, calls setText once.
        with patch("src.strategy_builder.ui.backtest_config_panel.QApplication"):
            stub._run_auto_calibration(config)

        assert CALIB_SKIP_MSG in real_widget.toPlainText(), (
            "Calibration skip message must appear in results_text after _run_auto_calibration()"
        )

        # Step 2: _on_run_clicked data-cache HIT path
        stub.cache_manager.get_cached_bars.return_value = [object()] * 100
        stub.cache_manager.get_metrics.return_value = {"hit_rate_pct": 75.0}

        orchestrate_val = MagicMock()
        orchestrate_val.success = True
        stub.orchestrator.validate_strategy.return_value = orchestrate_val
        stub.orchestrator.serialize_config_for_backtest.return_value = {
            "blocks": [{"name": "Alpha"}],
            "name": "TestStrategy",
        }

        with patch("src.optimizer_v3.database.get_database_manager"), \
             patch("src.strategy_builder.ui.backtest_config_panel.QApplication"), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread") as MockThread, \
             patch("src.strategy_builder.ui.backtest_config_panel.BacktestWorker") as MockWorker, \
             patch("src.optimizer_v3.core.trade_registry.get_trade_registry"):
            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            MockThread.return_value = mock_thread
            MockWorker.return_value = MagicMock()

            try:
                stub._on_run_clicked()
            except Exception:
                pass  # Worker start failures don't affect results_text content

    def _run_on_run_clicked_with_cache_miss(self, stub, real_widget):
        """
        Simulate: second run with same settings (calibration cache-hit) and
        data cache-miss path.
        """
        config = {"blocks": [{"name": "Alpha"}]}

        import hashlib
        import json

        fingerprint_payload = {
            "block_names": ["Alpha"],
            "timeframe": "15m",
            "period_days": 180,
            "mode": "production",
        }
        cached_fp = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode()
        ).hexdigest()
        stub._calibration_fingerprint = cached_fp

        with patch("src.strategy_builder.ui.backtest_config_panel.QApplication"):
            stub._run_auto_calibration(config)

        assert CALIB_SKIP_MSG in real_widget.toPlainText(), (
            "Calibration skip message must appear before _on_run_clicked()"
        )

        # Data cache MISS
        stub.cache_manager.get_cached_bars.return_value = None
        stub.cache_manager.get_metrics.return_value = {"hit_rate_pct": 0.0}

        orchestrate_val = MagicMock()
        orchestrate_val.success = True
        stub.orchestrator.validate_strategy.return_value = orchestrate_val
        stub.orchestrator.serialize_config_for_backtest.return_value = {
            "blocks": [{"name": "Alpha"}],
            "name": "TestStrategy",
        }

        with patch("src.optimizer_v3.database.get_database_manager"), \
             patch("src.strategy_builder.ui.backtest_config_panel.QApplication"), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread") as MockThread, \
             patch("src.strategy_builder.ui.backtest_config_panel.BacktestWorker") as MockWorker, \
             patch("src.optimizer_v3.core.trade_registry.get_trade_registry"):
            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            MockThread.return_value = mock_thread
            MockWorker.return_value = MagicMock()

            try:
                stub._on_run_clicked()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # AC1: Cache-hit path — calibration skip message survives
    # ------------------------------------------------------------------

    def test_calib_skip_message_survives_data_cache_hit(self, qapp):
        """
        After _on_run_clicked data-cache HIT path, results_text must still
        contain the calibration skip message.

        Regression: before the fix, results_text.setText(...) in the cache-HIT
        branch (line 2758) overwrote the skip message entirely.
        """
        stub, real_widget = _make_stub_with_real_results_text(qapp)
        self._run_on_run_clicked_with_cache_hit(stub, real_widget)

        plain = real_widget.toPlainText()
        assert CALIB_SKIP_MSG in plain, (
            f"Calibration skip message must still be in results_text after data-cache HIT.\n"
            f"Got: {plain!r}"
        )

    def test_cache_hit_status_also_present_after_data_cache_hit(self, qapp):
        """
        After the data-cache HIT append, the cache-hit prefix must also be present
        in results_text — confirming append (not replace) was used.
        """
        stub, real_widget = _make_stub_with_real_results_text(qapp)
        self._run_on_run_clicked_with_cache_hit(stub, real_widget)

        plain = real_widget.toPlainText()
        assert CACHE_HIT_PREFIX in plain, (
            f"Data-cache HIT text must be present in results_text.\nGot: {plain!r}"
        )

    # ------------------------------------------------------------------
    # AC2: Cache-miss path — calibration skip message survives
    # ------------------------------------------------------------------

    def test_calib_skip_message_survives_data_cache_miss(self, qapp):
        """
        After _on_run_clicked data-cache MISS path, results_text must still
        contain the calibration skip message.

        Regression: before the fix, results_text.setText(...) in the cache-MISS
        branch (line 2767) overwrote the skip message entirely.
        """
        stub, real_widget = _make_stub_with_real_results_text(qapp)
        self._run_on_run_clicked_with_cache_miss(stub, real_widget)

        plain = real_widget.toPlainText()
        assert CALIB_SKIP_MSG in plain, (
            f"Calibration skip message must still be in results_text after data-cache MISS.\n"
            f"Got: {plain!r}"
        )

    def test_cache_miss_status_also_present_after_data_cache_miss(self, qapp):
        """
        After the data-cache MISS append, the cache-miss prefix must also be present —
        confirming both messages coexist in the widget.
        """
        stub, real_widget = _make_stub_with_real_results_text(qapp)
        self._run_on_run_clicked_with_cache_miss(stub, real_widget)

        plain = real_widget.toPlainText()
        assert CACHE_MISS_PREFIX in plain, (
            f"Data-cache MISS text must be present in results_text.\nGot: {plain!r}"
        )

    # ------------------------------------------------------------------
    # AC3: QTextEdit.append semantics guard (unit-level proof)
    # ------------------------------------------------------------------

    def test_qtextedit_append_preserves_existing_content(self, qapp):
        """
        Direct proof: QTextEdit.append() must not erase pre-existing content.
        This is the semantic property our fix relies on.
        """
        widget = QTextEdit()
        widget.setText("First line")
        widget.append("Second line")

        plain = widget.toPlainText()
        assert "First line" in plain, (
            "QTextEdit.append() must preserve prior content — 'First line' erased"
        )
        assert "Second line" in plain, (
            "QTextEdit.append() must add new content — 'Second line' missing"
        )

    def test_qtextedit_set_text_does_overwrite(self, qapp):
        """
        Confirm (as a guard) that QTextEdit.setText() DOES overwrite.
        This documents why the original setText in _on_run_clicked was the bug.
        """
        widget = QTextEdit()
        widget.setText("First line")
        widget.setText("Second line")  # overwrites — the old bug

        plain = widget.toPlainText()
        assert "First line" not in plain, (
            "QTextEdit.setText() must replace content — this test proves the original bug exists"
        )
        assert "Second line" in plain, (
            "QTextEdit.setText() must set new content"
        )
