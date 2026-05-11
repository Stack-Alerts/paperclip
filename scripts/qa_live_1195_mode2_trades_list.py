#!/usr/bin/env python3
"""
Live-UI QA for BTCAAAAA-1195: single-core Mode 2 trades_list fix.

Verifies that BacktestWorker in Mode 2 (Live Replay) emits backtest_finished
with a non-empty trades_list key, which was the missing element causing Config
Discovery to display 0 trades for every Mode 2 variant.

Run:
    python scripts/qa_live_1195_mode2_trades_list.py

Requirements:
  - DISPLAY must be set (real xcb); offscreen is rejected.
  - Exits 0 on pass, 1 on failure/error.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# Require real X11 — reject offscreen shortcut
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    del os.environ["QT_QPA_PLATFORM"]
os.environ.setdefault("DISPLAY", ":0")

from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication

SCREENSHOT_DIR = Path("/tmp/btcaaaaa_1195_qa")
SCREENSHOT_DIR.mkdir(exist_ok=True)

_log_lines: List[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    _log_lines.append(msg)


# ---------------------------------------------------------------------------
# Fake bar — satisfies all attribute access in BacktestWorker + tpsl_calculator
# ---------------------------------------------------------------------------
class _FakeBar:
    """Minimal bar satisfying BacktestWorker's attribute access."""

    def __init__(self, idx: int, base_price: float = 50_000.0):
        p = base_price + idx * 5
        self.open = p
        self.high = p + 50
        self.low = p - 30
        self.close = p + 10
        self.volume = 1000.0
        self.ts_init = int((1_700_000_000 + idx * 900) * 1e9)  # nanoseconds, 15m apart


# ---------------------------------------------------------------------------
# DictWrapper — mirrors BacktestWorker's internal wrapper for dict→attribute access
# ---------------------------------------------------------------------------
class _DictWrapper:
    def __init__(self, data: Dict):
        self._data = data

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        val = self._data.get(name)
        if isinstance(val, dict):
            return _DictWrapper(val)
        if isinstance(val, list):
            return [_DictWrapper(item) if isinstance(item, dict) else item for item in val]
        return val

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data


# ---------------------------------------------------------------------------
# ForcedEvaluator — overrides evaluate_bar to guarantee exactly one entry
# ---------------------------------------------------------------------------
# Import real classes so ForcedEvaluator inherits enter_trade / exit_trade
import src.optimizer_v3.core.institutional_signal_evaluator as _ise_module
_RealEvaluator = _ise_module.InstitutionalSignalEvaluator
_SignalResult = _ise_module.SignalEvaluationResult


class ForcedEvaluator(_RealEvaluator):
    """
    Evaluator that forces exactly one entry at bar index 3.
    Exit is handled by max_bars_held (5 bars) in BacktestWorker.
    Inherits enter_trade / exit_trade from InstitutionalSignalEvaluator.
    """

    def evaluate_bar(self, current_bar, bar_index: int, lookback_bars, total_bars=None):
        ts = datetime.fromtimestamp(
            current_bar.ts_init / 1e9, tz=timezone.utc
        ).replace(tzinfo=None)

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


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QA_1195_Mode2_TradesList")

    platform = app.platformName()
    log(f"Qt platform plugin: {platform}")
    if platform in ("offscreen", "minimal"):
        log(f"FAIL: Expected xcb, got '{platform}' — live-path requirement not met")
        return 1

    log(f"DISPLAY={os.environ.get('DISPLAY', '<unset>')} — xcb confirmed")

    # --- Patch evaluator before worker import resolves it ---
    _ise_module.InstitutionalSignalEvaluator = ForcedEvaluator
    log("Patched InstitutionalSignalEvaluator → ForcedEvaluator")

    from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
    from src.optimizer_v3.core.trade_registry import get_trade_registry

    # Clear registry before run
    registry = get_trade_registry()
    registry.clear()
    log(f"TradeRegistry cleared; initial count: {len(registry.get_all_trades())}")

    # Synthetic bars (50 × 15m bars)
    NUM_BARS = 50
    fake_bars = [_FakeBar(i) for i in range(NUM_BARS)]
    log(f"Created {NUM_BARS} synthetic FakeBar objects")

    # Minimal strategy config — empty blocks so evaluator init doesn't load real blocks
    strategy_config = {
        "name": "QA_Mode2_Test",
        "strategy_type": "Bullish",
        "blocks": [],
        "exit_conditions": [],
    }

    # Minimal backtest config — mode=2, short max_bars_held to guarantee exit
    backtest_config = {
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

    worker = BacktestWorker(
        strategy_config=strategy_config,
        backtest_config=backtest_config,
        cached_bars=fake_bars,
    )

    # --- Capture result ---
    result_holder: Dict[str, Any] = {}
    loop = QEventLoop()

    def on_finished(success: bool, results: dict) -> None:
        result_holder["success"] = success
        result_holder["results"] = results
        loop.quit()

    worker.backtest_finished.connect(on_finished)
    worker.start()

    # Safety timeout — 30 s
    QTimer.singleShot(30_000, loop.quit)
    loop.exec_()

    # Restore original evaluator class
    _ise_module.InstitutionalSignalEvaluator = _RealEvaluator

    if not result_holder:
        log("FAIL: backtest_finished was never emitted (timeout)")
        return 1

    success = result_holder.get("success", False)
    results = result_holder.get("results", {})

    log(f"backtest_finished: success={success}")
    log(f"  keys in results: {sorted(results.keys())}")
    log(f"  trades (count key): {results.get('trades', 'MISSING')}")
    log(f"  trades_list present: {'trades_list' in results}")
    trades_list = results.get("trades_list", "KEY_MISSING")
    if trades_list == "KEY_MISSING":
        log("FAIL: 'trades_list' key is absent from backtest_finished payload")
        return 1

    log(f"  trades_list length: {len(trades_list)}")

    if len(trades_list) == 0:
        log("FAIL: trades_list is present but empty — no trades were recorded")
        return 1

    log("PASS: trades_list is present and non-empty")
    for i, t in enumerate(trades_list[:3], 1):
        log(
            f"  Trade #{i}: entry=${t.get('entry_price', '?'):.2f}  "
            f"exit=${t.get('exit_price', '?'):.2f}  "
            f"pnl=${t.get('pnl', '?'):.2f}"
        )

    # Screenshot evidence
    screen = app.primaryScreen()
    if screen:
        shot_path = str(SCREENSHOT_DIR / "qa_1195_pass.png")
        pixmap = screen.grabWindow(0)
        if pixmap.save(shot_path):
            log(f"Screenshot saved: {shot_path}")

    # Write log artifact
    log_path = SCREENSHOT_DIR / "qa_1195_run.log"
    log_path.write_text("\n".join(_log_lines))
    log(f"Log written: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
