"""
QA tests for BTCAAAAA-637: Maximized windows restore to correct screen.

Regression: All windows always opened on primary screen, ignoring which
monitor they were maximized on. Root cause: _save_window_geometry() only
saved 'maximized=True', not *which* screen the window was maximized on.
On restore with no saved normal pos/size, the mixin centered on primary
then called showMaximized() — so a window maximized on screen 4 always
re-opened maximized on screen 1.

Fix (commit 76e4edf):
- _save_window_geometry() now saves 'maximized_screen_name' when the
  window is closed while maximized, using frameGeometry().center() +
  screenAt() to identify the current screen.
- _restore_window_geometry() reads 'maximized_screen_name'; when
  saved_pos is None but maximized=True, it moves the window to the
  centre of the saved screen BEFORE QTimer.singleShot(50, showMaximized)
  fires, so the OS WM maximizes to the correct monitor.
- If the saved screen is disconnected, falls back to primary screen.
- All 259 prior window geometry tests continue to pass (no regression).

Acceptance criteria tested here:
  AC-1  _save_window_geometry() writes 'maximized_screen_name' when window
        is maximized; does NOT write it when window is not maximized.
  AC-2  _restore_window_geometry() reads 'maximized_screen_name' from
        QSettings on restore.
  AC-3  When maximized=True and maximized_screen_name matches an available
        screen, the window is moved to that screen before showMaximized().
  AC-4  When maximized=True and maximized_screen_name does NOT match any
        available screen (monitor disconnected), fallback to primary screen.
  AC-5  When maximized=False, maximized_screen_name is NOT used (normal
        pos/size path is unchanged).
  AC-6  When maximized=True and maximized_screen_name is absent (old
        QSettings with no key — first open after update), fallback to
        primary screen.
  AC-7  AST regression guard: 'maximized_screen_name' is present in
        styles.py (guards against accidental removal).
  AC-8  50 ms QTimer.singleShot deferral is preserved (no regression from
        BTCAAAAA-474/475).
  AC-9  'maximized_screen_name' key is removed from QSettings when
        screenAt() returns None (defensive cleanup).
  AC-10 When screenAt() returns a screen, settings.remove() is NOT called
        for 'maximized_screen_name' (key must be saved, not removed).
"""

from __future__ import annotations

import ast
import pathlib
import sys
from unittest.mock import MagicMock, call, patch, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STYLES_PATH = pathlib.Path("src/strategy_builder/ui/styles.py")
UI_DIR = pathlib.Path("src/strategy_builder/ui")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _styles_src() -> str:
    return STYLES_PATH.read_text()


def _styles_ast() -> ast.Module:
    return ast.parse(_styles_src())


def _find_method_node(tree: ast.Module, method_name: str) -> ast.FunctionDef | None:
    """Return the first FunctionDef with the given name in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                return node
    return None


def _make_test_window_class(styles_mod, key="testWin", default_size=(800, 600)):
    """
    Build a minimal WindowGeometryMixin subclass for unit testing.
    Qt methods are stubbed so no display is required.
    """
    class TestWindow(styles_mod.WindowGeometryMixin):
        GEOMETRY_SETTINGS_KEY = key
        GEOMETRY_DEFAULT_SIZE = default_size
        _move_calls = None

        def __init__(self):
            self._geometry_restored = False
            self._move_calls = []

        def resize(self, size):
            pass

        def move(self, x, y):
            self._move_calls.append((x, y))

        def showMaximized(self):
            pass

        def width(self):
            return default_size[0]

        def height(self):
            return default_size[1]

        def size(self):
            return MagicMock()

    return TestWindow


# ---------------------------------------------------------------------------
# AC-7  AST regression guard — key present in source
# ---------------------------------------------------------------------------

class TestASTRegressionGuard:
    """Verify that 'maximized_screen_name' is present in styles.py."""

    def test_maximized_screen_name_in_source(self):
        """AC-7: styles.py must reference 'maximized_screen_name'."""
        src = _styles_src()
        assert "maximized_screen_name" in src, (
            "styles.py does not contain 'maximized_screen_name'. "
            "The BTCAAAAA-637 fix must be present in WindowGeometryMixin."
        )

    def test_save_contains_maximized_screen_name_key_string(self):
        """AC-1 (AST): _save_window_geometry must reference 'maximized_screen_name' as a string key."""
        src = _styles_src()
        # The key appears in f-strings like f"{key}/maximized_screen_name"
        assert "maximized_screen_name" in src, (
            "_save_window_geometry must reference 'maximized_screen_name' "
            "as a QSettings key."
        )

    def test_restore_reads_maximized_screen_name(self):
        """AC-2 (AST): _restore_window_geometry must read 'maximized_screen_name' via settings.value()."""
        tree = _styles_ast()
        restore_method = _find_method_node(tree, "_restore_window_geometry")
        assert restore_method is not None, "_restore_window_geometry not found in styles.py"

        # Find any string constant with 'maximized_screen_name' in the restore method
        found = any(
            isinstance(node, ast.Constant) and isinstance(node.value, str)
            and "maximized_screen_name" in node.value
            for node in ast.walk(restore_method)
        )
        assert found, (
            "_restore_window_geometry must read a QSettings key containing "
            "'maximized_screen_name'."
        )

    def test_save_writes_maximized_screen_name_key(self):
        """AC-1 (AST): _save_window_geometry must write a key containing 'maximized_screen_name'."""
        tree = _styles_ast()
        save_method = _find_method_node(tree, "_save_window_geometry")
        assert save_method is not None, "_save_window_geometry not found in styles.py"

        found = any(
            isinstance(node, ast.Constant) and isinstance(node.value, str)
            and "maximized_screen_name" in node.value
            for node in ast.walk(save_method)
        )
        assert found, (
            "_save_window_geometry must write a QSettings key containing "
            "'maximized_screen_name'. The BTCAAAAA-637 fix is missing."
        )

    def test_remove_called_for_maximized_screen_name(self):
        """AC-9 (AST): settings.remove() must be called in save when screen is None."""
        src = _styles_src()
        # Both 'remove' and 'maximized_screen_name' must be present in styles.py
        assert "settings.remove" in src or ".remove(" in src, (
            "settings.remove() is not called anywhere in styles.py. "
            "It must be called when screenAt() returns None for maximized_screen_name."
        )

    def test_50ms_timer_preserved(self):
        """AC-8 (AST): QTimer.singleShot(50, ...) deferral must still be present."""
        tree = _styles_ast()
        restore_method = _find_method_node(tree, "_restore_window_geometry")
        assert restore_method is not None, "_restore_window_geometry not found in styles.py"

        found_50ms = False
        for node in ast.walk(restore_method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "singleShot"
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value == 50:
                        found_50ms = True
                        break

        assert found_50ms, (
            "QTimer.singleShot(50, ...) not found in _restore_window_geometry. "
            "The 50 ms deferral from BTCAAAAA-474/475 must be preserved."
        )

    def test_no_singleshot_with_0ms(self):
        """AC-8 regression: QTimer.singleShot(0, ...) must NOT appear in restore."""
        tree = _styles_ast()
        restore_method = _find_method_node(tree, "_restore_window_geometry")
        assert restore_method is not None

        found_0ms = False
        for node in ast.walk(restore_method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "singleShot"
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value == 0:
                        found_0ms = True
                        break

        assert not found_0ms, (
            "QTimer.singleShot(0, ...) found in _restore_window_geometry — "
            "this is a regression from BTCAAAAA-474/475. Must be 50 ms."
        )


# ---------------------------------------------------------------------------
# AC-1  _save_window_geometry writes maximized_screen_name when maximized
# ---------------------------------------------------------------------------

class TestSaveMaximizedScreenName:
    """AC-1: _save_window_geometry saves maximized_screen_name iff maximized."""

    def test_saves_maximized_screen_name_when_maximized(self):
        """AC-1: When isMaximized() is True, settings.setValue(…/maximized_screen_name, …) is called."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = MagicMock()
        mock_screen = MagicMock()
        mock_screen.name.return_value = "DP-2"

        center_pt = MagicMock()
        fg = MagicMock()
        fg.center.return_value = center_pt

        mock_gui = MagicMock()
        mock_gui.screenAt.return_value = mock_screen

        class MaximizedWindow(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def isMaximized(self):
                return True

            def frameGeometry(self):
                return fg

        win = MaximizedWindow()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
        ):
            win._save_window_geometry()

        # Should have saved maximized_screen_name
        calls_with_key = [
            c for c in mock_settings.setValue.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert calls_with_key, (
            "settings.setValue('…/maximized_screen_name', …) was NOT called "
            "when window is maximized. BTCAAAAA-637 fix missing."
        )

        # The screen name should be "DP-2"
        found_correct_name = any(
            "DP-2" in str(c) for c in mock_settings.setValue.call_args_list
        )
        assert found_correct_name, (
            "settings.setValue for maximized_screen_name was called but "
            "did not contain the correct screen name 'DP-2'."
        )

    def test_does_not_write_maximized_screen_name_when_not_maximized(self):
        """AC-1: When isMaximized() is False, maximized_screen_name key must NOT be written."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = MagicMock()
        mock_screen = MagicMock()
        mock_screen.name.return_value = "DP-2"

        frame_topleft = MagicMock()
        fg = MagicMock()
        fg.topLeft.return_value = frame_topleft

        mock_gui = MagicMock()
        mock_gui.screenAt.return_value = mock_screen

        class NotMaximizedWindow(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def isMaximized(self):
                return False

            def frameGeometry(self):
                return fg

            def size(self):
                return MagicMock()

        win = NotMaximizedWindow()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
        ):
            win._save_window_geometry()

        # maximized_screen_name must NOT be in setValue calls when not maximized
        bad_calls = [
            c for c in mock_settings.setValue.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert not bad_calls, (
            "settings.setValue was called with 'maximized_screen_name' when "
            "isMaximized() is False — this key should only be written when maximized."
        )

    def test_removes_maximized_screen_name_when_screen_is_none(self):
        """AC-9: When screenAt() returns None while maximized, settings.remove() is called."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = MagicMock()
        center_pt = MagicMock()
        fg = MagicMock()
        fg.center.return_value = center_pt

        mock_gui = MagicMock()
        mock_gui.screenAt.return_value = None  # No screen found

        class MaximizedWindowNoScreen(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def isMaximized(self):
                return True

            def frameGeometry(self):
                return fg

        win = MaximizedWindowNoScreen()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
        ):
            win._save_window_geometry()

        # Should call settings.remove for maximized_screen_name
        remove_calls = [
            c for c in mock_settings.remove.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert remove_calls, (
            "settings.remove('…/maximized_screen_name') was NOT called when "
            "screenAt() returns None. The key must be cleaned up."
        )

        # Must NOT setValue for maximized_screen_name
        bad_set_calls = [
            c for c in mock_settings.setValue.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert not bad_set_calls, (
            "settings.setValue was called for 'maximized_screen_name' even "
            "though screenAt() returned None — should call remove() instead."
        )


# ---------------------------------------------------------------------------
# AC-10  When screenAt() returns a valid screen, remove() is NOT called
# ---------------------------------------------------------------------------

class TestScreenAtValidDoesNotRemove:
    """AC-10: When screenAt() returns a valid screen, settings.remove() is not called for maximized_screen_name."""

    def test_no_remove_when_screen_found(self):
        """settings.remove() must NOT be called for maximized_screen_name when screenAt() succeeds."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = MagicMock()
        mock_screen = MagicMock()
        mock_screen.name.return_value = "HDMI-3"

        center_pt = MagicMock()
        fg = MagicMock()
        fg.center.return_value = center_pt

        mock_gui = MagicMock()
        mock_gui.screenAt.return_value = mock_screen  # screen found

        class MaximizedWindowOnScreen(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def isMaximized(self):
                return True

            def frameGeometry(self):
                return fg

        win = MaximizedWindowOnScreen()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
        ):
            win._save_window_geometry()

        # Must NOT remove the key (screen was found, key should be written)
        remove_calls = [
            c for c in mock_settings.remove.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert not remove_calls, (
            "settings.remove('…/maximized_screen_name') was called even though "
            "screenAt() returned a valid screen. Should only remove when screen is None."
        )

        # Must setValue with the correct name
        set_calls = [
            c for c in mock_settings.setValue.call_args_list
            if "maximized_screen_name" in str(c)
        ]
        assert set_calls, (
            "settings.setValue('…/maximized_screen_name', …) was not called "
            "even though screenAt() returned a valid screen."
        )


# ---------------------------------------------------------------------------
# AC-3 / AC-4 / AC-5 / AC-6  Restore: maximized screen positioning
# ---------------------------------------------------------------------------

class TestRestoreMaximizedToCorrectScreen:
    """AC-3/4/5/6: _restore_window_geometry moves window to correct screen before maximize."""

    def _make_mock_settings(self, maximized: bool, pos=None, size=None,
                             screen_name=None, maximized_screen_name=None):
        """Build a mock QSettings stub for _restore_window_geometry tests."""
        data = {
            "testWin/maximized": maximized,
            "testWin/pos": pos,
            "testWin/size": size,
            "testWin/screen_name": screen_name,
            "testWin/maximized_screen_name": maximized_screen_name,
        }

        mock_settings = MagicMock()

        def settings_value(key, default=None, type=None):  # noqa: A002
            val = data.get(key, default)
            if type is bool and val is not None:
                return bool(val)
            return val

        mock_settings.value = settings_value
        return mock_settings

    def test_restore_moves_to_maximized_screen_when_available(self):
        """AC-3: When maximized=True and screen is available, window is moved to that screen."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = self._make_mock_settings(
            maximized=True,
            maximized_screen_name="HDMI-2",
        )

        # Screen named "HDMI-2" at x=2560
        target_screen = MagicMock()
        target_screen.name.return_value = "HDMI-2"
        screen_geo = MagicMock()
        screen_geo.center.return_value = MagicMock()
        screen_geo.center.return_value.x.return_value = 2560
        screen_geo.center.return_value.y.return_value = 540
        target_screen.availableGeometry.return_value = screen_geo

        mock_gui = MagicMock()
        mock_gui.screens.return_value = [target_screen]

        mock_qtimer = MagicMock()

        class TestWindow(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)
            _move_calls = None

            def __init__(self):
                self._geometry_restored = False
                self._move_calls = []

            def resize(self, size):
                pass

            def move(self, x, y):
                self._move_calls.append((x, y))

            def showMaximized(self):
                pass

        win = TestWindow()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
            patch.object(styles_mod, "_QSize", MagicMock(return_value=MagicMock())),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                win._restore_window_geometry()

        # Window must have been moved
        assert win._move_calls, (
            "win.move() was never called during restore with maximized=True "
            "and a matching maximized_screen_name. "
            "Window should be positioned on the saved screen before showMaximized()."
        )

        # The move should be centred on the HDMI-2 screen
        # center.x=2560, default_w=800 → 2560 - 800//2 = 2160
        moved_x, moved_y = win._move_calls[0]
        assert moved_x == 2560 - 400, (
            f"Window was moved to x={moved_x} but expected 2160 "
            f"(center of HDMI-2 at x=2560 minus half default_w=400). "
            "BTCAAAAA-637 fix: must move to saved screen centre before maximize."
        )

        # Timer must have been called (showMaximized deferred)
        assert mock_qtimer.singleShot.called, (
            "QTimer.singleShot was NOT called. showMaximized must be deferred."
        )

    def test_restore_fallback_to_primary_when_screen_disconnected(self):
        """AC-4: When maximized_screen_name does not match any screen, fall back to primary."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = self._make_mock_settings(
            maximized=True,
            maximized_screen_name="DP-4",  # monitor disconnected
        )

        # Only primary screen available (DP-4 is gone)
        primary_screen = MagicMock()
        primary_screen.name.return_value = "eDP-1"
        primary_geo = MagicMock()
        primary_geo.center.return_value = MagicMock()
        primary_geo.center.return_value.x.return_value = 960
        primary_geo.center.return_value.y.return_value = 540
        primary_screen.availableGeometry.return_value = primary_geo

        mock_gui = MagicMock()
        mock_gui.screens.return_value = [primary_screen]
        mock_gui.primaryScreen.return_value = primary_screen

        mock_qtimer = MagicMock()
        center_called = []

        class TestWindowFallback(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def __init__(self):
                self._geometry_restored = False

            def resize(self, size):
                pass

            def move(self, x, y):
                pass

            def showMaximized(self):
                pass

            def _center_on_primary(self, w=None, h=None):
                center_called.append((w, h))

        win = TestWindowFallback()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
            patch.object(styles_mod, "_QSize", MagicMock(return_value=MagicMock())),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                win._restore_window_geometry()

        # _center_on_primary must have been called as fallback
        assert center_called, (
            "_center_on_primary() was NOT called when maximized_screen_name "
            "'DP-4' is unavailable (monitor disconnected). "
            "BTCAAAAA-637 fix: must fall back to primary screen."
        )

    def test_restore_fallback_to_primary_when_no_screen_hint(self):
        """AC-6: When maximized=True but no maximized_screen_name, fall back to primary."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = self._make_mock_settings(
            maximized=True,
            maximized_screen_name=None,  # absent — old QSettings without key
        )

        mock_gui = MagicMock()
        mock_gui.screens.return_value = []

        mock_qtimer = MagicMock()
        center_called = []

        class TestWindowNoHint(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def __init__(self):
                self._geometry_restored = False

            def resize(self, size):
                pass

            def move(self, x, y):
                pass

            def showMaximized(self):
                pass

            def _center_on_primary(self, w=None, h=None):
                center_called.append((w, h))

        win = TestWindowNoHint()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
            patch.object(styles_mod, "_QSize", MagicMock(return_value=MagicMock())),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                win._restore_window_geometry()

        assert center_called, (
            "_center_on_primary() was NOT called when maximized=True but "
            "maximized_screen_name is absent (first run after update). "
            "Should fall back to primary screen."
        )

    def test_restore_not_maximized_does_not_call_timer(self):
        """AC-5: When maximized=False, QTimer.singleShot must NOT be called."""
        import src.strategy_builder.ui.styles as styles_mod

        saved_pos = MagicMock()
        saved_pos.x.return_value = 200
        saved_pos.y.return_value = 100

        mock_settings = self._make_mock_settings(
            maximized=False,
            pos=saved_pos,
            size=MagicMock(),
            screen_name="eDP-1",
            maximized_screen_name="HDMI-2",  # present but must not be used
        )

        preferred_screen = MagicMock()
        preferred_screen.name.return_value = "eDP-1"
        geo = MagicMock()
        geo.left.return_value = 0
        geo.top.return_value = 0
        geo.right.return_value = 1920
        geo.bottom.return_value = 1080
        # Make the rect intersection appear usable
        intersection = MagicMock()
        intersection.width.return_value = 800
        intersection.height.return_value = 600
        geo.intersected = MagicMock(return_value=intersection)
        preferred_screen.availableGeometry.return_value = geo

        mock_gui = MagicMock()
        mock_gui.screens.return_value = [preferred_screen]

        # QRect: return a mock whose .intersected() returns our usable intersection
        mock_rect_instance = MagicMock()
        mock_rect_instance.intersected.return_value = intersection
        mock_qrect = MagicMock(return_value=mock_rect_instance)

        mock_qtimer = MagicMock()

        class TestWindowNotMaximized(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWin"
            GEOMETRY_DEFAULT_SIZE = (800, 600)

            def __init__(self):
                self._geometry_restored = False

            def resize(self, size):
                pass

            def move(self, x, y):
                pass

            def showMaximized(self):
                pass

        win = TestWindowNotMaximized()

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui),
            patch.object(styles_mod, "_QSize", MagicMock(return_value=MagicMock())),
            patch.object(styles_mod, "_QRect", mock_qrect),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                win._restore_window_geometry()

        # QTimer.singleShot must NOT be called when not maximized
        assert not mock_qtimer.singleShot.called, (
            "QTimer.singleShot was called even though maximized=False. "
            "showMaximized should only be deferred when the window was maximized."
        )
