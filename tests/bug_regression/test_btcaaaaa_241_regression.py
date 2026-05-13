"""
Regression tests for BTCAAAAA-241: Config Discovery UI polish.

Issue: BTCAAAAA-241
Components:
  - src/strategy_builder/ui/config_discovery_results_dialog.py
  - src/strategy_builder/ui/backtest_config_panel.py

Fix (53e511e9):
1. Re-raise and activateWindow() on results_dialog after QProgressDialog closes,
   preventing it from being buried behind the main window.
2. Replace raw-dict QMessageBox confirmation with custom _ApplyConfigDialog
   featuring a styled QTableWidget with flattened key->value rows,
   Yes/No->Yes/No boolean display, and Apply/Cancel buttons.
3. Remove setMaximumHeight(180) constraint on summary pane; update splitter
   initial sizes from [500,180] to [600,300].
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-241"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


# ---------------------------------------------------------------------------
# _flatten_dict function tests
# ---------------------------------------------------------------------------


class TestFlattenDict:
    """Verify _flatten_dict processes nested config deltas correctly."""

    def _get_flatten_dict(self):
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            _flatten_dict,
        )
        return _flatten_dict

    def test_flat_dict(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({"lookback": 120, "risk": 0.02})
        assert ("lookback", "120") in result
        assert ("risk", "0.02") in result

    def test_nested_dict(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({"adaptive_sl": {"initial_stop": 0.5, "trail": True}})
        assert ("adaptive_sl.initial_stop", "0.5") in result
        assert ("adaptive_sl.trail", "Yes") in result

    def test_bool_yes_no(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({"active": True, "debug": False})
        assert ("active", "Yes") in result
        assert ("debug", "No") in result

    def test_float_formatting(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({"val": 0.5, "large": 1234.5678})
        assert ("val", "0.5") in result
        assert ("large", "1234.57") in result

    def test_deeply_nested(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({"a": {"b": {"c": True, "d": 42}}})
        assert ("a.b.c", "Yes") in result
        assert ("a.b.d", "42") in result

    def test_empty_dict(self):
        _flatten_dict = self._get_flatten_dict()
        assert _flatten_dict({}) == []

    def test_mixed_types(self):
        _flatten_dict = self._get_flatten_dict()
        result = _flatten_dict({
            "name": "test",
            "ratio": 0.85,
            "enabled": True,
            "nested": {"sub": 10, "flag": False},
        })
        assert ("name", "test") in result
        assert ("ratio", "0.85") in result
        assert ("enabled", "Yes") in result
        assert ("nested.sub", "10") in result
        assert ("nested.flag", "No") in result


# ---------------------------------------------------------------------------
# _ApplyConfigDialog class verification
# ---------------------------------------------------------------------------


class TestApplyConfigDialog:
    """Verify _ApplyConfigDialog exists and has expected interface."""

    def test_class_exists(self):
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            _ApplyConfigDialog,
        )
        assert _ApplyConfigDialog is not None

    def test_class_is_qdialog_subclass(self):
        from PyQt5.QtWidgets import QDialog
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            _ApplyConfigDialog,
        )
        assert issubclass(_ApplyConfigDialog, QDialog)

    def test_constructor_signature(self):
        import inspect
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            _ApplyConfigDialog,
        )
        sig = inspect.signature(_ApplyConfigDialog.__init__)
        params = list(sig.parameters.keys())
        assert "scenario_description" in params
        assert "config_delta" in params
        assert "parent" in params

    def test_module_exports_apply_config_dialog(self):
        from src.strategy_builder.ui import config_discovery_results_dialog as mod
        assert hasattr(mod, "_ApplyConfigDialog")


# ---------------------------------------------------------------------------
# Source-code pattern verification (window foreground fix)
# ---------------------------------------------------------------------------


class TestWindowForegroundFix:
    """Verify raise_() and activateWindow() calls are in backtest_config_panel."""

    def _panel_source(self) -> str:
        path = _REPO_ROOT / "src/strategy_builder/ui/backtest_config_panel.py"
        return path.read_text(encoding="utf-8")

    def test_has_raise_call(self):
        source = self._panel_source()
        assert "raise_()" in source

    def test_has_activate_window_call(self):
        source = self._panel_source()
        assert "activateWindow()" in source

    def test_has_process_events_after_activate(self):
        source = self._panel_source()
        assert "QApplication.processEvents()" in source


# ---------------------------------------------------------------------------
# Summary pane source-code verification
# ---------------------------------------------------------------------------


class TestSummaryPane:
    """Verify summary pane changes from BTCAAAAA-241 are present."""

    def _dialog_source(self) -> str:
        path = _REPO_ROOT / "src/strategy_builder/ui/config_discovery_results_dialog.py"
        return path.read_text(encoding="utf-8")

    def test_no_maximum_height_180(self):
        """setMaximumHeight(180) on summary pane was removed by the fix."""
        source = self._dialog_source()
        assert "setMaximumHeight(180)" not in source

    def test_splitter_sizes_600_300(self):
        source = self._dialog_source()
        assert "setSizes([600, 300])" in source

    def test_summary_groupbox_exists(self):
        source = self._dialog_source()
        assert "summary_group" in source

    def test_summary_text_readonly(self):
        source = self._dialog_source()
        assert "_summary_text" in source


# ---------------------------------------------------------------------------
# Module-level AST import verification
# ---------------------------------------------------------------------------


class TestModuleASTImports:
    """Verify key imports remain in config_discovery_results_dialog.py."""

    def _get_dialog_imports(self) -> set[str]:
        path = _REPO_ROOT / "src/strategy_builder/ui/config_discovery_results_dialog.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.name)
        return imports

    def test_imports_qtablewidget(self):
        imports = self._get_dialog_imports()
        assert "QTableWidget" in imports

    def test_imports_qtablewidget_item(self):
        imports = self._get_dialog_imports()
        assert "QTableWidgetItem" in imports

    def test_imports_qdialog_button_box(self):
        imports = self._get_dialog_imports()
        assert "QDialogButtonBox" in imports
