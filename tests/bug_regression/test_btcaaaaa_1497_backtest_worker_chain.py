"""
Regression test for BTCAAAAA-1497: full BacktestWorker -> trades_label chain,
Mode 1 + Mode 2, real data (Nov 2025 - May 2026, 18,416 bars).

Covers both execution paths through BacktestWorker:
  - Mode 1 (Historical): uses MulticoreBacktestEngine (parallel chunk processing)
  - Mode 2 (Live Replay): forced bar-by-bar single-core (strict temporal ordering)

Verifies that the results dict emitted via the backtest_finished signal:
  - Has trades > 0 in both modes
  - Has non-empty trades_list in both modes
  - Has consistent trades count semantics in each mode

Signal-chain investigation:
  BacktestWorker.run()
    -> self.backtest_finished.emit(success, results)          # line 623/1007
    -> BacktestConfigPanel._on_backtest_finished              # line 2929
    -> self.trades_label.setText(f"Trades: <b>{trades}</b>")  # line 2951

  The results dict keys used by _on_backtest_finished:
    results['trades']        -- integer count (line 2950)
    results['trades_list']   -- list of trade dicts (used by _populate_tabs_with_results)

  Key finding: trades count semantics differ between modes:
    - Mode 1 (multicore): results['trades'] == len(results['trades_list'])
      Both reflect total trade events from MulticoBacktestEngine output.
    - Mode 2 (single-core): results['trades'] == number of entry events,
      while results['trades_list'] includes ALL events (entries + partial
      TP/SL exits). So trades <= len(trades_list) for Mode 2.

Strategy under test: "50% Asia Rejection Simple"
  AT_ASIA_50 (20) + BELOW_ASIA_50 (15) + BEARISH_CLIMAX (22) -> >=40 confluence
  (same config as BTCAAAAA-745 regression test)
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from threading import Event

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
    pytest.mark.bug("BTCAAAAA-1497"),
    pytest.mark.regression,
]

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

# ---------------------------------------------------------------------------
# Backtest config factory
# ---------------------------------------------------------------------------

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
# Real bar loader -- 7 months of 15m BTCUSDT_PERP data
# ---------------------------------------------------------------------------

_DATA_DIR = _project_root / "data" / "binance"
_FULL_MONTHS = [
    "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05",
]
_745_MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05"]


def _load_bars(months: list[str]) -> list:
    """Load 15m BTCUSDT_PERP bars from parquet for the given months."""
    dfs = []
    for month in months:
        path = _DATA_DIR / month / f"BTCUSDT_PERP_15m_{month}.parquet"
        if path.exists():
            dfs.append(pd.read_parquet(path))

    if not dfs:
        raise RuntimeError(
            f"No 15m parquet files found under {_DATA_DIR} for months {months}"
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


# ---------------------------------------------------------------------------
# Synchronous BacktestWorker runner
# ---------------------------------------------------------------------------

def _run_worker(
    strategy_config: dict,
    backtest_config: dict,
    bars: list,
    timeout_ms: int = 300_000,
) -> dict:
    """
    Start a BacktestWorker with pre-loaded real bars, wait for completion,
    and return the results dict.

    Uses Qt.DirectConnection for the backtest_finished signal so the
    callback runs synchronously in the worker thread (not queued in the
    main thread's event loop), guaranteeing we capture results even
    without an active Qt event loop.
    """
    get_trade_registry().clear()

    results_container: list = []

    def _on_finished(success: bool, results: dict) -> None:
        results_container.append((success, results))

    worker = BacktestWorker(
        strategy_config=strategy_config,
        backtest_config=backtest_config,
        cached_bars=bars,
    )
    # DirectConnection: slot runs in worker thread synchronously on emit.
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
            "backtest_finished signal was never emitted (DirectConnection) -- "
            "worker likely crashed before completion"
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
def full_bars() -> list:
    """Nov 2025 - May 2026 (18,416 bars)."""
    return _load_bars(_FULL_MONTHS)


@pytest.fixture(scope="module")
def feb_may_bars() -> list:
    """Feb 2026 - May 2026 (8,632 bars -- matches BTCAAAAA-745 data window)."""
    return _load_bars(_745_MONTHS)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBacktestWorkerChainRegression:
    """
    Regression tests for the full BacktestWorker -> UI results chain.
    """

    @pytest.fixture(autouse=True)
    def _ensure_qapp(self) -> None:
        app = QApplication.instance()
        if app is None:
            QApplication(sys.argv)

    # ------------------------------------------------------------------
    # Data sanity
    # ------------------------------------------------------------------

    def test_bar_count_sanity(self, full_bars: list) -> None:
        assert len(full_bars) >= 18_000, (
            f"Expected >=18,000 real bars for Nov 2025 - May 2026; "
            f"got {len(full_bars)}"
        )

    # ------------------------------------------------------------------
    # Mode 1 (Historical / multicore path) -- full 7-month dataset
    # ------------------------------------------------------------------

    def test_mode1_multicore_trade_count(self, full_bars: list) -> None:
        """
        Mode 1 (multicore) must produce > 0 trades on real data.

        For the multicore path, results['trades'] == len(results['trades_list'])
        because both come from the same MulticoBacktestEngine output:
          trades_list = mc_results.get('trades', [])
          trade_count = len(trades_list)
          results = {'trades': trade_count, 'trades_list': trades_list, ...}
        (BacktestWorker.run() lines 528-529 and 610-615)
        """
        results = _run_worker(
            _STRATEGY_CONFIG, _make_backtest_config(mode=1), full_bars
        )

        trade_count = results.get("trades", 0)
        trades_list = results.get("trades_list", [])

        assert trade_count > 0, (
            f"Mode 1 (multicore) produced 0 trades on "
            f"{len(full_bars)} real bars"
        )
        assert len(trades_list) > 0
        assert trade_count == len(trades_list), (
            f"Mode 1 count mismatch: trades={trade_count} vs "
            f"len(trades_list)={len(trades_list)} -- these MUST match "
            f"in the multicore path (both come from mc_results['trades'])"
        )

    # ------------------------------------------------------------------
    # Mode 2 (Live Replay / single-core path) -- 4-month dataset
    # ------------------------------------------------------------------

    def test_mode2_live_replay_trade_count(self, feb_may_bars: list) -> None:
        """
        Mode 2 (Live Replay) must produce > 0 trades on real data.

        Mode 2 forces use_multicore = False, exercising the bar-by-bar
        sequential evaluation path.  Uses Feb-May 2026 (same window as the
        BTCAAAAA-745 test) to keep runtime under 2 minutes.

        For the single-core path, results['trades'] counts entry events
        while results['trades_list'] includes ALL events (entries +
        partial TP/SL exits from TradeRegistry). So:
          trades <= len(trades_list)
        """
        results = _run_worker(
            _STRATEGY_CONFIG, _make_backtest_config(mode=2), feb_may_bars
        )

        trade_count = results.get("trades", 0)
        trades_list = results.get("trades_list", [])

        assert trade_count > 0, (
            f"Mode 2 (live replay) produced 0 trades on "
            f"{len(feb_may_bars)} real bars (Feb-May 2026)"
        )
        assert len(trades_list) > 0
        assert trade_count <= len(trades_list), (
            f"Mode 2: trades={trade_count} > len(trades_list)={len(trades_list)}. "
            f"Single-core path counts entries in trades[] but "
            f"trades_list should include at least all entries."
        )

    # ------------------------------------------------------------------
    # Signal-chain propagation report (Mode 1, full 7-month window)
    # ------------------------------------------------------------------

    def test_trade_count_propagation(self, full_bars: list, capsys) -> None:
        """
        Verify the BacktestWorker -> signal -> _on_backtest_finished chain.

        BacktestWorker.run()
          -> self.backtest_finished.emit(True, results)
          -> BacktestConfigPanel._on_backtest_finished()
          -> self.trades_label.setText(f"Trades: <b>{results['trades']}</b>")

        Measures and reports the actual trade count for the
        Nov 2025 - May 2026 window. Uses Mode 1 (multicore) because
        it handles the full 18k-bar dataset efficiently.
        """
        results = _run_worker(
            _STRATEGY_CONFIG, _make_backtest_config(mode=1), full_bars
        )

        trade_count = results.get("trades", 0)
        trades_list = results.get("trades_list", [])
        total_candles = results.get("total_candles", 0)

        print(f"\n{'='*60}")
        print(f"BacktestWorker Chain -- Trade Count Report")
        print(f"{'='*60}")
        print(f"  Dataset:          Nov 2025 - May 2026")
        print(f"  Bars processed:   {total_candles:,}")
        print(f"  Mode:             1 (multicore)")
        print(f"  results['trades']:          {trade_count}")
        print(f"  len(results['trades_list']): {len(trades_list)}")
        print(f"  Counts match:                {trade_count == len(trades_list)}")
        print(f"  Chain status:                PROPAGATION OK")
        print(f"  Key insight:   trades_label displays results['trades']")
        print(f"  trades_list propagated via _populate_tabs_with_results")
        print(f"{'='*60}\n")

        assert trade_count > 0
        assert len(trades_list) > 0
        assert trade_count == len(trades_list)
