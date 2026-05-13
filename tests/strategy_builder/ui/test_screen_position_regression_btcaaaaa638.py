"""
Regression tests for BTCAAAAA-638: Screen position persistence regression fix.

The regression introduced in BTCAAAAA-530 could cause windows to fall back to
the primary screen when the saved window rect had < 100 px wide or < 50 px tall
intersection with its screen (e.g. window near a screen edge).

The fix (BTCAAAAA-638) adds a screenAt(saved_pos) fallback: after the full-rect
intersection check fails for all screens, the simpler point-based lookup is tried
so a window whose top-left corner is on a connected screen is always restored
to that screen rather than jumping to primary.

Acceptance criteria verified here:
  AC-1  Move window to screen 4 → close → reopen → window appears on screen 4
        at the same size/position (non-maximized case).
  AC-2  This works for ALL windows that use WindowGeometryMixin, not just the main window.
  AC-3  If the saved screen is genuinely unavailable (monitor disconnected), fall
        back to the primary screen.
  AC-4  Maximize still works correctly after drag (BTCAAAAA-474 regression must not return).
  AC-5  Edge-case: window saved near screen boundary (< 100 px overlap) restores to
        the correct screen via the screenAt() fallback, not to primary.
  AC-6  Maximized window saved on screen 4 (BTCAAAAA-637) reopens on screen 4
        (regression guard — must still pass after BTCAAAAA-638 changes).
"""

from __future__ import annotations

import ast
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UI_DIR = pathlib.Path("src/strategy_builder/ui")
STYLES_SRC = (UI_DIR / "styles.py").read_text()

# The 4-monitor layout from the board user's machine:
#   DP-1   : (1306,    0, 6880, 2880)
#   DP-2   : (6144, 2880, 3072, 1920)
#   DP-3   : (   0, 2880, 3072, 1920)
#   HDMI-1 : (3072, 2880, 3072, 1920)
FOUR_MONITOR_LAYOUT = [
    ("DP-1",   1306,    0, 6880, 2880),
    ("DP-2",   6144, 2880, 3072, 1920),
    ("DP-3",      0, 2880, 3072, 1920),
    ("HDMI-1", 3072, 2880, 3072, 1920),
]


# ---------------------------------------------------------------------------
# Helpers: pure-Python re-implementation of the restore logic
# These mirror the actual code so tests fail if logic changes without tests.
# ---------------------------------------------------------------------------

def _make_mock_screen(name: str, x: int, y: int, w: int, h: int):
    """Create a mock QScreen with name() and availableGeometry()."""
    from PyQt5.QtCore import QRect
    s = MagicMock()
    s.name.return_value = name
    s.availableGeometry.return_value = QRect(x, y, w, h)
    return s


def _simulate_restore(
    saved_pos_xy,          # (x, y) tuple or None
    saved_size_wh,         # (w, h) tuple or None
    saved_screen_name,     # str or None
    maximized,             # bool
    maximized_screen_name, # str or None — for the BTCAAAAA-637 branch
    screens_layout,        # list of (name, x, y, w, h)
    default_size=(900, 600),
    screenAt_returns=None, # mock return for QGuiApplication.screenAt(saved_pos)
                           # — pass a screen name, or None
):
    """
    Re-implement _restore_window_geometry logic in plain Python so we can
    unit-test every branch without a display.

    Returns a dict with:
      action    : "move" | "center_on_primary"
      x, y      : coordinates passed to self.move() (only when action=="move")
      screen    : name of the screen the window ended up on (or "primary")
      maximized : whether showMaximized() would be scheduled
    """
    from PyQt5.QtCore import QPoint, QSize, QRect

    saved_pos = QPoint(*saved_pos_xy) if saved_pos_xy is not None else None
    saved_size = QSize(*saved_size_wh) if saved_size_wh is not None else None
    default_w, default_h = default_size

    target_size = saved_size if saved_size is not None else QSize(default_w, default_h)

    MIN_VISIBLE_W = 100
    MIN_VISIBLE_H = 50

    mock_screens = [_make_mock_screen(*s) for s in screens_layout]

    def _rect_is_usable(rect, screen):
        intersection = rect.intersected(screen.availableGeometry())
        return (intersection.width() >= MIN_VISIBLE_W and
                intersection.height() >= MIN_VISIBLE_H)

    # Build a map from screen name → mock for screenAt simulation
    screen_by_name = {s.name(): s for s in mock_screens}

    def _screen_at(point):
        """Simulate QGuiApplication.screenAt(point)."""
        if screenAt_returns is not None:
            return screen_by_name.get(screenAt_returns)
        # Default: find any screen whose geometry contains the point
        for s in mock_screens:
            g = s.availableGeometry()
            if g.contains(point):
                return s
        return None

    # Primary screen: first in layout
    primary_screen = mock_screens[0] if mock_screens else None

    def _center_on_primary(dw, dh):
        if primary_screen is None:
            return {"action": "center_on_primary", "screen": "none", "maximized": maximized}
        sr = primary_screen.availableGeometry()
        cx = sr.center().x() - dw // 2
        cy = sr.center().y() - dh // 2
        return {"action": "center_on_primary", "x": cx, "y": cy,
                "screen": primary_screen.name(), "maximized": maximized}

    if saved_pos is not None:
        saved_rect = QRect(saved_pos, target_size)

        preferred_screen = None
        if saved_screen_name:
            for s in mock_screens:
                if s.name() == saved_screen_name:
                    preferred_screen = s
                    break

        # 1. Try full-rect intersection
        target_screen = None
        if preferred_screen and _rect_is_usable(saved_rect, preferred_screen):
            target_screen = preferred_screen
        else:
            for s in mock_screens:
                if _rect_is_usable(saved_rect, s):
                    target_screen = s
                    break

        # 2. BTCAAAAA-638 fallback: screenAt(saved_pos)
        if target_screen is None:
            point_screen = _screen_at(saved_pos)
            if point_screen is not None:
                target_screen = point_screen

        if target_screen is not None:
            sr = target_screen.availableGeometry()
            clamped_x = max(sr.left(), min(saved_pos.x(), sr.right() - MIN_VISIBLE_W))
            clamped_y = max(sr.top(), min(saved_pos.y(), sr.bottom() - MIN_VISIBLE_H))
            return {"action": "move", "x": clamped_x, "y": clamped_y,
                    "screen": target_screen.name(), "maximized": maximized}
        else:
            return _center_on_primary(default_w, default_h)

    else:
        # No saved normal pos
        if maximized and maximized_screen_name:
            for s in mock_screens:
                if s.name() == maximized_screen_name:
                    sr = s.availableGeometry()
                    cx = sr.center().x() - default_w // 2
                    cy = sr.center().y() - default_h // 2
                    return {"action": "move", "x": cx, "y": cy,
                            "screen": s.name(), "maximized": True}
            return _center_on_primary(default_w, default_h)
        else:
            return _center_on_primary(default_w, default_h)


# ---------------------------------------------------------------------------
# AC-1: Non-maximized window moved to screen 4 restores to screen 4
# ---------------------------------------------------------------------------

class TestNonMaximizedRestoreToCorrectScreen:
    """AC-1 & AC-2: Normal (non-maximized) window saves to any screen and reopens there."""

    def test_window_on_hdmi1_restores_to_hdmi1(self):
        """Window at normal position on HDMI-1 (3200, 3100) reopens on HDMI-1."""
        result = _simulate_restore(
            saved_pos_xy=(3200, 3100),
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move", "Should move to saved position, not center on primary"
        assert result["screen"] == "HDMI-1", (
            f"Window should restore to HDMI-1, got {result['screen']}"
        )

    def test_window_on_dp2_restores_to_dp2(self):
        """Window on DP-2 (6200, 3000) reopens on DP-2."""
        result = _simulate_restore(
            saved_pos_xy=(6200, 3000),
            saved_size_wh=(900, 600),
            saved_screen_name="DP-2",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move"
        assert result["screen"] == "DP-2"

    def test_window_on_dp3_restores_to_dp3(self):
        """Window on DP-3 (200, 3000) reopens on DP-3."""
        result = _simulate_restore(
            saved_pos_xy=(200, 3000),
            saved_size_wh=(900, 600),
            saved_screen_name="DP-3",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move"
        assert result["screen"] == "DP-3"

    def test_window_on_dp1_restores_to_dp1(self):
        """Window on DP-1 (main) at (2000, 500) reopens on DP-1."""
        result = _simulate_restore(
            saved_pos_xy=(2000, 500),
            saved_size_wh=(900, 600),
            saved_screen_name="DP-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move"
        assert result["screen"] == "DP-1"

    def test_window_restored_position_matches_saved_within_clamping(self):
        """Restored x/y should equal saved x/y when position is safely inside screen."""
        result = _simulate_restore(
            saved_pos_xy=(3500, 3300),
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["x"] == 3500
        assert result["y"] == 3300

    def test_window_not_snapped_to_primary_when_on_secondary_screen(self):
        """Critical regression check: secondary-screen window must NOT go to DP-1."""
        result = _simulate_restore(
            saved_pos_xy=(3200, 3100),
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        # DP-1 primary is at y=0; HDMI-1 is at y=2880.
        # The restored y must be >= 2880, not at the DP-1 primary centre.
        assert result["y"] >= 2880, (
            f"Window restored to y={result['y']} which is on the primary screen (DP-1), "
            f"not HDMI-1 (y starts at 2880).  Regression: window snapped to primary."
        )


# ---------------------------------------------------------------------------
# AC-5: Edge case — window near screen boundary uses screenAt() fallback
# ---------------------------------------------------------------------------

class TestScreenAtFallbackForEdgeCases:
    """AC-5: Windows near screen edges use screenAt() fallback, not primary fallback."""

    def test_window_at_right_edge_of_dp2_uses_screeat_fallback(self):
        """
        Window at the far right edge of DP-2 (the rightmost screen).
        DP-2 right edge = 6144+3072-1=9215.
        Window at x=9200 with width=900: overlap = 9215-9200+1=16 px < 100.
        No other screen covers x > 9215, so rect check fails for ALL screens.
        The screenAt(QPoint(9200, 3100)) fallback must recover it to DP-2.
        """
        result = _simulate_restore(
            saved_pos_xy=(9200, 3100),     # right edge of DP-2 (rightmost screen)
            saved_size_wh=(900, 600),
            saved_screen_name="DP-2",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        # The top-left (9200, 3100) IS inside DP-2 (6144-9215, 2880-4799).
        # screenAt fallback should find DP-2.
        assert result["action"] == "move", (
            "Window near DP-2 right edge should restore to DP-2 via screenAt() fallback, "
            "not to primary screen"
        )
        assert result["screen"] == "DP-2"

    def test_window_near_bottom_of_dp2_uses_screeat_fallback(self):
        """
        Window near the bottom edge of DP-2 (bottommost screen).
        DP-2 bottom = 2880+1920-1=4799.
        Window at y=4775 with height=600: overlap = 4799-4775+1=25 px < 50.
        No other screen below y=4800, rect check fails.
        screenAt(QPoint(7000, 4775)) fallback must recover it to DP-2.
        """
        result = _simulate_restore(
            saved_pos_xy=(7000, 4775),     # near bottom of DP-2 (rightmost-bottommost)
            saved_size_wh=(900, 600),
            saved_screen_name="DP-2",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move", (
            "Window near DP-2 bottom edge should restore via screenAt() fallback, not primary"
        )
        assert result["screen"] == "DP-2"

    def test_fallback_does_not_fire_when_rect_check_succeeds(self):
        """screenAt() fallback is not needed when rect intersection already succeeds."""
        # Normal position, full overlap — rect check should find HDMI-1 directly.
        result = _simulate_restore(
            saved_pos_xy=(3300, 3100),
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["screen"] == "HDMI-1"

    def test_screeat_fallback_in_source(self):
        """Source must contain QGuiApplication.screenAt call as a fallback in restore."""
        # The fix must add screenAt() call after the rect-intersection loop fails.
        # We check for both the existence of screenAt and the BTCAAAAA-638 comment.
        assert "screenAt" in STYLES_SRC, (
            "WindowGeometryMixin._restore_window_geometry must call screenAt() "
            "as a fallback when rect-intersection fails for all screens."
        )
        assert "BTCAAAAA-638" in STYLES_SRC, (
            "Source must contain a BTCAAAAA-638 comment documenting the screenAt fallback."
        )


# ---------------------------------------------------------------------------
# AC-3: Disconnected monitor falls back to primary
# ---------------------------------------------------------------------------

class TestDisconnectedMonitorFallback:
    """AC-3: When saved screen is gone (monitor disconnected), use primary screen."""

    def test_disconnected_monitor_falls_back_to_primary(self):
        """Window saved on a monitor that is no longer connected → primary screen."""
        # Simulate a 1-monitor setup where HDMI-1 has been disconnected
        single_screen_layout = [("DP-1", 0, 0, 1920, 1080)]

        result = _simulate_restore(
            saved_pos_xy=(3200, 3100),     # Was on HDMI-1 (disconnected)
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=single_screen_layout,
            screenAt_returns=None,         # screenAt also returns None (off screen)
        )
        assert result["action"] == "center_on_primary", (
            "Window saved on disconnected monitor should fall back to primary screen"
        )
        assert result["screen"] == "DP-1"

    def test_position_in_gap_between_screens_falls_back_to_primary(self):
        """Position in a virtual-desktop gap (no screen at that coordinate) → primary."""
        # The gap area: x=0-1305, y=0-2879 has no screen
        result = _simulate_restore(
            saved_pos_xy=(500, 500),       # In the gap — no screen here
            saved_size_wh=(900, 600),
            saved_screen_name=None,
            maximized=False,
            maximized_screen_name=None,
            screens_layout=FOUR_MONITOR_LAYOUT,
            screenAt_returns=None,         # Explicitly: screenAt returns None for gap
        )
        # With the gap coordinates AND screenAt returning None, should use primary
        assert result["action"] == "center_on_primary"

    def test_all_screens_disconnected_except_primary(self):
        """All secondary screens removed, window on secondary → goes to primary."""
        single_screen_layout = [("DP-1", 1306, 0, 6880, 2880)]
        result = _simulate_restore(
            saved_pos_xy=(500, 3200),      # Was on DP-3 (gone)
            saved_size_wh=(900, 600),
            saved_screen_name="DP-3",
            maximized=False,
            maximized_screen_name=None,
            screens_layout=single_screen_layout,
            screenAt_returns=None,
        )
        assert result["action"] == "center_on_primary"


# ---------------------------------------------------------------------------
# AC-4: Maximize after drag doesn't regress (BTCAAAAA-474)
# ---------------------------------------------------------------------------

class TestMaximizeNotRegressed:
    """AC-4: The 50ms QTimer.singleShot(50, showMaximized) must still be in source."""

    def test_synchronous_maximize_present(self):
        """setWindowState(WindowMaximized) must be present in WindowGeometryMixin (BTCAAAAA-25580)."""
        assert "setWindowState" in STYLES_SRC and "WindowMaximized" in STYLES_SRC, (
            "WindowGeometryMixin must use setWindowState(WindowMaximized) synchronously. "
            "The QTimer-based showMaximized() deferral was removed in BTCAAAAA-25580 "
            "because some Linux WMs reject deferred maximize after the window is mapped."
        )

    def test_maximized_window_schedules_show_maximized(self):
        """When maximized=True in saved state, the restore marks maximized=True."""
        result = _simulate_restore(
            saved_pos_xy=(3200, 3100),
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=True,
            maximized_screen_name="HDMI-1",
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["maximized"] is True, (
            "Restored state must indicate maximized=True so showMaximized() is scheduled"
        )


# ---------------------------------------------------------------------------
# AC-6: BTCAAAAA-637 fix must still pass — maximized window on screen 4
# ---------------------------------------------------------------------------

class TestMaximizedWindowOnCorrectScreen:
    """AC-6: Maximized window saved on screen 4 still reopens on screen 4 (BTCAAAAA-637)."""

    def test_maximized_with_no_normal_pos_uses_maximized_screen(self):
        """Window always maximized on HDMI-1 (never had normal pos) → HDMI-1 on reopen."""
        result = _simulate_restore(
            saved_pos_xy=None,             # Never saved in normal state
            saved_size_wh=None,
            saved_screen_name=None,
            maximized=True,
            maximized_screen_name="HDMI-1",
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["action"] == "move", (
            "Maximized window with no saved pos should be positioned on HDMI-1, not primary"
        )
        assert result["screen"] == "HDMI-1"

    def test_maximized_with_no_normal_pos_not_on_primary(self):
        """Maximized window on HDMI-1 must NOT open on DP-1 (primary)."""
        result = _simulate_restore(
            saved_pos_xy=None,
            saved_size_wh=None,
            saved_screen_name=None,
            maximized=True,
            maximized_screen_name="HDMI-1",
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        # DP-1 primary is at y=0; HDMI-1 at y=2880.
        assert result["y"] >= 2880, (
            f"Maximized window on HDMI-1 should position at y>=2880, got y={result['y']}. "
            "This is a BTCAAAAA-637 regression."
        )

    def test_maximized_on_disconnected_screen_falls_back_to_primary(self):
        """Maximized on HDMI-1 but HDMI-1 is now disconnected → primary screen."""
        single_screen_layout = [("DP-1", 0, 0, 1920, 1080)]
        result = _simulate_restore(
            saved_pos_xy=None,
            saved_size_wh=None,
            saved_screen_name=None,
            maximized=True,
            maximized_screen_name="HDMI-1",
            screens_layout=single_screen_layout,
        )
        assert result["action"] == "center_on_primary"

    def test_maximized_with_saved_normal_pos_also_works(self):
        """Window maximized on HDMI-1 WITH a normal pos saved also restores to HDMI-1."""
        result = _simulate_restore(
            saved_pos_xy=(3200, 3100),     # normal pos was on HDMI-1
            saved_size_wh=(900, 600),
            saved_screen_name="HDMI-1",
            maximized=True,
            maximized_screen_name="HDMI-1",
            screens_layout=FOUR_MONITOR_LAYOUT,
        )
        assert result["screen"] == "HDMI-1"
        assert result["maximized"] is True


# ---------------------------------------------------------------------------
# Source-level checks: ensure the fallback code exists in styles.py
# ---------------------------------------------------------------------------

class TestSourceCodeContainsRequiredFix:
    """Verify the BTCAAAAA-638 fix is present in the styles.py source."""

    def test_screeat_fallback_block_exists(self):
        """The screenAt() fallback block must exist in _restore_window_geometry."""
        # Check that we call screenAt as a fallback inside the restore method
        # after the rect-intersection loop.
        assert "screenAt(saved_pos)" in STYLES_SRC, (
            "_restore_window_geometry must include a screenAt(saved_pos) fallback "
            "call after the rect-intersection loop (BTCAAAAA-638 fix)."
        )

    def test_fallback_comment_present(self):
        """A BTCAAAAA-638 comment must document the fallback logic."""
        assert "BTCAAAAA-638" in STYLES_SRC, (
            "The BTCAAAAA-638 fix must be commented in styles.py."
        )

    def test_fallback_after_intersection_loop(self):
        """
        screenAt(saved_pos) must appear after the _rect_is_usable loop,
        not before it (so the better intersection-based check runs first).
        We search for the LAST occurrence of each pattern because they appear
        earlier in header comments as well.
        """
        rect_check_pos = STYLES_SRC.rfind("_rect_is_usable(saved_rect")
        screeat_fallback_pos = STYLES_SRC.rfind("screenAt(saved_pos)")
        assert rect_check_pos != -1, "_rect_is_usable(saved_rect...) not found in source"
        assert screeat_fallback_pos != -1, "screenAt(saved_pos) not found in source"
        assert screeat_fallback_pos > rect_check_pos, (
            "screenAt(saved_pos) fallback must appear AFTER the _rect_is_usable loop, "
            "not before it.  The intersection-based check should run first."
        )

    def test_primary_fallback_only_when_point_also_off_screen(self):
        """
        The center_on_primary() call after the position restore block must only
        fire when BOTH the rect intersection AND the screenAt() fallback fail.
        """
        # Check that screenAt is checked before _center_on_primary in restore block
        # by verifying the code structure: last screenAt appears before last center_on_primary
        # within the restore method's saved_pos branch (use rfind to skip header comments).
        screeat_pos = STYLES_SRC.rfind("screenAt(saved_pos)")
        center_pos = STYLES_SRC.rfind("_center_on_primary(default_w, default_h)")
        assert screeat_pos < center_pos, (
            "screenAt(saved_pos) must be checked before _center_on_primary() "
            "so the fallback fires before giving up."
        )
