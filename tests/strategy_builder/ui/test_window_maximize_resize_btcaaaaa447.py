"""
QA tests for BTCAAAAA-447: Re-audit and fix window maximize/resize issues
on ALL windows (regression from BTCAAAAA-387).

Root causes addressed:
1. BacktestConfigDialog — showMaximized() was being called in _init_ui(),
   conflicting with restoreGeometry() in showEvent; fixed by moving default-
   maximized behaviour to showEvent else-branch.
2. ConfigDiscoveryResultsDialog — setWindowFlags(Qt.Window) did not include
   explicit WindowMaximizeButtonHint / WindowMinimizeButtonHint; fixed with
   explicit flags + same showEvent first-run maximise pattern.
3. LogViewerWindow — setGeometry() hard-pinned position to (100, 100) and
   prevented QSettings restore; replaced with setMinimumSize + resize.
4. StrategyBrowserDialog (QMainWindow) — no setWindowFlags; on some Linux
   window managers a QMainWindow with a parent inherits limiting flags from
   the parent; fixed with explicit Qt.Window + maximize/minimize hints.
5. ValidationReportWindow (QMainWindow) — same as #4.
6. AutoFixConfirmDialog — missing maximize/minimize hints; added.
7. AlertDialog — bare QFont() calls; replaced with create_font() from styles.
   (style-discipline fix, co-committed with the window-management fixes).

Tests cover:
- AC-1: All windows have explicit WindowMaximizeButtonHint +
        WindowMinimizeButtonHint.
- AC-2: No conflicting showMaximized() call in _init_ui() / __init__ on
        windows that use showEvent for first-run maximise.
- AC-3: showEvent + closeEvent geometry persistence for all dialogs whose
        geometry is restored in showEvent.
- AC-4: _restore_geometry() / _restore_settings() used in __init__ for
        windows that restore before show (preferred pattern for QMainWindow).
- AC-5: No bare QFont() instantiation in alert_dialog.py (style discipline).
- AC-6: create_font() imported and used in alert_dialog.py.
- Regression: previously-passing windows not degraded.
"""

from __future__ import annotations

import ast
import pathlib
import sys
import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UI_DIR = pathlib.Path("src/strategy_builder/ui")


# ---------------------------------------------------------------------------
# QApplication fixture (shared across test session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _src(filename: str) -> str:
    return (UI_DIR / filename).read_text()


def _ast(filename: str) -> ast.Module:
    return ast.parse(_src(filename))


def _has_attr_ref(tree: ast.Module, attr: str) -> bool:
    """True if the AST contains any ast.Attribute node with .attr == attr."""
    return any(
        isinstance(n, ast.Attribute) and n.attr == attr for n in ast.walk(tree)
    )


def _has_method(tree: ast.Module, name: str) -> bool:
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        for n in ast.walk(tree)
    )


def _has_call(tree: ast.Module, method: str) -> bool:
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == method
        for n in ast.walk(tree)
    )


def _uses_geometry_mixin(src: str) -> bool:
    """True if the file uses WindowGeometryMixin for geometry persistence.

    WindowGeometryMixin (defined in styles.py) handles saveGeometry /
    restoreGeometry / QSettings internally, so files that inherit from it do
    not need to call those APIs directly.
    """
    return "WindowGeometryMixin" in src


def _method_body_src(tree: ast.Module, method_name: str) -> str:
    """
    Return the source-level text of all lines belonging to the named method,
    by un-parsing its AST node.  Works even when the method is split across
    multiple classes.  Returns '' if not found.
    """
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        ):
            return ast.unparse(node)
    return ""


def _count_calls(tree: ast.Module, method: str) -> int:
    return sum(
        1
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == method
    )


# ---------------------------------------------------------------------------
# AC-1: WindowMaximizeButtonHint + WindowMinimizeButtonHint on ALL top-level
#        windows that the board interacts with.
# ---------------------------------------------------------------------------

# Dialogs that MUST carry explicit maximize + minimize hints.
MAXIMIZE_REQUIRED = [
    "backtest_config_dialog.py",
    "config_discovery_results_dialog.py",
    "data_verify_dialog.py",
    "exit_condition_dialog.py",
    "log_viewer_window.py",
    "new_strategy_dialog.py",
    "settings_dialog.py",
    "timing_constraint_dialog.py",
    "validation_dialog.py",
    "validation_report_window.py",
    "strategy_browser_dialog.py",
    "auto_fix_confirm_dialog.py",
]


class TestExplicitMaximizeFlags:
    """AC-1: every window carries explicit maximize + minimize hints."""

    @pytest.mark.parametrize("filename", MAXIMIZE_REQUIRED)
    def test_maximize_hint(self, filename):
        src = _src(filename)
        assert "WindowMaximizeButtonHint" in src, (
            f"{filename}: missing Qt.WindowMaximizeButtonHint"
        )

    @pytest.mark.parametrize("filename", MAXIMIZE_REQUIRED)
    def test_minimize_hint(self, filename):
        src = _src(filename)
        assert "WindowMinimizeButtonHint" in src, (
            f"{filename}: missing Qt.WindowMinimizeButtonHint"
        )

    @pytest.mark.parametrize("filename", MAXIMIZE_REQUIRED)
    def test_qt_window_flag(self, filename):
        """Qt.Window base flag must accompany the button hints."""
        src = _src(filename)
        assert "Qt.Window" in src, (
            f"{filename}: missing Qt.Window base flag — "
            "button hints have no effect without it"
        )


# ---------------------------------------------------------------------------
# AC-2: No showMaximized() inside _init_ui or __init__ when showEvent
#        handles first-run maximise.  Calling showMaximized() in _init_ui
#        triggers showEvent immediately; if showEvent also calls
#        restoreGeometry this creates a geometry fight.
# ---------------------------------------------------------------------------


class TestNoShowMaximizedInInit:
    """
    Dialogs that use showEvent for first-run maximise must NOT also call
    showMaximized() inside _init_ui.
    """

    def _init_ui_has_show_maximized(self, filename: str) -> bool:
        tree = _ast(filename)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_init_ui"
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "showMaximized"
                    ):
                        return True
        return False

    def test_backtest_config_dialog_no_show_maximized_in_init_ui(self):
        assert not self._init_ui_has_show_maximized("backtest_config_dialog.py"), (
            "backtest_config_dialog._init_ui must NOT call showMaximized(); "
            "first-run maximise is handled in showEvent"
        )

    def test_config_discovery_no_show_maximized_in_init_ui(self):
        assert not self._init_ui_has_show_maximized(
            "config_discovery_results_dialog.py"
        ), (
            "config_discovery_results_dialog._init_ui must NOT call "
            "showMaximized(); first-run maximise is handled in showEvent"
        )


# ---------------------------------------------------------------------------
# AC-2b: showEvent else-branch provides default-maximised first-run for
#         dialogs that open maximised on first launch.
# ---------------------------------------------------------------------------


class TestShowEventFirstRunMaximize:
    """showEvent must call showMaximized() for the else (no saved geometry) path."""

    def _show_event_calls_show_maximized(self, filename: str) -> bool:
        tree = _ast(filename)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "showEvent"
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "showMaximized"
                    ):
                        return True
        return False

    def test_backtest_config_show_event_has_show_maximized(self):
        src = _src("backtest_config_dialog.py")
        # Accept either direct showMaximized() call in showEvent OR
        # WindowGeometryMixin usage (which handles first-run maximise internally
        # via QTimer.singleShot(0, self.showMaximized) in _restore_window_geometry).
        assert self._show_event_calls_show_maximized("backtest_config_dialog.py") or _uses_geometry_mixin(src), (
            "backtest_config_dialog.showEvent should call showMaximized() "
            "for first-run (no saved geometry) path, or use WindowGeometryMixin "
            "which handles this internally"
        )

    def test_config_discovery_show_event_has_show_maximized(self):
        src = _src("config_discovery_results_dialog.py")
        tree = _ast("config_discovery_results_dialog.py")
        # Accept either direct showMaximized() call in showEvent OR
        # WindowGeometryMixin usage (which handles first-run maximise internally
        # via QTimer.singleShot(0, self.showMaximized) in _restore_window_geometry).
        assert self._show_event_calls_show_maximized(
            "config_discovery_results_dialog.py"
        ) or _uses_geometry_mixin(src), (
            "config_discovery_results_dialog.showEvent should call "
            "showMaximized() for first-run (no saved geometry) path, or use "
            "WindowGeometryMixin which handles this internally"
        )


# ---------------------------------------------------------------------------
# AC-3: Geometry persistence via showEvent + closeEvent (dialog-pattern).
# ---------------------------------------------------------------------------

# Dialogs that persist geometry via showEvent / closeEvent.
SHOW_CLOSE_GEOMETRY_DIALOGS = [
    "backtest_config_dialog.py",
    "config_discovery_results_dialog.py",
    "data_verify_dialog.py",
    "exit_condition_dialog.py",
    "new_strategy_dialog.py",
    "settings_dialog.py",
    "timing_constraint_dialog.py",
    "validation_dialog.py",
]


class TestShowCloseGeometryPersistence:
    """AC-3: showEvent/closeEvent geometry save+restore for QDialog subclasses."""

    @pytest.mark.parametrize("filename", SHOW_CLOSE_GEOMETRY_DIALOGS)
    def test_show_event_defined(self, filename):
        tree = _ast(filename)
        assert _has_method(tree, "showEvent"), (
            f"{filename}: showEvent() not defined"
        )

    @pytest.mark.parametrize("filename", SHOW_CLOSE_GEOMETRY_DIALOGS)
    def test_close_event_defined(self, filename):
        tree = _ast(filename)
        assert _has_method(tree, "closeEvent"), (
            f"{filename}: closeEvent() not defined"
        )

    @pytest.mark.parametrize("filename", SHOW_CLOSE_GEOMETRY_DIALOGS)
    def test_restore_geometry_called(self, filename):
        src = _src(filename)
        tree = _ast(filename)
        # Accept either direct restoreGeometry() call OR WindowGeometryMixin
        # (which calls restoreGeometry internally via _restore_window_geometry).
        assert _has_call(tree, "restoreGeometry") or _uses_geometry_mixin(src), (
            f"{filename}: restoreGeometry() not found and WindowGeometryMixin not used"
        )

    @pytest.mark.parametrize("filename", SHOW_CLOSE_GEOMETRY_DIALOGS)
    def test_save_geometry_called(self, filename):
        src = _src(filename)
        tree = _ast(filename)
        # Accept either direct saveGeometry() call OR WindowGeometryMixin
        # (which calls saveGeometry internally via _save_window_geometry).
        assert _has_call(tree, "saveGeometry") or _uses_geometry_mixin(src), (
            f"{filename}: saveGeometry() not found and WindowGeometryMixin not used"
        )

    @pytest.mark.parametrize("filename", SHOW_CLOSE_GEOMETRY_DIALOGS)
    def test_qsettings_present(self, filename):
        src = _src(filename)
        # Accept either direct QSettings import OR WindowGeometryMixin
        # (which manages QSettings internally).
        assert "QSettings" in src or _uses_geometry_mixin(src), (
            f"{filename}: QSettings not found and WindowGeometryMixin not used — geometry cannot be persisted"
        )


# ---------------------------------------------------------------------------
# AC-4: QMainWindow subclasses restore geometry in __init__ (before show),
#        not in showEvent, to avoid re-applying geometry on every show.
# ---------------------------------------------------------------------------

# Windows that use _restore_geometry / _restore_settings in __init__.
INIT_RESTORE_WINDOWS = [
    ("log_viewer_window.py", "_restore_geometry"),
    ("strategy_browser_dialog.py", "_restore_settings"),
    ("validation_report_window.py", "_restore_geometry"),
]


class TestInitRestoreGeometry:
    """AC-4: windows that restore geometry in __init__ must define the helper."""

    @pytest.mark.parametrize("filename,helper", INIT_RESTORE_WINDOWS)
    def test_restore_helper_defined(self, filename, helper):
        tree = _ast(filename)
        assert _has_method(tree, helper), (
            f"{filename}: {helper}() not defined"
        )

    @pytest.mark.parametrize("filename,helper", INIT_RESTORE_WINDOWS)
    def test_restore_geometry_in_helper(self, filename, helper):
        src = _src(filename)
        tree = _ast(filename)
        # Accept either direct restoreGeometry() call inside the helper OR
        # WindowGeometryMixin usage (which calls restoreGeometry internally via
        # _restore_window_geometry / _save_window_geometry).
        if _uses_geometry_mixin(src):
            return  # mixin handles geometry — pass
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == helper
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "restoreGeometry"
                    ):
                        return  # found — pass
        pytest.fail(
            f"{filename}: restoreGeometry() not called inside {helper}() "
            f"and WindowGeometryMixin not used"
        )

    @pytest.mark.parametrize("filename,helper", INIT_RESTORE_WINDOWS)
    def test_no_geometry_restore_in_show_event(self, filename, helper):
        """
        showEvent must NOT call restoreGeometry for these windows — they
        already restore in __init__.  Double-restoring fights the user's
        manual resize/move after the window is shown.
        """
        tree = _ast(filename)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "showEvent"
            ):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "restoreGeometry"
                    ):
                        pytest.fail(
                            f"{filename}: showEvent must NOT call "
                            "restoreGeometry — this window already restores "
                            f"geometry in {helper}() (called from __init__)"
                        )


# ---------------------------------------------------------------------------
# AC-4b: LogViewerWindow must not use setGeometry() to pin position.
# ---------------------------------------------------------------------------


class TestLogViewerNoHardPinnedGeometry:
    """setGeometry(x, y, w, h) hard-pins position and blocks QSettings restore."""

    def test_no_set_geometry_call(self):
        tree = _ast("log_viewer_window.py")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setGeometry"
            ):
                # Allow on popup/child widgets but not on self
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "self":
                        pytest.fail(
                            "log_viewer_window: self.setGeometry() must not "
                            "be used — it hard-pins position and prevents "
                            "QSettings geometry restoration"
                        )


# ---------------------------------------------------------------------------
# AC-5 & AC-6: alert_dialog.py — no bare QFont(); create_font() used.
# ---------------------------------------------------------------------------


class TestAlertDialogStyleDiscipline:
    """alert_dialog.py must not contain bare QFont() calls; use create_font()."""

    def test_no_bare_qfont(self):
        tree = _ast("alert_dialog.py")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "QFont"
            ):
                pytest.fail(
                    "alert_dialog.py: bare QFont() found — "
                    "use create_font() from styles.py instead"
                )

    def test_create_font_imported(self):
        src = _src("alert_dialog.py")
        assert "create_font" in src, (
            "alert_dialog.py: create_font not imported from styles.py"
        )

    def test_create_font_called(self):
        tree = _ast("alert_dialog.py")
        # create_font is a module-level function imported from styles.py, so
        # it is called as a plain Name node (create_font(...)), not an
        # attribute access (obj.create_font(...)).
        found = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "create_font"
            for n in ast.walk(tree)
        )
        assert found, "alert_dialog.py: create_font() is not called anywhere"

    def test_qfont_not_imported_directly(self):
        src = _src("alert_dialog.py")
        # QFont may still appear in imports as part of PyQt5.QtGui but must
        # NOT be used directly in widget code.
        assert "from PyQt5.QtGui import QFont" not in src, (
            "alert_dialog.py: direct 'from PyQt5.QtGui import QFont' import "
            "should be removed — use create_font() from styles.py"
        )


# ---------------------------------------------------------------------------
# Regression: previously-passing windows not degraded
# ---------------------------------------------------------------------------


class TestRegressionGuard:
    """
    Ensure windows that were already correct before BTCAAAAA-447 are
    still correct.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            "data_verify_dialog.py",
            "exit_condition_dialog.py",
            "timing_constraint_dialog.py",
            "new_strategy_dialog.py",
            "validation_dialog.py",
            "settings_dialog.py",
        ],
    )
    def test_maximize_hint_still_present(self, filename):
        src = _src(filename)
        assert "WindowMaximizeButtonHint" in src

    @pytest.mark.parametrize(
        "filename",
        [
            "data_verify_dialog.py",
            "exit_condition_dialog.py",
            "timing_constraint_dialog.py",
            "new_strategy_dialog.py",
            "validation_dialog.py",
            "settings_dialog.py",
            "log_viewer_window.py",
        ],
    )
    def test_close_event_still_present(self, filename):
        tree = _ast(filename)
        assert _has_method(tree, "closeEvent"), (
            f"{filename}: closeEvent() was removed — geometry will not persist"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "data_verify_dialog.py",
            "exit_condition_dialog.py",
            "timing_constraint_dialog.py",
            "new_strategy_dialog.py",
            "validation_dialog.py",
            "settings_dialog.py",
            "log_viewer_window.py",
        ],
    )
    def test_save_geometry_still_present(self, filename):
        src = _src(filename)
        tree = _ast(filename)
        # Accept either direct saveGeometry() call OR WindowGeometryMixin
        # (which handles persistence internally via _save_window_geometry).
        assert _has_call(tree, "saveGeometry") or _uses_geometry_mixin(src), (
            f"{filename}: saveGeometry() removed and WindowGeometryMixin not used"
        )
