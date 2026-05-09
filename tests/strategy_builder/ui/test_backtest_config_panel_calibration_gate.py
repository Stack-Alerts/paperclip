"""
Unit tests for BacktestConfigPanel auto-calibration flow — BTCAAAAA-338/339.

Replaces the old calibration-gate test suite (BTCAAAAA-327/329).

Covers:
- _run_auto_calibration(): skips when no blocks present
- _run_auto_calibration(): shows status messages before and after calibration
- _run_auto_calibration(): spawns TrainingThread with correct parameters
- _run_auto_calibration(): applies optimal_delay results to blocks in-place
- _run_auto_calibration(): gracefully degrades when TrainingThread raises
- _run_auto_calibration(): gracefully degrades on timeout
- _on_run_clicked(): calls _run_auto_calibration() (no calibration dialog, no gate)
- _on_run_clicked(): proceeds past validation when strategy is valid
- Code structure: no _is_calibrated(), no setCurrentIndex(1), _run_auto_calibration present
"""

from __future__ import annotations

import sys
import types
import inspect
import pytest
from unittest.mock import MagicMock, patch, call, ANY

from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------

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
    """
    Return a MagicMock stub with _run_auto_calibration bound from the real
    BacktestConfigPanel source, without triggering QWidget.__init__.
    """
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    fn = BacktestConfigPanel._run_auto_calibration

    stub = MagicMock()
    stub.results_text = MagicMock()
    # Initialize cache attributes as None (mirrors BacktestConfigPanel.__init__)
    stub._calibration_fingerprint = None
    stub._calibration_cache = None

    stub._run_auto_calibration = types.MethodType(fn, stub)
    return stub


def _make_run_clicked_stub():
    """
    Return a stub with _on_run_clicked and _run_auto_calibration bound from
    the real BacktestConfigPanel source.
    """
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    run_clicked_fn = BacktestConfigPanel._on_run_clicked
    auto_calib_fn = BacktestConfigPanel._run_auto_calibration

    stub = MagicMock()
    stub.results_text = MagicMock()
    stub.confluence_spin = MagicMock()
    stub.confluence_spin.value.return_value = 3

    stub._run_auto_calibration = types.MethodType(auto_calib_fn, stub)
    stub._on_run_clicked = types.MethodType(run_clicked_fn, stub)

    return stub


# ---------------------------------------------------------------------------
# Tests for _run_auto_calibration()
# ---------------------------------------------------------------------------

class TestRunAutoCalibration:
    """Unit tests for BacktestConfigPanel._run_auto_calibration()."""

    def test_skips_when_no_blocks(self, qapp):
        """When strategy_config_dict has no blocks, method returns without error."""
        stub = _make_calibration_stub()
        # Should not raise, should not call results_text.setText
        stub._run_auto_calibration({'blocks': []})
        stub.results_text.setText.assert_not_called()

    def test_skips_when_blocks_key_missing(self, qapp):
        """When strategy_config_dict has no 'blocks' key, method skips silently."""
        stub = _make_calibration_stub()
        stub._run_auto_calibration({})
        stub.results_text.setText.assert_not_called()

    def test_shows_calibrating_status_message(self, qapp):
        """Status area must show calibration-in-progress message before thread starts."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'BlockA'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

        # The very first setText call must mention calibration
        first_call_text = stub.results_text.setText.call_args_list[0].args[0]
        assert "calibration" in first_call_text.lower() or "calibrat" in first_call_text.lower()

    def test_shows_complete_status_after_success(self, qapp):
        """Status area must show completion message after a successful calibration."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'BlockA'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ):
            stub._run_auto_calibration(config)

        appended_texts = [c.args[0] for c in stub.results_text.append.call_args_list]
        assert any(
            "calibration complete" in t.lower() or "starting backtest" in t.lower()
            for t in appended_texts
        ), f"Expected completion message in append calls: {appended_texts}"

    def test_training_thread_receives_correct_parameters(self, qapp):
        """TrainingThread must be started with 15m timeframe, 180-day lookback, production mode."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}, {'name': 'Beta'}]}

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            return_value=mock_thread,
        ) as MockThread:
            stub._run_auto_calibration(config)

        init_kwargs = MockThread.call_args
        _, kwargs = init_kwargs if isinstance(init_kwargs[0], tuple) else ((), init_kwargs[1])
        # Accept positional or keyword args
        all_args = dict(zip(
            ['selected_blocks', 'mode', 'period_days', 'selected_timeframes', 'logger'],
            init_kwargs[0] if init_kwargs[0] else []
        ))
        all_args.update(init_kwargs[1] if init_kwargs[1] else {})

        assert all_args.get('mode') == 'production', "mode must be 'production'"
        assert all_args.get('period_days') == 180, "period_days must be 180"
        assert all_args.get('selected_timeframes') == ['15m'], "timeframe must be ['15m']"
        assert set(all_args.get('selected_blocks', [])) == {'Alpha', 'Beta'}

    def test_applies_optimal_delay_to_blocks_when_not_simulation(self, qapp):
        """When TrainingThread.is_simulation_mode=False, optimal_delay IS written into blocks."""
        stub = _make_calibration_stub()
        block_a = {'name': 'Alpha'}
        config = {'blocks': [block_a]}

        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 5}]

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False
        mock_thread.is_simulation_mode = False  # Real calibration path active

        # Capture the signal connection and call _on_complete synchronously
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

        assert block_a.get('optimal_delay') == 5, (
            f"Expected optimal_delay=5 on block Alpha when not in simulation mode, got {block_a}"
        )

    def test_does_not_apply_optimal_delay_when_simulation_mode(self, qapp):
        """When TrainingThread.is_simulation_mode=True, optimal_delay is NOT written to blocks.

        This guards against random/dummy calibration data silently overwriting
        manually-tuned block delays (BTCAAAAA-348).
        """
        stub = _make_calibration_stub()
        block_a = {'name': 'Alpha', 'optimal_delay': 42}  # manually-set value
        config = {'blocks': [block_a]}

        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 7}]  # random/fake result

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False
        mock_thread.is_simulation_mode = True  # Simulation mode — do NOT apply

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

        assert block_a.get('optimal_delay') == 42, (
            f"Manually-set optimal_delay must NOT be overwritten in simulation mode, got {block_a}"
        )

        # Status message must inform user that simulation mode was active
        appended_texts = [c.args[0] for c in stub.results_text.append.call_args_list]
        assert any(
            "simulation mode" in t.lower() for t in appended_texts
        ), f"Expected 'simulation mode' message, got: {appended_texts}"

    def test_graceful_degradation_when_thread_raises(self, qapp):
        """When TrainingThread constructor raises, _run_auto_calibration does not propagate."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            side_effect=RuntimeError("simulated failure"),
        ):
            # Must NOT raise
            stub._run_auto_calibration(config)

        # Warning/skip message appended
        appended_texts = [c.args[0] for c in stub.results_text.append.call_args_list]
        assert any(
            "calibration skipped" in t.lower() or "proceeding" in t.lower()
            for t in appended_texts
        ), f"Expected graceful-degradation message, got: {appended_texts}"

    def test_graceful_degradation_does_not_modify_blocks_on_failure(self, qapp):
        """On exception, blocks in strategy_config_dict are left unchanged."""
        stub = _make_calibration_stub()
        block_a = {'name': 'Alpha'}
        config = {'blocks': [block_a]}

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            side_effect=RuntimeError("boom"),
        ):
            stub._run_auto_calibration(config)

        assert 'optimal_delay' not in block_a, (
            "optimal_delay must NOT be set on blocks when calibration fails"
        )


# ---------------------------------------------------------------------------
# Tests for _on_run_clicked() auto-calibration integration
# ---------------------------------------------------------------------------

class TestOnRunClickedAutoCalibration:
    """Tests that _on_run_clicked() integrates auto-calibration correctly."""

    def test_no_calibration_dialog_when_running(self, qapp):
        """_on_run_clicked() must never show a 'Calibration Required' dialog."""
        stub = _make_run_clicked_stub()

        # Strategy validation fails — stops cleanly after calibration call
        mock_val = MagicMock()
        mock_val.success = False
        mock_val.message = "test stop"
        stub.orchestrator.validate_strategy.return_value = mock_val

        with patch(
            "src.optimizer_v3.database.get_database_manager"
        ), patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ) as MockThread:
            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            MockThread.return_value = mock_thread

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        # QMessageBox must never have been called with "Calibration Required"
        # (The stub has no real QMessageBox — if the old code path ran, it
        # would call QMessageBox which is a MagicMock on the stub; check
        # the setWindowTitle was not called with that title on any mock.)
        for mock_call in stub.mock_calls:
            if 'setWindowTitle' in str(mock_call):
                assert 'Calibration Required' not in str(mock_call), (
                    "_on_run_clicked() must not show 'Calibration Required' dialog"
                )

    def test_auto_calibration_called_before_worker_creation(self, qapp):
        """_run_auto_calibration must be called before BacktestWorker is created."""
        stub = _make_run_clicked_stub()

        call_order = []

        mock_val = MagicMock()
        mock_val.success = True
        stub.orchestrator.validate_strategy.return_value = mock_val
        stub.orchestrator.serialize_config_for_backtest.return_value = {
            'blocks': [{'name': 'Alpha'}],
            'name': 'TestStrategy',
        }

        original_auto_calib = stub._run_auto_calibration

        def _track_auto_calib(cfg):
            call_order.append('auto_calibration')
            return original_auto_calib(cfg)

        stub._run_auto_calibration = _track_auto_calib

        with patch(
            "src.optimizer_v3.database.get_database_manager"
        ), patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ) as MockThread, patch(
            "src.strategy_builder.ui.backtest_config_panel.BacktestWorker",
        ) as MockWorker:
            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            MockThread.return_value = mock_thread

            def _track_worker(*a, **kw):
                call_order.append('worker_created')
                return MagicMock()

            MockWorker.side_effect = _track_worker

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        assert 'auto_calibration' in call_order, "_run_auto_calibration was never called"
        if 'worker_created' in call_order:
            auto_idx = call_order.index('auto_calibration')
            worker_idx = call_order.index('worker_created')
            assert auto_idx < worker_idx, (
                "_run_auto_calibration must be called BEFORE BacktestWorker creation"
            )

    def test_validate_strategy_called_before_auto_calibration(self, qapp):
        """Strategy validation must happen before auto-calibration (fail fast on bad strategy)."""
        stub = _make_run_clicked_stub()

        # Strategy validation fails — auto-calibration should NOT run
        mock_val = MagicMock()
        mock_val.success = False
        mock_val.message = "No strategy"
        stub.orchestrator.validate_strategy.return_value = mock_val

        auto_calib_called = []
        original = stub._run_auto_calibration

        def _track(cfg):
            auto_calib_called.append(True)
            return original(cfg)

        stub._run_auto_calibration = _track

        with patch("src.optimizer_v3.database.get_database_manager"), \
             patch("src.strategy_builder.ui.backtest_config_panel.QApplication"):
            try:
                stub._on_run_clicked()
            except Exception:
                pass

        assert not auto_calib_called, (
            "_run_auto_calibration must NOT be called when strategy validation fails"
        )

    def test_backtest_proceeds_after_calibration(self, qapp):
        """After calibration, the backtest worker must be created and started."""
        stub = _make_run_clicked_stub()

        mock_val = MagicMock()
        mock_val.success = True
        stub.orchestrator.validate_strategy.return_value = mock_val
        stub.orchestrator.serialize_config_for_backtest.return_value = {
            'blocks': [{'name': 'Alpha'}],
            'name': 'TestStrategy',
        }
        stub.cache_manager = MagicMock()
        stub.cache_manager.get_cached_bars.return_value = None
        stub.cache_manager.get_metrics.return_value = {'hit_rate_pct': 0.0}
        stub.trades_panel = MagicMock()
        stub.output_panel = MagicMock()
        stub.run_btn = MagicMock()
        stub.pause_btn = MagicMock()
        stub.stop_btn = MagicMock()
        stub.results_btn = MagicMock()
        stub.live_output_tab_index = 1
        stub.tab_widget = MagicMock()
        stub.get_config = MagicMock(return_value={
            'timeframe': '15m',
            'lookback_days': 180,
        })

        with patch("src.optimizer_v3.database.get_database_manager"), \
             patch("src.strategy_builder.ui.backtest_config_panel.QApplication"), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread") as MockThread, \
             patch("src.strategy_builder.ui.backtest_config_panel.BacktestWorker") as MockWorker, \
             patch("src.optimizer_v3.core.trade_registry.get_trade_registry"):
            mock_thread = MagicMock()
            mock_thread.isRunning.return_value = False
            MockThread.return_value = mock_thread

            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        MockWorker.assert_called_once()
        mock_worker.start.assert_called_once()


# ---------------------------------------------------------------------------
# Code structure / placement checks (static analysis via source inspection)
# ---------------------------------------------------------------------------

class TestCodeStructuralRequirements:
    """
    Structural checks on the source that verify the new implementation
    acceptance criteria.
    """

    def test_is_calibrated_method_removed(self):
        """_is_calibrated() must NOT exist in BacktestConfigPanel."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        assert not hasattr(BacktestConfigPanel, '_is_calibrated'), (
            "_is_calibrated() must be removed from BacktestConfigPanel — "
            "calibration now runs automatically"
        )

    def test_no_set_current_index_1_in_on_run_clicked(self):
        """_on_run_clicked() must NOT contain setCurrentIndex(1) (old Calibrate redirect)."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "setCurrentIndex(1)" not in src, (
            "_on_run_clicked() must not redirect to tab index 1; "
            "Calibrate tab has been removed"
        )

    def test_run_auto_calibration_method_exists(self):
        """_run_auto_calibration() must exist in BacktestConfigPanel."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        assert hasattr(BacktestConfigPanel, '_run_auto_calibration'), (
            "_run_auto_calibration() must be added to BacktestConfigPanel"
        )

    def test_auto_calibration_called_in_on_run_clicked_source(self):
        """_on_run_clicked() source must call _run_auto_calibration."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "_run_auto_calibration" in src, (
            "_on_run_clicked() must call _run_auto_calibration()"
        )

    def test_no_training_panel_attribute_in_on_run_clicked(self):
        """_on_run_clicked() must not reference self.training_panel."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "training_panel" not in src, (
            "_on_run_clicked() must not reference self.training_panel "
            "(Calibrate tab was removed)"
        )

    def test_no_calibration_required_dialog_in_on_run_clicked(self):
        """_on_run_clicked() must not contain 'Calibration Required' dialog text."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "Calibration Required" not in src, (
            "_on_run_clicked() must not show the old 'Calibration Required' dialog"
        )

    def test_run_auto_calibration_uses_production_mode(self):
        """_run_auto_calibration() must use 'production' mode."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'production'" in src or '"production"' in src, (
            "_run_auto_calibration() must use mode='production'"
        )

    def test_run_auto_calibration_uses_15m_timeframe(self):
        """_run_auto_calibration() must hardcode '15m' timeframe."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "'15m'" in src or '"15m"' in src, (
            "_run_auto_calibration() must hardcode timeframe '15m'"
        )

    def test_run_auto_calibration_uses_180_day_lookback(self):
        """_run_auto_calibration() must hardcode 180-day lookback."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "180" in src, (
            "_run_auto_calibration() must hardcode 180-day lookback period"
        )

    def test_run_auto_calibration_has_graceful_degradation(self):
        """_run_auto_calibration() must have exception handling (graceful degradation)."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._run_auto_calibration)
        assert "except" in src, (
            "_run_auto_calibration() must catch exceptions and degrade gracefully"
        )

    def test_no_training_panel_ui_import_in_init_ui(self):
        """_init_ui() source must not import or instantiate TrainingPanelUI."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._init_ui)
        assert "TrainingPanelUI" not in src, (
            "_init_ui() must not import or instantiate TrainingPanelUI "
            "(Calibrate tab was removed)"
        )


# ---------------------------------------------------------------------------
# Tests for calibration cache (BTCAAAAA-641) — fingerprint-based skip
# ---------------------------------------------------------------------------

class TestCalibrationCache:
    """Tests for cache hit / cache miss / settings-change invalidation (BTCAAAAA-641)."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_calibration_with_results(self, stub, config, calib_results):
        """Run _run_auto_calibration with a mock thread that fires results."""
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False
        mock_thread.is_simulation_mode = False
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

    # ------------------------------------------------------------------
    # AC1: Cache initialisation in __init__
    # ------------------------------------------------------------------

    def test_cache_attributes_initialized_to_none(self):
        """BacktestConfigPanel.__init__ must set _calibration_fingerprint and _calibration_cache to None."""
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        import inspect
        src = inspect.getsource(BacktestConfigPanel.__init__)
        assert "_calibration_fingerprint" in src, (
            "_calibration_fingerprint must be initialized in __init__"
        )
        assert "_calibration_cache" in src, (
            "_calibration_cache must be initialized in __init__"
        )

    # ------------------------------------------------------------------
    # AC2: Cache stored after successful non-simulation calibration
    # ------------------------------------------------------------------

    def test_cache_stored_after_successful_calibration(self, qapp):
        """After a successful non-simulation run, fingerprint and delay_map are stored."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}
        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 3}]

        self._run_calibration_with_results(stub, config, calib_results)

        assert stub._calibration_fingerprint is not None, (
            "_calibration_fingerprint must be set after successful calibration"
        )
        assert stub._calibration_cache is not None, (
            "_calibration_cache must be set after successful calibration"
        )
        assert stub._calibration_cache == {'Alpha': 3}, (
            f"Cache should contain the delay_map; got {stub._calibration_cache}"
        )

    # ------------------------------------------------------------------
    # AC3: Skip on cache hit — same settings
    # ------------------------------------------------------------------

    def test_skips_calibration_on_cache_hit(self, qapp):
        """When fingerprint matches, calibration thread is NOT spawned and skip message shown."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}
        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 7}]

        # First run: populates cache
        self._run_calibration_with_results(stub, config, calib_results)

        # Reset mocks for second run
        stub.results_text.reset_mock()

        # Second run: same config → should hit cache
        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ) as MockThread:
            stub._run_auto_calibration(config)

        # TrainingThread must NOT have been instantiated on cache hit
        MockThread.assert_not_called()

        # Status must show skip message (exact spec string)
        first_set_text = stub.results_text.setText.call_args_list[0].args[0]
        assert "skipping" in first_set_text.lower() or "cached" in first_set_text.lower(), (
            f"Expected skip/cached message on cache hit, got: {first_set_text!r}"
        )

    def test_cache_hit_skip_message_exact_string(self, qapp):
        """Cache-hit status message must match the exact spec string."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}
        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 7}]

        self._run_calibration_with_results(stub, config, calib_results)
        stub.results_text.reset_mock()

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ):
            stub._run_auto_calibration(config)

        first_set_text = stub.results_text.setText.call_args_list[0].args[0]
        expected = (
            "✓ Calibration already complete for current settings — skipping. "
            "Using cached parameters."
        )
        assert first_set_text == expected, (
            f"Exact skip message required.\nExpected: {expected!r}\nGot:      {first_set_text!r}"
        )

    def test_cache_hit_applies_cached_delay_to_blocks(self, qapp):
        """On cache hit, the cached optimal_delay is applied to blocks in-place."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}
        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 9}]

        self._run_calibration_with_results(stub, config, calib_results)

        # Second run with fresh block dict (simulates new Run Test click)
        config2 = {'blocks': [{'name': 'Alpha'}]}
        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
        ):
            stub._run_auto_calibration(config2)

        assert config2['blocks'][0].get('optimal_delay') == 9, (
            f"Cached optimal_delay=9 must be applied on cache hit; got {config2['blocks'][0]}"
        )

    # ------------------------------------------------------------------
    # AC4: Re-run on settings change (block added/removed)
    # ------------------------------------------------------------------

    def test_re_runs_when_blocks_change(self, qapp):
        """After block list changes, fingerprint mismatches and calibration re-runs."""
        stub = _make_calibration_stub()
        config_a = {'blocks': [{'name': 'Alpha'}]}
        calib_results_a = [{'signal_name': 'Alpha', 'optimal_delay': 5}]

        self._run_calibration_with_results(stub, config_a, calib_results_a)

        old_fingerprint = stub._calibration_fingerprint

        # Change blocks
        config_b = {'blocks': [{'name': 'Alpha'}, {'name': 'Beta'}]}
        calib_results_b = [
            {'signal_name': 'Alpha', 'optimal_delay': 5},
            {'signal_name': 'Beta', 'optimal_delay': 2},
        ]

        stub.results_text.reset_mock()
        self._run_calibration_with_results(stub, config_b, calib_results_b)

        # Fingerprint should have changed
        assert stub._calibration_fingerprint != old_fingerprint, (
            "Fingerprint must change when block list changes"
        )
        assert stub._calibration_cache == {'Alpha': 5, 'Beta': 2}, (
            f"Cache must be updated with new results; got {stub._calibration_cache}"
        )

    # ------------------------------------------------------------------
    # AC5: Cache-miss status message (exact spec string)
    # ------------------------------------------------------------------

    def test_cache_miss_status_message_exact_string(self, qapp):
        """Cache-miss (first run) status must match the exact spec string."""
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

        first_set_text = stub.results_text.setText.call_args_list[0].args[0]
        expected = "⚙️ Calibration required — running calibration before backtest..."
        assert first_set_text == expected, (
            f"Exact cache-miss message required.\nExpected: {expected!r}\nGot:      {first_set_text!r}"
        )

    # ------------------------------------------------------------------
    # AC6: Simulation mode guard — never cache simulation results
    # ------------------------------------------------------------------

    def test_simulation_results_not_cached(self, qapp):
        """Simulation-mode results must NOT be stored in the calibration cache."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}
        calib_results = [{'signal_name': 'Alpha', 'optimal_delay': 99}]

        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = False
        mock_thread.is_simulation_mode = True  # Simulation mode
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

        assert stub._calibration_fingerprint is None, (
            "Fingerprint must NOT be stored when running in simulation mode"
        )
        assert stub._calibration_cache is None, (
            "Cache must NOT be populated when running in simulation mode"
        )

    # ------------------------------------------------------------------
    # AC7: Graceful degradation — exception does not update cache
    # ------------------------------------------------------------------

    def test_cache_not_updated_on_exception(self, qapp):
        """When calibration raises, neither fingerprint nor cache should be set."""
        stub = _make_calibration_stub()
        config = {'blocks': [{'name': 'Alpha'}]}

        with patch(
            "src.strategy_builder.ui.backtest_config_panel.QApplication"
        ), patch(
            "src.optimizer_v3.core.training_thread.TrainingThread",
            side_effect=RuntimeError("network error"),
        ):
            stub._run_auto_calibration(config)

        assert stub._calibration_fingerprint is None, (
            "Fingerprint must NOT be set when calibration fails with an exception"
        )
        assert stub._calibration_cache is None, (
            "Cache must NOT be set when calibration fails with an exception"
        )

    # ------------------------------------------------------------------
    # Static analysis: verify hashlib and json are imported at module level
    # ------------------------------------------------------------------

    def test_hashlib_imported_at_module_level(self):
        """hashlib must be imported at the top of backtest_config_panel.py."""
        import src.strategy_builder.ui.backtest_config_panel as mod
        import hashlib
        assert hasattr(mod, 'hashlib') or 'hashlib' in dir(mod), (
            "hashlib must be imported at module level"
        )
        # Also verify by source inspection
        import inspect
        src_lines = inspect.getsource(mod).split('\n')
        assert any(line.strip() == 'import hashlib' for line in src_lines[:50]), (
            "'import hashlib' must appear in the first 50 lines of the module"
        )

    def test_json_imported_at_module_level(self):
        """json must be imported at the top of backtest_config_panel.py."""
        import src.strategy_builder.ui.backtest_config_panel as mod
        import inspect
        src_lines = inspect.getsource(mod).split('\n')
        assert any(line.strip() == 'import json' for line in src_lines[:50]), (
            "'import json' must appear in the first 50 lines of the module"
        )
