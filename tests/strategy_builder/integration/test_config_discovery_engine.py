"""
Unit Tests for Config Discovery Engine — Phase 5 (BTCAAAAA-150)

Tests the implemented classes in
  src/strategy_builder/ui/config_permutation_engine.py
delivered by UIEngineer (BTCAAAAA-149, Phase 1–2).

Test tasks covered:
  5.1 — Unit tests for ConfigPermutationEngine / permutation helpers
  5.2 — Unit tests for DiscoveryResult / aggregate_metrics (metrics calculation)

Author: QAEngineer (BTCAAAAA-150)
Date: 2026-05-04
"""

from __future__ import annotations

import math
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub PyQt5 before any engine import (headless CI support)
# ---------------------------------------------------------------------------
def _ensure_pyqt5_stubs():
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
        AlignLeft = 0x01
        AlignRight = 0x02

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
# Import guard — skip tests cleanly when module import chain is broken.
# ---------------------------------------------------------------------------
try:
    from src.strategy_builder.ui.config_permutation_engine import (
        ConfigPermutationEngine,
        ConfigPermutationWorker,
        DiscoveryResult,
        DiscoveryScenario,
        ParameterRange,
        aggregate_metrics,
        generate_single_axis_permutations,
        generate_pairwise_permutations,
        _set_nested,
        DEFAULT_PARAMETER_RANGES,
    )
    _MODULE_AVAILABLE = True
except ImportError as _import_err:
    _MODULE_AVAILABLE = False
    _import_err_msg = str(_import_err)

_skip_if_missing = pytest.mark.skipif(
    not _MODULE_AVAILABLE,
    reason=f"config_permutation_engine import failed: {_import_err_msg if not _MODULE_AVAILABLE else ''}",
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def two_value_ranges() -> List[ParameterRange]:
    """Two ranges, 2 values each — 4 single-axis scenarios total."""
    return [
        ParameterRange(key="risk_pct", label="Risk %", values=[5, 10]),
        ParameterRange(key="tpsl_mode", label="TP/SL Mode", values=["Fibonacci", "Fixed"]),
    ]


@pytest.fixture
def adaptive_sl_ranges() -> List[ParameterRange]:
    """Ranges that exercise nested dot-notation key construction."""
    return [
        ParameterRange(
            key="adaptive_sl.volatility_lookback", label="Vol LB",
            values=[10, 20, 30],
        ),
        ParameterRange(
            key="adaptive_sl.volatility_multiplier", label="Vol Mult",
            values=[1.0, 1.5],
        ),
    ]


@pytest.fixture
def base_config() -> Dict[str, Any]:
    return {
        "tpsl_mode": "Fibonacci",
        "risk_pct": 10,
        "adaptive_sl": {
            "enabled": True,
            "volatility_lookback": 20,
            "volatility_multiplier": 1.2,
        },
    }


@pytest.fixture
def sample_trades() -> List[Dict[str, Any]]:
    """Representative mix of winning and losing trades."""
    return [
        {"pnl": 200.0, "bars_held": 10, "exit_condition_name": "TP1", "exit_reason": "TP1"},
        {"pnl": 150.0, "bars_held": 8,  "exit_condition_name": "TP2", "exit_reason": "TP2"},
        {"pnl": -80.0, "bars_held": 5,  "exit_condition_name": "SL",  "exit_reason": "STOP_LOSS"},
        {"pnl": 90.0,  "bars_held": 12, "exit_condition_name": "TP1", "exit_reason": "TP1"},
        {"pnl": -120.0,"bars_held": 3,  "exit_condition_name": "SL",  "exit_reason": "STOP_LOSS"},
        {"pnl": 0.0,   "bars_held": 50, "exit_condition_name": "",    "exit_reason": "MAX_BARS"},
    ]


@pytest.fixture
def sample_scenario() -> "DiscoveryScenario":
    return DiscoveryScenario(
        scenario_id="DISC_0001",
        description="Test scenario",
        config_delta={"risk_pct": 10},
    )


# ===========================================================================
# 5.1 — ParameterRange
# ===========================================================================

class TestParameterRange:

    @_skip_if_missing
    def test_explicit_values_returned(self):
        pr = ParameterRange(key="risk_pct", label="Risk %", values=[5, 10, 15])
        assert pr.get_values() == [5, 10, 15]

    @_skip_if_missing
    def test_linspace_values_generated(self):
        pr = ParameterRange(key="leverage", label="Lev", min_val=1.0, max_val=3.0, steps=3)
        vals = pr.get_values()
        assert len(vals) == 3
        assert abs(vals[0] - 1.0) < 0.001
        assert abs(vals[-1] - 3.0) < 0.001

    @_skip_if_missing
    def test_format_value(self):
        pr = ParameterRange(key="x", label="X", values=[1.5], fmt="{:.1f}x")
        assert pr.format_value(1.5) == "1.5x"

    @_skip_if_missing
    def test_nested_key_accepted(self):
        pr = ParameterRange(key="adaptive_sl.volatility_lookback", label="VL", values=[10])
        assert "." in pr.key

    @_skip_if_missing
    def test_steps_2_linspace(self):
        pr = ParameterRange(key="x", label="X", min_val=0.0, max_val=1.0, steps=2)
        vals = pr.get_values()
        assert len(vals) == 2
        assert vals[0] == 0.0
        assert vals[1] == 1.0

    @_skip_if_missing
    def test_steps_1_returns_min(self):
        pr = ParameterRange(key="x", label="X", min_val=5.0, max_val=10.0, steps=1)
        vals = pr.get_values()
        assert len(vals) == 1
        assert vals[0] == 5.0

    @_skip_if_missing
    def test_missing_min_max_raises(self):
        pr = ParameterRange(key="x", label="X")  # no values, no min/max
        with pytest.raises((ValueError, TypeError)):
            pr.get_values()


# ===========================================================================
# 5.1 — _set_nested helper
# ===========================================================================

class TestSetNested:

    @_skip_if_missing
    def test_top_level_key(self):
        d = {"risk_pct": 5, "tpsl_mode": "Fixed"}
        out = _set_nested(d, "risk_pct", 10)
        assert out["risk_pct"] == 10

    @_skip_if_missing
    def test_nested_key(self):
        d = {"adaptive_sl": {"volatility_lookback": 20}}
        out = _set_nested(d, "adaptive_sl.volatility_lookback", 30)
        assert out["adaptive_sl"]["volatility_lookback"] == 30

    @_skip_if_missing
    def test_creates_missing_parent_dict(self):
        d = {}
        out = _set_nested(d, "adaptive_sl.volatility_multiplier", 1.5)
        assert out["adaptive_sl"]["volatility_multiplier"] == 1.5

    @_skip_if_missing
    def test_original_dict_not_mutated(self):
        d = {"risk_pct": 5}
        _set_nested(d, "risk_pct", 99)
        assert d["risk_pct"] == 5  # original untouched

    @_skip_if_missing
    def test_deeply_nested_key(self):
        d = {}
        out = _set_nested(d, "a.b.c", 42)
        assert out["a"]["b"]["c"] == 42


# ===========================================================================
# 5.1 — generate_single_axis_permutations
# ===========================================================================

class TestGenerateSingleAxisPermutations:

    @_skip_if_missing
    def test_count_equals_sum_of_values(self, two_value_ranges, base_config):
        # 2 + 2 = 4 total scenarios (each axis swept independently)
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        assert len(scenarios) == 4

    @_skip_if_missing
    def test_returns_list_of_discovery_scenario(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        for s in scenarios:
            assert isinstance(s, DiscoveryScenario)

    @_skip_if_missing
    def test_scenario_ids_unique(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        ids = [s.scenario_id for s in scenarios]
        assert len(ids) == len(set(ids))

    @_skip_if_missing
    def test_config_delta_has_correct_key(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        for s in scenarios:
            # Each single-axis scenario touches exactly one key
            assert len(s.config_delta) == 1

    @_skip_if_missing
    def test_nested_key_in_config_delta(self, adaptive_sl_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, adaptive_sl_ranges)
        for s in scenarios:
            key = list(s.config_delta.keys())[0]
            # Dot-notation preserved in delta
            assert "adaptive_sl." in key

    @_skip_if_missing
    def test_all_values_covered(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        risk_vals = {s.config_delta["risk_pct"] for s in scenarios if "risk_pct" in s.config_delta}
        assert risk_vals == {5, 10}

    @_skip_if_missing
    def test_empty_ranges_returns_empty(self, base_config):
        scenarios = generate_single_axis_permutations(base_config, [])
        assert scenarios == []

    @_skip_if_missing
    def test_param_labels_populated(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        for s in scenarios:
            assert len(s.param_labels) >= 1
            label, val = s.param_labels[0]
            assert isinstance(label, str)
            assert isinstance(val, str)

    @_skip_if_missing
    def test_description_not_empty(self, two_value_ranges, base_config):
        scenarios = generate_single_axis_permutations(base_config, two_value_ranges)
        for s in scenarios:
            assert s.description.strip()


# ===========================================================================
# 5.1 — ConfigPermutationEngine (facade)
# ===========================================================================

class TestConfigPermutationEngineFacade:

    @_skip_if_missing
    def test_engine_constructs(self):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config={"risk_pct": 10},
            cached_bars=[],
        )
        assert engine is not None

    @_skip_if_missing
    def test_build_scenarios_single_axis(self, two_value_ranges, base_config):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(ranges=two_value_ranges, strategy="single_axis")
        assert len(scenarios) == 4

    @_skip_if_missing
    def test_build_scenarios_uses_defaults_when_ranges_none(self, base_config):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(strategy="single_axis")
        # DEFAULT_PARAMETER_RANGES has 6 ranges, each with steps; total > 0
        assert len(scenarios) > 0

    @_skip_if_missing
    def test_build_scenarios_max_scenarios_cap(self, two_value_ranges, base_config):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(
            ranges=two_value_ranges,
            strategy="single_axis",
            max_scenarios=2,
        )
        assert len(scenarios) == 2

    @_skip_if_missing
    def test_create_worker_returns_worker(self, two_value_ranges, base_config):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(ranges=two_value_ranges, strategy="single_axis")
        worker = engine.create_worker(scenarios)
        assert isinstance(worker, ConfigPermutationWorker)

    @_skip_if_missing
    def test_worker_has_required_signals(self, two_value_ranges, base_config):
        engine = ConfigPermutationEngine(
            base_strategy_config={},
            base_backtest_config=base_config,
            cached_bars=[],
        )
        scenarios = engine.build_scenarios(ranges=two_value_ranges, strategy="single_axis")
        worker = engine.create_worker(scenarios)
        for signal_name in ("scenario_complete", "progress_updated",
                            "discovery_complete", "error_occurred"):
            assert hasattr(worker, signal_name), (
                f"ConfigPermutationWorker missing signal: {signal_name}"
            )


# ===========================================================================
# 5.1 — DEFAULT_PARAMETER_RANGES
# ===========================================================================

class TestDefaultParameterRanges:

    @_skip_if_missing
    def test_default_ranges_not_empty(self):
        assert len(DEFAULT_PARAMETER_RANGES) > 0

    @_skip_if_missing
    def test_all_default_ranges_have_get_values(self):
        for r in DEFAULT_PARAMETER_RANGES:
            vals = r.get_values()
            assert len(vals) > 0, f"Range '{r.key}' returned no values"

    @_skip_if_missing
    def test_default_ranges_cover_adaptive_sl(self):
        keys = [r.key for r in DEFAULT_PARAMETER_RANGES]
        adaptive_keys = [k for k in keys if k.startswith("adaptive_sl.")]
        assert len(adaptive_keys) >= 2, (
            "Default ranges must include at least 2 adaptive_sl parameters"
        )


# ===========================================================================
# 5.2 — aggregate_metrics: DiscoveryResult computation
# ===========================================================================

class TestAggregateMetrics:

    @_skip_if_missing
    def test_returns_discovery_result(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert isinstance(result, DiscoveryResult)

    @_skip_if_missing
    def test_total_pnl(self, sample_scenario, sample_trades):
        expected = sum(t["pnl"] for t in sample_trades)
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert abs(result.total_pnl - expected) < 0.001

    @_skip_if_missing
    def test_trade_count(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.trade_count == len(sample_trades)

    @_skip_if_missing
    def test_win_rate(self, sample_scenario, sample_trades):
        winning = sum(1 for t in sample_trades if t["pnl"] > 0)
        expected_wr = (winning / len(sample_trades)) * 100.0
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert abs(result.win_rate - expected_wr) < 0.001

    @_skip_if_missing
    def test_avg_pnl_per_trade(self, sample_scenario, sample_trades):
        expected = sum(t["pnl"] for t in sample_trades) / len(sample_trades)
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert abs(result.avg_pnl_per_trade - expected) < 0.001

    @_skip_if_missing
    def test_sharpe_is_finite(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert math.isfinite(result.sharpe_ratio), (
            f"Sharpe must be finite, got {result.sharpe_ratio}"
        )

    @_skip_if_missing
    def test_sharpe_zero_for_empty_trades(self, sample_scenario):
        result = aggregate_metrics(sample_scenario, [])
        assert result.sharpe_ratio == 0.0

    @_skip_if_missing
    def test_sharpe_zero_for_single_trade(self, sample_scenario):
        single = [{"pnl": 100.0, "bars_held": 5,
                   "exit_condition_name": "TP1", "exit_reason": "TP1"}]
        result = aggregate_metrics(sample_scenario, single)
        assert result.sharpe_ratio == 0.0

    @_skip_if_missing
    def test_exit_tp1_count(self, sample_scenario, sample_trades):
        expected = sum(1 for t in sample_trades if t.get("exit_condition_name") == "TP1")
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.exit_tp1 == expected

    @_skip_if_missing
    def test_exit_sl_count(self, sample_scenario, sample_trades):
        expected = sum(1 for t in sample_trades if "STOP" in t.get("exit_reason", "").upper())
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.exit_sl == expected

    @_skip_if_missing
    def test_exit_time_count(self, sample_scenario, sample_trades):
        expected = sum(1 for t in sample_trades if "MAX_BARS" in t.get("exit_reason", "").upper())
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.exit_time == expected

    @_skip_if_missing
    def test_empty_trades_returns_zero_metrics(self, sample_scenario):
        result = aggregate_metrics(sample_scenario, [])
        assert result.total_pnl == 0.0
        assert result.win_rate == 0.0
        assert result.trade_count == 0

    @_skip_if_missing
    def test_error_parameter_stored(self, sample_scenario):
        result = aggregate_metrics(sample_scenario, [], error="NautilusTrader data load failed")
        assert result.error is not None
        assert "NautilusTrader" in result.error

    @_skip_if_missing
    def test_max_drawdown_non_negative(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.max_drawdown >= 0.0

    @_skip_if_missing
    def test_avg_bars_held(self, sample_scenario, sample_trades):
        expected = sum(t["bars_held"] for t in sample_trades) / len(sample_trades)
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert abs(result.avg_bars_held - expected) < 0.001

    @_skip_if_missing
    def test_all_wins_win_rate_100(self, sample_scenario):
        all_wins = [{"pnl": 100.0, "bars_held": 5,
                     "exit_condition_name": "TP1", "exit_reason": "TP1"}
                    for _ in range(5)]
        result = aggregate_metrics(sample_scenario, all_wins)
        assert result.win_rate == 100.0

    @_skip_if_missing
    def test_all_losses_win_rate_zero(self, sample_scenario):
        all_losses = [{"pnl": -50.0, "bars_held": 3,
                       "exit_condition_name": "SL", "exit_reason": "STOP_LOSS"}
                      for _ in range(4)]
        result = aggregate_metrics(sample_scenario, all_losses)
        assert result.win_rate == 0.0

    @_skip_if_missing
    def test_scenario_id_preserved(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.scenario_id == sample_scenario.scenario_id

    @_skip_if_missing
    def test_description_preserved(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.description == sample_scenario.description

    @_skip_if_missing
    def test_raw_trades_stored(self, sample_scenario, sample_trades):
        result = aggregate_metrics(sample_scenario, sample_trades)
        assert result.raw_trades == sample_trades


# ===========================================================================
# 5.2 — DiscoveryResult sortability
# ===========================================================================

class TestDiscoveryResultSortability:

    @_skip_if_missing
    def test_sort_by_total_pnl(self, sample_scenario):
        r1 = DiscoveryResult(
            scenario_id="A", description="high", config_delta={}, param_labels=[],
            total_pnl=500.0,
        )
        r2 = DiscoveryResult(
            scenario_id="B", description="low", config_delta={}, param_labels=[],
            total_pnl=-100.0,
        )
        ranked = sorted([r2, r1], key=lambda r: r.total_pnl, reverse=True)
        assert ranked[0].total_pnl == 500.0

    @_skip_if_missing
    def test_sort_by_win_rate(self, sample_scenario):
        r1 = DiscoveryResult(
            scenario_id="A", description="", config_delta={}, param_labels=[],
            win_rate=80.0,
        )
        r2 = DiscoveryResult(
            scenario_id="B", description="", config_delta={}, param_labels=[],
            win_rate=40.0,
        )
        ranked = sorted([r2, r1], key=lambda r: r.win_rate, reverse=True)
        assert ranked[0].win_rate == 80.0

    @_skip_if_missing
    def test_sort_by_sharpe(self, sample_scenario):
        r1 = DiscoveryResult(
            scenario_id="A", description="", config_delta={}, param_labels=[],
            sharpe_ratio=2.5,
        )
        r2 = DiscoveryResult(
            scenario_id="B", description="", config_delta={}, param_labels=[],
            sharpe_ratio=0.5,
        )
        ranked = sorted([r2, r1], key=lambda r: r.sharpe_ratio, reverse=True)
        assert ranked[0].sharpe_ratio == 2.5
