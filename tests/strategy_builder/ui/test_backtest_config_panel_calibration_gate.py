"""
Unit tests for BacktestConfigPanel calibration gate — BTCAAAAA-327/329.

Covers:
- _is_calibrated() logic: export_btn enabled → calibrated; disabled → not calibrated
- _is_calibrated() defensive: exception from training_panel → returns True (safe default)
- _on_run_clicked() when NOT calibrated: QMessageBox.Warning shown, tab switches to index 1,
  backtest does NOT start (early return before validate_strategy)
- _on_run_clicked() when calibrated: no dialog shown, proceeds past validation
- No changes to calibration logic or backtest logic when gate passes
"""

from __future__ import annotations

import sys
import types
import pytest
from unittest.mock import MagicMock, patch, call

from PyQt5.QtWidgets import QApplication, QMessageBox


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
# Helper — create a minimal stand-in object that has the two target methods
# bound from BacktestConfigPanel, but without ever calling __init__.
# ---------------------------------------------------------------------------

def _make_stub(training_panel_export_btn_enabled: bool):
    """
    Create a minimal stub that exposes _is_calibrated() and _on_run_clicked()
    as unbound methods called on `self`, without invoking QWidget.__init__.

    We import the unbound methods directly from the class and call them with
    our stub as `self`.  This sidesteps all Qt and DB heavy-lifting while
    exercising the exact same source code paths.
    """
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    # Pull the methods we need as plain functions
    _is_calibrated_fn = BacktestConfigPanel._is_calibrated
    _on_run_clicked_fn = BacktestConfigPanel._on_run_clicked

    # Build a minimal mock training panel
    mock_training_panel = MagicMock()
    mock_training_panel.export_btn.isEnabled.return_value = training_panel_export_btn_enabled

    # Build stub with all instance attributes that the two methods reference
    stub = MagicMock()
    stub.training_panel = mock_training_panel

    mock_tab_widget = MagicMock()
    stub.tab_widget = mock_tab_widget

    mock_orch = MagicMock()
    stub.orchestrator = mock_orch

    stub.results_text = MagicMock()

    # Bind the real methods to our stub so `self` is our stub
    stub._is_calibrated = types.MethodType(_is_calibrated_fn, stub)
    stub._on_run_clicked = types.MethodType(_on_run_clicked_fn, stub)

    return stub, mock_orch, mock_tab_widget


# ---------------------------------------------------------------------------
# Tests for _is_calibrated()
# ---------------------------------------------------------------------------

class TestIsCalibrated:
    """Unit tests for BacktestConfigPanel._is_calibrated()."""

    def test_returns_true_when_export_btn_enabled(self, qapp):
        """If training_panel.export_btn.isEnabled() is True, calibration is done."""
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=True)
        assert stub._is_calibrated() is True

    def test_returns_false_when_export_btn_disabled(self, qapp):
        """If training_panel.export_btn.isEnabled() is False, calibration has not been run."""
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=False)
        assert stub._is_calibrated() is False

    def test_defensive_returns_true_when_exception_raised(self, qapp):
        """If training_panel raises on access, _is_calibrated() must return True (safe default)."""
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=False)
        broken_training_panel = MagicMock()
        broken_training_panel.export_btn.isEnabled.side_effect = AttributeError("panel not ready")
        stub.training_panel = broken_training_panel
        # Must NOT raise; must return True
        result = stub._is_calibrated()
        assert result is True

    def test_defensive_returns_true_when_training_panel_missing(self, qapp):
        """If training_panel attribute is entirely absent, returns True."""
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=False)

        # Remove training_panel so accessing it raises AttributeError
        # (on a MagicMock we can't del, so replace with a property-raising object)
        class _Raiser:
            @property
            def training_panel(self):
                raise AttributeError("no training_panel")

        # Patch _is_calibrated on the stub with the original source bound to a raiser stub
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        import types as _types
        raiser = _Raiser()
        fn = BacktestConfigPanel._is_calibrated
        bound = _types.MethodType(fn, raiser)
        result = bound()
        assert result is True


# ---------------------------------------------------------------------------
# Tests for _on_run_clicked() calibration gate behaviour
# ---------------------------------------------------------------------------

class TestOnRunClickedCalibrationGate:
    """Tests for the calibration gate inside _on_run_clicked()."""

    def _run_gate(self, stub, *, patch_db=True):
        """
        Helper: call stub._on_run_clicked() with QMessageBox and DB mocked.
        Returns (MockMsgBox_class, mock_msg_instance).
        """
        ctx_msgbox = patch(
            "src.strategy_builder.ui.backtest_config_panel.QMessageBox"
        )
        MockMsgBox = ctx_msgbox.__enter__()
        mock_msg_instance = MagicMock()
        MockMsgBox.return_value = mock_msg_instance
        MockMsgBox.Warning = QMessageBox.Warning
        MockMsgBox.Ok = QMessageBox.Ok

        ctx_db = patch("src.optimizer_v3.database.get_database_manager") if patch_db else None
        if ctx_db:
            ctx_db.__enter__()

        try:
            stub._on_run_clicked()
        except Exception:
            pass
        finally:
            ctx_msgbox.__exit__(None, None, None)
            if ctx_db:
                ctx_db.__exit__(None, None, None)

        return MockMsgBox, mock_msg_instance

    def test_warning_dialog_title_when_not_calibrated(self, qapp):
        """
        When calibration has NOT been run, the dialog title must be
        'Calibration Required'.
        The gate uses a local import so we patch PyQt5.QtWidgets.QMessageBox.
        """
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=False)

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        mock_msg.setWindowTitle.assert_called_once_with("Calibration Required")

    def test_warning_dialog_icon_is_warning(self, qapp):
        """The dialog icon must be QMessageBox.Warning."""
        stub, _, _ = _make_stub(training_panel_export_btn_enabled=False)

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        mock_msg.setIcon.assert_called_once_with(QMessageBox.Warning)

    def test_tab_switches_to_calibrate_index_1_when_not_calibrated(self, qapp):
        """After the dialog is dismissed, the tab must switch to index 1 (Calibrate)."""
        stub, _, mock_tab_widget = _make_stub(training_panel_export_btn_enabled=False)

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        mock_tab_widget.setCurrentIndex.assert_called_once_with(1)

    def test_backtest_does_not_start_when_not_calibrated(self, qapp):
        """
        When calibration has not been run, _on_run_clicked() must return early
        WITHOUT calling orchestrator.validate_strategy().
        """
        stub, mock_orch, _ = _make_stub(training_panel_export_btn_enabled=False)

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        mock_orch.validate_strategy.assert_not_called()

    def test_backtest_proceeds_when_calibrated(self, qapp):
        """
        When calibration HAS been run, _on_run_clicked() must NOT show a
        calibration dialog and MUST call orchestrator.validate_strategy().
        """
        stub, mock_orch, mock_tab_widget = _make_stub(training_panel_export_btn_enabled=True)

        # Validation fails → stops cleanly after gate
        mock_val = MagicMock()
        mock_val.success = False
        mock_val.message = "test stop"
        mock_orch.validate_strategy.return_value = mock_val

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        # Gate passed → validate_strategy must have been called
        mock_orch.validate_strategy.assert_called_once()

        # No calibration dialog
        for c in mock_msg.setWindowTitle.call_args_list:
            assert c.args[0] != "Calibration Required", (
                "Calibration dialog must NOT appear when calibration is complete"
            )

        # Tab must NOT have been force-switched to Calibrate (index 1)
        for c in mock_tab_widget.setCurrentIndex.call_args_list:
            assert c.args[0] != 1, (
                "Tab must not switch to Calibrate when calibration already done"
            )

    def test_gate_does_not_interfere_with_no_strategy_validation(self, qapp):
        """
        If calibration IS done but strategy validation fails, the validation
        error path is triggered (not the calibration gate).
        """
        stub, mock_orch, _ = _make_stub(training_panel_export_btn_enabled=True)

        mock_val = MagicMock()
        mock_val.success = False
        mock_val.message = "No strategy loaded"
        mock_orch.validate_strategy.return_value = mock_val

        with patch(
            "PyQt5.QtWidgets.QMessageBox"
        ) as MockMsgBox, patch(
            "src.optimizer_v3.database.get_database_manager"
        ):
            mock_msg = MagicMock()
            MockMsgBox.return_value = mock_msg
            MockMsgBox.Warning = QMessageBox.Warning
            MockMsgBox.Ok = QMessageBox.Ok

            try:
                stub._on_run_clicked()
            except Exception:
                pass

        # Calibration gate must have passed → reached validate_strategy
        mock_orch.validate_strategy.assert_called_once()

        # No calibration dialog
        for c in mock_msg.setWindowTitle.call_args_list:
            assert c.args[0] != "Calibration Required"


# ---------------------------------------------------------------------------
# Code structure / placement checks (static analysis via source inspection)
# ---------------------------------------------------------------------------

class TestCodeStructuralRequirements:
    """
    Structural checks on the source that verify acceptance-criteria placement
    constraints.
    """

    def test_is_calibrated_uses_export_btn_is_enabled(self):
        """_is_calibrated() must use export_btn.isEnabled() as proxy."""
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._is_calibrated)
        assert "export_btn.isEnabled()" in src, (
            "_is_calibrated() must use export_btn.isEnabled() as calibration proxy"
        )

    def test_is_calibrated_has_defensive_except(self):
        """_is_calibrated() must have a try/except that returns True on failure."""
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._is_calibrated)
        assert "except" in src, "_is_calibrated() must have exception handling"
        assert "return True" in src, "_is_calibrated() must return True in except block"

    def test_calibration_gate_at_top_of_on_run_clicked(self):
        """
        The calibration gate must appear BEFORE the '# Validate strategy' block
        inside _on_run_clicked().
        """
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)

        gate_pos = src.find("_is_calibrated")
        validate_pos = src.find("# Validate strategy")

        assert gate_pos != -1, "_is_calibrated() call not found in _on_run_clicked"
        assert validate_pos != -1, "'# Validate strategy' comment not found in _on_run_clicked"
        assert gate_pos < validate_pos, (
            "Calibration gate (_is_calibrated call) must appear BEFORE '# Validate strategy' block"
        )

    def test_calibration_gate_switches_to_index_1(self):
        """The gate must switch to tab index 1 (Calibrate tab)."""
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "setCurrentIndex(1)" in src, (
            "_on_run_clicked() must call setCurrentIndex(1) in calibration gate"
        )

    def test_calibration_gate_uses_warning_message_box(self):
        """The gate must use QMessageBox.Warning icon."""
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert "QMessageBox.Warning" in src, (
            "Calibration gate must use QMessageBox.Warning icon"
        )

    def test_window_title_is_calibration_required(self):
        """The dialog title must be 'Calibration Required'."""
        import inspect
        from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        src = inspect.getsource(BacktestConfigPanel._on_run_clicked)
        assert '"Calibration Required"' in src, (
            "Dialog title must be 'Calibration Required'"
        )
