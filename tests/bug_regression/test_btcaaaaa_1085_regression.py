"""
Regression tests for BTCAAAAA-1085 — flush signal queue & store fingerprint
unconditionally after calibration.

Bug: _run_auto_calibration had two gaps:

Gap 1 (cache bypass on empty results):
    ``elif calibration_results:`` meant the fingerprint and delay_map were
    only written when results were non-empty.  If calibration completed with
    zero entries (a valid outcome), the next call would compute a different
    fingerprint (never stored) and trigger a redundant re-run.

Gap 2 (unsynchronised signal delivery):
    After the while-loop exited (thread isRunning()==False), cross-thread
    Qt signals (training_complete → _on_complete) might not yet have been
    delivered.  The code read ``calibration_results`` before the signal had
    fired, losing valid results.

Fix (both in src/strategy_builder/ui/backtest_config_panel.py):
    Gap 1: Change ``elif calibration_results:`` to ``else:`` so the cache
           is always written when calibration runs to completion, regardless
           of whether results are empty.
    Gap 2: Call ``calibration_thread.wait()`` then
           ``QApplication.processEvents()`` after the loop to flush the
           signal queue before reading calibration_results.
"""

from __future__ import annotations

import types
import sys
import pytest
from unittest.mock import MagicMock, patch


pytestmark = [
    pytest.mark.bug("BTCAAAAA-1085"),
    pytest.mark.regression,
]

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Helper — build a minimal stub for _run_auto_calibration tests
# ---------------------------------------------------------------------------

def _make_calibration_stub():
    fn = None
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
    fn = BacktestConfigPanel._run_auto_calibration
    stub = MagicMock()
    stub.results_text = MagicMock()
    stub._calibration_fingerprint = None
    stub._calibration_cache = None
    stub._run_auto_calibration = types.MethodType(fn, stub)
    return stub


# ---------------------------------------------------------------------------
# Gap 1 tests — cache stored unconditionally after calibration (even when
# calibration_results is empty)
# ---------------------------------------------------------------------------

class TestGap1EmptyCalibrationResults:
    """Gap 1: calibration_results == [] must still write fingerprint + cache."""

    def _run_calibration(self, stub, config, calib_results, sim_mode=False):
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False
        mock_thread.is_simulation_mode = sim_mode
        connected_callbacks = []

        def _capture_connect(cb):
            connected_callbacks.append(cb)

        mock_thread.training_complete.connect.side_effect = _capture_connect

        def _start():
            for cb in connected_callbacks:
                cb(calib_results)

        mock_thread.start.side_effect = _start

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

    def test_cache_stored_when_results_empty(self, qapp):
        """Empty calibration_results must still write fingerprint + cache."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        self._run_calibration(stub, config, calib_results=[])

        assert stub._calibration_fingerprint is not None
        assert stub._calibration_cache is not None
        assert stub._calibration_cache == {}

    def test_cache_hit_after_empty_results(self, qapp):
        """After an empty-result calibration, the next call must hit cache."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        self._run_calibration(stub, config, calib_results=[])
        stub.results_text.reset_mock()

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ) as MockThread:
            stub._run_auto_calibration(config)

        MockThread.assert_not_called()
        first_set_text = stub.results_text.setText.call_args_list[0].args[0]
        assert "skipping" in first_set_text.lower()

    def test_cache_stored_with_partial_results(self, qapp):
        """Partial results must still cache."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}, {'name': 'Beta'}]}

        self._run_calibration(
            stub, config,
            calib_results=[{'signal_name': 'Alpha', 'optimal_delay': 5}],
        )

        assert stub._calibration_fingerprint is not None
        assert stub._calibration_cache == {'Alpha': 5}

    def test_cache_stored_when_all_results_missing_keys(self, qapp):
        """Results with missing signal_name or optimal_delay must still cache."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        self._run_calibration(
            stub, config,
            calib_results=[{'foo': 'bar'}],
        )

        assert stub._calibration_fingerprint is not None
        assert stub._calibration_cache == {}

    def test_empty_results_not_cached_in_simulation_mode(self, qapp):
        """Simulation mode must NOT cache even when results are empty."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        self._run_calibration(
            stub, config,
            calib_results=[],
            sim_mode=True,
        )

        assert stub._calibration_fingerprint is None
        assert stub._calibration_cache is None

    def test_empty_results_produces_correct_status_message(self, qapp):
        """Empty results still shows 'Calibration complete' message."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        self._run_calibration(stub, config, calib_results=[])

        appended_texts = [c.args[0] for c in stub.results_text.append.call_args_list]
        assert any(
            "calibration complete" in t.lower() or "starting backtest" in t.lower()
            for t in appended_texts
        )


# ---------------------------------------------------------------------------
# Gap 2 tests — signal queue flush verification
# ---------------------------------------------------------------------------

class TestGap2SignalQueueFlush:
    """Gap 2: calibration_thread.wait() + processEvents() flush sequence."""

    def test_wait_and_process_events_called_after_loop(self, qapp):
        """After the isRunning loop exits, wait() and processEvents() must be called."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication.processEvents"
        ) as mock_proc_events, patch(
            "src.strategy_builder.ui.backtest_config_panel.calibration_cache.save_cache"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

        mock_thread.wait.assert_called()
        assert mock_proc_events.called

    def test_wait_called_after_loop_exits(self, qapp):
        """The code must call wait() directly after the while loop (not only inside it).

        Verifies that a wait() call happens even when isRunning() is False
        and the while-loop body never executes.
        """
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

        # wait() must have been called with no timeout arg (the post-loop
        # wait() on line 2693) — the in-loop wait uses wait(200)
        assert any(
            len(call[0]) == 0 or call[0] == ()
            for call in mock_thread.wait.call_args_list
        ), f"Expected a wait() call with no args (post-loop), got: {mock_thread.wait.call_args_list}"

    def test_timeout_path_still_works(self, qapp):
        """When calibration times out, the method degrades gracefully."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

        appended_texts = [c.args[0] for c in stub.results_text.append.call_args_list]
        assert any(
            "timed out" in t.lower() or "timeout" in t.lower()
            for t in appended_texts
        )

    def test_wait_called_on_both_paths(self, qapp):
        """wait() must be called for both simulation and non-simulation paths."""
        for sim_mode in (True, False):
            stub = _make_calibration_stub()
            config = {'blocks': [{'name': 'Alpha'}]}

            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            mock_thread.is_simulation_mode = sim_mode

            with patch(
                "src.strategy_builder.ui.backtest_config_panel.QApplication"
            ), patch(
                "src.optimizer_v3.core.training_thread.TrainingThread",
                return_value=mock_thread,
            ):
                stub._run_auto_calibration(config)

            mock_thread.wait.assert_called()
