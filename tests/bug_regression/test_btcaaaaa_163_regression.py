"""
Regression tests for BTCAAAAA-163: ConfigDiscoveryResultsDialog data_provider
AttributeError + QMessageBox dark theme.

Issue: BTCAAAAA-163
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause:
1. BacktestConfigPanel.__init__ did not initialize self.data_provider before
   _on_config_discovery_clicked() accessed it, causing AttributeError.
2. QMessageBox dialogs were created without a parent widget and without
   applying MAIN_STYLESHEET, breaking dark theme consistency.

Fix:
1. Initialize self.data_provider = get_backtest_provider() in
   BacktestConfigPanel.__init__ and BacktestWorker.__init__
2. Pass self as parent to all QMessageBox dialogs + apply MAIN_STYLESHEET
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-163"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# MAIN_STYLESHEET verification
# ---------------------------------------------------------------------------


class TestMainStylesheet:
    def test_import_from_styles(self):
        from src.strategy_builder.ui.styles import MAIN_STYLESHEET

        assert MAIN_STYLESHEET is not None

    def test_is_string(self):
        from src.strategy_builder.ui.styles import MAIN_STYLESHEET

        assert isinstance(MAIN_STYLESHEET, str)

    def test_is_non_empty(self):
        from src.strategy_builder.ui.styles import MAIN_STYLESHEET

        assert len(MAIN_STYLESHEET) > 0

    def test_contains_dialog_styles(self):
        from src.strategy_builder.ui.styles import MAIN_STYLESHEET

        assert "QDialog" in MAIN_STYLESHEET

    def test_contains_widget_styles(self):
        from src.strategy_builder.ui.styles import MAIN_STYLESHEET

        assert "QMainWindow" in MAIN_STYLESHEET


# ---------------------------------------------------------------------------
# get_backtest_provider verification
# ---------------------------------------------------------------------------


class TestBacktestDataProvider:
    def test_import_get_backtest_provider(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            get_backtest_provider,
        )

        assert callable(get_backtest_provider)

    def test_import_backtest_data_provider_class(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            BacktestDataProvider,
        )

        assert BacktestDataProvider is not None

    def test_get_backtest_provider_returns_instance(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            BacktestDataProvider,
            get_backtest_provider,
        )

        provider = get_backtest_provider()
        assert isinstance(provider, BacktestDataProvider)

    def test_provider_has_load_bars_method(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            get_backtest_provider,
        )

        provider = get_backtest_provider()
        assert hasattr(provider, "load_bars_for_backtest")
        assert callable(provider.load_bars_for_backtest)

    def test_provider_has_validate_date_range_method(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            get_backtest_provider,
        )

        provider = get_backtest_provider()
        assert hasattr(provider, "validate_date_range")

    def test_provider_has_get_available_range_method(self):
        from src.optimizer_v3.core.backtest_data_provider import (
            get_backtest_provider,
        )

        provider = get_backtest_provider()
        assert hasattr(provider, "get_available_range")


# ---------------------------------------------------------------------------
# data_provider initialization in BacktestConfigPanel
# ---------------------------------------------------------------------------


class TestBacktestConfigPanelDataProvider:
    @patch(
        "src.strategy_builder.ui.backtest_config_panel.get_backtest_provider"
    )
    def test_data_provider_is_set_after_init(
        self,
        mock_get_provider,
        qapp,
    ):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )

        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        cache_path = (
            "src.optimizer_v3.core.data_cache_manager.get_data_cache_manager"
        )

        with (
            patch(cache_path, return_value=MagicMock()),
            patch.object(
                BacktestConfigPanel,
                "_init_ui",
                new=MagicMock(),
            ),
            patch.object(
                BacktestConfigPanel,
                "_auto_calculate_confluence_on_init",
                new=MagicMock(),
            ),
            patch.object(
                BacktestConfigPanel,
                "_load_calibration_disk_cache",
                new=MagicMock(),
            ),
        ):
            panel = BacktestConfigPanel(orchestrator=MagicMock())

        assert hasattr(panel, "data_provider")
        assert panel.data_provider is mock_provider

    @patch(
        "src.strategy_builder.ui.backtest_config_panel.get_backtest_provider"
    )
    def test_data_provider_not_none_after_init(
        self,
        mock_get_provider,
        qapp,
    ):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )

        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        cache_path = (
            "src.optimizer_v3.core.data_cache_manager.get_data_cache_manager"
        )

        with (
            patch(cache_path, return_value=MagicMock()),
            patch.object(
                BacktestConfigPanel,
                "_init_ui",
                new=MagicMock(),
            ),
            patch.object(
                BacktestConfigPanel,
                "_auto_calculate_confluence_on_init",
                new=MagicMock(),
            ),
            patch.object(
                BacktestConfigPanel,
                "_load_calibration_disk_cache",
                new=MagicMock(),
            ),
        ):
            panel = BacktestConfigPanel(orchestrator=MagicMock())

        assert panel.data_provider is not None


# ---------------------------------------------------------------------------
# BacktestWorker data_provider verification
# ---------------------------------------------------------------------------


class TestBacktestWorkerDataProvider:
    def test_worker_init_has_data_provider(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestWorker,
        )

        source = inspect.getsource(BacktestWorker.__init__)
        assert "data_provider" in source
        assert "get_backtest_provider" in source

    def test_worker_data_provider_set_via_init(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestWorker,
        )

        source = inspect.getsource(BacktestWorker.__init__)
        assert "self.data_provider =" in source


# ---------------------------------------------------------------------------
# QMessageBox dark theme — source code pattern verification
# ---------------------------------------------------------------------------


class TestQMessageBoxParentStylesheet:
    def _get_method_source(self, method_name: str) -> str:
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )

        method = getattr(BacktestConfigPanel, method_name, None)
        assert method is not None, f"Method {method_name} not found"
        return inspect.getsource(method)

    def test_config_discovery_qmessagebox_has_parent(self):
        source = self._get_method_source("_on_config_discovery_clicked")
        assert "QMessageBox(self)" in source, (
            "Config Discovery confirm dialog must pass self as parent"
        )

    def test_config_discovery_qmessagebox_has_stylesheet(self):
        source = self._get_method_source("_on_config_discovery_clicked")
        assert "setStyleSheet(MAIN_STYLESHEET)" in source, (
            "Config Discovery confirm dialog must apply MAIN_STYLESHEET"
        )

    def test_config_discovery_uses_qmessagebox_import(self):
        source = self._get_method_source("_on_config_discovery_clicked")
        assert "from PyQt5.QtWidgets import QMessageBox" in source, (
            "QMessageBox must be imported in the method"
        )

    def test_config_discovery_msgbox_uses_question_icon(self):
        source = self._get_method_source("_on_config_discovery_clicked")
        assert "QMessageBox.Question" in source

    def test_config_discovery_msgbox_has_yes_no_buttons(self):
        source = self._get_method_source("_on_config_discovery_clicked")
        assert "QMessageBox.Yes" in source
        assert "QMessageBox.No" in source

    def test_module_imports_main_stylesheet(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            MAIN_STYLESHEET,
        )

        assert MAIN_STYLESHEET is not None

    def test_module_imports_get_backtest_provider(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            get_backtest_provider,
        )

        assert callable(get_backtest_provider)


# ---------------------------------------------------------------------------
# Module-level import verification via AST
# ---------------------------------------------------------------------------


class TestModuleASTImports:
    def _get_module_imports(self) -> set[str]:
        module_path = (
            _REPO_ROOT
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        )
        tree = ast.parse(module_path.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.name)
        return imports

    def test_module_imports_main_stylesheet(self):
        imports = self._get_module_imports()
        assert "MAIN_STYLESHEET" in imports, (
            "MAIN_STYLESHEET must be imported at module level from styles"
        )

    def test_module_imports_get_backtest_provider(self):
        imports = self._get_module_imports()
        assert "get_backtest_provider" in imports, (
            "get_backtest_provider must be imported at module level"
        )
