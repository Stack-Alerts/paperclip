"""Regression tests for BTCAAAAA-475 / BTCAAAAA-25580 / BTCAAAAA-26202: Qt window maximize fix.

Issues: BTCAAAAA-475, BTCAAAAA-25580, BTCAAAAA-26202
Fix: Defer setWindowState(WindowMaximized) in WindowGeometryMixin.showEvent()
     to AFTER super().showEvent() so the WM receives the maximize request
     on a mapped window (BTCAAAAA-26202).

Pass criteria tested here:
    AC-1  WindowGeometryMixin.showEvent() calls setWindowState(WindowMaximized)
          after super().showEvent() when saved state has maximized=True.
    AC-2  When maximized=True in QSettings, showEvent maximizes after
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
