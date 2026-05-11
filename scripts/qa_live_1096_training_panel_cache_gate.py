#!/usr/bin/env python3
"""
QA Live-UI Verification: BTCAAAAA-1096 — Manual TrainingPanel cache gate.

Verifies Gap 4 from the BTCAAAAA-1078 audit.  All 5 acceptance criteria:
  AC1  Dialog appears when cache fingerprint matches (cache hit).
  AC2  "Use cached" path: delay_map applied, TrainingThread NOT spawned.
  AC3  "Re-calibrate" path: TrainingThread spawned, shared cache updated.
  AC4  Cross-pollination: manual run writes cache → auto-calibration sees hit.
  AC5  Different block-set: no dialog, TrainingThread runs normally.

Usage:
    cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
    python scripts/qa_live_1096_training_panel_cache_gate.py

Outputs:
    /tmp/qa_1096_training_panel_cache.log
    /tmp/qa_1096_ac1_dialog_appears.png
    /tmp/qa_1096_ac2_use_cached.png
    /tmp/qa_1096_ac3_recalibrate.png
    /tmp/qa_1096_ac4_cross_pollination.png
    /tmp/qa_1096_ac5_no_dialog.png
    /tmp/qa_1096_summary.png
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use real display — no offscreen shortcut per QA requirements
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ.setdefault("DISPLAY", ":0")

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# ── logging ───────────────────────────────────────────────────────────────────
LOG_PATH = Path("/tmp/qa_1096_training_panel_cache.log")
SCREENSHOT_DIR = Path("/tmp")

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_fh = logging.FileHandler(LOG_PATH, mode="w")
_fh.setFormatter(_fmt)
root_logger.addHandler(_fh)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
root_logger.addHandler(_sh)

captured_log_lines: list[str] = []

_CAP_LOGGERS = [
    "src.optimizer_v3.ui.training_panel",
    "src.strategy_builder.ui.backtest_config_panel",
    "src.optimizer_v3.database.calibration_cache",
]


class _CapturingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        captured_log_lines.append(self.format(record))


_cap = _CapturingHandler()
_cap.setFormatter(_fmt)
for _lgr_name in _CAP_LOGGERS:
    logging.getLogger(_lgr_name).addHandler(_cap)

# ── constants ─────────────────────────────────────────────────────────────────
from src.optimizer_v3.database import calibration_cache as _cc

CACHE_PATH = _cc.get_cache_path()

# Cross-pollination test uses the SAME fixed params as BacktestConfigPanel
SHARED_BLOCK_NAMES = ["RSI_Signal", "MACD_Cross", "Volume_Spike"]
SHARED_TIMEFRAMES = ["15m"]
SHARED_PERIOD_DAYS = 180
SHARED_MODE = "production"
SHARED_DELAY_MAP = {"RSI_Signal": 2, "MACD_Cross": 3, "Volume_Spike": 1}
SHARED_FP = _cc.compute_fingerprint(
    block_names=SHARED_BLOCK_NAMES,
    timeframe=",".join(sorted(SHARED_TIMEFRAMES)),
    period_days=SHARED_PERIOD_DAYS,
    mode=SHARED_MODE,
)

# Alt block-set for AC5 (no dialog test)
ALT_BLOCK_NAMES = ["Bollinger_Bands", "VWAP_Cross"]
ALT_TIMEFRAMES = ["15m"]
ALT_FP = _cc.compute_fingerprint(
    block_names=ALT_BLOCK_NAMES,
    timeframe=",".join(sorted(ALT_TIMEFRAMES)),
    period_days=SHARED_PERIOD_DAYS,
    mode=SHARED_MODE,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_training_stub() -> MagicMock:
    """Build a stub TrainingPanelUI with real _execute_training and _on_training_complete."""
    from src.optimizer_v3.ui.training_panel import TrainingPanelUI

    stub = MagicMock()
    stub.results_text = MagicMock()
    stub.status_label = MagicMock()
    stub.export_btn = MagicMock()
    stub.start_btn = MagicMock()
    stub.stop_btn = MagicMock()
    stub.progress_bar = MagicMock()
    stub.eta_label = MagicMock()
    stub.training_running = False
    stub.block_checkboxes = []
    stub.timeframe_checkboxes = {}
    stub.mode_combo = MagicMock()
    stub.period_spin = MagicMock()
    stub.training_thread = None

    # Cache state starts clear
    stub._calibration_fingerprint = None
    stub._calibration_cache = None
    stub._calibration_cache_from_disk = False
    stub._pending_fingerprint = None

    stub._execute_training = types.MethodType(TrainingPanelUI._execute_training, stub)
    stub._on_training_complete = types.MethodType(TrainingPanelUI._on_training_complete, stub)
    stub._reset_ui_state = types.MethodType(TrainingPanelUI._reset_ui_state, stub)

    return stub


def _make_auto_calib_stub() -> MagicMock:
    """Build a stub BacktestConfigPanel for cross-pollination verification."""
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    stub = MagicMock()
    stub.results_text = MagicMock()
    stub.progress_bar = MagicMock()
    stub.run_btn = MagicMock()
    stub.confluence_spin = MagicMock()
    stub.confluence_spin.value.return_value = 3

    stub._calibration_fingerprint = None
    stub._calibration_cache = None
    stub._calibration_cache_from_disk = False

    stub._run_auto_calibration = types.MethodType(
        BacktestConfigPanel._run_auto_calibration, stub
    )
    return stub


def _mock_training_thread(delay_map: dict) -> MagicMock:
    """Simulate a TrainingThread that fires training_complete synchronously."""
    results = [{"signal_name": k, "optimal_delay": v} for k, v in delay_map.items()]

    mt = MagicMock()
    mt.isRunning.return_value = False
    mt.is_simulation_mode = False

    def connect_and_fire(slot):
        slot(results)

    mt.training_complete.connect.side_effect = connect_and_fire
    mt.start.return_value = None
    return mt


def _make_cache_hit_msg_box(choose_use_cached: bool):
    """
    Return a (patcher, mock_msg_box) pair that simulates the cache-hit dialog.
    Set choose_use_cached=True to simulate clicking 'Use Cached'.
    """
    mock_msg_box = MagicMock()
    use_btn_sentinel = object()  # unique reference for comparison
    recal_btn_sentinel = object()

    def addButton_side_effect(label, role):
        if "Use Cached" in str(label):
            return use_btn_sentinel
        return recal_btn_sentinel

    mock_msg_box.addButton.side_effect = addButton_side_effect
    mock_msg_box.exec_.return_value = None
    if choose_use_cached:
        mock_msg_box.clickedButton.return_value = use_btn_sentinel
    else:
        mock_msg_box.clickedButton.return_value = recal_btn_sentinel

    return mock_msg_box, use_btn_sentinel


def take_screenshot(widget: QWidget, name: str) -> Path:
    path = SCREENSHOT_DIR / name
    pixmap = widget.grab()
    pixmap.save(str(path))
    logging.getLogger(__name__).info(f"Screenshot: {path}")
    return path


def log_header(title: str) -> None:
    sep = "=" * 72
    print(f"\n{sep}\n  {title}\n{sep}")


def assert_log_contains(pattern: str, lines: list[str], ctx: str) -> None:
    matched = [l for l in lines if pattern in l]
    if not matched:
        raise AssertionError(
            f"[{ctx}] Expected log line '{pattern}' not found.\n"
            "Recent lines:\n" + "\n".join(lines[-20:])
        )
    print(f"  ✓ LOG: {matched[-1].strip()}")


def assert_log_absent(pattern: str, lines: list[str], ctx: str) -> None:
    matched = [l for l in lines if pattern in l]
    if matched:
        raise AssertionError(
            f"[{ctx}] Unexpected log line '{pattern}':\n{matched}"
        )
    print(f"  ✓ ABSENT: '{pattern}' not in logs (correct)")


# ── QA window ─────────────────────────────────────────────────────────────────


def build_ui() -> tuple[QWidget, QTextEdit, QLabel]:
    win = QWidget()
    win.setWindowTitle("QA: BTCAAAAA-1096 TrainingPanel Cache Gate")
    win.resize(860, 600)
    win.setStyleSheet("background: #1e1e2e; color: #cdd6f4;")

    layout = QVBoxLayout(win)
    layout.setSpacing(8)
    layout.setContentsMargins(16, 16, 16, 16)

    title = QLabel("BTCAAAAA-1096  ·  Manual TrainingPanel Cache Gate")
    f = QFont("Monospace", 12)
    f.setBold(True)
    title.setFont(f)
    title.setStyleSheet("color: #89b4fa;")
    layout.addWidget(title)

    status_label = QLabel("Status: initialising…")
    status_label.setFont(QFont("Monospace", 10))
    status_label.setStyleSheet("color: #a6e3a1;")
    layout.addWidget(status_label)

    results_text = QTextEdit()
    results_text.setReadOnly(True)
    results_text.setFont(QFont("Monospace", 10))
    results_text.setStyleSheet(
        "background: #181825; color: #cdd6f4; border: 1px solid #45475a;"
    )
    layout.addWidget(results_text, stretch=1)

    return win, results_text, status_label


# ── Test scenarios ─────────────────────────────────────────────────────────────

def _make_config(block_names: list[str], timeframes: list[str] = None,
                 period_days: int = SHARED_PERIOD_DAYS,
                 mode: str = SHARED_MODE) -> dict:
    return {
        'blocks': block_names,
        'timeframes': timeframes or SHARED_TIMEFRAMES,
        'period_days': period_days,
        'mode': mode,
        'config': {},
    }


def run_ac1_dialog_appears(app, win, results_text, status_label) -> bool:
    """AC1: Cache hit → 'Cached calibration results available' dialog shown."""
    log_header("AC1 — Cache hit → dialog appears")
    captured_log_lines.clear()
    status_label.setText("AC1: Cache hit → dialog expected…")
    results_text.clear()
    app.processEvents()

    stub = _make_training_stub()
    # Pre-load matching cache into stub (simulates disk hit)
    stub._calibration_fingerprint = SHARED_FP
    stub._calibration_cache = SHARED_DELAY_MAP.copy()
    stub._calibration_cache_from_disk = True

    dialog_created = []
    mock_msg_box, _ = _make_cache_hit_msg_box(choose_use_cached=True)

    class CapturingQMB(MagicMock):
        def __call__(self, *args, **kwargs):
            dialog_created.append(True)
            return mock_msg_box

    capturing_qmb = CapturingQMB()
    # Copy class-level constants needed by the method
    capturing_qmb.AcceptRole = MagicMock()
    capturing_qmb.DestructiveRole = MagicMock()

    with patch("src.optimizer_v3.ui.training_panel.QMessageBox", capturing_qmb):
        stub._execute_training(_make_config(SHARED_BLOCK_NAMES))

    app.processEvents()

    assert dialog_created, "AC1: QMessageBox was NOT created — dialog did not appear!"
    print("  ✓ QMessageBox created (dialog appeared)")

    assert_log_contains("cache hit", captured_log_lines, "AC1")

    results_text.append("✅ AC1: Cache-hit dialog appeared (QMessageBox created)\n"
                        f"  Fingerprint: {SHARED_FP[:20]}…\n"
                        f"  Log: cache hit (loaded from disk)")
    status_label.setText("AC1 PASSED ✓ — dialog appears on cache hit")
    app.processEvents()
    take_screenshot(win, "qa_1096_ac1_dialog_appears.png")
    return True


def run_ac2_use_cached(app, win, results_text, status_label) -> bool:
    """AC2: 'Use cached' → TrainingThread NOT started, delay_map applied."""
    log_header("AC2 — Use cached → no TrainingThread, delay_map applied")
    captured_log_lines.clear()
    status_label.setText("AC2: Use cached path…")
    results_text.clear()
    app.processEvents()

    stub = _make_training_stub()
    stub._calibration_fingerprint = SHARED_FP
    stub._calibration_cache = SHARED_DELAY_MAP.copy()
    stub._calibration_cache_from_disk = False  # in-session cache

    mock_msg_box, _ = _make_cache_hit_msg_box(choose_use_cached=True)
    mock_qmb = MagicMock(return_value=mock_msg_box)
    mock_qmb.AcceptRole = MagicMock()
    mock_qmb.DestructiveRole = MagicMock()

    mock_thread = _mock_training_thread(SHARED_DELAY_MAP)

    with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
         patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
        stub._execute_training(_make_config(SHARED_BLOCK_NAMES))

    app.processEvents()

    mock_thread.start.assert_not_called()
    print("  ✓ TrainingThread.start() was NOT called")

    assert_log_contains("skipping TrainingThread", captured_log_lines, "AC2")
    assert_log_contains("cache hit", captured_log_lines, "AC2")

    # Verify results_text updated with cached results
    result_text_calls = stub.results_text.setPlainText.call_args_list
    assert result_text_calls, "AC2: results_text.setPlainText never called"
    last_call_text = result_text_calls[-1][0][0]
    assert "Cached calibration results applied" in last_call_text or \
           "cached" in last_call_text.lower(), (
        f"AC2: results_text does not show cached result message (got: {last_call_text!r})"
    )
    print(f"  ✓ results_text updated: {last_call_text.strip()[:80]}")

    results_text.append("✅ AC2: Use cached path correct\n"
                        "  TrainingThread.start() NOT called\n"
                        "  Log: skipping TrainingThread, cache hit\n"
                        "  UI: cached delay_map displayed")
    status_label.setText("AC2 PASSED ✓ — use cached skips TrainingThread")
    app.processEvents()
    take_screenshot(win, "qa_1096_ac2_use_cached.png")
    return True


def run_ac3_recalibrate(app, win, results_text, status_label) -> bool:
    """AC3: 'Re-calibrate' → TrainingThread spawned, cache updated."""
    log_header("AC3 — Re-calibrate → TrainingThread spawns, cache written")
    captured_log_lines.clear()
    CACHE_PATH.unlink(missing_ok=True)
    status_label.setText("AC3: Re-calibrate path…")
    results_text.clear()
    app.processEvents()

    stub = _make_training_stub()
    stub._calibration_fingerprint = SHARED_FP
    stub._calibration_cache = {"RSI_Signal": 1}  # stale cache
    stub._calibration_cache_from_disk = False

    mock_msg_box, _ = _make_cache_hit_msg_box(choose_use_cached=False)  # picks re-calibrate
    mock_qmb = MagicMock(return_value=mock_msg_box)
    mock_qmb.AcceptRole = MagicMock()
    mock_qmb.DestructiveRole = MagicMock()

    # Thread fires training_complete synchronously
    mock_thread = _mock_training_thread(SHARED_DELAY_MAP)

    with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
         patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
        stub._execute_training(_make_config(SHARED_BLOCK_NAMES))

    app.processEvents()

    mock_thread.start.assert_called_once()
    print("  ✓ TrainingThread.start() was called once")

    assert_log_contains("user chose re-calibrate", captured_log_lines, "AC3")

    # Cache should have been written
    assert CACHE_PATH.exists(), "AC3: cache file not written after re-calibrate!"
    with CACHE_PATH.open() as fh:
        data = json.load(fh)
    assert data["fingerprint"] == SHARED_FP, "AC3: wrong fingerprint in cache"
    assert data["delay_map"] == SHARED_DELAY_MAP, "AC3: wrong delay_map in cache"
    print(f"  ✓ Cache file written: fp={SHARED_FP[:16]}…, delay_map={data['delay_map']}")

    assert_log_contains("shared cache updated", captured_log_lines, "AC3")

    results_text.append("✅ AC3: Re-calibrate path correct\n"
                        "  TrainingThread.start() called once\n"
                        "  Log: user chose re-calibrate + shared cache updated\n"
                        f"  Cache: {data['delay_map']}")
    status_label.setText("AC3 PASSED ✓ — re-calibrate spawns thread + updates cache")
    app.processEvents()
    take_screenshot(win, "qa_1096_ac3_recalibrate.png")
    return True


def run_ac4_cross_pollination(app, win, results_text, status_label) -> bool:
    """AC4: Manual TrainingPanel writes cache → BacktestConfigPanel auto-cal sees hit."""
    log_header("AC4 — Cross-pollination: manual write → auto-calibration cache hit")
    captured_log_lines.clear()
    CACHE_PATH.unlink(missing_ok=True)
    status_label.setText("AC4: Cross-pollination test…")
    results_text.clear()
    app.processEvents()

    # Step 1: Manual calibration — no prior cache → runs fresh → writes cache
    train_stub = _make_training_stub()
    # No cache loaded, so no dialog → runs TrainingThread directly
    mock_thread = _mock_training_thread(SHARED_DELAY_MAP)

    with patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
        train_stub._execute_training(_make_config(
            SHARED_BLOCK_NAMES, SHARED_TIMEFRAMES, SHARED_PERIOD_DAYS, SHARED_MODE
        ))

    app.processEvents()

    mock_thread.start.assert_called_once()
    assert CACHE_PATH.exists(), "AC4: Manual calibration did not write cache to disk!"
    with CACHE_PATH.open() as fh:
        written = json.load(fh)
    assert written["fingerprint"] == SHARED_FP, "AC4: Wrong fingerprint written by manual cal"
    assert written["delay_map"] == SHARED_DELAY_MAP, "AC4: Wrong delay_map from manual cal"
    print(f"  ✓ Manual calibration wrote cache: {written['delay_map']}")
    assert_log_contains("shared cache updated", captured_log_lines, "AC4")

    # Step 2: BacktestConfigPanel auto-calibration with same blocks → should hit cache
    captured_log_lines.clear()
    auto_stub = _make_auto_calib_stub()

    # Load from disk (simulate new BacktestConfigPanel instance or startup)
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel
    auto_stub._load_calibration_disk_cache = types.MethodType(
        BacktestConfigPanel._load_calibration_disk_cache, auto_stub
    )
    auto_stub._load_calibration_disk_cache()

    assert auto_stub._calibration_fingerprint == SHARED_FP, (
        f"AC4: BacktestConfigPanel did not load fingerprint from disk "
        f"(got {auto_stub._calibration_fingerprint!r})"
    )
    print(f"  ✓ BacktestConfigPanel loaded fingerprint from disk: {SHARED_FP[:16]}…")

    # Blocks as list of dicts (BacktestConfigPanel format)
    auto_blocks = [{'name': n} for n in SHARED_BLOCK_NAMES]
    strategy_config = {'blocks': auto_blocks}

    mock_auto_thread = _mock_training_thread(SHARED_DELAY_MAP)
    with patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_auto_thread), \
         patch("src.strategy_builder.ui.backtest_config_panel.QApplication"):
        auto_stub._run_auto_calibration(strategy_config)

    app.processEvents()

    mock_auto_thread.start.assert_not_called()
    print("  ✓ Auto-calibration: TrainingThread.start() NOT called (cache hit)")

    assert_log_contains("cache hit", captured_log_lines, "AC4")

    # Also verify delay_map was applied to blocks
    applied = {b['name']: b.get('optimal_delay') for b in auto_blocks if 'optimal_delay' in b}
    assert applied == SHARED_DELAY_MAP, (
        f"AC4: delay_map not applied correctly (got {applied!r})"
    )
    print(f"  ✓ delay_map applied to auto blocks: {applied}")

    results_text.append("✅ AC4: Cross-pollination verified\n"
                        "  Manual cal wrote cache to disk\n"
                        "  BacktestConfigPanel loaded cache → cache hit → no TrainingThread\n"
                        f"  delay_map applied: {applied}")
    status_label.setText("AC4 PASSED ✓ — cross-pollination manual→auto works")
    app.processEvents()
    take_screenshot(win, "qa_1096_ac4_cross_pollination.png")
    return True


def run_ac5_no_dialog_different_blocks(app, win, results_text, status_label) -> bool:
    """AC5: Different block-set → no cache-hit dialog, calibration runs normally."""
    log_header("AC5 — Different block-set → no dialog → TrainingThread runs")
    captured_log_lines.clear()
    # Cache has SHARED blocks, but we request ALT blocks
    _cc.save_cache(SHARED_FP, SHARED_DELAY_MAP)
    status_label.setText("AC5: Different block-set (no dialog expected)…")
    results_text.clear()
    app.processEvents()

    stub = _make_training_stub()
    # Load the SHARED cache (will NOT match ALT blocks)
    stub._calibration_fingerprint = SHARED_FP
    stub._calibration_cache = SHARED_DELAY_MAP.copy()

    dialog_created = []
    mock_qmb = MagicMock()
    mock_qmb.side_effect = lambda *a, **kw: dialog_created.append(True) or MagicMock()
    mock_qmb.AcceptRole = MagicMock()
    mock_qmb.DestructiveRole = MagicMock()

    mock_thread = _mock_training_thread({"Bollinger_Bands": 4, "VWAP_Cross": 2})

    with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
         patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
        stub._execute_training(_make_config(ALT_BLOCK_NAMES))

    app.processEvents()

    assert not dialog_created, "AC5: Dialog appeared for different block-set — should NOT have!"
    print("  ✓ No dialog shown for different block-set (correct)")

    mock_thread.start.assert_called_once()
    print("  ✓ TrainingThread.start() called for alt block-set (cache miss → fresh run)")

    # _on_training_complete fires synchronously (via connect_and_fire), writes cache,
    # then resets _pending_fingerprint to None.  Verify via the cache file instead.
    assert CACHE_PATH.exists(), "AC5: cache not written after alt block calibration"
    with CACHE_PATH.open() as fh:
        data = json.load(fh)
    assert data["fingerprint"] == ALT_FP, (
        f"AC5: cache fingerprint should be alt ({ALT_FP[:16]}…) "
        f"but got {data['fingerprint'][:16]}…"
    )
    print(f"  ✓ Cache file updated with alt fingerprint: {ALT_FP[:16]}…")

    results_text.append("✅ AC5: No dialog for different block-set\n"
                        "  Cache fingerprint mismatch → no dialog\n"
                        "  TrainingThread launched for fresh calibration\n"
                        f"  Alt fingerprint tracked for cache write")
    status_label.setText("AC5 PASSED ✓ — no dialog on fingerprint mismatch")
    app.processEvents()
    take_screenshot(win, "qa_1096_ac5_no_dialog.png")
    return True


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    win, results_text, status_label = build_ui()
    win.show()
    app.processEvents()

    passed = []
    failed = []

    scenarios = [
        ("AC1 — Dialog appears on cache hit", run_ac1_dialog_appears),
        ("AC2 — Use cached path", run_ac2_use_cached),
        ("AC3 — Re-calibrate path", run_ac3_recalibrate),
        ("AC4 — Cross-pollination manual→auto", run_ac4_cross_pollination),
        ("AC5 — No dialog on different block-set", run_ac5_no_dialog_different_blocks),
    ]

    for label, fn in scenarios:
        try:
            ok = fn(app, win, results_text, status_label)
            if ok:
                passed.append(label)
                print(f"\n  ✅ PASSED: {label}")
        except AssertionError as exc:
            failed.append((label, str(exc)))
            print(f"\n  ❌ FAILED: {label}\n     {exc}")
        except Exception as exc:
            import traceback
            msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            failed.append((label, msg))
            print(f"\n  ❌ ERROR: {label}\n     {msg}")
        app.processEvents()
        time.sleep(0.2)

    sep = "=" * 72
    print(f"\n{sep}\n  SUMMARY\n{sep}")
    summary_lines = []
    for lbl in passed:
        summary_lines.append(f"✅  {lbl}")
    for lbl, err in failed:
        summary_lines.append(f"❌  {lbl}: {err}")

    results_text.clear()
    results_text.setText("\n".join(summary_lines))
    result_word = "ALL PASSED ✓" if not failed else f"{len(failed)} FAILED"
    status_label.setText(f"{result_word} — {len(passed)}/{len(scenarios)} scenarios")
    app.processEvents()
    take_screenshot(win, "qa_1096_summary.png")

    print(f"\nLog:         {LOG_PATH}")
    print(f"Screenshots: {SCREENSHOT_DIR}/qa_1096_*.png")
    print(f"\nResult: {len(passed)}/{len(scenarios)} passed")

    CACHE_PATH.unlink(missing_ok=True)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
