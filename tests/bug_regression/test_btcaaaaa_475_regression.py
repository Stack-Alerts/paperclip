"""Regression tests for BTCAAAAA-475 / BTCAAAAA-25580: Qt window maximize fix.

Issues: BTCAAAAA-475, BTCAAAAA-25580
Fix: Synchronous setWindowState(WindowMaximized) in WindowGeometryMixin.showEvent()

What changed:
    QTimer.singleShot(50, self.showMaximized)
    ->
    setWindowState(windowState() | Qt.WindowMaximized)  # in showEvent, before super

Why:
    A deferred showMaximized() via QTimer fires after the window is already
    mapped by the window manager. Some Linux WMs reject maximize requests
    that arrive after the initial map cycle, causing the window to remain
    unmaximized on multi-monitor setups.

Pass criteria tested here:
    AC-1  WindowGeometryMixin.showEvent() calls setWindowState(WindowMaximized)
          synchronously when saved state has maximized=True.
    AC-2  When maximized=True in QSettings, showEvent applies the state before
          delegating to super().showEvent().
    AC-3  When maximized=False in QSettings, showEvent does NOT maximize.
    AC-4  Maximized window positioning on target screen works correctly.
    AC-5  All windows in scope use WindowGeometryMixin (no window bypasses
          the mixin and therefore misses the fix).
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-475"),
    pytest.mark.regression,
]

# Re-export from the canonical test file
from tests.strategy_builder.ui.test_maximize_without_prior_tab_click_btcaaaaa475 import (  # noqa: F401
    TestAllWindowsUseMixin,
    TestShowEventMaximizeBehaviour,
    TestSynchronousMaximizeAST,
)
