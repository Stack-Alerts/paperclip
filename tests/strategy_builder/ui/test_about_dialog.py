"""
Tests for the About dialog layout fix — BTCAAAAA-255 / BTCAAAAA-256 QA coverage.

Verifies:
1. Dialog is a QDialog (not QMessageBox) — free-floating, no parent lock.
2. Dialog width is ≥ 600px (wider than the old QMessageBox default ~400px).
3. Dialog height is ≤ 500px (shorter than the old QMessageBox default).
4. Window title is set correctly.
5. All required content is present (platform description, capabilities list,
   institutional footer).
6. No QMessageBox.about() call exists anywhere in the _on_about / show_about
   implementations (static AST check).
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialog, QTextBrowser, QPushButton

# ---------------------------------------------------------------------------
# QApplication singleton fixture (module-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
SBMW_PATH = REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py"
QTGUI_MW_PATH = REPO_ROOT / "src" / "utils" / "Strategy_Builder" / "qt_gui" / "main_window.py"


# ---------------------------------------------------------------------------
# Helper: parse _on_about source from strategy_builder_main_window.py
# ---------------------------------------------------------------------------

def _get_on_about_source() -> str:
    """Extract the _on_about method body as source text."""
    src = SBMW_PATH.read_text(encoding="utf-8")
    lines = src.splitlines()
    method_lines: list[str] = []
    in_method = False
    base_indent: int | None = None

    for line in lines:
        if not in_method:
            stripped = line.lstrip()
            if stripped.startswith("def _on_about("):
                in_method = True
                base_indent = len(line) - len(stripped)
                method_lines.append(line)
            continue

        # Still collecting lines of the method
        if not line.strip():
            method_lines.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and line.strip():
            # Next method/class at same or lower indentation — stop
            break
        method_lines.append(line)

    return "\n".join(method_lines)


def _get_show_about_source() -> str:
    """Extract the show_about method body from qt_gui/main_window.py."""
    src = QTGUI_MW_PATH.read_text(encoding="utf-8")
    lines = src.splitlines()
    method_lines: list[str] = []
    in_method = False
    base_indent: int | None = None

    for line in lines:
        if not in_method:
            stripped = line.lstrip()
            if stripped.startswith("def show_about("):
                in_method = True
                base_indent = len(line) - len(stripped)
                method_lines.append(line)
            continue

        if not line.strip():
            method_lines.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and line.strip():
            break
        method_lines.append(line)

    return "\n".join(method_lines)


# ===========================================================================
# Static source-code checks (no Qt required)
# ===========================================================================

class TestAboutDialogStaticChecks:
    """AST / source-text checks — no display required."""

    def test_sbmw_no_qmessagebox_about_call(self):
        """_on_about must NOT call QMessageBox.about()."""
        src = _get_on_about_source()
        assert "QMessageBox.about" not in src, (
            "strategy_builder_main_window._on_about still uses QMessageBox.about() "
            "— centering lock not removed"
        )

    def test_qtgui_no_qmessagebox_about_call(self):
        """show_about (qt_gui) must NOT call QMessageBox.about()."""
        src = _get_show_about_source()
        assert "QMessageBox.about" not in src, (
            "qt_gui/main_window.show_about still uses QMessageBox.about() "
            "— centering lock not removed"
        )

    def test_sbmw_uses_qdialog_no_parent(self):
        """_on_about must create QDialog() with no parent (free-floating)."""
        src = _get_on_about_source()
        assert "QDialog()" in src, (
            "_on_about must use QDialog() with no parent argument to be free-floating"
        )

    def test_qtgui_uses_qdialog_no_parent(self):
        """show_about must create QDialog() with no parent (free-floating)."""
        src = _get_show_about_source()
        assert "QDialog()" in src, (
            "qt_gui show_about must use QDialog() with no parent argument to be free-floating"
        )

    def test_sbmw_resize_wider_than_500(self):
        """_on_about must resize dialog to width ≥ 600px."""
        src = _get_on_about_source()
        # Look for resize(W, H) call — width must be ≥ 600
        import re
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches, "_on_about must call dialog.resize(width, height)"
        width = int(matches[0][0])
        assert width >= 600, (
            f"About dialog width {width}px is too narrow — must be ≥ 600px"
        )

    def test_sbmw_resize_shorter_than_500(self):
        """_on_about must resize dialog to height ≤ 500px (content-fitted)."""
        src = _get_on_about_source()
        import re
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches, "_on_about must call dialog.resize(width, height)"
        height = int(matches[0][1])
        assert height <= 500, (
            f"About dialog height {height}px is too tall — must be ≤ 500px"
        )

    def test_qtgui_resize_wider_than_500(self):
        """show_about (qt_gui) must resize dialog to width ≥ 600px."""
        src = _get_show_about_source()
        import re
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches, "qt_gui show_about must call dialog.resize(width, height)"
        width = int(matches[0][0])
        assert width >= 600, (
            f"qt_gui About dialog width {width}px is too narrow — must be ≥ 600px"
        )

    def test_qtgui_resize_shorter_than_500(self):
        """show_about (qt_gui) must resize dialog to height ≤ 500px."""
        src = _get_show_about_source()
        import re
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches, "qt_gui show_about must call dialog.resize(width, height)"
        height = int(matches[0][1])
        assert height <= 500, (
            f"qt_gui About dialog height {height}px is too tall — must be ≤ 500px"
        )

    # --- Content checks on strategy_builder_main_window._on_about ---

    def test_sbmw_content_platform_description(self):
        """_on_about HTML content must mention NautilusTrader."""
        src = _get_on_about_source()
        assert "NautilusTrader" in src, (
            "About dialog must mention NautilusTrader in content"
        )

    def test_sbmw_content_capabilities_list(self):
        """_on_about content must include key capabilities."""
        src = _get_on_about_source()
        assert "Walk-forward" in src or "walk-forward" in src, (
            "Capabilities list must mention walk-forward backtesting"
        )
        assert "NautilusTrader execution" in src or "execution engine" in src.lower(), (
            "Capabilities list must mention NautilusTrader execution engine"
        )

    def test_sbmw_content_institutional_footer(self):
        """_on_about must have institutional footer with copyright."""
        src = _get_on_about_source()
        assert "2026" in src, "About dialog footer must include year 2026"
        assert "BTC Trade Engine" in src, (
            "About dialog footer must mention BTC Trade Engine"
        )

    def test_sbmw_window_title(self):
        """_on_about must set window title to 'About BTC Trade Engine'."""
        src = _get_on_about_source()
        assert "About BTC Trade Engine" in src, (
            "About dialog window title must be 'About BTC Trade Engine'"
        )

    # --- Content checks on qt_gui show_about ---

    def test_qtgui_content_strategy_builder_version(self):
        """show_about (qt_gui) must mention Strategy Builder v3.0."""
        src = _get_show_about_source()
        assert "Strategy Builder v3.0" in src, (
            "qt_gui About dialog must mention 'Strategy Builder v3.0'"
        )

    def test_qtgui_content_features_list(self):
        """show_about (qt_gui) must list building blocks."""
        src = _get_show_about_source()
        assert "building blocks" in src, (
            "qt_gui About dialog must mention building blocks"
        )

    def test_qtgui_content_footer_copyright(self):
        """show_about (qt_gui) must include copyright year."""
        src = _get_show_about_source()
        assert "2026" in src, "qt_gui About dialog footer must include year 2026"

    def test_qtgui_window_title(self):
        """show_about (qt_gui) must set window title to 'About Strategy Builder'."""
        src = _get_show_about_source()
        assert "About Strategy Builder" in src, (
            "qt_gui About dialog window title must be 'About Strategy Builder'"
        )


# ===========================================================================
# Runtime Qt widget checks (requires QApplication)
# ===========================================================================

class TestAboutDialogRuntime:
    """Instantiate _on_about with exec_() mocked to avoid blocking."""

    def test_sbmw_dialog_is_qdialog_instance(self, qapp):
        """_on_about must create a QDialog instance (not a QMessageBox)."""
        captured: list[QDialog] = []

        original_exec = QDialog.exec_

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0  # do not block

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                # Build a minimal mock window — no real main window needed
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert len(captured) == 1, "_on_about must open exactly one dialog"
        assert isinstance(captured[0], QDialog), (
            f"_on_about opened a {type(captured[0]).__name__} instead of a QDialog"
        )

    def test_sbmw_dialog_geometry(self, qapp):
        """About dialog from _on_about must be ≥600px wide and ≤500px tall."""
        captured: list[QDialog] = []

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert captured, "No dialog was captured"
        dlg = captured[0]
        sz = dlg.size()
        assert sz.width() >= 600, (
            f"About dialog width {sz.width()}px is too narrow — must be ≥ 600px"
        )
        assert sz.height() <= 500, (
            f"About dialog height {sz.height()}px is too tall — must be ≤ 500px"
        )

    def test_sbmw_dialog_has_no_parent(self, qapp):
        """About dialog must be free-floating (parent() is None)."""
        captured: list[QDialog] = []

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert captured, "No dialog was captured"
        dlg = captured[0]
        assert dlg.parent() is None, (
            "About dialog has a parent — it is NOT free-floating. "
            "Use QDialog() with no parent argument."
        )

    def test_sbmw_dialog_window_title(self, qapp):
        """About dialog window title must be 'About BTC Trade Engine'."""
        captured: list[QDialog] = []

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert captured, "No dialog was captured"
        assert captured[0].windowTitle() == "About BTC Trade Engine", (
            f"Unexpected window title: '{captured[0].windowTitle()}'"
        )

    def test_sbmw_dialog_contains_text_browser(self, qapp):
        """About dialog must contain a QTextBrowser for content display."""
        captured: list[QDialog] = []

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert captured, "No dialog was captured"
        dlg = captured[0]
        browsers = dlg.findChildren(QTextBrowser)
        assert browsers, "About dialog must contain a QTextBrowser for content"

    def test_sbmw_dialog_contains_close_button(self, qapp):
        """About dialog must have a Close button."""
        captured: list[QDialog] = []

        def _mock_exec(self_dialog):
            captured.append(self_dialog)
            return 0

        with patch.object(QDialog, "exec_", _mock_exec):
            with patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_main_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_dialog_stylesheet",
                return_value=""
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.create_font",
                return_value=QFont()
            ), patch(
                "src.strategy_builder.ui.strategy_builder_main_window.get_primary_button_stylesheet",
                return_value=""
            ):
                from src.strategy_builder.ui.strategy_builder_main_window import (
                    StrategyBuilderMainWindow,
                )
                win = StrategyBuilderMainWindow.__new__(StrategyBuilderMainWindow)
                win._on_about()

        assert captured, "No dialog was captured"
        dlg = captured[0]
        buttons = dlg.findChildren(QPushButton)
        close_buttons = [b for b in buttons if "close" in b.text().lower()]
        assert close_buttons, (
            "About dialog must have a 'Close' button; "
            f"found buttons: {[b.text() for b in buttons]}"
        )
