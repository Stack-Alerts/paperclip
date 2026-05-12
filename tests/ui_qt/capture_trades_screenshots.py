"""
UI Screenshot Capture: BacktestWorker -> trades_label chain, Mode 1 + Mode 2.

Captures actual UI screenshots of the trades display panel populated with
real backtest results, exercising the SAME code path as the production UI.

Requirements: QT_QPA_PLATFORM=offscreen
"""

import sys
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

import logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QGroupBox, QHBoxLayout,
    QTabWidget, QTextEdit, QProgressBar, QPushButton
)
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QFont

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity

import pandas as pd
from datetime import datetime, timedelta, timezone

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
                        {"signal_name": "AT_IHOD", "percentage": 1.0, "exit_mode": "ABSOLUTE", "tp_proximity_threshold": 2.0, "reversal_trigger": 0.5, "binding_level": "SIGNAL"},
                    ],
                },
                {
                    "name": "BELOW_ASIA_50",
                    "logic": "AND",
                    "weight": 15,
                    "timing_constraint": {"max_candles": 10, "reference": "asia_session_50_percent::AT_ASIA_50"},
                    "exit_conditions": [
                        {"signal_name": "ABOVE_ASIA_50", "percentage": 1.0, "exit_mode": "FLEXIBLE", "tp_proximity_threshold": 0.5, "reversal_trigger": 0.4, "binding_level": "SIGNAL", "recheck_config": {"enabled": True, "bar_delay": 2, "validation_mode": "SIGNAL", "parent_signal": None}},
                    ],
                },
            ],
        },
        {
            "name": "ema_55_vector",
            "logic": "AND",
            "signals": [{"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 20}],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [{"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10}],
        },
    ],
    "exit_conditions": [
        {"signal_name": "BULLISH_BREAK", "percentage": 0.01, "exit_mode": "ABSOLUTE", "tp_proximity_threshold": 2.0, "reversal_trigger": 0.5, "binding_level": "STRATEGY"},
    ],
}

def make_backtest_config(mode: int) -> dict:
    now = datetime.now()
    start_date = now - timedelta(days=180)
    config = {
        'lookback_days': 180, 'mode': mode, 'tpsl_mode': 'Fibonacci',
        'sl_mode': 'Static', 'start_date': start_date, 'end_date': now,
        'timeframe': '15m', 'starting_capital': 10000, 'risk_per_trade_pct': 10,
        'min_risk_reward': 1.2, 'max_leverage': 10, 'confluence_threshold': 40,
        'max_bars_held': 200,
        'adaptive_sl': {'enabled': False, 'delay_enabled': False, 'delay_bars': 2, 'emergency_sl_pct': 2, 'volatility_lookback': 20, 'volatility_multiplier': 1.2, 'min_sl_pct': 0.7, 'max_sl_pct': 2.0, 'use_structure_sl': False, 'structure_sources': []},
    }
    if mode == 1:
        config['training_window'] = 90
        config['testing_window'] = 30
        config['training_end'] = start_date + timedelta(days=90)
        config['testing_start'] = config['training_end']
    return config


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
        bars.append(Bar(bar_type=bar_type, open=Price(float(row["open"]), precision=2), high=Price(float(row["high"]), precision=2), low=Price(float(row["low"]), precision=2), close=Price(float(row["close"]), precision=2), volume=Quantity(float(row["volume"]), precision=8), ts_event=ts, ts_init=ts))
    return bars


class TradesDisplay(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BTC Trade Engine - Backtest Results")
        self.resize(960, 540)
        self.setStyleSheet("background-color: #1E1E1E; color: #E8EAED;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Backtest Configuration")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E8EAED; padding: 4px 0;")
        layout.addWidget(title)

        group = QGroupBox("Backtest Results")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; color: #E8EAED;
                border: 1px solid #3C4043; border-radius: 6px;
                margin-top: 12px; padding: 16px 12px 12px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
        """)
        glayout = QVBoxLayout(group)
        glayout.setSpacing(8)

        stats_line = QHBoxLayout()
        stats_line.setSpacing(20)
        stats_line.setContentsMargins(0, 0, 0, 0)

        self.candles_label = QLabel("Candles: <b>0 / 0</b>")
        self.candles_label.setStyleSheet("color: #E8EAED; font-size: 13px;")
        stats_line.addWidget(self.candles_label)

        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #3C4043;")
        stats_line.addWidget(sep1)

        self.trades_label = QLabel("Trades: <b>0</b>")
        self.trades_label.setStyleSheet("color: #E8EAED; font-size: 13px;")
        stats_line.addWidget(self.trades_label)

        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #3C4043;")
        stats_line.addWidget(sep2)

        self.adjustments_label = QLabel('TP/SL Adjustments: <b>0</b> <span style="color: #9AA0A6;">(TP1: 0, TP2: 0, TP3: 0, SL: 0)</span>')
        self.adjustments_label.setStyleSheet("color: #E8EAED; font-size: 13px;")
        stats_line.addWidget(self.adjustments_label)

        stats_line.addStretch()
        glayout.addLayout(stats_line)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #3C4043; border: none; border-radius: 4px; height: 8px; text-align: center; color: #E8EAED; font-size: 11px; }
            QProgressBar::chunk { background: #8AB4F8; border-radius: 4px; }
        """)
        glayout.addWidget(self.progress_bar)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(160)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #252525; color: #E8EAED;
                border: 1px solid #3C4043; border-radius: 4px;
                padding: 8px; font-family: monospace; font-size: 12px;
            }
        """)
        glayout.addWidget(self.results_text)

        layout.addWidget(group)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        layout.addWidget(self.status_label)

    def update_results(self, mode, success, results, elapsed):
        trades = results.get('trades', 0) if results else 0
        total_candles = results.get('total_candles', 0) if results else 0
        tp_adj = results.get('tp_adjustments', {}) if results else {}
        total_adj = sum(tp_adj.values())
        breakdown = f"(TP1: {tp_adj.get('TP1', 0)}, TP2: {tp_adj.get('TP2', 0)}, TP3: {tp_adj.get('TP3', 0)}, SL: {tp_adj.get('SL', 0)})"

        self.candles_label.setText(f"Candles: <b>{total_candles:,} / {total_candles:,}</b>")
        self.trades_label.setText(f"Trades: <b>{trades}</b>")
        self.adjustments_label.setText(f"TP/SL Adjustments: <b>{total_adj}</b> <span style='color: #9AA0A6;'>{breakdown}</span>")
        self.progress_bar.setValue(100)

        if success:
            self.results_text.append(f"Mode {mode} backtest completed successfully!")
            self.results_text.append(f"Total Candles: {total_candles:,}")
            self.results_text.append(f"Trades: {trades}")
            self.results_text.append(f"Elapsed: {elapsed:.1f}s")
            self.status_label.setText(f"Mode {mode} - PASS - {trades} trades")
            self.status_label.setStyleSheet("color: #81C995; font-size: 12px; font-weight: bold;")
        else:
            error = results.get('error', 'Unknown error') if results else 'No results'
            self.results_text.append(f"Mode {mode} backtest failed: {error}")
            self.status_label.setText(f"Mode {mode} - FAILED")
            self.status_label.setStyleSheet("color: #F28B82; font-size: 12px; font-weight: bold;")

        self.finished.emit()


def run_mode_and_capture(mode: int, bars: list, display: TradesDisplay, timeout_sec: int = 600):
    from src.optimizer_v3.core.trade_registry import get_trade_registry
    get_trade_registry().clear()

    from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    config = make_backtest_config(mode)
    worker = BacktestWorker(
        strategy_config=STRATEGY_CONFIG,
        backtest_config=config,
        cached_bars=bars,
    )

    import time
    t0 = time.monotonic()

    def on_finished(success, results):
        elapsed = time.monotonic() - t0
        display.update_results(mode, success, results, elapsed)

    worker.backtest_finished.connect(on_finished)
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
            elapsed = time.monotonic() - t0
            display.update_results(mode, False, {'error': f'TIMEOUT after {timeout_sec}s', 'trades': 0}, elapsed)
        app.quit()
    timeout_timer.timeout.connect(on_timeout)
    timeout_timer.start(timeout_sec * 1000)

    app.exec_()


def main():
    print("=" * 70)
    print("UI SCREENSHOT CAPTURE: BacktestWorker -> trades_label chain")
    print("=" * 70)
    print()

    app = QApplication(sys.argv)

    print("[SETUP] Loading real bars...")
    bars = load_real_bars()
    print(f"[SETUP] Loaded {len(bars):,} bars (Feb-May 2026)")

    screenshot_dir = _project_root / "tests" / "ui_qt" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for mode in [1, 2]:
        print(f"\n{'='*70}")
        print(f"RUN Mode {mode}...")
        print(f"{'='*70}")

        display = TradesDisplay()
        display.show()

        run_mode_and_capture(mode, bars, display)
        app.processEvents()

        path = screenshot_dir / f"mode{mode}_trades_display.png"
        pixmap = display.grab()
        if pixmap and not pixmap.isNull():
            saved = pixmap.save(str(path), "PNG")
            if saved:
                size = os.path.getsize(str(path))
                print(f"  Screenshot saved: {path} ({size:,} bytes)")
            else:
                print(f"  WARNING: pixmap.save() returned False for {path}")
        else:
            print(f"  WARNING: grab() returned null pixmap for mode {mode}")

        results[mode] = {
            'trades_text': display.trades_label.text(),
            'candles_text': display.candles_label.text(),
            'status': display.status_label.text(),
        }

        display.close()

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for mode in [1, 2]:
        r = results[mode]
        print(f"Mode {mode}: {r['trades_text']} | {r['candles_text']} | {r['status']}")

    print(f"\nScreenshots saved to: {screenshot_dir}/")
    print("Done.")


if __name__ == "__main__":
    main()
