"""
QA re-test for BTCAAAAA-475 follow-up fix (commit a5ad2b0).

What changed:
    QTimer.singleShot(0, self.showMaximized)
    →
    QTimer.singleShot(50, self.showMaximized)

Why:
    A delay of 0 ms fires at the next event-loop iteration but Qt has not
    completed its initial layout pass at that point.  The symptom is that
    maximize appears to do nothing on first open without any prior user
    interaction (e.g. clicking a tab).  The tab click triggers a layout
    recalculation that incidentally corrects the window state.

    50 ms gives Qt and the OS window manager enough time to finish the
    initial layout/paint cycle so showMaximized() reliably fills the screen
    even on the very first maximize attempt with no preceding user
    interaction.

Board-reported reproduction sequence (MUST pass):
    1. Open window fresh — no prior state from this session
    2. Do NOT click any tab, button, or widget
    3. Immediately click maximize → MUST fill the screen   ← this failed before

Pass criteria tested here:
    AC-1  The timer delay in _restore_window_geometry is ≥ 50 ms (not 0 ms).
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

import ast
import pathlib
import sys
from unittest.mock import MagicMock, call, patch

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
    """Return the first FunctionDef with the given name in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                return node
    return None


def _src(filename: str) -> str:
    return (UI_DIR / filename).read_text()


# ---------------------------------------------------------------------------
# AC-1 / AC-5  AST checks — timer delay value in source
# ---------------------------------------------------------------------------

class TestTimerDelayAST:
    """AST-level regression guard for the singleShot delay value."""

    def _find_singlesshot_calls_in_restore(self, tree: ast.Module):
        """
        Return all ast.Call nodes that are QTimer.singleShot(…) inside the
        _restore_window_geometry method.
        """
        calls = []
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_restore_window_geometry"
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "singleShot"
                    ):
                        calls.append(child)
        return calls

    def test_single_shot_call_exists_in_restore(self):
        """_restore_window_geometry must contain at least one QTimer.singleShot call."""
        tree = _styles_ast()
        calls = self._find_singlesshot_calls_in_restore(tree)
        assert calls, (
            "styles.py: _restore_window_geometry must call QTimer.singleShot "
            "to defer showMaximized() until after Qt completes the layout pass."
        )

    def test_timer_delay_is_50ms_not_0ms(self):
        """
        The singleShot delay MUST be 50 (not 0).

        A delay of 0 fires at the next event-loop tick before Qt finishes its
        initial layout pass.  50 ms is required to reliably fill the screen on
        first maximize without prior tab interaction.
        """
        tree = _styles_ast()
        calls = self._find_singlesshot_calls_in_restore(tree)
        assert calls, "_restore_window_geometry has no QTimer.singleShot call."

        for call_node in calls:
            args = call_node.args
            assert args, "QTimer.singleShot called with no arguments — unexpected."
            first_arg = args[0]
            # The first argument must be the integer literal 50
            assert (
                isinstance(first_arg, ast.Constant) and first_arg.value == 50
            ), (
                f"QTimer.singleShot delay is {ast.dump(first_arg)!r}, expected 50. "
                "Commit a5ad2b0 changed this from 0 → 50 ms to fix maximize on "
                "first open without prior tab click (BTCAAAAA-475 follow-up)."
            )

    def test_timer_delay_is_not_zero(self):
        """
        Regression guard: singleShot(0, ...) in _restore_window_geometry must NOT exist.

        If someone reverts the fix back to 0 ms this test catches it immediately.
        """
        tree = _styles_ast()
        calls = self._find_singlesshot_calls_in_restore(tree)
        for call_node in calls:
            args = call_node.args
            if args:
                first_arg = args[0]
                assert not (
                    isinstance(first_arg, ast.Constant) and first_arg.value == 0
                ), (
                    "QTimer.singleShot(0, ...) found in _restore_window_geometry — "
                    "this is the pre-fix value that caused maximize to fail on first "
                    "open without prior user interaction.  The delay must be ≥ 50 ms."
                )

    def test_callback_is_show_maximized(self):
        """
        The singleShot callback must ultimately invoke showMaximized — either
        directly as self.showMaximized, or via a named closure that calls it.
        """
        tree = _styles_ast()
        calls = self._find_singlesshot_calls_in_restore(tree)
        assert calls, "_restore_window_geometry has no QTimer.singleShot call."

        for call_node in calls:
            args = call_node.args
            assert len(args) >= 2, (
                "QTimer.singleShot must have at least 2 args: (delay, callback)."
            )
            callback_arg = args[1]
            # Accept either self.showMaximized directly, or a named closure
            is_direct = (
                isinstance(callback_arg, ast.Attribute)
                and callback_arg.attr == "showMaximized"
            )
            is_closure = isinstance(callback_arg, ast.Name)
            assert is_direct or is_closure, (
                f"singleShot callback is {ast.dump(callback_arg)!r}, "
                "expected self.showMaximized or a named closure."
            )
            # If it's a closure, verify showMaximized is called inside it
            if is_closure:
                closure_name = callback_arg.id
                restore_method = _find_method_node(_styles_ast(), "_restore_window_geometry")
                closure_def = None
                for node in ast.walk(restore_method):
                    if isinstance(node, ast.FunctionDef) and node.name == closure_name:
                        closure_def = node
                        break
                assert closure_def is not None, (
                    f"Closure '{closure_name}' passed to singleShot not found in "
                    "_restore_window_geometry."
                )
                has_show_maximized = any(
                    isinstance(n, ast.Attribute) and n.attr == "showMaximized"
                    for n in ast.walk(closure_def)
                )
                assert has_show_maximized, (
                    f"Closure '{closure_name}' does not call showMaximized(). "
                    "The 50ms deferral must ultimately invoke self.showMaximized()."
                )


# ---------------------------------------------------------------------------
# AC-2 / AC-3 / AC-4  Runtime unit tests with mocked Qt
# ---------------------------------------------------------------------------

class TestRestoreWindowGeometryTimerBehaviour:
    """
    Runtime unit tests for WindowGeometryMixin._restore_window_geometry.

    Qt objects are mocked so these tests run in headless CI without a display.
    """

    def _make_mixin_with_saved_state(self, maximized: bool):
        """
        Build a minimal WindowGeometryMixin instance whose QSettings stub
        returns a specified maximized flag.  Returns (instance, mock_timer).
        """
        sys.path.insert(0, ".")

        # We patch the Qt internals used inside _restore_window_geometry so we
        # can invoke the real Python logic without a display.
        import importlib
        import types

        # Build a lightweight fake Qt module tree so the import inside
        # _restore_window_geometry succeeds
        mock_qtimer = MagicMock()

        # Stub QSettings to return our desired maximized value
        mock_settings = MagicMock()

        def settings_value(key, default=None, type=None):  # noqa: A002
            if key.endswith("/maximized"):
                return maximized
            if key.endswith("/pos"):
                return None  # no saved position → centre on primary
            if key.endswith("/size"):
                return None
            if key.endswith("/screen_name"):
                return None
            return default

        mock_settings.value = settings_value

        # Stub QGuiApplication.primaryScreen().availableGeometry()
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

        # Stub QSize
        mock_qsize = MagicMock(return_value=MagicMock())

        # Stub QRect
        mock_qrect = MagicMock(return_value=MagicMock(
            intersected=lambda _: MagicMock(width=lambda: 0, height=lambda: 0)
        ))

        # Patch the private module-level aliases in styles
        import src.strategy_builder.ui.styles as styles_mod

        # Create the mixin instance
        class _TestWindow(styles_mod.WindowGeometryMixin):
            GEOMETRY_SETTINGS_KEY = "testWindow"
            GEOMETRY_DEFAULT_SIZE = (1200, 800)

            def __init__(self):
                # Don't call QWidget.__init__ — we're not testing Qt rendering
                self._geometry_restored = False

            # Stub the Qt methods called inside _restore_window_geometry
            def resize(self, *a):
                pass

            def move(self, *a):
                pass

            def showMaximized(self):
                pass

            def width(self):
                return 1200

            def height(self):
                return 800

        instance = _TestWindow()

        return instance, mock_settings, mock_qtimer, mock_gui_app, mock_qsize, mock_qrect

    def test_timer_called_with_50ms_when_maximized(self):
        """
        When maximized=True is in QSettings, QTimer.singleShot must be called
        with delay=50 and self.showMaximized as the callback.

        This is the core fix for BTCAAAAA-475: the first maximize click must
        fill the screen even without any prior tab/widget interaction.
        """
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_qtimer, mock_gui_app, mock_qsize, mock_qrect = (
            self._make_mixin_with_saved_state(maximized=True)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
            patch.object(styles_mod, "_QRect", mock_qrect),
            # Patch QTimer inside the styles module's namespace
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            # Also patch the import that happens inside the function
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                instance._restore_window_geometry()

        # QTimer.singleShot must have been called
        assert mock_qtimer.singleShot.called, (
            "QTimer.singleShot was NOT called when maximized=True. "
            "showMaximized() must be deferred via QTimer to avoid calling it "
            "before Qt completes the initial layout pass."
        )

        # Extract the delay argument from the call
        call_args = mock_qtimer.singleShot.call_args
        assert call_args is not None, "QTimer.singleShot call_args is None."
        delay = call_args[0][0]  # positional arg 0
        assert delay == 50, (
            f"QTimer.singleShot delay is {delay!r}, expected 50. "
            "A delay of 0 ms is insufficient — Qt has not finished its initial "
            "layout pass at the next event-loop tick, causing maximize to appear "
            "to do nothing on first open without prior user interaction. "
            "(Commit a5ad2b0 changed 0 → 50 ms to fix BTCAAAAA-475.)"
        )

    def test_timer_not_called_when_not_maximized(self):
        """
        When maximized=False in QSettings, QTimer.singleShot must NOT be called.
        """
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_qtimer, mock_gui_app, mock_qsize, mock_qrect = (
            self._make_mixin_with_saved_state(maximized=False)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
            patch.object(styles_mod, "_QRect", mock_qrect),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                instance._restore_window_geometry()

        assert not mock_qtimer.singleShot.called, (
            "QTimer.singleShot should NOT be called when maximized=False — "
            "showMaximized() is only needed when the window was previously maximized."
        )

    def test_second_call_to_restore_is_noop(self):
        """
        _restore_window_geometry has an idempotency guard (_geometry_restored flag).
        A second call must not trigger another QTimer.singleShot.
        """
        import src.strategy_builder.ui.styles as styles_mod

        instance, mock_settings, mock_qtimer, mock_gui_app, mock_qsize, mock_qrect = (
            self._make_mixin_with_saved_state(maximized=True)
        )

        with (
            patch.object(styles_mod, "_QSettings", return_value=mock_settings),
            patch.object(styles_mod, "_QGuiApplication", mock_gui_app),
            patch.object(styles_mod, "_QSize", mock_qsize),
            patch.object(styles_mod, "_QRect", mock_qrect),
            patch("src.strategy_builder.ui.styles.QTimer", mock_qtimer, create=True),
        ):
            with patch.dict("sys.modules", {"PyQt5.QtCore": MagicMock(QTimer=mock_qtimer)}):
                instance._restore_window_geometry()  # first call
                instance._restore_window_geometry()  # second call — must be no-op

        # singleShot must have been called exactly once
        assert mock_qtimer.singleShot.call_count == 1, (
            f"QTimer.singleShot was called {mock_qtimer.singleShot.call_count} times "
            "but must only be called once (idempotency guard failed)."
        )


# ---------------------------------------------------------------------------
# AC-6  All windows use WindowGeometryMixin (coverage regression guard)
# ---------------------------------------------------------------------------

class TestAllWindowsUseMixin:
    """
    Every application window must use WindowGeometryMixin to inherit the
    50 ms maximize-delay fix.  Any window that bypasses the mixin will still
    exhibit the first-maximize bug even after commit a5ad2b0.
    """

    @pytest.mark.parametrize("filename", ALL_MIXIN_WINDOWS)
    def test_window_uses_geometry_mixin(self, filename: str):
        src = _src(filename)
        assert "WindowGeometryMixin" in src, (
            f"{filename} does not use WindowGeometryMixin. "
            "All windows must inherit the mixin so they benefit from the "
            "50 ms showMaximized timer fix (BTCAAAAA-475 follow-up)."
        )

    @pytest.mark.parametrize("filename", ALL_MIXIN_WINDOWS)
    def test_window_calls_restore_in_show_event(self, filename: str):
        src = _src(filename)
        assert "_restore_window_geometry" in src, (
            f"{filename} does not call _restore_window_geometry(). "
            "The mixin fix only activates when this method is called in showEvent."
        )
