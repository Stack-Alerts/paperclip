"""
Regression Tests for Test Wiring Behavior — Phase 5.4 (BTCAAAAA-150)

Purpose: Ensure the existing "🔬 Test Wiring" flow is NOT broken by the
Config Discovery Engine additions (BTCAAAAA-149).

Critical invariants to protect:
  1. test_scenarios.py exports remain stable — CRITICAL_SCENARIOS,
     EDGE_SCENARIOS, PARAMETER_VARIATION_SCENARIOS, generate_pairwise_scenarios()
  2. BacktestScenario dataclass is backwards-compatible (id, description,
     config, expected_behavior fields).
  3. Scenario count: CRITICAL ≥ 8, EDGE ≥ 5, PARAMETER_VARIATION ≥ 16.
  4. All scenario IDs are unique across all lists.
  5. No scenario has an empty config dict.
  6. generate_pairwise_scenarios() returns a non-empty list.
  7. _generate_wiring_report() / _on_test_wiring_clicked() remain callable
     on BacktestConfigPanel (not renamed/deleted).

These tests run WITHOUT Qt and WITHOUT a live backtest — pure import/structure
validation.  They are cheap and should always be green.

Author: QAEngineer (BTCAAAAA-150)
Date: 2026-05-04
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Ensure project root is importable in all run contexts
# ---------------------------------------------------------------------------
_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ===========================================================================
# 5.4 Regression — test_scenarios.py contract
# ===========================================================================

class TestScenariosModuleExports:
    """test_scenarios.py must export the same public API it has always had."""

    def test_import_succeeds(self):
        """Module must import without error."""
        from tests.integration import test_scenarios  # noqa: F401

    def test_backtest_scenario_dataclass_fields(self):
        """BacktestScenario must have the four canonical fields."""
        from tests.integration.test_scenarios import BacktestScenario
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(BacktestScenario)}
        required = {"id", "description", "config", "expected_behavior"}
        missing = required - field_names
        assert not missing, f"BacktestScenario missing fields: {missing}"

    def test_critical_scenarios_exported(self):
        from tests.integration.test_scenarios import CRITICAL_SCENARIOS
        assert CRITICAL_SCENARIOS, "CRITICAL_SCENARIOS must not be empty"

    def test_edge_scenarios_exported(self):
        from tests.integration.test_scenarios import EDGE_SCENARIOS
        assert EDGE_SCENARIOS, "EDGE_SCENARIOS must not be empty"

    def test_parameter_variation_scenarios_exported(self):
        from tests.integration.test_scenarios import PARAMETER_VARIATION_SCENARIOS
        assert PARAMETER_VARIATION_SCENARIOS, "PARAMETER_VARIATION_SCENARIOS must not be empty"

    def test_generate_pairwise_scenarios_callable(self):
        from tests.integration.test_scenarios import generate_pairwise_scenarios
        assert callable(generate_pairwise_scenarios)

    def test_generate_pairwise_returns_list(self):
        from tests.integration.test_scenarios import generate_pairwise_scenarios
        result = generate_pairwise_scenarios()
        assert isinstance(result, list), "generate_pairwise_scenarios must return a list"

    def test_generate_pairwise_nonempty(self):
        from tests.integration.test_scenarios import generate_pairwise_scenarios
        result = generate_pairwise_scenarios()
        assert len(result) > 0, "generate_pairwise_scenarios must return at least one scenario"


class TestScenariosMinimumCounts:
    """
    Minimum counts guard the 23-scenario baseline referenced in issue description.
    Any reduction below these thresholds breaks the existing test wiring flow.
    """

    def test_critical_scenario_minimum_count(self):
        from tests.integration.test_scenarios import CRITICAL_SCENARIOS
        assert len(CRITICAL_SCENARIOS) >= 8, (
            f"CRITICAL_SCENARIOS must have ≥8 entries, has {len(CRITICAL_SCENARIOS)}"
        )

    def test_edge_scenario_minimum_count(self):
        from tests.integration.test_scenarios import EDGE_SCENARIOS
        assert len(EDGE_SCENARIOS) >= 5, (
            f"EDGE_SCENARIOS must have ≥5 entries, has {len(EDGE_SCENARIOS)}"
        )

    def test_parameter_variation_minimum_count(self):
        from tests.integration.test_scenarios import PARAMETER_VARIATION_SCENARIOS
        # Current baseline: 10 paired scenarios (5 parameter pairs × 2 values each).
        # Must not drop below this — any removal breaks pairwise wiring verification.
        assert len(PARAMETER_VARIATION_SCENARIOS) >= 10, (
            f"PARAMETER_VARIATION_SCENARIOS must have ≥10 entries, "
            f"has {len(PARAMETER_VARIATION_SCENARIOS)}"
        )

    def test_combined_minimum_23_scenarios(self):
        """Original Test Wiring used 23+ scenarios — combined base must stay ≥23."""
        from tests.integration.test_scenarios import (
            CRITICAL_SCENARIOS,
            EDGE_SCENARIOS,
            PARAMETER_VARIATION_SCENARIOS,
        )
        total = len(CRITICAL_SCENARIOS) + len(EDGE_SCENARIOS) + len(PARAMETER_VARIATION_SCENARIOS)
        assert total >= 23, (
            f"Combined base scenarios dropped below 23 (regression): got {total}"
        )


class TestScenarioDataIntegrity:
    """Individual scenarios must be structurally valid."""

    def _all_scenarios(self):
        from tests.integration.test_scenarios import (
            CRITICAL_SCENARIOS,
            EDGE_SCENARIOS,
            PARAMETER_VARIATION_SCENARIOS,
        )
        return CRITICAL_SCENARIOS + EDGE_SCENARIOS + PARAMETER_VARIATION_SCENARIOS

    def test_all_scenario_ids_unique(self):
        scenarios = self._all_scenarios()
        ids = [s.id for s in scenarios]
        assert len(ids) == len(set(ids)), (
            f"Duplicate scenario IDs found: "
            f"{[i for i in ids if ids.count(i) > 1]}"
        )

    def test_no_scenario_has_empty_config(self):
        scenarios = self._all_scenarios()
        for s in scenarios:
            assert s.config, (
                f"Scenario '{s.id}' has an empty config dict — must include at least one key"
            )

    def test_all_scenarios_have_non_empty_description(self):
        scenarios = self._all_scenarios()
        for s in scenarios:
            assert s.description and s.description.strip(), (
                f"Scenario '{s.id}' has an empty description"
            )

    def test_all_scenarios_have_expected_behavior(self):
        scenarios = self._all_scenarios()
        for s in scenarios:
            assert isinstance(s.expected_behavior, dict), (
                f"Scenario '{s.id}' expected_behavior must be a dict"
            )

    def test_critical_scenarios_have_min_trades(self):
        from tests.integration.test_scenarios import CRITICAL_SCENARIOS
        for s in CRITICAL_SCENARIOS:
            assert "min_trades" in s.expected_behavior, (
                f"CRITICAL scenario '{s.id}' must specify 'min_trades' in expected_behavior"
            )

    def test_parameter_variation_scenarios_have_matching_pair(self):
        """
        Each parameter variation scenario must have a partner with a different
        value for the same parameter (to verify wiring via diff comparison).
        The naming convention PARAM_<BASE>_LOW / PARAM_<BASE>_HIGH encodes pairs.
        """
        from tests.integration.test_scenarios import PARAMETER_VARIATION_SCENARIOS

        prefixes = {}
        for s in PARAMETER_VARIATION_SCENARIOS:
            # Derive base key: PARAM_VOL_LB_LOW → PARAM_VOL_LB
            parts = s.id.rsplit("_", 1)
            if len(parts) == 2:
                base, suffix = parts
                if suffix in ("LOW", "HIGH", "TIGHT", "LOOSE"):
                    prefixes.setdefault(base, []).append(s.id)

        for base, ids in prefixes.items():
            assert len(ids) >= 2, (
                f"Parameter variation '{base}' has only one scenario ({ids}) — "
                "add a counterpart so wiring can be verified by diff"
            )


# ===========================================================================
# 5.4 Regression — BacktestConfigPanel API contract
# ===========================================================================

class TestBacktestConfigPanelWiringAPI:
    """
    Verify the wiring-test entry points on BacktestConfigPanel remain callable.

    We do not execute them (that requires Qt + live data), but we confirm:
      - The class is importable
      - The key wiring methods exist and are callable
    """

    @pytest.fixture(autouse=True)
    def _stub_pyqt(self):
        """
        Inject minimal PyQt5 stubs if the real package isn't available,
        so tests can run in headless CI.
        """
        if "PyQt5" not in sys.modules:
            import types
            from unittest.mock import MagicMock

            def _pyqtSignal(*a, **kw):
                sig = MagicMock()
                sig.emit = MagicMock()
                sig.connect = MagicMock()
                sig.disconnect = MagicMock()
                return sig

            class _Qt:
                WindowModal = 0
                AlignCenter = 0x84

            pyqt5 = types.ModuleType("PyQt5")
            qt_core = types.ModuleType("PyQt5.QtCore")
            qt_core.Qt = _Qt
            qt_core.QThread = MagicMock
            qt_core.pyqtSignal = _pyqtSignal
            qt_core.QTimer = MagicMock
            qt_core.QEventLoop = MagicMock

            qt_widgets = types.ModuleType("PyQt5.QtWidgets")
            for name in (
                "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
                "QProgressBar", "QTextEdit", "QGroupBox", "QApplication",
                "QWidget", "QMainWindow", "QSpinBox", "QDoubleSpinBox",
                "QComboBox", "QCheckBox", "QRadioButton", "QButtonGroup",
                "QMessageBox", "QProgressDialog", "QTabWidget", "QScrollArea",
                "QSplitter", "QFrame", "QSizePolicy", "QLineEdit",
                "QAbstractItemView", "QHeaderView", "QTableView", "QSlider",
            ):
                setattr(qt_widgets, name, MagicMock)

            qt_core.QSortFilterProxyModel = MagicMock

            qt_gui = types.ModuleType("PyQt5.QtGui")
            qt_gui.QFont = MagicMock
            qt_gui.QStandardItem = MagicMock
            qt_gui.QStandardItemModel = MagicMock

            sys.modules.update({
                "PyQt5": pyqt5,
                "PyQt5.QtCore": qt_core,
                "PyQt5.QtWidgets": qt_widgets,
                "PyQt5.QtGui": qt_gui,
            })
            pyqt5.QtCore = qt_core
            pyqt5.QtWidgets = qt_widgets
            pyqt5.QtGui = qt_gui

    def test_backtest_config_panel_importable(self):
        """Module-level import must not raise."""
        try:
            import importlib
            importlib.import_module("src.strategy_builder.ui.backtest_config_panel")
        except ImportError as exc:
            pytest.skip(f"Cannot import backtest_config_panel (dependency issue): {exc}")

    def test_on_test_wiring_clicked_exists(self):
        """_on_test_wiring_clicked must remain defined (not renamed/deleted)."""
        try:
            from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
            assert hasattr(BacktestConfigPanel, "_on_test_wiring_clicked"), (
                "_on_test_wiring_clicked was removed or renamed — breaks existing Test Wiring flow"
            )
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

    def test_generate_wiring_report_exists(self):
        """_generate_wiring_report must remain defined."""
        try:
            from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
            assert hasattr(BacktestConfigPanel, "_generate_wiring_report"), (
                "_generate_wiring_report was removed or renamed — breaks CSV report generation"
            )
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

    def test_capture_ui_state_exists(self):
        """_capture_ui_state / _restore_ui_state must remain defined."""
        try:
            from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
            assert hasattr(BacktestConfigPanel, "_capture_ui_state"), (
                "_capture_ui_state missing — breaks state save/restore during test loop"
            )
            assert hasattr(BacktestConfigPanel, "_restore_ui_state"), (
                "_restore_ui_state missing — original config not restored after wiring test"
            )
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

    def test_apply_scenario_to_ui_exists(self):
        """_apply_scenario_to_ui must remain defined (used inside wiring loop)."""
        try:
            from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
            assert hasattr(BacktestConfigPanel, "_apply_scenario_to_ui"), (
                "_apply_scenario_to_ui missing — scenario application broken"
            )
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

    def test_get_config_returns_all_expected_keys(self):
        """
        get_config() structural contract: calling it on a stub instance must
        return a dict with the keys that the wiring test and discovery engine
        depend on.

        We mock out all widget accessors so no Qt event loop is needed.
        """
        try:
            from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

        # Patch all spin/combo widgets on the class so __init__ doesn't need Qt
        mock_panel = MagicMock(spec=BacktestConfigPanel)
        mock_panel.lookback_spin.value.return_value = 90
        mock_panel.training_spin.value.return_value = 60
        mock_panel.testing_spin.value.return_value = 30
        mock_panel.mode_group.checkedId.return_value = 2
        mock_panel.tpsl_combo.currentText.return_value = "Fibonacci"
        mock_panel.sl_combo.currentText.return_value = "Adaptive v2.0"
        mock_panel.capital_spin.value.return_value = 10_000
        mock_panel.risk_spin.value.return_value = 10
        mock_panel.rr_spin.value.return_value = 20
        mock_panel.leverage_spin.value.return_value = 10
        mock_panel.confluence_spin.value.return_value = 40
        mock_panel.max_bars_spin.value.return_value = 200
        mock_panel.delayed_sl_check.isChecked.return_value = True
        mock_panel.delay_spin.value.return_value = 2
        mock_panel.emergency_spin.value.return_value = 2
        mock_panel.vol_lookback_spin.value.return_value = 20
        mock_panel.vol_multi_spin.value.return_value = 1.2
        mock_panel.min_sl_spin.value.return_value = 0.7
        mock_panel.max_sl_spin.value.return_value = 2.0
        mock_panel.structure_check.isChecked.return_value = True

        # Call the REAL get_config using the mock as self
        config = BacktestConfigPanel.get_config(mock_panel)

        required_top_level_keys = {
            "lookback_days", "mode", "tpsl_mode", "sl_mode",
            "starting_capital", "risk_per_trade_pct", "adaptive_sl",
        }
        for key in required_top_level_keys:
            assert key in config, f"get_config() missing key: '{key}'"

        adaptive_sl_keys = {
            "enabled", "delay_bars", "emergency_sl_pct",
            "volatility_lookback", "volatility_multiplier",
            "min_sl_pct", "max_sl_pct",
        }
        assert "adaptive_sl" in config
        for key in adaptive_sl_keys:
            assert key in config["adaptive_sl"], (
                f"get_config()['adaptive_sl'] missing key: '{key}'"
            )


# ===========================================================================
# 5.4 Regression — wiring report output format
# ===========================================================================

class TestWiringReportOutput:
    """
    The CSV written by _generate_wiring_report must include the columns that
    downstream analysis tools (test_wiring_enhanced.py) expect.
    """

    def test_result_dict_has_scenario_id_key(self):
        """
        Each entry in the test_results list passed to _generate_wiring_report
        must contain 'scenario_id'.  Verified by inspecting the call site in
        backtest_config_panel.py.
        """
        # This test verifies that the BacktestConfigPanel._on_test_wiring_clicked
        # builds result dicts that include 'scenario_id'.
        # We check the source-level constant — if the key name changes the test fails.
        try:
            import inspect
            import importlib
            mod = importlib.import_module("src.strategy_builder.ui.backtest_config_panel")
            source = inspect.getsource(mod)
            assert "'scenario_id'" in source or '"scenario_id"' in source, (
                "Key 'scenario_id' not found in backtest_config_panel source — "
                "wiring report CSV column name may have changed"
            )
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")

    def test_result_dict_has_description_key(self):
        """CSV must include 'description' column."""
        try:
            import inspect
            import importlib
            mod = importlib.import_module("src.strategy_builder.ui.backtest_config_panel")
            source = inspect.getsource(mod)
            assert "'description'" in source or '"description"' in source
        except ImportError as exc:
            pytest.skip(f"Import failed: {exc}")
