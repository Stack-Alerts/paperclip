"""Regression tests for BTCAAAAA-475: Qt window maximize timer delay fix.

Issue: BTCAAAAA-475
Fix commit: a5ad2b0

What changed:
    QTimer.singleShot(0, self.showMaximized)
    ->
    QTimer.singleShot(50, self.showMaximized)

Why:
    A delay of 0 ms fires at the next event-loop iteration but Qt has not
    completed its initial layout pass at that point.  The symptom is that
    maximize appears to do nothing on first open without any prior user
    interaction (e.g. clicking a tab).  The tab click triggers a layout
    recalculation that incidentally corrects the window state.

    50 ms gives Qt and the OS window manager enough time to finish the
    initial layout/paint cycle so showMaximized() reliably fills the screen
    even on the very first maximize attempt with no preceding user interaction.

Board-reported reproduction sequence (MUST pass):
    1. Open window fresh — no prior state from this session
    2. Do NOT click any tab, button, or widget
    3. Immediately click maximize -> MUST fill the screen   <- this failed before

Pass criteria tested here:
    AC-1  The timer delay in _restore_window_geometry is >= 50 ms (not 0 ms).
    AC-2  When maximized=True in QSettings, QTimer.singleShot is called with
          delay=50 (not 0, not any other value).
    AC-3  When maximized=False in QSettings, QTimer.singleShot is NOT called
          at all.
    AC-4  The timer is invoked with self.showMaximized as the callback (not
          some other callable).
    AC-5  AST check: the literal 0 is not passed to singleShot in styles.py
          (regression guard against reverting the fix).
    AC-6  All windows in scope use WindowGeometryMixin (no window bypasses
          the mixin and therefore misses the fix).
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-475"),
    pytest.mark.regression,
]

# Re-export the test classes from the canonical test file so the Impact Gate
# runner (which maps BTCAAAAA-475 -> tests/bug_regression/test_btcaaaaa_475_regression.py)
# can discover and run them.
from tests.strategy_builder.ui.test_maximize_without_prior_tab_click_btcaaaaa475 import (  # noqa: F401
    TestAllWindowsUseMixin,
    TestRestoreWindowGeometryTimerBehaviour,
    TestTimerDelayAST,
)
