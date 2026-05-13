"""
Regression tests for BTCAAAAA-1018.

Bug: _run_auto_calibration sets a calibration-skip message via setText on
results_text; if _on_run_clicked then calls setText for data-cache status it
overwrites the calibration message entirely.

Fix: src/strategy_builder/ui/backtest_config_panel.py — use append() instead
of setText() for the cache-status messages in _on_run_clicked so both messages
are preserved.

This file re-exports the existing real-widget integration test from
tests/strategy_builder/ui/test_backtest_config_panel_calibration_gate.py so
the Impact Gate runner can discover it by bug ID.
"""

from __future__ import annotations

import sys
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1018"),
    pytest.mark.regression,
]

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


from tests.strategy_builder.ui.test_backtest_config_panel_calibration_gate import (  # noqa: E402, F401
    TestResultsTextNotOverwrittenOnCacheHit,
)
