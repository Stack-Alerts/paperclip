"""
Regression tests for BTCAAAAA-659: Fix: Unable to maximize window.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-659
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: StrategyBuilderMainWindow did not call setWindowFlags(), so some
Linux window managers omitted the maximize button or blocked maximization.

Fix: Added explicit setWindowFlags() in _init_ui() with:
    Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
    | Qt.WindowCloseButtonHint

Tests are defined in tests/strategy_builder/ui/test_window_flags_btcaaaaa659.py
and re-exported here for the Impact Gate runner to discover.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-659"),
    pytest.mark.regression,
]

from tests.strategy_builder.ui.test_window_flags_btcaaaaa659 import (  # noqa: E402, F401
    TestStrategyBuilderMainWindowFlags,
    TestStrategyBuilderNoBlockingConstraints,
    TestStrategyBuilderGeometryMixinUnaffected,
    TestStrategyBuilderMainWindowFlagsMatchPattern,
    TestRegressionGuard659,
)
