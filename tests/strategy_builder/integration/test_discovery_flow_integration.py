"""
Integration Tests for Config Discovery Engine — Full Discovery Flow (Phase 5.3)

Tests the end-to-end discovery pipeline:
  1. ConfigPermutationEngine.build_scenarios() generates N scenario configs.
  2. Each scenario is executed via a (mocked) backtest worker.
  3. aggregate_metrics() produces DiscoveryResult per scenario.
  4. Results are ranked and surfaced to the UI.

The MulticoreBacktestEngine is mocked so these tests run without NautilusTrader
data or a live display.  They verify wiring and interface contracts only.

Author: QAEngineer (BTCAAAAA-150)
Date: 2026-05-04
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub PyQt5 before any engine import
# ---------------------------------------------------------------------------
def _ensure_pyqt5_stubs():
    import importlib.util
    if importlib.util.find_spec("PyQt5") is not None:
        return  # real PyQt5 available — do not inject stubs
    if "PyQt5" in sys.modules:
        return
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
    qt_core.QSortFilterProxyModel = MagicMock

    qt_widgets = types.ModuleType("PyQt5.QtWidgets")
    for name in (
        "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
        "QProgressBar", "QTextEdit", "QGroupBox", "QApplication",
        "QWidget", "QMainWindow", "QSpinBox", "QDoubleSpinBox",
        "QComboBox", "QCheckBox", "QRadioButton", "QButtonGroup",
        "QMessageBox", "QProgressDialog", "QTabWidget", "QScrollArea",
        "QSplitter", "QFrame", "QSizePolicy", "QAbstractItemView",
        "QHeaderView", "QTableView", "QSlider",
    ):
        setattr(qt_widgets, name, MagicMock)

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


_ensure_pyqt5_stubs()


import pytest


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------
try:
    from src.strategy_builder.ui.config_permutation_engine import (
        ConfigPermutationEngine,
        DiscoveryResult,
        DiscoveryScenario,
        ParameterRange,
        aggregate_metrics,
        generate_single_axis_permutations,
    )
    _ENGINE_AVAILABLE = True
    _import_err_msg = ""
except ImportError as _e:
    _ENGINE_AVAILABLE = False
    _import_err_msg = str(_e)

_skip_if_engine_missing = pytest.mark.skipif(
    not _ENGINE_AVAILABLE,
    reason=f"config_permutation_engine import failed: {_import_err_msg}",
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_fake_trades(scenario_config: Dict[str, Any], count: int = 5) -> List[Dict[str, Any]]:
    """
    Deterministic fake trades: PnL scales with risk_pct so that
    scenarios with higher risk produce higher total PnL (for ranking tests).
    """
    risk = scenario_config.get("risk_pct", 10)
    trades = []
    for i in range(count):
        pnl = (risk * 10.0) if i % 3 != 0 else -(risk * 5.0)
        trades.append({
            "pnl": pnl,
            "bars_held": 10 + i,
            "exit_condition_name": "TP1" if pnl > 0 else "SL",
            "exit_reason": "TP1" if pnl > 0 else "STOP_LOSS",
        })
    return trades


@pytest.fixture
def two_param_ranges() -> List[ParameterRange]:
    return [
        ParameterRange(key="risk_pct", label="Risk %", values=[5, 10]),
        ParameterRange(key="tpsl_mode", label="TP/SL Mode", values=["Fibonacci", "Fixed"]),
    ]


@pytest.fixture
def base_config() -> Dict[str, Any]:
    return {
        "tpsl_mode": "Fibonacci",
        "risk_pct": 10,
        "adaptive_sl": {"enabled": True, "volatility_lookback": 20},
    }


# ===========================================================================
# 5.3 — Integration: build → run (mocked) → aggregate → rank
# ===========================================================================

class TestDiscoveryFlowEndToEnd:

    @_skip_if_engine_missing
    def test_all_scenarios_produce_results(self, two_param_ranges, base_config):
        """Each scenario from build_scenarios must yield a DiscoveryResult."""
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(ranges=two_param_ranges, strategy="single_axis")

        results: List[DiscoveryResult] = []
        for scenario in scenarios:
            # Simulate worker result for this scenario: apply delta to base_config
            merged = dict(base_config)
            merged.update(scenario.config_delta)
            trades = _make_fake_trades(merged)
            results.append(aggregate_metrics(scenario, trades))

        assert len(results) == len(scenarios)

    @_skip_if_engine_missing
    def test_each_result_has_valid_metrics(self, two_param_ranges, base_config):
        """All DiscoveryResult metrics must be valid (finite, in range)."""
        import math
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(ranges=two_param_ranges, strategy="single_axis")

        for scenario in scenarios:
            merged = dict(base_config)
            merged.update(scenario.config_delta)
            trades = _make_fake_trades(merged, count=5)
            result = aggregate_metrics(scenario, trades)

            assert result.trade_count > 0
            assert math.isfinite(result.total_pnl)
            assert math.isfinite(result.win_rate)
            assert 0.0 <= result.win_rate <= 100.0
            assert math.isfinite(result.sharpe_ratio)
            assert result.avg_bars_held >= 0.0

    @_skip_if_engine_missing
    def test_results_sortable_by_pnl(self, base_config):
        """Results must be sortable by total_pnl descending."""
        ranges = [ParameterRange(key="risk_pct", label="Risk %", values=[5, 10, 15])]
        scenarios = generate_single_axis_permutations(base_config, ranges)

        results: List[DiscoveryResult] = []
        for scenario in scenarios:
            merged = dict(base_config)
            merged.update(scenario.config_delta)
            trades = _make_fake_trades(merged)
            results.append(aggregate_metrics(scenario, trades))

        ranked = sorted(results, key=lambda r: r.total_pnl, reverse=True)
        # Highest risk_pct (15) should produce highest PnL in fake worker
        top_delta = ranked[0].config_delta
        assert top_delta.get("risk_pct") == 15, (
            f"Expected risk_pct=15 at top, got {top_delta}"
        )

    @_skip_if_engine_missing
    def test_results_sortable_by_sharpe(self, two_param_ranges, base_config):
        """Results can be ranked by sharpe_ratio."""
        scenarios = generate_single_axis_permutations(base_config, two_param_ranges)
        results = [
            aggregate_metrics(s, _make_fake_trades(dict(base_config, **s.config_delta)))
            for s in scenarios
        ]
        by_sharpe = sorted(results, key=lambda r: r.sharpe_ratio, reverse=True)
        assert all(math.isfinite(r.sharpe_ratio) for r in by_sharpe)

    @_skip_if_engine_missing
    def test_zero_trade_scenario_handled(self, base_config):
        """A scenario returning 0 trades must not raise and must have 0 metrics."""
        scenario = DiscoveryScenario(
            scenario_id="DISC_ZERO",
            description="Zero trade scenario",
            config_delta={"risk_pct": 10},
        )
        result = aggregate_metrics(scenario, [])
        assert result.trade_count == 0
        assert result.total_pnl == 0.0
        assert result.win_rate == 0.0
        assert result.sharpe_ratio == 0.0

    @_skip_if_engine_missing
    def test_failed_worker_result_stored_not_lost(self, base_config):
        """
        When a worker fails (empty trades + error), aggregate_metrics must
        store the error and return a zero-metric result (not raise).
        """
        scenario = DiscoveryScenario(
            scenario_id="DISC_FAIL",
            description="Failed scenario",
            config_delta={"risk_pct": 10},
        )
        result = aggregate_metrics(
            scenario, [], error="NautilusTrader data load failed"
        )
        assert result.error is not None
        assert "NautilusTrader" in result.error
        assert result.trade_count == 0

    @_skip_if_engine_missing
    def test_max_scenarios_cap_limits_workflow(self, two_param_ranges, base_config):
        """max_scenarios cap must limit the total scenarios processed."""
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(
            ranges=two_param_ranges,
            strategy="single_axis",
            max_scenarios=2,
        )
        assert len(scenarios) == 2

        results = [
            aggregate_metrics(s, _make_fake_trades(base_config))
            for s in scenarios
        ]
        assert len(results) == 2


class TestDiscoveryFlowResultsWindowContract:
    """
    Documents expected interface for ConfigDiscoveryResultsDialog (Phase 3).
    Tests are xfail until Phase 3 is delivered.  When the dialog is implemented
    these should flip to passing automatically.
    """

    def test_results_dialog_importable(self):
        """Dialog module must import without error in headless CI."""
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            ConfigDiscoveryResultsDialog,  # noqa: F401
        )

    @pytest.mark.xfail(
        reason="ConfigDiscoveryResultsDialog needs DiscoveryResult list — "
               "Phase 3 acceptance test"
    )
    def test_results_dialog_apply_config_signal_exists(self):
        """Dialog must expose a config_selected (or apply_config) signal."""
        from src.strategy_builder.ui.config_discovery_results_dialog import (
            ConfigDiscoveryResultsDialog,
        )
        # Either attribute name is acceptable
        has_signal = (
            hasattr(ConfigDiscoveryResultsDialog, "config_selected")
            or hasattr(ConfigDiscoveryResultsDialog, "apply_config")
        )
        assert has_signal, (
            "Dialog must have a signal for 'Apply Config' button "
            "(config_selected or apply_config)"
        )


import math  # for the body of test_results_sortable_by_sharpe
