"""
Regression tests for BTCAAAAA-640: preserve calibration cache across backtest
window close/reopen.

Bug: BacktestConfigPanel was recreated each time the backtest dialog was closed
and reopened (_on_run_backtest created a new BacktestConfigDialog when the
existing one was not visible), resetting _calibration_fingerprint to None on
every cycle and making calibration run on every Run Test.

Fix: Reuse the existing BacktestConfigDialog if it exists (show() on a closed
but not destroyed dialog), so the in-memory calibration cache survives close/
reopen within a single application session.

Issue: BTCAAAAA-640
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Expanded to meet Impact Gate 10-test minimum bar (BTCAAAAA-25160).
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-640"),
    pytest.mark.regression,
]

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestOnRunBacktestReuseWindow:
    """_on_run_backtest must reuse existing backtest_window to preserve cache."""

    def _make_main_window(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        win = MagicMock(spec=StrategyBuilderMainWindow)
        win.backtest_window = None
        win.orchestrator = MagicMock()
        win.orchestrator._pending_backtest_config = None
        win._update_status = MagicMock()
        return win

    def test_reuses_existing_window_when_hidden(self, qapp):
        win = self._make_main_window()
        existing_dialog = MagicMock()
        win.backtest_window = existing_dialog

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            bound()

        MockDialog.assert_not_called()
        existing_dialog.show.assert_called_once()
        existing_dialog.raise_.assert_called_once()
        existing_dialog.activateWindow.assert_called_once()

    def test_creates_new_window_when_none(self, qapp):
        win = self._make_main_window()
        win.backtest_window = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        MockDialog.assert_called_once_with(win.orchestrator, win)
        mock_instance.show.assert_called_once()

    def test_destroyed_signal_clears_reference(self, qapp):
        win = self._make_main_window()
        win.backtest_window = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        assert mock_instance.destroyed.connect.called
        signal_args = mock_instance.destroyed.connect.call_args[0][0]
        signal_args()
        assert win.backtest_window is None

    def test_activate_existing_window_over_new_create(self, qapp):
        win = self._make_main_window()
        existing = MagicMock()
        win.backtest_window = existing

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            bound()

        MockDialog.assert_not_called()
        existing.activateWindow.assert_called_once()

    def test_show_on_existing_window_sets_visible(self, qapp):
        win = self._make_main_window()
        existing = MagicMock()
        win.backtest_window = existing

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            bound()

        MockDialog.assert_not_called()
        existing.show.assert_called_once()

    def test_status_update_on_open(self, qapp):
        """_on_run_backtest must update status when dialog opens."""
        win = self._make_main_window()
        win.backtest_window = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        win._update_status.assert_any_call("Backtest configuration opened")

    def test_error_shows_critical_message(self, qapp):
        """When BacktestConfigDialog raises, QMessageBox.critical must be called."""
        win = self._make_main_window()
        win.backtest_window = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            MockDialog.side_effect = RuntimeError("creation failed")
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.QMessageBox.critical"
            ) as mock_critical:
                bound()

            mock_critical.assert_called_once()

    def test_error_updates_status_failed(self, qapp):
        """When BacktestConfigDialog raises, status must show failure."""
        win = self._make_main_window()
        win.backtest_window = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            MockDialog.side_effect = RuntimeError("creation failed")
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.QMessageBox.critical"
            ):
                bound()

        win._update_status.assert_any_call("Backtest configuration failed to open")

    def test_pending_config_applied_when_lookback_days(self, qapp):
        """pending_backtest_config with lookback_days must be applied."""
        win = self._make_main_window()
        win.backtest_window = None
        win.orchestrator._pending_backtest_config = {"lookback_days": 30}

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        mock_instance.backtest_panel.apply_config_from_dict.assert_called_once_with(
            {"lookback_days": 30}, source="database"
        )

    def test_pending_config_skipped_without_lookback_days(self, qapp):
        """pending_backtest_config without lookback_days must be skipped."""
        win = self._make_main_window()
        win.backtest_window = None
        win.orchestrator._pending_backtest_config = {"mode": 2}

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        mock_instance.backtest_panel.apply_config_from_dict.assert_not_called()

    def test_pending_config_none_skips_silently(self, qapp):
        """pending_backtest_config of None must not raise or apply."""
        win = self._make_main_window()
        win.backtest_window = None
        win.orchestrator._pending_backtest_config = None

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            bound()

        mock_instance.backtest_panel.apply_config_from_dict.assert_not_called()
        mock_instance.show.assert_called_once()

    def test_config_retention_error_does_not_block_show(self, qapp):
        """Exception in config retention must not prevent dialog from showing."""
        win = self._make_main_window()
        win.backtest_window = None
        win.orchestrator._pending_backtest_config = {"lookback_days": 30}

        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        bound = StrategyBuilderMainWindow._on_run_backtest.__get__(win, StrategyBuilderMainWindow)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.BacktestConfigDialog"
        ) as MockDialog:
            mock_instance = MagicMock()
            mock_instance.backtest_panel.apply_config_from_dict.side_effect = (
                ValueError("corrupt config")
            )
            MockDialog.return_value = mock_instance
            bound()

        mock_instance.show.assert_called_once()
        win._update_status.assert_any_call("Backtest configuration opened")
