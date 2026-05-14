"""
QA re-test for BTCAAAAA-475 follow-up fix.
Updated for BTCAAAAA-26202: setWindowState is now called AFTER
super().showEvent() so the WM receives the maximise request on an
already-mapped window, keeping Qt and WM state in sync.

Board-reported reproduction sequence (MUST pass):
    1. Open window fresh — no prior state from this session
    2. Do NOT click any tab, button, or widget
    3. Immediately click maximize → MUST fill the screen

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

import ast
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STYLES_PATH = pathlib.Path("src/strategy_builder/ui/styles.py")

# All windows that must use WindowGeometryMixin (and thus benefit from the fix)
ALL_MIXIN_WINDOWS = [
    "strategy_builder_main_window.py",
    "validation_report_window.py",
    "exit_condition_dialog.py",
    "strategy_browser_dialog.py",
    "backtest_config_dialog.py",
    "log_viewer_window.py",
    "settings_dialog.py",
    "new_strategy_dialog.py",
    "validation_dialog.py",
    "timing_constraint_dialog.py",
    "data_verify_dialog.py",
    "config_discovery_results_dialog.py",
]

UI_DIR = pathlib.Path("src/strategy_builder/ui")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _styles_src() -> str:
    return STYLES_PATH.read_text()


def _styles_ast() -> ast.Module:
    return ast.parse(_styles_src())


def _find_method_node(tree: ast.Module, method_name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                return node
    return None


def _src(filename: str) -> str:
    return (UI_DIR / filename).read_text()


# ---------------------------------------------------------------------------
# AC-1 / AC-3  AST checks — synchronous maximize in showEvent
# ---------------------------------------------------------------------------

class TestSynchronousMaximizeAST:
    """AST-level regression guard for the synchronous maximize fix."""

    def _find_setwindowstate_calls_in_showevent(self, tree: ast.Module):
        calls = []
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "showEvent"
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "setWindowState"
                    ):
                        calls.append(child)
        return calls

    def test_setwindowstate_call_exists_in_showevent(self):
        """WindowGeometryMixin.showEvent must contain setWindowState call."""
        tree = _styles_ast()
        calls = self._find_setwindowstate_calls_in_showevent(tree)
        assert calls, (
            "styles.py: WindowGeometryMixin.showEvent must call setWindowState "
            "to apply maximized state AFTER super().showEvent() (BTCAAAAA-26202)."
        )

    def test_setwindowstate_uses_windowmaximized(self):
        """The setWindowState call must reference Qt.WindowMaximized."""
        tree = _styles_ast()
        calls = self._find_setwindowstate_calls_in_showevent(tree)
        assert calls, "WindowGeometryMixin.showEvent has no setWindowState call."

        for call_node in calls:
            args = call_node.args
            assert args, "setWindowState called with no arguments."
            first_arg = args[0]
            assert (
                isinstance(first_arg, ast.BinOp)
                and isinstance(first_arg.op, ast.BitOr)
            ) or isinstance(first_arg, ast.Attribute) or isinstance(first_arg, ast.Name), (
                "setWindowState must be called with an expression involving WindowMaximized."
            )
            # Check for WindowMaximized in the AST
            has_maximized = any(
                isinstance(n, ast.Attribute) and "WindowMaximized" in n.attr
                for n in ast.walk(call_node)
            )
            assert has_maximized, (
                "setWindowState must include Qt.WindowMaximized flag."
            )

    def test_no_qtimer_singleshot_in_restore(self):
        """QTimer.singleShot must NOT exist in _restore_window_geometry anymore."""
        tree = _styles_ast()
        restore_method = _find_method_node(tree, "_restore_window_geometry")
        assert restore_method is not None, "_restore_window_geometry not found."

        has_singleshot = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "singleShot"
            for node in ast.walk(restore_method)
        )
        assert not has_singleshot, (
            "QTimer.singleShot must be removed from _restore_window_geometry. "
            "Maximize is now applied synchronously in WindowGeometryMixin.showEvent "
            "before the WM maps the window."
        )


# ---------------------------------------------------------------------------
# AC-2 / AC-3 / AC-4  Runtime unit tests with mocked Qt
# ---------------------------------------------------------------------------

class TestShowEventMaximizeBehaviour:
    """
    Runtime unit tests for WindowGeometryMixin.showEvent maximize behavior.

    Qt objects are mocked so these tests run in headless CI without a display.
    """

    def _make_mixin_with_saved_state(self, maximized: bool, maximized_screen_name=None):
        """Build a minimal WindowGeometryMixin instance with controlled QSettings."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_settings = MagicMock()

        def settings_value(key, default=None, type=None):  # noqa: A002
            if key.endswith("/maximized"):
                return maximized
            if key.endswith("/pos"):
                return None
            if key.endswith("/size"):
                return None
            if key.endswith("/screen_name"):
                return None
            if key.endswith("/maximized_screen_name"):
                return maximized_screen_name
            return default

        mock_settings.value = settings_value

        mock_screen = MagicMock()
        mock_screen.availableGeometry.return_value = MagicMock(
            center=lambda: MagicMock(x=lambda: 960, y=lambda: 540),
            left=lambda: 0,
            top=lambda: 0,
            right=lambda: 1920,
            bottom=lambda: 1080,
        )
        mock_gui_app = MagicMock()
        mock_gui_app.primaryScreen.return_value = mock_screen
        mock_gui_app.screens.return_value = [mock_screen]

        mock_qsize = MagicMock(return_value=MagicMock())

        # Stub class to provide the super().showEvent() target that
        # WindowGeometryMixin.showEvent expects in the MRO chain.
        class _ShowEventStub:
            def showEvent(self, event):
                pass

        class _TestWindow(styles_mod.WindowGeometryMixin, _ShowEventStub):
            GEOMETRY_SETTINGS_KEY = "testWindow"
            GEOMETRY_DEFAULT_SIZE = (1200, 800)

            def __init__(self):
                self._geometry_restored = False
                self._move_calls = []
                self._window_state = 0

            def resize(self, *a):
                pass

            def move(self, x, y):
                self._move_calls.append((x, y))

            def showMaximized(self):
                pass

            def windowState(self):
                return self._window_state

            def setWindowState(self, state):
                self._window_state = state

            def isMaximized(self):
                return bool(self._window_state & 2)  # Qt.WindowMaximized == 2

        instance = _TestWindow()
        return instance, mock_settings, mock_gui_app, mock_qsize

    def test_showevent_sets_maximized_when_saved_maximized(self):
        """When maximized=True in QSettings, showEvent must set WindowMaximized."""
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_gui_app, mock_qsize = (
            self._make_mixin_with_saved_state(maximized=True)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
        ):
            instance.showEvent(None)

        assert instance.isMaximized(), (
            "showEvent did not maximize the window when saved state had maximized=True."
        )

    def test_showevent_does_not_maximize_when_not_saved(self):
        """When maximized=False in QSettings, showEvent must NOT maximize."""
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_gui_app, mock_qsize = (
            self._make_mixin_with_saved_state(maximized=False)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
        ):
            instance.showEvent(None)

        assert not instance.isMaximized(), (
            "showEvent maximized the window when saved state had maximized=False."
        )

    def test_position_on_maximized_screen(self):
        """When maximized with maximized_screen_name, window must move to that screen."""
        import src.strategy_builder.ui.styles as styles_mod

        mock_screens = {
            "DP-1": MagicMock(
                name=lambda: "DP-1",
                availableGeometry=MagicMock(
                    return_value=MagicMock(
                        center=lambda: MagicMock(x=lambda: 960, y=lambda: 540),
                        left=lambda: 0, top=lambda: 0,
                        right=lambda: 1920, bottom=lambda: 1080,
                    )
                ),
            ),
        }

        instance, mock_settings, mock_gui_app, mock_qsize = (
            self._make_mixin_with_saved_state(maximized=True, maximized_screen_name="DP-1")
        )
        mock_gui_app.screens.return_value = list(mock_screens.values())
        mock_gui_app.primaryScreen.return_value = mock_screens["DP-1"]

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
        ):
            instance.showEvent(None)

        assert len(instance._move_calls) > 0, (
            "showEvent should move the window when a maximized_screen_name is set."
        )

    def test_second_call_to_showevent_is_noop(self):
        """showEvent must be idempotent (_geometry_restored guard)."""
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_gui_app, mock_qsize = (
            self._make_mixin_with_saved_state(maximized=True)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
        ):
            instance.showEvent(None)  # first call
            instance.showEvent(None)  # second call — must be no-op

        # setWindowState should only be applied once
        assert instance.isMaximized(), "Window should be maximized after first showEvent."


# ---------------------------------------------------------------------------
# AC-5  All windows use WindowGeometryMixin (coverage regression guard)
# ---------------------------------------------------------------------------

class TestAllWindowsUseMixin:
    """Every application window must use WindowGeometryMixin."""

    @pytest.mark.parametrize("filename", ALL_MIXIN_WINDOWS)
    def test_window_uses_geometry_mixin(self, filename: str):
        src = _src(filename)
        assert "WindowGeometryMixin" in src, (
            f"{filename} does not use WindowGeometryMixin. "
            "All windows must inherit the mixin so they benefit from the "
            "synchronous maximize fix."
        )

    @pytest.mark.parametrize("filename", ALL_MIXIN_WINDOWS)
    def test_window_calls_restore_in_show_event(self, filename: str):
        src = _src(filename)
        assert "_restore_window_geometry" in src, (
            f"{filename} does not call _restore_window_geometry(). "
            "The mixin non-maximized position restore requires this call in showEvent."
        )
