"""
QA tests for BTCAAAAA-659: Fix: Unable to maximize window

Root cause: StrategyBuilderMainWindow did not call setWindowFlags(), so some
Linux window managers omitted the maximize button or blocked maximization.

Fix: Added explicit setWindowFlags() in _init_ui() with:
    Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
    | Qt.WindowCloseButtonHint

Acceptance criteria verified:
- AC-1: Qt.WindowMaximizeButtonHint present in StrategyBuilderMainWindow
- AC-2: Qt.WindowMinimizeButtonHint present (full button set)
- AC-3: Qt.Window base flag present (required for hints to take effect)
- AC-4: Qt.WindowCloseButtonHint present (close button not accidentally removed)
- AC-5: setWindowFlags() called in _init_ui()
- AC-6: WindowGeometryMixin showMaximized() path is unaffected
- AC-7: No setFixedSize() or setMaximumSize() calls that would block maximize
"""

from __future__ import annotations

import ast
import pathlib

MAIN_WINDOW_FILE = pathlib.Path(
    "src/strategy_builder/ui/strategy_builder_main_window.py"
)


def _src() -> str:
    return MAIN_WINDOW_FILE.read_text()


def _tree() -> ast.Module:
    return ast.parse(_src())


def _init_ui_node(tree: ast.Module) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_init_ui"
        ):
            return node
    return None


class TestStrategyBuilderMainWindowFlags:
    """AC-1 through AC-5: explicit window flags in StrategyBuilderMainWindow."""

    def test_window_maximize_hint_present(self):
        """Qt.WindowMaximizeButtonHint must be present so the maximize button is visible."""
        assert "WindowMaximizeButtonHint" in _src(), (
            "strategy_builder_main_window.py: missing Qt.WindowMaximizeButtonHint — "
            "maximize button will not appear on all Linux window managers"
        )

    def test_window_minimize_hint_present(self):
        """Qt.WindowMinimizeButtonHint must be present alongside the maximize hint."""
        assert "WindowMinimizeButtonHint" in _src(), (
            "strategy_builder_main_window.py: missing Qt.WindowMinimizeButtonHint"
        )

    def test_qt_window_base_flag_present(self):
        """Qt.Window base flag is required for button hints to take effect."""
        assert "Qt.Window" in _src(), (
            "strategy_builder_main_window.py: missing Qt.Window base flag — "
            "WindowMaximizeButtonHint has no effect without it"
        )

    def test_window_close_hint_present(self):
        """Qt.WindowCloseButtonHint must be present so the close button is not lost."""
        assert "WindowCloseButtonHint" in _src(), (
            "strategy_builder_main_window.py: missing Qt.WindowCloseButtonHint — "
            "the close button would be removed when custom flags are set"
        )

    def test_set_window_flags_called_in_init_ui(self):
        """setWindowFlags() must be called inside _init_ui()."""
        tree = _tree()
        init_ui = _init_ui_node(tree)
        assert init_ui is not None, (
            "strategy_builder_main_window.py: _init_ui() method not found"
        )
        found = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setWindowFlags"
            for node in ast.walk(init_ui)
        )
        assert found, (
            "strategy_builder_main_window.py: setWindowFlags() not called in _init_ui() — "
            "window flags are not set and maximize button may be missing"
        )


class TestStrategyBuilderNoBlockingConstraints:
    """AC-7: no setFixedSize / setMaximumSize that would prevent maximization."""

    def test_no_set_fixed_size(self):
        """setFixedSize() prevents the window from being resized or maximized."""
        tree = _tree()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setFixedSize"
            ):
                # Only flag calls on self (the main window itself)
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                    pytest.fail(
                        "strategy_builder_main_window.py: self.setFixedSize() call found — "
                        "this prevents the window from being maximized"
                    )

    def test_no_set_maximum_size_blocking_maximize(self):
        """setMaximumSize() with small dimensions would prevent maximization."""
        src = _src()
        # A broad guard: if setMaximumSize is called on self, flag it for review.
        # The main window should not cap its own size.
        tree = _tree()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setMaximumSize"
            ):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                    import pytest as _pytest
                    _pytest.fail(
                        "strategy_builder_main_window.py: self.setMaximumSize() call found — "
                        "this may prevent the window from being maximized"
                    )


class TestStrategyBuilderGeometryMixinUnaffected:
    """AC-6: WindowGeometryMixin usage is intact — geometry persistence not broken."""

    def test_window_geometry_mixin_still_used(self):
        """The fix must not remove WindowGeometryMixin from the class hierarchy."""
        src = _src()
        assert "WindowGeometryMixin" in src, (
            "strategy_builder_main_window.py: WindowGeometryMixin no longer used — "
            "geometry persistence (save/restore maximized state) would be lost"
        )

    def test_class_still_inherits_qmainwindow(self):
        """StrategyBuilderMainWindow must still be a QMainWindow subclass."""
        src = _src()
        assert "QMainWindow" in src, (
            "strategy_builder_main_window.py: QMainWindow base class not found — "
            "class structure may have been accidentally changed"
        )


class TestStrategyBuilderMainWindowFlagsMatchPattern:
    """Verify the flags match the established pattern from SettingsDialog / StrategyBrowserDialog."""

    def _flags_call_src(self) -> str:
        """Return the unparsed source of the setWindowFlags() call in _init_ui."""
        tree = _tree()
        init_ui = _init_ui_node(tree)
        if init_ui is None:
            return ""
        for node in ast.walk(init_ui):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setWindowFlags"
            ):
                return ast.unparse(node)
        return ""

    def test_flags_include_all_four_required_components(self):
        """The setWindowFlags() call must include all four required flag components."""
        flags_src = self._flags_call_src()
        assert flags_src, "setWindowFlags() call not found in _init_ui()"
        assert "Qt.Window" in flags_src, "Qt.Window missing from setWindowFlags() call"
        assert "WindowMaximizeButtonHint" in flags_src, (
            "WindowMaximizeButtonHint missing from setWindowFlags() call"
        )
        assert "WindowMinimizeButtonHint" in flags_src, (
            "WindowMinimizeButtonHint missing from setWindowFlags() call"
        )
        assert "WindowCloseButtonHint" in flags_src, (
            "WindowCloseButtonHint missing from setWindowFlags() call"
        )


# ---------------------------------------------------------------------------
# Regression guard: MAXIMIZE_REQUIRED list from test_window_maximize_resize_447
# must not be broken by this change (spot-check StrategyBrowserDialog)
# ---------------------------------------------------------------------------


class TestRegressionGuard659:
    """Ensure previously-passing windows are still correct after this fix."""

    def test_strategy_browser_dialog_still_has_maximize_hint(self):
        src = pathlib.Path("src/strategy_builder/ui/strategy_browser_dialog.py").read_text()
        assert "WindowMaximizeButtonHint" in src, (
            "strategy_browser_dialog.py: WindowMaximizeButtonHint removed — regression"
        )

    def test_settings_dialog_still_has_maximize_hint(self):
        src = pathlib.Path("src/strategy_builder/ui/settings_dialog.py").read_text()
        assert "WindowMaximizeButtonHint" in src, (
            "settings_dialog.py: WindowMaximizeButtonHint removed — regression"
        )
