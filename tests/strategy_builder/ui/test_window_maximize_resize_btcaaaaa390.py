"""
QA tests for BTCAAAAA-390: Fix maximize button and window resize issues.

Verifies acceptance criteria from commit 7f73fa3:
1. WindowMaximizeButtonHint and WindowMinimizeButtonHint present on all modified dialogs
2. No window resizes when dragged (non-modal dialogs only — tested via code review)
3. Geometry persistence — saveGeometry/restoreGeometry wired to showEvent/closeEvent,
   OR WindowGeometryMixin used (which implements geometry persistence internally
   without direct saveGeometry/restoreGeometry calls — see BTCAAAAA-475).
4. No regressions on already-correct windows
5. Code review: QSettings key naming convention, no hardcoded styles,
   timing_constraint_dialog uses create_font() (not raw QFont())

These are static/AST code-review tests plus lightweight runtime initialisation
checks.  Full manual interaction (drag, maximize click, pixel-perfect restore)
cannot be automated reliably in a headless CI environment, but the structural
checks below cover all acceptance-criteria items that can be verified
programmatically.

Note (BTCAAAAA-507): BTCAAAAA-475 introduced WindowGeometryMixin in styles.py as
an architectural replacement for direct saveGeometry()/restoreGeometry() calls.
The mixin deliberately avoids saveGeometry/restoreGeometry to fix a Qt5 window
state desync bug (Qt5's saveGeometry bakes the maximized flag into the geometry
blob, causing the OS window manager to get out of sync with Qt's window state).
All geometry persistence checks have been updated to accept WindowGeometryMixin
as a valid implementation.
"""

from __future__ import annotations

import ast
import pathlib
import pytest

# ---------------------------------------------------------------------------
# Constants — file paths under test
# ---------------------------------------------------------------------------

UI_DIR = pathlib.Path("src/strategy_builder/ui")

MODIFIED_DIALOGS = [
    "data_verify_dialog.py",
    "exit_condition_dialog.py",
    "timing_constraint_dialog.py",
    "new_strategy_dialog.py",
    "backtest_config_dialog.py",
    "validation_dialog.py",
    "settings_dialog.py",
    "config_discovery_results_dialog.py",
]

EXPECTED_GEOMETRY_KEYS = {
    "data_verify_dialog.py": "dataVerifyDialog/geometry",
    "exit_condition_dialog.py": "exitConditionDialog/geometry",
    "timing_constraint_dialog.py": "timingConstraintDialog/geometry",
    "new_strategy_dialog.py": "newStrategyDialog/geometry",
    "backtest_config_dialog.py": "backtestConfigDialog/geometry",
    "validation_dialog.py": "validationDialog/geometry",
    "settings_dialog.py": "settingsDialog/geometry",
    "config_discovery_results_dialog.py": "configDiscoveryDialog/geometry",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_source(filename: str) -> str:
    return (UI_DIR / filename).read_text()


def _parse_ast(filename: str) -> ast.Module:
    return ast.parse(_read_source(filename))


def _uses_geometry_mixin(src: str) -> bool:
    """True if the file uses WindowGeometryMixin for geometry persistence.

    WindowGeometryMixin (defined in styles.py) handles saveGeometry /
    restoreGeometry / QSettings internally, so files that inherit from it do
    not need direct calls to those APIs.
    """
    return "WindowGeometryMixin" in src


def _has_flag_call(tree: ast.Module, flag_name: str) -> bool:
    """Return True if the AST contains any attribute reference to flag_name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == flag_name:
            return True
    return False


def _has_method(tree: ast.Module, method_name: str) -> bool:
    """Return True if the AST defines a function/method with method_name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == method_name:
                return True
    return False


def _has_call(tree: ast.Module, method_name: str) -> bool:
    """Return True if the AST contains a call to an attribute named method_name."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method_name
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# AC-1: Maximize and Minimize button hints
# ---------------------------------------------------------------------------

class TestMaximizeMinimizeHints:
    """AC-1: WindowMaximizeButtonHint + WindowMinimizeButtonHint present."""

    @pytest.mark.parametrize("filename", [
        "data_verify_dialog.py",
        "exit_condition_dialog.py",
        "timing_constraint_dialog.py",
        "new_strategy_dialog.py",
        "backtest_config_dialog.py",
        "validation_dialog.py",
        "settings_dialog.py",
    ])
    def test_maximize_hint_present(self, filename):
        """WindowMaximizeButtonHint must appear in the source."""
        source = _read_source(filename)
        assert "WindowMaximizeButtonHint" in source, (
            f"{filename}: missing Qt.WindowMaximizeButtonHint — "
            "maximize button will not be visible on all platforms."
        )

    @pytest.mark.parametrize("filename", [
        "data_verify_dialog.py",
        "exit_condition_dialog.py",
        "timing_constraint_dialog.py",
        "new_strategy_dialog.py",
        "backtest_config_dialog.py",
        "validation_dialog.py",
        "settings_dialog.py",
    ])
    def test_minimize_hint_present(self, filename):
        """WindowMinimizeButtonHint must appear in the source."""
        source = _read_source(filename)
        assert "WindowMinimizeButtonHint" in source, (
            f"{filename}: missing Qt.WindowMinimizeButtonHint — "
            "minimize button will not be visible on all platforms."
        )

    def test_config_discovery_uses_qt_window_flag(self):
        """
        config_discovery_results_dialog.py uses Qt.Window which gives the OS
        standard title bar (maximize/minimize are implicit on all platforms).
        """
        source = _read_source("config_discovery_results_dialog.py")
        assert "Qt.Window" in source, (
            "config_discovery_results_dialog.py must use Qt.Window flag "
            "to expose the OS maximize/minimize controls."
        )


# ---------------------------------------------------------------------------
# AC-3/4: Geometry persistence
# ---------------------------------------------------------------------------

class TestGeometryPersistence:
    """AC-3/4: saveGeometry / restoreGeometry wired in show/close events."""

    @pytest.mark.parametrize("filename", MODIFIED_DIALOGS)
    def test_save_geometry_called(self, filename):
        """saveGeometry() must be called, or WindowGeometryMixin must be used.

        WindowGeometryMixin (BTCAAAAA-475) deliberately avoids saveGeometry()
        to fix a Qt5 window-state desync bug; it stores pos/size/maximized
        as separate QSettings keys instead.
        """
        src = _read_source(filename)
        tree = _parse_ast(filename)
        # Accept either a direct saveGeometry() call OR WindowGeometryMixin usage
        assert _has_call(tree, "saveGeometry") or _uses_geometry_mixin(src), (
            f"{filename}: saveGeometry() call not found and WindowGeometryMixin not used — "
            "dialog will not persist its size/position."
        )

    @pytest.mark.parametrize("filename", MODIFIED_DIALOGS)
    def test_restore_geometry_called(self, filename):
        """restoreGeometry() must be called, or WindowGeometryMixin must be used.

        WindowGeometryMixin (BTCAAAAA-475) deliberately avoids restoreGeometry()
        to fix a Qt5 window-state desync bug; it restores pos/size/maximized
        from separate QSettings keys instead.
        """
        src = _read_source(filename)
        tree = _parse_ast(filename)
        # Accept either a direct restoreGeometry() call OR WindowGeometryMixin usage
        assert _has_call(tree, "restoreGeometry") or _uses_geometry_mixin(src), (
            f"{filename}: restoreGeometry() call not found and WindowGeometryMixin not used — "
            "dialog will not restore its saved size/position."
        )

    @pytest.mark.parametrize("filename", MODIFIED_DIALOGS)
    def test_close_event_defined(self, filename):
        """closeEvent() must be defined to save geometry on close."""
        tree = _parse_ast(filename)
        assert _has_method(tree, "closeEvent"), (
            f"{filename}: closeEvent() not defined — "
            "geometry will not be saved when the dialog is closed."
        )

    @pytest.mark.parametrize("filename", MODIFIED_DIALOGS)
    def test_qsettings_used(self, filename):
        """QSettings must be used to persist geometry, directly or via WindowGeometryMixin.

        WindowGeometryMixin (BTCAAAAA-475) owns the QSettings usage internally
        in styles.py, so files using the mixin do not need a direct QSettings
        reference.
        """
        src = _read_source(filename)
        # Accept either direct QSettings reference OR WindowGeometryMixin usage
        assert "QSettings" in src or _uses_geometry_mixin(src), (
            f"{filename}: QSettings not found and WindowGeometryMixin not used — "
            "geometry persistence requires QSettings."
        )

    @pytest.mark.parametrize("filename", list(EXPECTED_GEOMETRY_KEYS.keys()))
    def test_geometry_key_naming_convention(self, filename):
        """
        QSettings key must follow the BTC_Engine / StrategyBuilder convention
        and use the expected per-dialog key prefix.

        For dialogs using WindowGeometryMixin (BTCAAAAA-475), BTC_Engine and
        StrategyBuilder live in styles.py (not the dialog file), and the dialog
        file sets GEOMETRY_SETTINGS_KEY to the expected key prefix.  We accept
        this pattern as compliant.
        """
        expected_key = EXPECTED_GEOMETRY_KEYS[filename]
        # Strip the /geometry suffix — the expected key prefix is the part before "/"
        expected_prefix = expected_key.split("/")[0]
        source = _read_source(filename)
        styles_source = (UI_DIR / "styles.py").read_text()

        if _uses_geometry_mixin(source):
            # BTC_Engine + StrategyBuilder live in styles.py for mixin-based dialogs
            assert "BTC_Engine" in styles_source, (
                "styles.py: WindowGeometryMixin must use QSettings('BTC_Engine', ...) "
                "(found mismatched or missing app name in styles.py)."
            )
            assert "StrategyBuilder" in styles_source, (
                "styles.py: WindowGeometryMixin must use QSettings(..., 'StrategyBuilder') "
                "(found mismatched or missing org name in styles.py)."
            )
            assert expected_prefix in source, (
                f"{filename}: Expected GEOMETRY_SETTINGS_KEY prefix '{expected_prefix}' not found. "
                "Keys must follow the agreed naming convention."
            )
        else:
            # Direct QSettings usage: BTC_Engine + StrategyBuilder + full key must be in the dialog file
            assert "BTC_Engine" in source, (
                f"{filename}: QSettings must use application 'BTC_Engine' "
                "(found mismatched or missing app name)."
            )
            assert "StrategyBuilder" in source, (
                f"{filename}: QSettings must use organization 'StrategyBuilder' "
                "(found mismatched or missing org name)."
            )
            assert expected_key in source, (
                f"{filename}: Expected geometry key '{expected_key}' not found in source. "
                "Keys must follow the agreed naming convention."
            )


# ---------------------------------------------------------------------------
# AC-6: Code quality — QFont removal in timing_constraint_dialog.py
# ---------------------------------------------------------------------------

class TestTimingConstraintDialogFontFix:
    """AC-6: timing_constraint_dialog.py must use create_font(), not raw QFont()."""

    def test_no_raw_qfont_instantiation(self):
        """
        All bare QFont() calls must have been replaced by create_font()
        from styles.py (BTCAAAAA-388 acceptance criterion).
        """
        tree = _parse_ast("timing_constraint_dialog.py")
        bare_qfont_calls = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "QFont"
            ):
                bare_qfont_calls.append(node.lineno)

        assert not bare_qfont_calls, (
            f"timing_constraint_dialog.py still has bare QFont() calls at lines "
            f"{bare_qfont_calls}. These must be replaced with create_font() "
            "from styles.py (BTCAAAAA-388 fix)."
        )

    def test_create_font_imported(self):
        """create_font must be imported from styles."""
        source = _read_source("timing_constraint_dialog.py")
        assert "create_font" in source, (
            "timing_constraint_dialog.py must import and use create_font() "
            "from styles.py — raw QFont() usage has been removed."
        )

    def test_qfont_not_imported(self):
        """QFont must NOT be imported in timing_constraint_dialog.py."""
        source = _read_source("timing_constraint_dialog.py")
        assert "from PyQt5.QtGui import QFont" not in source, (
            "timing_constraint_dialog.py must not import QFont — "
            "all font creation must go through create_font() from styles.py."
        )


# ---------------------------------------------------------------------------
# AC-6: No hardcoded styles introduced
# ---------------------------------------------------------------------------

class TestNoNewHardcodedStyles:
    """AC-6: No new hardcoded color/font style strings introduced in modified files."""

    # These patterns indicate inline style hardcoding we want to catch:
    HARDCODED_STYLE_PATTERNS = [
        "color: #",      # raw hex colors
        "font-size:",     # raw font-size CSS in setStyleSheet
        "font-family:",   # raw font-family CSS in setStyleSheet
        "QFont()",        # bare QFont construction
    ]

    @pytest.mark.parametrize("filename", MODIFIED_DIALOGS)
    def test_no_new_hardcoded_font_size_in_new_lines(self, filename):
        """
        The diff introduced in commit 7f73fa3 must not add hardcoded font-size
        CSS strings.  We check the full file for QFont() specifically since
        that was the known violation in timing_constraint_dialog.py.
        """
        tree = _parse_ast(filename)
        bare_qfont_calls = [
            node.lineno
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "QFont"
            )
        ]
        assert not bare_qfont_calls, (
            f"{filename}: bare QFont() call(s) at lines {bare_qfont_calls}. "
            "Font creation must use create_font() from styles.py."
        )


# ---------------------------------------------------------------------------
# AC-5: No regressions — intact windows not modified in commit 7f73fa3
# ---------------------------------------------------------------------------

class TestNoRegressionOnExistingWindows:
    """AC-5: Verify windows that were already correct are not broken."""

    def test_log_viewer_window_maximize_hint_present(self):
        """
        log_viewer_window.py explicitly sets WindowMaximizeButtonHint —
        verify it still does so (not accidentally removed).
        """
        path = UI_DIR / "log_viewer_window.py"
        if not path.exists():
            pytest.skip("log_viewer_window.py does not exist in this branch")
        source = path.read_text()
        assert "WindowMaximizeButtonHint" in source, (
            "log_viewer_window.py: WindowMaximizeButtonHint disappeared — regression!"
        )

    def test_strategy_browser_dialog_inherits_qmainwindow(self):
        """
        StrategyBrowserDialog inherits QMainWindow which natively provides
        maximize/minimize buttons without explicit window hints.  Verify
        the class still extends QMainWindow (not accidentally changed to
        QDialog which would strip buttons).
        """
        path = UI_DIR / "strategy_browser_dialog.py"
        if not path.exists():
            pytest.skip("strategy_browser_dialog.py does not exist in this branch")
        source = path.read_text()
        assert "QMainWindow" in source, (
            "strategy_browser_dialog.py no longer extends QMainWindow — "
            "maximize/minimize may have been stripped."
        )
        # Confirm no setWindowFlags call is suppressing maximize
        # (if setWindowFlags is added with Dialog-only hints, it should be flagged)
        assert "WindowNoState" not in source, (
            "strategy_browser_dialog.py: WindowNoState flag found — "
            "this could suppress maximize."
        )


# ---------------------------------------------------------------------------
# Runtime smoke tests — instantiation without crash
# ---------------------------------------------------------------------------

class TestDialogInstantiation:
    """Smoke tests: modified dialogs must instantiate without exception."""

    def test_new_strategy_dialog_instantiates(self, qapp):
        """NewStrategyDialog must construct without raising."""
        from unittest.mock import MagicMock, patch
        mock_db = MagicMock()
        mock_db.get_all_strategies.return_value = []
        with patch(
            "src.strategy_builder.ui.new_strategy_dialog.get_database_manager",
            return_value=mock_db,
        ):
            from src.strategy_builder.ui.new_strategy_dialog import NewStrategyDialog
            dialog = NewStrategyDialog()
            assert dialog is not None
            # Verify window flags contain maximize hint
            from PyQt5.QtCore import Qt
            flags = dialog.windowFlags()
            assert flags & Qt.WindowMaximizeButtonHint, (
                "NewStrategyDialog: Qt.WindowMaximizeButtonHint not set at runtime."
            )
            assert flags & Qt.WindowMinimizeButtonHint, (
                "NewStrategyDialog: Qt.WindowMinimizeButtonHint not set at runtime."
            )
            dialog.close()

    def test_validation_dialog_instantiates(self, qapp):
        """ValidationDialog must construct without raising."""
        from unittest.mock import MagicMock, patch
        mock_orchestrator = MagicMock()
        mock_orchestrator.validate_strategy.return_value = {"valid": True, "errors": [], "warnings": []}
        with patch(
            "src.strategy_builder.ui.validation_panel.StrategyBuilderOrchestrator",
            return_value=mock_orchestrator,
        ):
            from src.strategy_builder.ui.validation_dialog import ValidationDialog
            dialog = ValidationDialog(orchestrator=mock_orchestrator)
            assert dialog is not None
            # Verify window flags contain maximize hint
            from PyQt5.QtCore import Qt
            flags = dialog.windowFlags()
            assert flags & Qt.WindowMaximizeButtonHint, (
                "ValidationDialog: Qt.WindowMaximizeButtonHint not set at runtime."
            )
            assert flags & Qt.WindowMinimizeButtonHint, (
                "ValidationDialog: Qt.WindowMinimizeButtonHint not set at runtime."
            )
            dialog.close()
