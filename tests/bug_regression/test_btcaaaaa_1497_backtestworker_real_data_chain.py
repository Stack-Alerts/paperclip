"""
Regression test for BTCAAAAA-1497: BacktestWorker -> trades_label chain,
Mode 1 + Mode 2, real data.

Verifies that the full BacktestWorker (a QThread subclass used by the UI)
produces trades > 0 when fed real parquet data via cached_bars, for both
the multicore path (Mode 1) and the bar-by-bar sequential path (Mode 2).

Also confirms the backtest_finished signal delivers a results dict with
a non-empty trades_list that correctly propagates to _on_backtest_finished.

Dataset:
  15-minute BTCUSDT_PERP bars, Feb-May 2026 (same as BTCAAAAA-745).
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pandas as pd
import pytest

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
from src.optimizer_v3.core.trade_registry import get_trade_registry

pytestmark = pytest.mark.regression

_DATA_DIR = _project_root / "data" / "binance"
_MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05"]

_STRATEGY_CONFIG: dict = {
    "name": "50% Asia Rejection Simple",
    "strategy_type": "Bearish",
    "confluence_threshold": 40,
    "blocks": [
        {
            "name": "asia_session_50_percent",
            "logic": "AND",
            "signals": [
                {"name": "AT_ASIA_50", "logic": "AND", "weight": 20, "exit_conditions": []},
                {"name": "BELOW_ASIA_50", "logic": "AND", "weight": 15, "exit_conditions": []},
            ],
        },
        {
            "name": "ema_55_vector",
            "logic": "AND",
            "signals": [{"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 22}],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [{"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10}],
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


def _load_real_bars(limit: int | None = None) -> list:
    dfs = []
    for month in _MONTHS:
        path = _DATA_DIR / month / f"BTCUSDT_PERP_15m_{month}.parquet"
        if path.exists():
            dfs.append(pd.read_parquet(path))
    if not dfs:
        raise RuntimeError(
            f"No 15m parquet files found under {_DATA_DIR} for months {_MONTHS}."
        )
    df = pd.concat(dfs).sort_values("timestamp").reset_index(drop=True)
    if limit:
        df = df.iloc[:limit]

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


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def real_bars():
    """Full dataset for multicore path."""
    return _load_real_bars()


@pytest.fixture(scope="module")
def real_bars_subset():
    """Subset (~2000 bars) for sequential single-core paths which are slow."""
    return _load_real_bars(limit=2000)


class TestBacktestWorkerChainRegression:
    """Full-chain regression: BacktestWorker real data -> finished signal -> trades."""

    def _build_config(self, mode: int, use_multicore: bool | None = None) -> dict:
        config = dict(_BASE_BACKTEST_CONFIG)
        config["mode"] = mode
        if use_multicore is not None:
            config["use_multicore"] = use_multicore
        return config

    def _run_worker(
        self,
        mode: int,
        use_multicore: bool | None,
        bars: list,
        qapp: QApplication,
        timeout_s: int = 60,
    ) -> tuple[bool, dict]:
        get_trade_registry().clear()

        config = self._build_config(mode, use_multicore)
        worker = BacktestWorker(
            strategy_config=_STRATEGY_CONFIG,
            backtest_config=config,
            cached_bars=bars,
        )

        event = threading.Event()
        results_holder: dict = {}

        def on_finished(success: bool, results: dict) -> None:
            results_holder["success"] = success
            results_holder["results"] = results
            event.set()

        worker.backtest_finished.connect(on_finished, Qt.DirectConnection)

        worker.start()

        captured = event.wait(timeout=timeout_s)

        worker.wait(5000)
        if worker.isRunning():
            worker.terminate()
            worker.wait()

        if not captured:
            raise RuntimeError(
                f"BacktestWorker did not emit backtest_finished within "
                f"{timeout_s}s (mode={mode}, multicore={use_multicore}, "
                f"bars={len(bars)})."
            )

        success = results_holder["success"]
        results = results_holder["results"]
        assert success is not None
        return success, results

    # -- Bar count sanity --

    def test_bar_count_sanity(self, real_bars: list) -> None:
        assert len(real_bars) >= 8000, (
            f"Expected >=8,000 real bars; got {len(real_bars)}. "
            "Verify data/binance parquet files."
        )

    # -- Mode 1, multicore path (full dataset) --

    def test_mode1_multicore_trades_gt_zero(
        self, qapp: QApplication, real_bars: list
    ) -> None:
        success, results = self._run_worker(
            mode=1, use_multicore=None, bars=real_bars, qapp=qapp, timeout_s=60
        )
        assert success, (
            f"Mode 1 multicore backtest failed. Error: "
            f"{results.get('error', 'unknown') if results else 'None'}"
        )
        assert results is not None
        trades = results.get("trades", 0)
        trades_list = results.get("trades_list", [])
        assert trades > 0, (
            f"Mode 1 multicore produced 0 trades on real data. "
            f"This is the BTCAAAAA-1476/1477 regression."
        )
        assert len(trades_list) > 0, "trades_list must be non-empty"

    def test_mode1_multicore_trades_list_matches_count(
        self, qapp: QApplication, real_bars: list
    ) -> None:
        _, results = self._run_worker(
            mode=1, use_multicore=None, bars=real_bars, qapp=qapp, timeout_s=60
        )
        assert results["trades"] == len(results["trades_list"]), (
            f"results['trades']={results['trades']} != "
            f"len(results['trades_list'])={len(results['trades_list'])}"
        )

    # -- Mode 1, single-core path (subset) --

    def test_mode1_singlecore_trades_gt_zero(
        self, qapp: QApplication, real_bars_subset: list
    ) -> None:
        success, results = self._run_worker(
            mode=1, use_multicore=False, bars=real_bars_subset, qapp=qapp, timeout_s=120
        )
        assert success, (
            f"Mode 1 single-core backtest failed. Error: "
            f"{results.get('error', 'unknown') if results else 'None'}"
        )
        assert results is not None
        trades = results.get("trades", 0)
        assert trades > 0, (
            f"Mode 1 single-core produced 0 trades on real data. "
            f"This is the BTCAAAAA-1476/1477 regression."
        )
        # Note: single-core trades_list includes Trade objects from the
        # registry, which may contain sub-trades (partial exits) making
        # it larger than the trade_count. We only verify trades_list is
        # populated.
        assert len(results.get("trades_list", [])) > 0, "trades_list must be non-empty"

    # -- Mode 2 (live replay) path (subset) --

    def test_mode2_replay_trades_gt_zero(
        self, qapp: QApplication, real_bars_subset: list
    ) -> None:
        success, results = self._run_worker(
            mode=2, use_multicore=None, bars=real_bars_subset, qapp=qapp, timeout_s=120
        )
        assert success, (
            f"Mode 2 backtest failed. Error: "
            f"{results.get('error', 'unknown') if results else 'None'}"
        )
        assert results is not None
        trades = results.get("trades", 0)
        assert trades > 0, (
            f"Mode 2 produced 0 trades on real data. "
            f"This is the BTCAAAAA-1476/1477 regression."
        )
        assert len(results.get("trades_list", [])) > 0, "trades_list must be non-empty"

    # -- Cross-mode consistency --

    def test_both_modes_produce_trades_on_real_data(
        self, qapp: QApplication, real_bars: list, real_bars_subset: list
    ) -> None:
        _, r1 = self._run_worker(
            mode=1, use_multicore=None, bars=real_bars, qapp=qapp, timeout_s=60
        )
        get_trade_registry().clear()
        _, r2 = self._run_worker(
            mode=2, use_multicore=None, bars=real_bars_subset, qapp=qapp, timeout_s=120
        )
        assert r1["trades"] > 0, "Mode 1 must produce trades"
        assert r2["trades"] > 0, "Mode 2 must produce trades"

    # -- results dict propagation to _on_backtest_finished --

    def test_results_dict_propagates_trades_count_and_list_multicore(
        self, qapp: QApplication, real_bars: list
    ) -> None:
        _, results = self._run_worker(
            mode=1, use_multicore=None, bars=real_bars, qapp=qapp, timeout_s=60
        )
        assert "trades" in results, (
            "backtest_finished results dict missing 'trades' key. "
            "_on_backtest_finished reads results['trades'] to update the UI."
        )
        assert "trades_list" in results, (
            "backtest_finished results dict missing 'trades_list' key. "
            "_populate_tabs_with_results reads it for per-trade data."
        )
        assert isinstance(results["trades_list"], list)

    def test_results_dict_propagates_singlecore(
        self, qapp: QApplication, real_bars_subset: list
    ) -> None:
        _, results = self._run_worker(
            mode=1, use_multicore=False, bars=real_bars_subset, qapp=qapp, timeout_s=120
        )
        assert "trades" in results
        assert "trades_list" in results
        assert isinstance(results["trades_list"], list)

    def test_results_dict_propagates_mode2(
        self, qapp: QApplication, real_bars_subset: list
    ) -> None:
        _, results = self._run_worker(
            mode=2, use_multicore=None, bars=real_bars_subset, qapp=qapp, timeout_s=120
        )
        assert "trades" in results
        assert "trades_list" in results
        assert isinstance(results["trades_list"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
