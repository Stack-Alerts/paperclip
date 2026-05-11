#!/usr/bin/env python3
"""
QA script for BTCAAAAA-1205: End-to-end live X11 verification that Config Discovery
Mode 2 shows non-zero trades and non-zero P&L.

The fix (commit 0daee9b) adds `trades_list` to the single-core `backtest_finished`
payload.  BTCAAAAA-1195 verified the BacktestWorker path; this script verifies the
full Config Discovery UI dialog end-to-end in Mode 2.

Test phases:
  Phase 1 — Mode 2 baseline: call _run_test_and_wait() directly, assert trades_list > 0.
  Phase 2 — Config Discovery end-to-end: drive _on_config_discovery_clicked() with
             patched QMessageBox (auto-Yes) and a 3-scenario subset; assert at least
             one variant row shows trade_count > 0 in the results dialog.

Runs on real xcb display (DISPLAY=:0). Exits 2 if offscreen/minimal platform.
"""

import sys
import os
import types
import traceback
from pathlib import Path

# ── Platform guard — must use real xcb, never offscreen ─────────────────────
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    del os.environ["QT_QPA_PLATFORM"]
os.environ.setdefault("DISPLAY", ":0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

SCREENSHOT_DIR = Path("/tmp/qa_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOG_FILE = SCREENSHOT_DIR / "btcaaaaa_1205_config_discovery_mode2.txt"

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


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QA_1205_ConfigDiscoveryMode2")

    platform = app.platformName()
    log(f"Qt platform plugin: {platform}")
    log(f"DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
    log(f"Python: {sys.version.split()[0]}")

    if platform in ("offscreen", "minimal"):
        log(f"BLOCKED: Expected xcb, got {platform} — live X11 required")
        return 2

    # ── Import UI components ────────────────────────────────────────────────
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

    # ── Choose strategy ─────────────────────────────────────────────────────
    strategy_path = Path("tests/strategies/hod_rejection.json")
    if not strategy_path.exists():
        for p in sorted(Path("tests/strategies").glob("*.json")):
            strategy_path = p
            break
    if not strategy_path.exists():
        log("FAIL: No strategy JSON found in tests/strategies/")
        return 1

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

        # ── Create BacktestConfigDialog + panel ──────────────────────────────
        log("Creating BacktestConfigDialog...")
        try:
            dialog = BacktestConfigDialog(window.orchestrator, window)
            panel = dialog.backtest_panel
            # _run_test_and_wait uses self.app — inject it
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

        # ── Show UI ──────────────────────────────────────────────────────────
        window.show()
        dialog.show()
        window.raise_()
        dialog.raise_()
        dialog.activateWindow()
        QApplication.processEvents()

        # ════════════════════════════════════════════════════════════════════
        # PHASE 1 — Verify Mode 2 _run_test_and_wait returns trades_list
        # ════════════════════════════════════════════════════════════════════
        log("\n" + "─" * 60)
        log("Phase 1: Mode 2 baseline via _run_test_and_wait()")
        log("─" * 60)
        try:
            baseline = panel._run_test_and_wait()
            trades_list = baseline.get("trades_list", [])
            success = baseline.get("success", False)
            has_key = "trades_list" in baseline
            log(f"  success          = {success}")
            log(f"  has trades_list  = {has_key}")
            log(f"  trades_list len  = {len(trades_list)}")
            log(f"  trades (count)   = {baseline.get('trades', 0)}")

            _result["phase1_has_key"] = has_key
            _result["phase1_trades"] = len(trades_list)

            if not success:
                _errors.append(
                    f"Phase 1: Mode 2 backtest failed: {baseline.get('error', 'unknown')}"
                )
                log(f"FAIL: {_errors[-1]}")
            elif not has_key:
                _errors.append("Phase 1: 'trades_list' key missing — fix not applied")
                log(f"FAIL: {_errors[-1]}")
            elif len(trades_list) == 0:
                _errors.append(
                    "Phase 1: trades_list is empty — strategy produced no trades "
                    "in the backtest window (may need more lookback days)"
                )
                log(f"WARN: {_errors[-1]}")
            else:
                total_pnl = sum(t.get("pnl", 0) for t in trades_list)
                _result["phase1_total_pnl"] = total_pnl
                log(
                    f"  PASS: {len(trades_list)} trades, total P&L = {total_pnl:.2f}"
                )
        except Exception as exc:
            _errors.append(f"Phase 1 exception: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()

        # If Phase 1 hard-failed (no key or exception), abort
        if _errors and not _result.get("phase1_has_key"):
            log("\nAborting — Phase 1 hard failure, skipping Phase 2")
            app.quit()
            return

        # ════════════════════════════════════════════════════════════════════
        # PHASE 2 — Config Discovery end-to-end with 3 scenarios
        # ════════════════════════════════════════════════════════════════════
        log("\n" + "─" * 60)
        log("Phase 2: Config Discovery end-to-end (3 scenarios, Mode 2)")
        log("─" * 60)

        # --- Patch 1: reduce scenario set to 3 to keep run < 2 minutes -----
        try:
            from tests.integration.test_scenarios import CRITICAL_SCENARIOS

            slim_module = types.ModuleType("tests.integration.test_scenarios")
            slim_module.CRITICAL_SCENARIOS = CRITICAL_SCENARIOS[:3]
            slim_module.EDGE_SCENARIOS = []
            slim_module.PARAMETER_VARIATION_SCENARIOS = []
            sys.modules["tests.integration.test_scenarios"] = slim_module
            log(f"Patched scenario set to {len(CRITICAL_SCENARIOS[:3])} scenarios")
        except ImportError as exc:
            log(f"WARNING: Could not import test scenarios ({exc}); using default set")

        # --- Patch 2: auto-accept the QMessageBox confirmation --------------
        _orig_exec = QMessageBox.exec_

        def _auto_yes(self_msg):
            log("[AUTO] QMessageBox intercepted → returning Yes")
            return QMessageBox.Yes

        QMessageBox.exec_ = _auto_yes

        # --- Patch 3: intercept ConfigDiscoveryResultsDialog to capture data
        _results_captured: list = []
        _dialog_ref: list = [None]

        try:
            from src.strategy_builder.ui.config_discovery_results_dialog import (
                ConfigDiscoveryResultsDialog,
            )

            _orig_append = ConfigDiscoveryResultsDialog.append_result
            _orig_init = ConfigDiscoveryResultsDialog.__init__

            def _patched_init(self_dlg, *args, **kwargs):
                _orig_init(self_dlg, *args, **kwargs)
                _dialog_ref[0] = self_dlg
                log("ConfigDiscoveryResultsDialog created (reference captured)")

            def _patched_append(self_dlg, dr):
                _results_captured.append(dr)
                log(
                    f"  Row {len(_results_captured)}: "
                    f"scenario={dr.scenario_id!r}, "
                    f"trades={dr.trade_count}, "
                    f"pnl={dr.total_pnl:.2f}, "
                    f"error={dr.error!r}"
                )
                return _orig_append(self_dlg, dr)

            ConfigDiscoveryResultsDialog.__init__ = _patched_init
            ConfigDiscoveryResultsDialog.append_result = _patched_append
        except Exception as exc:
            log(f"WARNING: Could not patch ConfigDiscoveryResultsDialog: {exc}")
            _orig_append = None
            _orig_init = None

        # --- Run Config Discovery -------------------------------------------
        try:
            log("Calling panel._on_config_discovery_clicked() ...")
            panel._on_config_discovery_clicked()
            log("_on_config_discovery_clicked() returned")
        except Exception as exc:
            _errors.append(f"Phase 2 _on_config_discovery_clicked exception: {exc}")
            log(f"FAIL: {_errors[-1]}")
            traceback.print_exc()
        finally:
            QMessageBox.exec_ = _orig_exec
            try:
                if _orig_init is not None:
                    ConfigDiscoveryResultsDialog.__init__ = _orig_init
                if _orig_append is not None:
                    ConfigDiscoveryResultsDialog.append_result = _orig_append
            except Exception:
                pass

        # --- Evaluate results ------------------------------------------------
        nonzero_rows = [r for r in _results_captured if r.trade_count > 0]
        nonzero_pnl = [r for r in _results_captured if r.total_pnl != 0.0]
        _result["phase2_scenarios_run"] = len(_results_captured)
        _result["phase2_nonzero_trade_rows"] = len(nonzero_rows)

        log(f"\nScenarios run:       {len(_results_captured)}")
        log(f"Non-zero trades:     {len(nonzero_rows)}")
        log(f"Non-zero P&L:        {len(nonzero_pnl)}")

        if not _results_captured:
            _errors.append("Phase 2: Config Discovery returned 0 results")
            log(f"FAIL: {_errors[-1]}")
        elif len(nonzero_rows) == 0:
            _errors.append(
                f"Phase 2: all {len(_results_captured)} variants show 0 trades — "
                "fix not propagating through Config Discovery UI path"
            )
            log(f"FAIL: {_errors[-1]}")
        else:
            log(
                f"PASS Phase 2: {len(nonzero_rows)}/{len(_results_captured)} "
                "variants have trades > 0"
            )
            for r in nonzero_rows:
                log(f"  ✓ {r.scenario_id}: trades={r.trade_count}, pnl={r.total_pnl:.2f}")

        # --- Screenshot of results dialog ------------------------------------
        def _capture_and_quit() -> None:
            dlg = _dialog_ref[0]
            if dlg and dlg.isVisible():
                sshot = str(
                    SCREENSHOT_DIR / "btcaaaaa_1205_config_discovery_mode2_results.png"
                )
                path = capture_screenshot(dlg, sshot)
                if path:
                    _screenshots.append(path)
                    log(f"Screenshot (results dialog): {path}")
                else:
                    log("WARNING: Results dialog screenshot not captured")
            else:
                # Fallback to main window
                sshot = str(SCREENSHOT_DIR / "btcaaaaa_1205_main_window_fallback.png")
                path = capture_screenshot(window, sshot)
                if path:
                    _screenshots.append(path)
                    log(f"Screenshot (main window fallback): {path}")
                else:
                    log("WARNING: No screenshot captured")
            app.quit()

        QTimer.singleShot(2000, _capture_and_quit)

    def _on_timeout() -> None:
        _errors.append("TIMEOUT: Config Discovery did not complete within 600 s")
        log(f"FAIL: {_errors[-1]}")
        app.quit()

    QTimer.singleShot(500, _run_qa)
    QTimer.singleShot(600_000, _on_timeout)  # 10-minute safety net

    app.exec_()

    # ── Final summary ────────────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("QA RESULT SUMMARY — BTCAAAAA-1205")
    log("=" * 60)

    if _errors:
        log("RESULT: FAIL")
        for e in _errors:
            log(f"  - {e}")
        rc = 1
    else:
        log("RESULT: PASS")
        log(
            f"  Phase 1 (Mode 2 baseline):  "
            f"trades={_result.get('phase1_trades', 'N/A')}, "
            f"pnl={_result.get('phase1_total_pnl', 'N/A')}"
        )
        log(
            f"  Phase 2 (Config Discovery): "
            f"scenarios={_result.get('phase2_scenarios_run', 'N/A')}, "
            f"non-zero rows={_result.get('phase2_nonzero_trade_rows', 'N/A')}"
        )
        log(f"  Screenshots: {_screenshots}")
        rc = 0

    with open(LOG_FILE, "w") as f:
        f.write("\n".join(_log_lines))
    log(f"Full log written to: {LOG_FILE}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
