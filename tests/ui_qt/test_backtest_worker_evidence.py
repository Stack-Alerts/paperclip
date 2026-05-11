"""
UI Evidence Capture: Mode 1 + Mode 2 backtest via BacktestWorker.

Captures the exact trades_label text and any errors that would be displayed
in the Live Output tab when running backtests through the UI worker path.

This exercises the SAME code path as the full PyQt5 UI (BacktestWorker QThread)
without requiring X11/Xvfb — uses QT_QPA_PLATFORM=offscreen.

Reports:
  - Mode 1 (Historical, multicore) trades_label text
  - Mode 2 (Live Replay, single-core bar-by-bar) trades_label text
  - Any exceptions or errors from stderr
"""

import sys
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

import logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Strategy config — matches current_strategy.json AND test_btcaaaaa_745
# ---------------------------------------------------------------------------

STRATEGY_CONFIG: dict = {
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
                    "weight": 15,
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
                        "max_candles": 10,
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
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 20},
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

def make_backtest_config(mode: int) -> dict:
    now = datetime.now()
    lookback_days = 180
    start_date = now - timedelta(days=lookback_days)

    config = {
        'lookback_days': lookback_days,
        'mode': mode,
        'tpsl_mode': 'Fibonacci',
        'sl_mode': 'Static',
        'start_date': start_date,
        'end_date': now,
        'timeframe': '15m',
        'starting_capital': 10000,
        'risk_per_trade_pct': 10,
        'min_risk_reward': 1.2,
        'max_leverage': 10,
        'confluence_threshold': 40,
        'max_bars_held': 200,
        'adaptive_sl': {
            'enabled': False,
            'delay_enabled': False,
            'delay_bars': 2,
            'emergency_sl_pct': 2,
            'volatility_lookback': 20,
            'volatility_multiplier': 1.2,
            'min_sl_pct': 0.7,
            'max_sl_pct': 2.0,
            'use_structure_sl': False,
            'structure_sources': [],
        },
    }

    if mode == 1:
        config['training_window'] = 90
        config['testing_window'] = 30
        config['training_end'] = start_date + timedelta(days=90)
        config['testing_start'] = config['training_end']

    return config


# ---------------------------------------------------------------------------
# Bar-loading helper (same as test_btcaaaaa_745)
# ---------------------------------------------------------------------------

DATA_DIR = _project_root / "data" / "binance"
MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05"]


def load_real_bars() -> list:
    dfs = []
    for month in MONTHS:
        path = DATA_DIR / month / f"BTCUSDT_PERP_15m_{month}.parquet"
        if path.exists():
            dfs.append(pd.read_parquet(path))

    if not dfs:
        raise RuntimeError(f"No 15m parquet files found under {DATA_DIR}")

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
# Signal collector — captures signals that the UI uses to set trades_label
# ---------------------------------------------------------------------------

class SignalCollector(QObject):
    """Collects BacktestWorker signals to mimic what BacktestConfigPanel does."""

    finished = pyqtSignal(bool, dict)
    progress = pyqtSignal(int, int, str)
    live_msg = pyqtSignal(str, str, str)
    trade_data = pyqtSignal(dict)
    status_msg = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.messages = []
        self.trades_count = 0
        self.trades_label_text = "Trades: <b>0</b>"
        self.error_text = None
        self.success = None
        self.results = None

    def on_live_message(self, msg, level, category):
        self.messages.append((level, category, msg))

    def on_trade_data(self, data):
        pass

    def on_status_message(self, msg):
        self.messages.append(("INFO", "STATUS", msg))

    def on_progress(self, current, total, msg):
        pass

    def on_finished(self, success, results):
        self.success = success
        self.results = results
        trades = results.get('trades', 0) if results else 0
        self.trades_count = trades
        self.trades_label_text = f"Trades: <b>{trades}</b>"
        if not success:
            self.error_text = results.get('error', 'Unknown error') if results else 'No results'
        self.finished.emit(success, results)


def run_backtest(mode: int, bars: list, timeout_sec: int = 600) -> dict:
    """
    Run BacktestWorker in mode 1 or 2 and capture results.

    Returns dict with keys: success, trades_count, trades_label_text,
    error_text, messages, elapsed_sec.
    """
    from src.optimizer_v3.core.trade_registry import get_trade_registry
    get_trade_registry().clear()

    from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    config = make_backtest_config(mode)
    collector = SignalCollector()

    worker = BacktestWorker(
        strategy_config=STRATEGY_CONFIG,
        backtest_config=config,
        cached_bars=bars,
    )
    worker.live_message.connect(collector.on_live_message)
    worker.trade_data_emit.connect(collector.on_trade_data)
    worker.status_message.connect(collector.on_status_message)
    worker.progress_updated.connect(collector.on_progress)
    worker.backtest_finished.connect(collector.on_finished)

    import time
    t0 = time.monotonic()

    worker.start()

    def check_done():
        if not worker.isRunning():
            app.quit()

    timer = QTimer()
    timer.timeout.connect(check_done)
    timer.start(100)

    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)

    def on_timeout():
        if worker.isRunning():
            worker.stop()
            worker.wait(5000)
            collector.success = False
            collector.error_text = f"TIMEOUT after {timeout_sec}s"
            collector.trades_label_text = "Trades: <b>0</b>"
            collector.trades_count = 0
            collector.finished.emit(False, {'error': collector.error_text})
        app.quit()

    timeout_timer.timeout.connect(on_timeout)
    timeout_timer.start(timeout_sec * 1000)

    app.exec_()

    elapsed = time.monotonic() - t0

    # Collect all error messages
    errors = [m[2] for m in collector.messages if m[0] == "ERROR"]

    return {
        'success': collector.success,
        'trades_count': collector.trades_count,
        'trades_label_text': collector.trades_label_text,
        'error_text': collector.error_text,
        'errors': errors,
        'all_messages': collector.messages,
        'elapsed_sec': elapsed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("UI EVIDENCE CAPTURE: BacktestWorker (UI code path)")
    print("=" * 80)
    print()

    app = QApplication(sys.argv)

    print(f"[SETUP] Loading real bars from {DATA_DIR}...")
    try:
        bars = load_real_bars()
        print(f"[SETUP] Loaded {len(bars):,} bars (Feb-May 2026)")
    except Exception as e:
        print(f"[SETUP] FAILED to load bars: {e}")
        sys.exit(1)

    print()
    print("-" * 80)
    print("RUN 1: Mode 1 (Historical, multicore)")
    print("-" * 80)
    sys.stdout.flush()
    result1 = run_backtest(mode=1, bars=bars)
    print(f"  Success: {result1['success']}")
    print(f"  Trades count: {result1['trades_count']}")
    print(f"  Trades label text: {result1['trades_label_text']}")
    print(f"  Elapsed: {result1['elapsed_sec']:.1f}s")
    if result1['error_text']:
        print(f"  Error: {result1['error_text']}")
    if result1['errors']:
        print(f"  Live Output errors:")
        for e in result1['errors']:
            print(f"    ERROR: {e}")
    sys.stdout.flush()

    print()
    print("-" * 80)
    print("RUN 2: Mode 2 (Live Replay, bar-by-bar sequential)")
    print("-" * 80)
    sys.stdout.flush()
    result2 = run_backtest(mode=2, bars=bars)
    print(f"  Success: {result2['success']}")
    print(f"  Trades count: {result2['trades_count']}")
    print(f"  Trades label text: {result2['trades_label_text']}")
    print(f"  Elapsed: {result2['elapsed_sec']:.1f}s")
    if result2['error_text']:
        print(f"  Error: {result2['error_text']}")
    if result2['errors']:
        print(f"  Live Output errors:")
        for e in result2['errors']:
            print(f"    ERROR: {e}")
    sys.stdout.flush()

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Mode 1 trades_label = {result1['trades_label_text']}")
    print(f"Mode 2 trades_label = {result2['trades_label_text']}")
    if result1['error_text'] or result2['error_text']:
        print("ERRORS DETECTED:")
        if result1['error_text']:
            print(f"  Mode 1: {result1['error_text']}")
        if result2['error_text']:
            print(f"  Mode 2: {result2['error_text']}")
    else:
        print("No errors detected")

    if result1['trades_count'] == 0:
        print("WARNING: Mode 1 produced ZERO trades - ZERO TRADES regression confirmed")
    if result2['trades_count'] == 0:
        print("WARNING: Mode 2 produced ZERO trades - ZERO TRADES regression confirmed")

    print()
    print("Full message log follows:")
    print()
    for mode_name, result in [("MODE 1", result1), ("MODE 2", result2)]:
        print(f"--- {mode_name} messages ---")
        for level, category, msg in result['all_messages']:
            print(f"  [{level}][{category}] {msg}")
