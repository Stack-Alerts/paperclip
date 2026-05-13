"""
Regression tests for BTCAAAAA-257: About dialog layout fix (free-floating QDialog).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-257
Fixed in commit: 9ffc7acb (same fix as BTCAAAAA-255)
Component: src/strategy_builder/ui/strategy_builder_main_window.py
           archived/utils_strategy_builder_legacy/qt_gui/main_window.py

Root cause: QMessageBox.about() locked the About dialog to the main window
position and produced a narrow, tall layout.

Fix: Replace QMessageBox.about() with a free-floating QDialog() that is
wider (>=600px), content-fitted (<=500px tall), and styled properly.

Since BTCAAAAA-257 and BTCAAAAA-255 share the same fix, the regression tests
from test_btcaaaaa_255_regression.py are re-exported here.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-257"),
    pytest.mark.regression,
]

from tests.bug_regression.test_btcaaaaa_255_regression import (  # noqa: E402, F401
    TestAboutDialogStaticChecksSBMW,
    TestAboutDialogStaticChecksQTGUI,
)
