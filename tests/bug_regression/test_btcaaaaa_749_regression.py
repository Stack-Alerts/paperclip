"""
Regression tests for BTCAAAAA-749: Quick Preview feature in StrategyBuilderMainWindow.

Issue: BTCAAAAA-749
Components:
    src/strategy_builder/ui/strategy_builder_main_window.py
    tests/ui_qt/test_quick_preview.py
    tests/ui_qt/test_quick_preview_mainwindow.py

What changed:
    Added Quick Preview button to StrategyBuilderMainWindow toolbar and
    QuickPreviewResultsDialog popup that shows 30-day backtest metrics
    (Win Rate, Total Signals, Total Trades, Avg Return).

Tests are defined in tests/ui_qt/ and re-exported here for the Impact Gate
runner to discover at tests/bug_regression/test_btcaaaaa_749_regression.py.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-749"),
    pytest.mark.regression,
]

# Re-export QuickPreviewResultsDialog tests
from tests.ui_qt.test_quick_preview import (  # noqa: E402, F401
    test_dialog_window_title,
    test_dialog_minimum_width,
    test_dialog_shows_win_rate_formatted,
    test_dialog_shows_total_signals,
    test_dialog_shows_total_trades,
    test_dialog_shows_avg_return_positive_signed,
    test_dialog_shows_avg_return_negative_signed,
    test_dialog_zero_trades_shows_hint,
    test_dialog_zero_trades_win_rate_zero,
    test_dialog_has_close_button,
    test_dialog_close_button_accepts,
    test_dialog_is_modal,
    test_dialog_win_rate_high_uses_success_styling,
    test_dialog_win_rate_low_uses_error_styling,
)

# Re-export Quick Preview button + main window tests
from tests.ui_qt.test_quick_preview_mainwindow import (  # noqa: E402, F401
    test_preview_button_exists_in_toolbar,
    test_preview_button_enabled_at_startup,
    test_no_blocks_guard_shows_warning_not_crash,
    test_double_click_guard_shows_information,
    test_preview_finished_re_enables_button,
    test_preview_finished_failure_re_enables_button,
    test_preview_finished_zero_trades_shows_dialog,
)
