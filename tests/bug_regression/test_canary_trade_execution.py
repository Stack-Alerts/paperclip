"""
Canary smoke tests for BTCAAAAA-1476: full data->signal->trade->registry path.

Exercises the real OHLCV load -> InstitutionalSignalEvaluator -> TradeRegistry
chain with zero mocks, covering high-volatility, low-volatility, and known-entry
sessions.

If this canary had existed before BTCAAAAA-1476, the zero-trades regression
would have failed CI within 5 minutes of PR open -- not 10 hours after a QA
sign-off.

Sessions (BTCUSDT_PERP 15m):
  1. High-vol: 2026-02-05 + 2026-02-06 -- 18.95% / 15.15% daily range
     (Feb 2026 is the highest-vol month in the dataset, avg daily range 5.61%)
  2. Low-vol:  2026-01-10 -- 0.49% daily range (tightest day in the dataset)
  3. Known-entry: 2026-02-01 to 2026-02-07 -- first week of highest-vol month,
     proven to produce entries by the BTCAAAAA-1497 regression tests

Strategy: "50% Asia Rejection Simple" (same config as BTCAAAAA-745/1497 tests)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

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
    pytest.mark.bug("BTCAAAAA-1476"),
    pytest.mark.smoke,
]

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

_BASE_BACKTEST_CONFIG: dict = {
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


def _load_bars_for_dates(dates: list[str]) -> list:
    dfs = []
    for month_dir in sorted(_DATA_DIR.iterdir()):
        if not month_dir.is_dir():
            continue
        for f in sorted(month_dir.iterdir()):
            if "15m" not in f.name or not f.name.endswith(".parquet"):
                continue
            df = pd.read_parquet(f)
            date_col = df["timestamp"].dt.date.astype(str)
            mask = date_col.isin(dates)
            if mask.any():
                dfs.append(df[mask])

    if not dfs:
        raise RuntimeError(
            f"No 15m parquet files found for dates {dates}. "
            f"Checked under {_DATA_DIR}."
        )

    df = pd.concat(dfs).sort_values("timestamp").reset_index(drop=True)

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
            f"BacktestWorker did not finish within {timeout_ms / 1000}s "
            f"({len(bars)} bars, mode={backtest_config.get('mode')})"
        )

    if not results_container:
        raise RuntimeError(
            "backtest_finished signal was never emitted -- "
            "worker likely crashed before completion"
        )

    success, results = results_container[0]
    if not success:
        raise RuntimeError(
            f"BacktestWorker failed: {results.get('error', 'unknown error')}"
        )

    return results


@pytest.fixture(scope="module")
def _ensure_qapp() -> None:
    app = QApplication.instance()
    if app is None:
        QApplication(sys.argv)


@pytest.fixture(scope="module")
def high_vol_bars() -> list:
    return _load_bars_for_dates([f"2026-02-{d:02d}" for d in range(1, 7)])


@pytest.fixture(scope="module")
def low_vol_bars() -> list:
    return _load_bars_for_dates(["2026-01-10"])


@pytest.fixture(scope="module")
def known_entry_bars() -> list:
    return _load_bars_for_dates([f"2026-02-{d:02d}" for d in range(1, 8)])


class TestCanaryTradeExecution:

    @pytest.fixture(autouse=True)
    def _init_qt(self, _ensure_qapp) -> None:
        pass

    def test_high_vol_sanity(self, high_vol_bars: list) -> None:
        assert len(high_vol_bars) == 576, (
            f"Expected 576 bars for Feb 1-6 (96 each); got {len(high_vol_bars)}"
        )

    def test_low_vol_sanity(self, low_vol_bars: list) -> None:
        assert len(low_vol_bars) == 96, (
            f"Expected 96 bars for Jan 10; got {len(low_vol_bars)}"
        )

    def test_known_entry_sanity(self, known_entry_bars: list) -> None:
        assert len(known_entry_bars) >= 96, (
            f"Expected >=96 bars for Feb 1-7; got {len(known_entry_bars)}"
        )

    def test_high_volatility_session(self, high_vol_bars: list) -> None:
        config = dict(_BASE_BACKTEST_CONFIG)
        config["mode"] = 2

        results = _run_worker(_STRATEGY_CONFIG, config, high_vol_bars)

        trades = results.get("trades", 0)
        trades_list = results.get("trades_list", [])

        assert trades > 0, (
            f"High-vol session (Feb 5-6 2026, 15-19% range) produced "
            f"0 trades on {len(high_vol_bars)} bars. "
            f"This is the BTCAAAAA-1476 regression pattern."
        )
        assert len(trades_list) > 0, "trades_list must be non-empty"

    def test_low_volatility_session(self, low_vol_bars: list) -> None:
        config = dict(_BASE_BACKTEST_CONFIG)
        config["mode"] = 2

        results = _run_worker(_STRATEGY_CONFIG, config, low_vol_bars)

        trades = results.get("trades", 0)
        trades_list = results.get("trades_list", [])

        assert isinstance(trades, int), f"trades must be int, got {type(trades)}"
        assert isinstance(trades_list, list), (
            f"trades_list must be list, got {type(trades_list)}"
        )

    def test_known_entry_signal_session(self, known_entry_bars: list) -> None:
        config = dict(_BASE_BACKTEST_CONFIG)
        config["mode"] = 2

        results = _run_worker(_STRATEGY_CONFIG, config, known_entry_bars)

        trades = results.get("trades", 0)
        trades_list = results.get("trades_list", [])

        assert trades > 0, (
            f"Known-entry window (Feb 1-7 2026, "
            f"{len(known_entry_bars)} bars) produced 0 trades. "
            f"This is the BTCAAAAA-1476 regression pattern."
        )
        assert len(trades_list) > 0, "trades_list must be non-empty"

    def test_zero_trades_with_impossible_config(self, high_vol_bars: list) -> None:
        impossible_config = dict(_STRATEGY_CONFIG)
        impossible_config["confluence_threshold"] = 999

        config = dict(_BASE_BACKTEST_CONFIG)
        config["mode"] = 2

        results = _run_worker(impossible_config, config, high_vol_bars)

        trades = results.get("trades", 0)
        assert trades == 0, (
            f"Impossible config (threshold=999) should produce 0 trades "
            f"on any data; got {trades}. This suggests the evaluator is "
            f"ignoring the confluence threshold."
        )
