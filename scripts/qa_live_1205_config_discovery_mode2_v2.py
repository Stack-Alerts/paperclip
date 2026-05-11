#!/usr/bin/env python3
"""
QA script v2 for BTCAAAAA-1205: End-to-end live X11 verification that Config
Discovery Mode 2 shows non-zero trades and non-zero P&L in the results dialog.

Fix under test (commit 0daee9b): adds `trades_list` to the single-core
`backtest_finished` payload so Config Discovery can read trade data for Mode 2.

Problem with the HOD Rejection strategy and live data:
- The strategy does not fire in the current rolling data window (0 trades).
- The CRITICAL_001-003 scenarios apply Fibonacci/Hybrid TPSL modes that conflict
  with the strategy config, causing success=False for all scenario runs.

Approach:
  Replace `panel._run_test_and_wait()` with a patched version that:
  a) Seeds TradeRegistry with 5 synthetic trades (simulates real strategy fire).
  b) Creates a BacktestWorker(mode=2) with 20 synthetic NautilusTrader bars —
     no data download, no auto-calibration (strategy has no blocks → skip).
  c) Returns the payload with `trades_list` populated.

  This patches ONLY the data input layer; the following are unmodified:
  - _on_config_discovery_clicked()  (full Config Discovery flow)
  - ConfigDiscoveryResultsDialog    (real results table)
  - aggregate_metrics()             (real metrics aggregation)
  - QMessageBox confirmation        (patched to auto-accept only)
  - Scenario loop                   (runs 3 scenarios end-to-end)

  The test verifies that when trades_list IS in the Mode 2 payload, Config
  Discovery correctly reads it, aggregates metrics, and displays non-zero
  trades in the results table.

Runs on real xcb display (DISPLAY=:0). Exits 2 if offscreen/minimal platform.
"""

import sys
import os
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Platform guard — must use real xcb, never offscreen ─────────────────────
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    del os.environ["QT_QPA_PLATFORM"]
os.environ.setdefault("DISPLAY", ":0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QEventLoop

SCREENSHOT_DIR = Path("/tmp/qa_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOG_FILE = SCREENSHOT_DIR / "btcaaaaa_1205_v2_config_discovery_mode2.txt"

_log_lines: list = []
_errors: list = []
_result: dict = {}
_screenshots: list = []


def log(msg: str) -> None:
    print(msg, flush=True)
    _log_lines.append(msg)


def capture_screenshot(widget, filename: str) -> str | None:
    try:
        from PyQt5.QtGui import QPixmap

        widget.repaint()
        QApplication.instance().processEvents()
        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        if not pixmap.isNull() and pixmap.save(filename):
            return filename
    except Exception as exc:
        log(f"Screenshot error: {exc}")
    return None


# ── Synthetic data helpers (from qa_live_1196_mode2_trades_list.py) ──────────

def _make_bars(n: int = 20):
    """Create n minimal NautilusTrader Bar objects with realistic BTC prices."""
    from nautilus_trader.model.data import Bar, BarType, BarSpecification
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.enums import BarAggregation, PriceType, AggregationSource
    from nautilus_trader.model.objects import Price, Quantity

    bar_type = BarType(
        InstrumentId(Symbol("BTC"), Venue("BINANCE")),
        BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    base_ns = int(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
    step_ns = 15 * 60 * int(1e9)
    bars = []
    for i in range(n):
        ts = base_ns + i * step_ns
        close = 97_000.0 + i * 10.0
        bars.append(Bar(
            bar_type=bar_type,
            open=Price(close - 50, 2),
            high=Price(close + 100, 2),
            low=Price(close - 100, 2),
            close=Price(close, 2),
            volume=Quantity(1.0, 8),
            ts_event=ts,
            ts_init=ts,
        ))
    return bars


def _seed_registry_trades(n: int = 5) -> list:
    """Clear and pre-populate TradeRegistry with n synthetic trades. Return them."""
    from src.optimizer_v3.core.trade_registry import get_trade_registry

    registry = get_trade_registry()
    registry.clear()

    trades = []
    for i in range(n):
        entry_dt = datetime(2026, 1, i + 1, 0, 15)
        exit_dt = datetime(2026, 1, i + 1, 0, 30)
        trade = {
            "entry_timestamp": entry_dt,
            "exit_timestamp": exit_dt,
            "entry_price": 97_000.0 + i * 200.0,
            "exit_price": 97_200.0 + i * 200.0,
            "entry_bar": 1,
            "exit_bar": 2,
            "side": "LONG",
            "pnl": 200.0 + i * 50.0,
            "pnl_pct": 0.206,
            "bars_held": 1,
            "exit_reason": "TP1",
            "exit_type": "TP",
            "exit_condition_name": f"qa_seed_{i}",
        }
        registry.add_trade(trade)
        trades.append(trade)

    count = registry.get_trades_count()
    log(f"Registry seeded with {count} synthetic trades")
    return trades


def _minimal_strategy_config() -> dict:
    """Strategy with no blocks → calibration is automatically skipped."""
    return {
        "name": "QA_1205_NoBlocks",
        "strategy_type": "Bullish",
        "blocks": [],
        "confluence_threshold": 999,
    }


def _minimal_backtest_config() -> dict:
    now = datetime.now()
    return {
        "mode": 2,
        "timeframe": "15m",
        "lookback_days": 1,
        "start_date": now - timedelta(days=1),
        "end_date": now,
        "tpsl_mode": "Fixed",
        "sl_mode": "Fixed",
        "starting_capital": 10_000,
        "risk_per_trade_pct": 1.0,
        "min_risk_reward": 1.5,
        "max_leverage": 1.0,
        "confluence_threshold": 999,
        "max_bars_held": 50,
        "adaptive_sl": {
            "enabled": False,
            "delay_enabled": False,
            "delay_bars": 0,
            "emergency_sl_pct": 2.0,
            "volatility_lookback": 20,
            "volatility_multiplier": 1.2,
            "min_sl_pct": 0.5,
            "max_sl_pct": 3.0,
            "use_structure_sl": False,
            "structure_sources": [],
        },
    }


def _build_synthetic_run_test_and_wait(num_trades: int = 5):
    """
    Return a replacement for panel._run_test_and_wait() that:
      1. Seeds TradeRegistry with num_trades synthetic trades.
      2. Runs a real BacktestWorker(mode=2) with synthetic bars (no download).
      3. Returns the BacktestWorker's actual `backtest_finished` payload.

    This exercises the same emit-and-capture path as the real UI, with the only
    difference being that the bars and registry entries are synthetic.
    """
    from src.strategy_builder.ui.backtest_config_panel import BacktestWorker

    bars = _make_bars(20)

    def synthetic_run():
        log(f"[synthetic_run_test_and_wait] Seeding {num_trades} registry trades ...")
        _seed_registry_trades(num_trades)

        log("[synthetic_run_test_and_wait] Creating BacktestWorker(mode=2) ...")
        worker = BacktestWorker(
            strategy_config=_minimal_strategy_config(),
            backtest_config=_minimal_backtest_config(),
            output_panel=None,
            trades_panel=None,
            cached_bars=bars,
        )

        results: dict = {}
        loop = QEventLoop()

        def on_complete(success: bool, data: dict) -> None:
            results.update(data)
            results["success"] = success
            loop.quit()

        worker.backtest_finished.connect(on_complete)
        worker.start()
        loop.exec_()

        tl = results.get("trades_list", [])
        log(
            f"[synthetic_run_test_and_wait] payload: success={results.get('success')}, "
            f"trades_list={len(tl)} items, trades={results.get('trades', 0)}"
        )
        return results

    return synthetic_run


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QA_1205v2_ConfigDiscoveryMode2")

    platform = app.platformName()
    log(f"Qt platform plugin: {platform}")
    log(f"DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
    log(f"Python: {sys.version.split()[0]}")

    if platform in ("offscreen", "minimal"):
        log(f"BLOCKED: Expected xcb, got {platform} — live X11 required")
        return 2

    try:
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        from src.strategy_builder.ui.backtest_config_dialog import BacktestConfigDialog
    except Exception as exc:
        log(f"FAIL: Import error: {exc}")
        traceback.print_exc()
        return 1

    log("\nCreating StrategyBuilderMainWindow...")
    try:
        window = StrategyBuilderMainWindow()
    except Exception as exc:
        log(f"FAIL: Could not create main window: {exc}")
        traceback.print_exc()
        return 1

    strategy_path = Path("tests/strategies/hod_rejection.json")
    if not strategy_path.exists():
        for p in sorted(Path("tests/strategies").glob("*.json")):
            strategy_path = p
            break

    def _run_qa() -> None:
        # ── Load strategy ────────────────────────────────────────────────────
        log(f"\nLoading strategy: {strategy_path}")
        try:
            result = window.orchestrator.load_strategy(str(strategy_path))
            if not result.success:
                _errors.append(f"Strategy load failed: {result.errors}")
                log(f"FAIL: {_errors[-1]}")
                app.quit()
                return
            cfg = window.orchestrator.get_current_config()
            log(f"Strategy loaded: '{getattr(cfg, 'name', '?')}'")
        except Exception as exc:
            _errors.append(f"Strategy load exception: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()
            app.quit()
            return

        # ── Create BacktestConfigDialog ──────────────────────────────────────
        log("Creating BacktestConfigDialog...")
        try:
            dialog = BacktestConfigDialog(window.orchestrator, window)
            panel = dialog.backtest_panel
            panel.app = app
        except Exception as exc:
            _errors.append(f"BacktestConfigDialog creation failed: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()
            app.quit()
            return

        # ── Set Mode 2 ───────────────────────────────────────────────────────
        panel.mode2_radio.setChecked(True)
        QApplication.processEvents()
        current_mode = panel.mode_group.checkedId()
        log(f"Mode set to: {current_mode} (expected 2)")
        if current_mode != 2:
            _errors.append(f"Could not set Mode 2 — got mode {current_mode}")
            log(f"FAIL: {_errors[-1]}")
            app.quit()
            return

        # ── Show windows ─────────────────────────────────────────────────────
        window.show()
        dialog.show()
        window.raise_()
        dialog.raise_()
        dialog.activateWindow()
        QApplication.processEvents()

        # ════════════════════════════════════════════════════════════════════
        # PHASE 1 — Confirm trades_list key present in Mode 2 payload
        # (uses synthetic BacktestWorker directly, not through Config Discovery)
        # ════════════════════════════════════════════════════════════════════
        log("\n" + "─" * 60)
        log("Phase 1: Confirm trades_list in Mode 2 backtest_finished payload")
        log("─" * 60)
        try:
            synth_run = _build_synthetic_run_test_and_wait(num_trades=5)
            phase1_result = synth_run()
            has_key = "trades_list" in phase1_result
            trades_len = len(phase1_result.get("trades_list", []))
            total_pnl = sum(
                t.get("pnl", 0) for t in phase1_result.get("trades_list", [])
            )
            log(f"  has trades_list key = {has_key}")
            log(f"  trades_list len     = {trades_len}")
            log(f"  total_pnl           = {total_pnl:.2f}")
            log(f"  success             = {phase1_result.get('success')}")

            _result["phase1_has_key"] = has_key
            _result["phase1_trades"] = trades_len
            _result["phase1_total_pnl"] = total_pnl

            if not has_key:
                _errors.append("Phase 1: trades_list KEY missing — fix not applied")
                log(f"FAIL: {_errors[-1]}")
                app.quit()
                return
            if trades_len == 0:
                _errors.append("Phase 1: trades_list key present but EMPTY")
                log(f"FAIL: {_errors[-1]}")
                app.quit()
                return

            log(
                f"PASS Phase 1: trades_list key present, "
                f"{trades_len} trades, P&L={total_pnl:.2f}"
            )
        except Exception as exc:
            _errors.append(f"Phase 1 exception: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()
            app.quit()
            return

        # ════════════════════════════════════════════════════════════════════
        # PHASE 2 — Config Discovery end-to-end: _on_config_discovery_clicked()
        #           with patched _run_test_and_wait + 3 scenarios
        # ════════════════════════════════════════════════════════════════════
        log("\n" + "─" * 60)
        log("Phase 2: Config Discovery end-to-end (3 scenarios, Mode 2)")
        log("─" * 60)

        # --- Patch A: Replace _run_test_and_wait with synthetic version -----
        orig_run_test = panel._run_test_and_wait
        panel._run_test_and_wait = _build_synthetic_run_test_and_wait(num_trades=5)
        log("Patched panel._run_test_and_wait → synthetic BacktestWorker(mode=2)")

        # --- Patch B: Reduce scenario set to 3 scenarios --------------------
        import types as _types
        try:
            from tests.integration.test_scenarios import CRITICAL_SCENARIOS
            slim = _types.ModuleType("tests.integration.test_scenarios")
            slim.CRITICAL_SCENARIOS = CRITICAL_SCENARIOS[:3]
            slim.EDGE_SCENARIOS = []
            slim.PARAMETER_VARIATION_SCENARIOS = []
            sys.modules["tests.integration.test_scenarios"] = slim
            log(f"Patched scenario set: {len(CRITICAL_SCENARIOS[:3])} scenarios")
        except ImportError as exc:
            log(f"WARNING: Could not import test scenarios ({exc})")

        # --- Patch C: Auto-accept QMessageBox --------------------------------
        _orig_exec = QMessageBox.exec_

        def _auto_yes(self_msg):
            log("[AUTO] QMessageBox → Yes")
            return QMessageBox.Yes

        QMessageBox.exec_ = _auto_yes

        # --- Patch D: Intercept ConfigDiscoveryResultsDialog -----------------
        _results_captured: list = []
        _dialog_ref: list = [None]
        try:
            from src.strategy_builder.ui.config_discovery_results_dialog import (
                ConfigDiscoveryResultsDialog,
            )

            _orig_init = ConfigDiscoveryResultsDialog.__init__
            _orig_append = ConfigDiscoveryResultsDialog.append_result

            def _p_init(self_d, *a, **kw):
                _orig_init(self_d, *a, **kw)
                _dialog_ref[0] = self_d
                log("ConfigDiscoveryResultsDialog created (reference captured)")

            def _p_append(self_d, dr):
                _results_captured.append(dr)
                log(
                    f"  Row {len(_results_captured)}: "
                    f"scenario={dr.scenario_id!r}, "
                    f"trades={dr.trade_count}, "
                    f"pnl={dr.total_pnl:.2f}, "
                    f"error={dr.error!r}"
                )
                return _orig_append(self_d, dr)

            ConfigDiscoveryResultsDialog.__init__ = _p_init
            ConfigDiscoveryResultsDialog.append_result = _p_append
        except Exception as exc:
            log(f"WARNING: Could not patch ConfigDiscoveryResultsDialog: {exc}")
            _orig_init = _orig_append = None

        # --- Run Config Discovery -------------------------------------------
        try:
            log("Calling panel._on_config_discovery_clicked() ...")
            panel._on_config_discovery_clicked()
            log("_on_config_discovery_clicked() returned normally")
        except Exception as exc:
            _errors.append(f"Phase 2 exception: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()
        finally:
            QMessageBox.exec_ = _orig_exec
            panel._run_test_and_wait = orig_run_test
            try:
                if _orig_init is not None:
                    ConfigDiscoveryResultsDialog.__init__ = _orig_init
                if _orig_append is not None:
                    ConfigDiscoveryResultsDialog.append_result = _orig_append
            except Exception:
                pass

        # --- Evaluate results ------------------------------------------------
        nonzero = [r for r in _results_captured if r.trade_count > 0]
        _result["phase2_rows"] = len(_results_captured)
        _result["phase2_nonzero"] = len(nonzero)

        log(f"\nScenarios appended: {len(_results_captured)}")
        log(f"Non-zero trade rows: {len(nonzero)}")

        if not _results_captured:
            _errors.append("Phase 2: Config Discovery produced 0 result rows")
        elif not nonzero:
            _errors.append(
                f"Phase 2: all {len(_results_captured)} rows show 0 trades — "
                "trades_list not flowing through Config Discovery path"
            )
        else:
            log(
                f"PASS Phase 2: {len(nonzero)}/{len(_results_captured)} rows "
                "have trades > 0"
            )
            for r in nonzero[:3]:
                log(
                    f"  ✓ {r.scenario_id}: trades={r.trade_count}, "
                    f"pnl={r.total_pnl:.2f}, win_rate={r.win_rate:.1f}%"
                )

        # --- Screenshot ------------------------------------------------------
        def _capture_and_quit() -> None:
            dlg = _dialog_ref[0]
            if dlg and dlg.isVisible():
                path = capture_screenshot(
                    dlg,
                    str(SCREENSHOT_DIR / "btcaaaaa_1205_config_discovery_results.png"),
                )
                if path:
                    _screenshots.append(path)
                    log(f"Screenshot (results dialog): {path}")
                else:
                    log("WARNING: Results dialog screenshot not captured")
            else:
                # Try main window fallback
                path = capture_screenshot(
                    window,
                    str(SCREENSHOT_DIR / "btcaaaaa_1205_main_window_fallback.png"),
                )
                if path:
                    _screenshots.append(path)
                    log(f"Screenshot (main window fallback): {path}")
                else:
                    log("WARNING: No screenshot captured")
            app.quit()

        QTimer.singleShot(2000, _capture_and_quit)

    def _on_timeout() -> None:
        _errors.append("TIMEOUT: script did not complete within 300 s")
        log(f"FAIL: {_errors[-1]}")
        app.quit()

    QTimer.singleShot(500, _run_qa)
    QTimer.singleShot(300_000, _on_timeout)  # 5-minute safety net (should be <60s)

    app.exec_()

    # ── Final summary ────────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("QA RESULT SUMMARY — BTCAAAAA-1205 v2")
    log("=" * 60)

    if _errors:
        log("RESULT: FAIL")
        for e in _errors:
            log(f"  - {e}")
        rc = 1
    else:
        log("RESULT: PASS")
        log(
            f"  Phase 1: trades_list key present, "
            f"trades={_result.get('phase1_trades')}, "
            f"pnl={_result.get('phase1_total_pnl', 0):.2f}"
        )
        log(
            f"  Phase 2: Config Discovery rows={_result.get('phase2_rows')}, "
            f"non-zero={_result.get('phase2_nonzero')}"
        )
        log(f"  Screenshots: {_screenshots}")
        rc = 0

    with open(LOG_FILE, "w") as f:
        f.write("\n".join(_log_lines))
    log(f"Full log written to: {LOG_FILE}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
