"""
Regression tests for BTCAAAAA-1195: single-core Mode 2 trades_list fix.

Bug: BacktestWorker in Mode 2 (Live Replay / bar-by-bar sequential) emitted
backtest_finished without a ``trades_list`` key in the results dict. Config
Discovery and downstream consumers that expected per-trade data displayed 0
trades for every Mode 2 variant.

Fix (``backtest_config_panel.py``): After the single-core bar loop, read the
TradeRegistry via ``get_trade_registry().get_all_trades()`` and include
the list of trade dicts as ``trades_list`` in the results payload emitted by
``backtest_finished``.

These tests verify that the Mode 2 backtest_finished results dict carries the
``trades_list`` key and that it is a non-empty list of trade dicts when the
evaluator has recorded trades.
"""

from __future__ import annotations

import sys

import pytest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
from src.optimizer_v3.core.trade_registry import get_trade_registry

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1195"),
    pytest.mark.regression,
]

_INSTRUMENT_ID = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
_BAR_SPEC = BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST)
_BAR_TYPE = BarType(_INSTRUMENT_ID, _BAR_SPEC, AggregationSource.EXTERNAL)
_BASE_TS_NS = 1_700_000_000_000_000_000


def _make_bar(idx: int, close: float = 50_000.0) -> Bar:
    p = close + idx * 5
    ts_ns = _BASE_TS_NS + idx * 900_000_000_000
    return Bar(
        bar_type=_BAR_TYPE,
        open=Price(p - 5, 2),
        high=Price(p + 50, 2),
        low=Price(p - 30, 2),
        close=Price(p, 2),
        volume=Quantity(1000.0, 8),
        ts_event=ts_ns,
        ts_init=ts_ns,
    )


def _strategy_config() -> dict:
    return {
        "name": "QA_1195_TradesList",
        "strategy_type": "Bullish",
        "blocks": [],
        "exit_conditions": [],
    }


def _backtest_config() -> dict:
    return {
        "mode": 2,
        "timeframe": "15m",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "use_multicore": False,
        "max_bars_held": 5,
        "tpsl_mode": "Fibonacci",
        "sl_mode": "Fixed",
        "confluence_threshold": 3,
        "starting_capital": 10_000,
        "risk_per_trade_pct": 1.0,
        "min_risk_reward": 1.5,
        "max_leverage": 10,
        "adaptive_sl": {"enabled": False, "volatility_lookback": 20},
    }


import src.optimizer_v3.core.institutional_signal_evaluator as _ise_module

_RealEvaluator = _ise_module.InstitutionalSignalEvaluator
_SignalResult = _ise_module.SignalEvaluationResult


class ForcedEvaluator(_RealEvaluator):
    def evaluate_bar(self, current_bar, bar_index: int, lookback_bars, total_bars=None):
        from datetime import datetime, timezone

        ts = datetime.fromtimestamp(current_bar.ts_init / 1e9, tz=timezone.utc).replace(
            tzinfo=None
        )

        if not self.current_trade and bar_index == 3:
            return _SignalResult(
                confluence_score=5,
                signals_fired=["FORCED_QA_ENTRY"],
                recheck_confirmations=[],
                should_enter=True,
                should_exit=False,
                exit_percentage=0.0,
                exit_reason="",
                timing_violations=[],
                bar_index=bar_index,
                timestamp=ts,
            )
        return _SignalResult(
            confluence_score=0,
            signals_fired=[],
            recheck_confirmations=[],
            should_enter=False,
            should_exit=False,
            exit_percentage=0.0,
            exit_reason="",
            timing_violations=[],
            bar_index=bar_index,
            timestamp=ts,
        )


# Module-level patch: swap evaluator so BacktestWorker uses ForcedEvaluator
_ise_module.InstitutionalSignalEvaluator = ForcedEvaluator


def _run_worker(bars: list, timeout_ms: int = 30_000) -> dict:
    get_trade_registry().clear()

    results_container: list = []

    def _on_finished(success: bool, results: dict) -> None:
        results_container.append((success, results))

    worker = BacktestWorker(
        strategy_config=_strategy_config(),
        backtest_config=_backtest_config(),
        cached_bars=bars,
    )
    worker.backtest_finished.connect(_on_finished, Qt.DirectConnection)
    worker.start()

    if not worker.wait(timeout_ms):
        worker.terminate()
        worker.wait()
        raise TimeoutError(
            f"BacktestWorker did not finish within {timeout_ms / 1000}s "
            f"({len(bars)} bars)"
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
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def synthetic_bars() -> list:
    return [_make_bar(i) for i in range(50)]


@pytest.fixture(scope="module")
def mode2_results(synthetic_bars: list) -> dict:
    return _run_worker(synthetic_bars)


class TestMode2TradesList:
    def test_has_trades_list_key(self, mode2_results: dict) -> None:
        assert "trades_list" in mode2_results, (
            "Mode 2 results missing 'trades_list' key — "
            "this is the BTCAAAAA-1195 regression."
        )

    def test_trades_list_is_list(self, mode2_results: dict) -> None:
        trades_list = mode2_results.get("trades_list", [])
        assert isinstance(trades_list, list), (
            f"trades_list must be a list, got {type(trades_list)}"
        )

    def test_trades_list_non_empty(self, mode2_results: dict) -> None:
        trades_list = mode2_results.get("trades_list", [])
        assert len(trades_list) > 0, (
            "trades_list is present but empty — "
            "the evaluator should have recorded at least one trade."
        )

    def test_trades_list_items_are_dicts(self, mode2_results: dict) -> None:
        for t in mode2_results.get("trades_list", []):
            assert isinstance(t, dict), (
                f"trades_list item has unexpected type: {type(t)}"
            )

    def test_has_total_candles(self, mode2_results: dict) -> None:
        assert "total_candles" in mode2_results
        assert mode2_results["total_candles"] == 50

    def test_has_trades_count(self, mode2_results: dict) -> None:
        assert "trades" in mode2_results
        assert mode2_results["trades"] > 0

    def test_trades_count_matches_list_length(self, mode2_results: dict) -> None:
        assert mode2_results["trades"] == len(mode2_results["trades_list"]), (
            "trades count must match length of trades_list"
        )

    def test_tp_adjustments_key_present(self, mode2_results: dict) -> None:
        assert "tp_adjustments" in mode2_results, (
            "Mode 2 results missing 'tp_adjustments' key"
        )

    def test_strategy_config_key_present(self, mode2_results: dict) -> None:
        assert "strategy_config" in mode2_results, (
            "Mode 2 results missing 'strategy_config' key"
        )

    def test_strategy_config_is_dict(self, mode2_results: dict) -> None:
        cfg = mode2_results.get("strategy_config", {})
        assert isinstance(cfg, dict), f"strategy_config must be a dict, got {type(cfg)}"

    def test_strategy_config_has_name_key(self, mode2_results: dict) -> None:
        cfg = mode2_results.get("strategy_config", {})
        assert "name" in cfg, "strategy_config missing 'name' key"
        assert cfg["name"] == "QA_1195_TradesList"
