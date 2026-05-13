"""
Regression tests for BTCAAAAA-255: About dialog layout fix (free-floating QDialog).

Issue: BTCAAAAA-255
Components:
  - src/strategy_builder/ui/strategy_builder_main_window.py (_on_about)
  - archived/utils_strategy_builder_legacy/qt_gui/main_window.py (show_about)

Fix: Replace QMessageBox.about() with a free-floating QDialog() that is:
  1. Free-floating (no parent) — not locked to main window position
  2. Wider (>=600px) — improved readability vs old ~400px default
  3. Content-fitted (<=500px tall) — not oversized
  4. Contains proper title, content, and Close button

All tests are static AST/text scans — no Qt event loop required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-255"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SBMW_PATH = (
    REPO_ROOT
    / "src"
    / "strategy_builder"
    / "ui"
    / "strategy_builder_main_window.py"
)
QTGUI_MW_PATH = (
    REPO_ROOT
    / "archived"
    / "utils_strategy_builder_legacy"
    / "qt_gui"
    / "main_window.py"
)


def _get_on_about_source() -> str:
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
        if not line.strip():
            method_lines.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and line.strip():
            break
        method_lines.append(line)
    return "\n".join(method_lines)


def _get_show_about_source() -> str:
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


class TestAboutDialogStaticChecksSBMW:
    """Static AST/text checks on strategy_builder_main_window._on_about — no Qt display required."""

    def test_sbmw_no_qmessagebox_about_call(self):
        src = _get_on_about_source()
        assert "QMessageBox.about" not in src

    def test_sbmw_uses_qdialog_no_parent(self):
        src = _get_on_about_source()
        assert "QDialog()" in src

    def test_sbmw_resize_wider_than_600(self):
        src = _get_on_about_source()
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches
        width = int(matches[0][0])
        assert width >= 600

    def test_sbmw_resize_shorter_than_500(self):
        src = _get_on_about_source()
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches
        height = int(matches[0][1])
        assert height <= 500

    def test_sbmw_window_title(self):
        src = _get_on_about_source()
        assert "About BTC Trade Engine" in src

    def test_sbmw_content_platform_description(self):
        src = _get_on_about_source()
        assert "NautilusTrader" in src

    def test_sbmw_content_capabilities_list(self):
        src = _get_on_about_source()
        assert "Walk-forward" in src or "walk-forward" in src
        assert "NautilusTrader execution" in src or "execution engine" in src.lower()

    def test_sbmw_content_institutional_footer(self):
        src = _get_on_about_source()
        assert "2026" in src
        assert "BTC Trade Engine" in src

    def test_sbmw_has_close_button(self):
        src = _get_on_about_source()
        assert "QPushButton" in src
        assert "Close" in src

    def test_sbmw_has_qt_browser(self):
        src = _get_on_about_source()
        assert "QTextBrowser" in src

    def test_sbmw_sets_stylesheet(self):
        src = _get_on_about_source()
        assert "setStyleSheet" in src or "stylesheet" in src.lower()


class TestAboutDialogStaticChecksQTGUI:
    """Static AST/text checks on qt_gui main_window.show_about — no Qt display required."""

    def test_qtgui_no_qmessagebox_about_call(self):
        src = _get_show_about_source()
        assert "QMessageBox.about" not in src

    def test_qtgui_uses_qdialog_no_parent(self):
        src = _get_show_about_source()
        assert "QDialog()" in src

    def test_qtgui_resize_wider_than_600(self):
        src = _get_show_about_source()
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches
        width = int(matches[0][0])
        assert width >= 600

    def test_qtgui_resize_shorter_than_500(self):
        src = _get_show_about_source()
        matches = re.findall(r"resize\(\s*(\d+)\s*,\s*(\d+)\s*\)", src)
        assert matches
        height = int(matches[0][1])
        assert height <= 500

    def test_qtgui_window_title(self):
        src = _get_show_about_source()
        assert "About Strategy Builder" in src

    def test_qtgui_content_strategy_builder_version(self):
        src = _get_show_about_source()
        assert "Strategy Builder v3.0" in src

    def test_qtgui_content_features_list(self):
        src = _get_show_about_source()
        assert "building blocks" in src

    def test_qtgui_content_footer_copyright(self):
        src = _get_show_about_source()
        assert "2026" in src
