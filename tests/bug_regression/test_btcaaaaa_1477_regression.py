"""
Regression tests for BTCAAAAA-1477: Zero-Trades Regression — Module-Wide Audit.

Verifies that the signal evaluation pipeline produces trades on real market
data after the structural hardening from ADR-0001 (R1-R7).  Covers both
Mode 1 (multicore) and Mode 2 (live replay) using a 1-month bar subset to
keep total runtime under 120s (the Impact Gate timeout).

Parent issue: BTCAAAAA-1476 — Board reported both modes producing 0 trades.
ADR: docs/architecture/adr/ADR-0001-zero-trades-regression-audit.md

If this test existed before BTCAAAAA-1476, the zero-trades regression would
have been caught within minutes rather than ~10 hours after QA sign-off.
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
    pytest.mark.bug("BTCAAAAA-1477"),
    pytest.mark.regression,
]

_project_root = Path(__file__).parent.parent.parent

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


def _run_worker(
    strategy_config: dict,
    backtest_config: dict,
    bars: list,
    timeout_ms: int = 120_000,
) -> dict:
    get_trade_registry().clear()

    results_container: list = []

    def _on_finished(success: bool, results: dict) -> None:
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
        raise RuntimeError("backtest_finished signal was never emitted")

    success, results = results_container[0]
    if not success:
        raise RuntimeError(
            f"BacktestWorker failed: {results.get('error', 'unknown error')}"
        )

    return results


@pytest.fixture(scope="module")
def single_month_bars() -> list:
    return _load_single_month("2026-03")


@pytest.fixture(scope="module")
def mode1_results(single_month_bars: list) -> dict:
    return _run_worker(
        _STRATEGY_CONFIG, _make_backtest_config(mode=1), single_month_bars
    )


@pytest.fixture(scope="module")
def mode2_results(single_month_bars: list) -> dict:
    return _run_worker(
        _STRATEGY_CONFIG, _make_backtest_config(mode=2), single_month_bars
    )


class TestZeroTradesRegression:
    """
    Regression tests for BTCAAAAA-1477 zero-trades failure class.
    Ensures both backtest modes produce trades on real market data and
    that results carry the expected structure for UI rendering.
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
        assert trade_count > 0, (
            f"Mode 1 produced 0 trades on Mar 2026 data. "
            f"This is the BTCAAAAA-1477 zero-trades regression pattern. "
            f"Check building block instantiation, signal evaluation, "
            f"or the required-signals gate (ADR-0001 SPOF-3)."
        )
        assert len(trades_list) > 0, "Mode 1 trades_list must be non-empty"

    def test_mode1_trades_list_matches_count(self, mode1_results: dict) -> None:
        assert mode1_results.get("trades", 0) == len(
            mode1_results.get("trades_list", [])
        ), (
            f"Mode 1: trades={mode1_results.get('trades')} != "
            f"len(trades_list)={len(mode1_results.get('trades_list', []))}"
        )

    def test_mode1_has_trades_key(self, mode1_results: dict) -> None:
        assert "trades" in mode1_results, (
            "Mode 1 results missing 'trades' key"
        )

    def test_mode1_has_trades_list_key(self, mode1_results: dict) -> None:
        assert "trades_list" in mode1_results, (
            "Mode 1 results missing 'trades_list' key"
        )

    def test_mode1_trades_list_items_are_dicts(self, mode1_results: dict) -> None:
        for t in mode1_results.get("trades_list", []):
            assert isinstance(t, dict), (
                f"Mode 1 trades_list item has unexpected type: {type(t)}"
            )

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
        assert trade_count > 0, (
            f"Mode 2 produced 0 trades on Mar 2026 data. "
            f"This is the BTCAAAAA-1477 zero-trades regression pattern. "
            f"Mode 2 shares the same signal evaluator and trade registry "
            f"as Mode 1 (ADR-0001 finding) -- zero-trades always affects both."
        )
        assert len(trades_list) > 0, "Mode 2 trades_list must be non-empty"

    def test_mode2_has_trades_key(self, mode2_results: dict) -> None:
        assert "trades" in mode2_results, (
            "Mode 2 results missing 'trades' key"
        )

    def test_mode2_has_trades_list_key(self, mode2_results: dict) -> None:
        assert "trades_list" in mode2_results, (
            "Mode 2 results missing 'trades_list' key"
        )

    def test_mode2_trades_list_items_are_dicts(self, mode2_results: dict) -> None:
        for t in mode2_results.get("trades_list", []):
            assert isinstance(t, dict), (
                f"Mode 2 trades_list item has unexpected type: {type(t)}"
            )

    # ------------------------------------------------------------------
    # Cross-mode consistency
    # ------------------------------------------------------------------

    def test_both_modes_produce_trades(
        self, mode1_results: dict, mode2_results: dict
    ) -> None:
        assert mode1_results.get("trades", 0) > 0, "Mode 1 must produce trades"
        assert mode2_results.get("trades", 0) > 0, "Mode 2 must produce trades"
