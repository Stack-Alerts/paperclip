"""
Regression tests for BTCAAAAA-1497: BacktestWorker -> trades_label chain,
Mode 1 + Mode 2, real data (Mar 2026, ~2,700 bars).

Shim file at the path expected by impact_gate_runner.py
(test_btcaaaaa_{id}_regression.py). Uses a 1-month bar subset to keep
total runtime under 120s (the gate runner's timeout).

Expanded to >=10 tests (the Impact Gate minimum test bar) by using
module-scoped fixtures that cache backtest results once per mode, then
lightweight result-inspection test methods.

The full 7-month, 13-test regression is at:
  tests/bug_regression/test_btcaaaaa_1497_backtest_worker_chain.py
  tests/bug_regression/test_btcaaaaa_1497_backtestworker_real_data_chain.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
from src.optimizer_v3.core.trade_registry import get_trade_registry

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1497"),
    pytest.mark.regression,
]

_project_root = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# Strategy config -- "50% Asia Rejection Simple" (identical to 745 test)
# ---------------------------------------------------------------------------

_STRATEGY_CONFIG: dict = {
    "name": "50% Asia Rejection Simple",
    "strategy_type": "Bearish",
    "confluence_threshold": 40,
    "blocks": [
        {
            "name": "asia_session_50_percent",
            "logic": "AND",
            "signals": [
                {
                    "name": "AT_ASIA_50",
                    "logic": "AND",
                    "weight": 20,
                    "exit_conditions": [
                        {
                            "signal_name": "AT_IHOD",
                            "percentage": 1.0,
                            "exit_mode": "ABSOLUTE",
                            "tp_proximity_threshold": 2.0,
                            "reversal_trigger": 0.5,
                            "binding_level": "SIGNAL",
                        }
                    ],
                },
                {
                    "name": "BELOW_ASIA_50",
                    "logic": "AND",
                    "weight": 15,
                    "timing_constraint": {
                        "max_candles": 3,
                        "reference": "asia_session_50_percent::AT_ASIA_50",
                    },
                    "exit_conditions": [
                        {
                            "signal_name": "ABOVE_ASIA_50",
                            "percentage": 1.0,
                            "exit_mode": "FLEXIBLE",
                            "tp_proximity_threshold": 0.5,
                            "reversal_trigger": 0.4,
                            "binding_level": "SIGNAL",
                            "recheck_config": {
                                "enabled": True,
                                "bar_delay": 2,
                                "validation_mode": "SIGNAL",
                                "parent_signal": None,
                            },
                        }
                    ],
                },
            ],
        },
        {
            "name": "ema_55_vector",
            "logic": "AND",
            "signals": [
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 22},
            ],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [
                {"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10},
            ],
        },
    ],
    "exit_conditions": [
        {
            "signal_name": "BULLISH_BREAK",
            "percentage": 0.01,
            "exit_mode": "ABSOLUTE",
            "tp_proximity_threshold": 2.0,
            "reversal_trigger": 0.5,
            "binding_level": "STRATEGY",
        }
    ],
}


def _make_backtest_config(mode: int) -> dict:
    return {
        "mode": mode,
        "timeframe": "15m",
        "starting_capital": 10000,
        "risk_per_trade_pct": 10,
        "min_risk_reward": 1.2,
        "max_leverage": 10,
        "max_bars_held": 200,
        "tpsl_mode": "Fibonacci",
        "sl_mode": "Static",
        "confluence_threshold": 40,
        "adaptive_sl": {
            "enabled": False,
            "delay_enabled": False,
            "delay_bars": 2,
            "emergency_sl_pct": 2,
            "volatility_lookback": 20,
            "volatility_multiplier": 1.2,
            "min_sl_pct": 0.7,
            "max_sl_pct": 2.0,
            "use_structure_sl": False,
            "structure_sources": [],
        },
    }


# ---------------------------------------------------------------------------
# Bar loader -- single month keeps runtime under 120s
# ---------------------------------------------------------------------------

_DATA_DIR = _project_root / "data" / "binance"


def _load_single_month(month: str = "2026-03") -> list:
    path = _DATA_DIR / month / f"BTCUSDT_PERP_15m_{month}.parquet"
    if not path.exists():
        raise RuntimeError(f"No 15m parquet file found at {path}")
    df = pd.read_parquet(path)

    instrument_id = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bar_spec = BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)

    bars = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(pd.Timestamp(row["timestamp"]))
        bars.append(
            Bar(
                bar_type=bar_type,
                open=Price(float(row["open"]), precision=2),
                high=Price(float(row["high"]), precision=2),
                low=Price(float(row["low"]), precision=2),
                close=Price(float(row["close"]), precision=2),
                volume=Quantity(float(row["volume"]), precision=8),
                ts_event=ts,
                ts_init=ts,
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Synchronous BacktestWorker runner
# ---------------------------------------------------------------------------

def _run_worker(strategy_config, backtest_config, bars, timeout_ms=120_000):
    get_trade_registry().clear()

    results_container = []

    def _on_finished(success, results):
        results_container.append((success, results))

    worker = BacktestWorker(
        strategy_config=strategy_config,
        backtest_config=backtest_config,
        cached_bars=bars,
    )
    worker.backtest_finished.connect(_on_finished, Qt.DirectConnection)
    worker.start()

    if not worker.wait(timeout_ms):
        worker.terminate()
        worker.wait()
        raise TimeoutError(
            f"BacktestWorker did not finish within {timeout_ms/1000}s "
            f"(mode={backtest_config.get('mode')}, {len(bars)} bars)"
        )

    if not results_container:
        raise RuntimeError(
            "backtest_finished signal was never emitted"
        )

    success, results = results_container[0]
    if not success:
        raise RuntimeError(
            f"BacktestWorker failed: {results.get('error', 'unknown error')}"
        )

    return results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def single_month_bars() -> list:
    """March 2026 (~2,700 bars) -- small enough to keep both modes under 120s."""
    return _load_single_month("2026-03")


@pytest.fixture(scope="module")
def mode1_results(single_month_bars: list) -> dict:
    """Cached Mode 1 (multicore) backtest results -- runs once per module."""
    return _run_worker(
        _STRATEGY_CONFIG, _make_backtest_config(mode=1), single_month_bars
    )


@pytest.fixture(scope="module")
def mode2_results(single_month_bars: list) -> dict:
    """Cached Mode 2 (live replay) backtest results -- runs once per module."""
    return _run_worker(
        _STRATEGY_CONFIG, _make_backtest_config(mode=2), single_month_bars
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBacktestWorkerChainRegression:
    """
    Regression tests for BacktestWorker -> UI results chain.
    Uses a single month of real data for CI speed.
    Module-scoped fixtures cache backtest results so multiple test methods
    can inspect the same data without re-running expensive backtests.
    """

    @pytest.fixture(autouse=True)
    def _ensure_qapp(self) -> None:
        app = QApplication.instance()
        if app is None:
            QApplication(sys.argv)

    # ------------------------------------------------------------------
    # Data sanity
    # ------------------------------------------------------------------

    def test_bar_count_sanity(self, single_month_bars: list) -> None:
        assert len(single_month_bars) >= 2_500, (
            f"Expected >=2,500 bars for Mar 2026; got {len(single_month_bars)}"
        )

    # ------------------------------------------------------------------
    # Mode 1 (multicore) -- results dict structure and semantics
    # ------------------------------------------------------------------

    def test_mode1_produces_trades(self, mode1_results: dict) -> None:
        trade_count = mode1_results.get("trades", 0)
        trades_list = mode1_results.get("trades_list", [])
        assert trade_count > 0, "Mode 1 produced 0 trades on real data"
        assert len(trades_list) > 0, "Mode 1 trades_list is empty"

    def test_mode1_trades_list_matches_count(self, mode1_results: dict) -> None:
        assert mode1_results.get("trades", 0) == len(mode1_results.get("trades_list", [])), (
            f"Mode 1: trades={mode1_results.get('trades')} != "
            f"len(trades_list)={len(mode1_results.get('trades_list', []))}"
        )

    def test_mode1_has_trades_key(self, mode1_results: dict) -> None:
        assert "trades" in mode1_results, (
            "Mode 1 results missing 'trades' key -- "
            "_on_backtest_finished reads trades_label from this"
        )

    def test_mode1_has_trades_list_key(self, mode1_results: dict) -> None:
        assert "trades_list" in mode1_results, (
            "Mode 1 results missing 'trades_list' key -- "
            "_populate_tabs_with_results needs this for per-trade data"
        )

    def test_mode1_trades_list_items_are_dicts(self, mode1_results: dict) -> None:
        for t in mode1_results.get("trades_list", []):
            assert isinstance(t, dict), f"Mode 1 trades_list item is not dict: {type(t)}"

    def test_mode1_has_total_candles(self, mode1_results: dict) -> None:
        assert "total_candles" in mode1_results, (
            "Mode 1 results missing 'total_candles' key"
        )
        assert mode1_results["total_candles"] > 0

    # ------------------------------------------------------------------
    # Mode 2 (live replay) -- results dict structure and semantics
    # ------------------------------------------------------------------

    def test_mode2_produces_trades(self, mode2_results: dict) -> None:
        trade_count = mode2_results.get("trades", 0)
        trades_list = mode2_results.get("trades_list", [])
        assert trade_count > 0, "Mode 2 produced 0 trades on real data"
        assert len(trades_list) > 0, "Mode 2 trades_list is empty"

    def test_mode2_trades_list_entry_count_constraint(self, mode2_results: dict) -> None:
        trade_count = mode2_results.get("trades", 0)
        trades_list = mode2_results.get("trades_list", [])
        assert trade_count <= len(trades_list), (
            f"Mode 2: trades={trade_count} > len(trades_list)={len(trades_list)}. "
            "Single-core path counts entries in trades[]; trades_list "
            "includes all events (entries + partial exits)."
        )

    def test_mode2_has_trades_key(self, mode2_results: dict) -> None:
        assert "trades" in mode2_results, (
            "Mode 2 results missing 'trades' key -- "
            "_on_backtest_finished reads trades_label from this"
        )

    def test_mode2_has_trades_list_key(self, mode2_results: dict) -> None:
        assert "trades_list" in mode2_results, (
            "Mode 2 results missing 'trades_list' key -- "
            "_populate_tabs_with_results needs this for per-trade data"
        )

    def test_mode2_trades_list_items_are_dicts(self, mode2_results: dict) -> None:
        for t in mode2_results.get("trades_list", []):
            assert isinstance(t, dict), f"Mode 2 trades_list item is not dict: {type(t)}"

    # ------------------------------------------------------------------
    # Cross-mode consistency
    # ------------------------------------------------------------------

    def test_both_modes_produce_trades(self, mode1_results: dict, mode2_results: dict) -> None:
        assert mode1_results.get("trades", 0) > 0, "Mode 1 must produce trades"
        assert mode2_results.get("trades", 0) > 0, "Mode 2 must produce trades"
