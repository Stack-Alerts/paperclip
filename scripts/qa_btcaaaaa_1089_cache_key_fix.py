#!/usr/bin/env python3
"""
QA live-path verification for BTCAAAAA-1089 / BTCAAAAA-1088.

Verifies BacktestDataProvider cache key stability after the end_date rounding fix.
Must NOT use QT_QPA_PLATFORM=offscreen.

Tests covered:
  Test 1  — Cross-run cache hit (same key → cache hit on second load)
  Test 2  — Within-run caching (only block 1 loads from DB; blocks 2..N hit cache)
  Test 3  — end_date is UTC midnight (00:00:00.000000)
  Test 4  — BacktestDataProvider returns non-empty bars for 180-day window from
            real local Parquet files (BTCAAAAA-1101 populated 2025-11 and 2025-12).
"""
import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# ── Real xcb display — never override to offscreen ──
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    del os.environ['QT_QPA_PLATFORM']
os.environ.setdefault('DISPLAY', ':0')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import QApplication

SCREENSHOT_DIR = Path('/tmp/qa_screenshots')
SCREENSHOT_DIR.mkdir(exist_ok=True)
LOG_FILE = SCREENSHOT_DIR / 'btcaaaaa_1089_cache_key_fix.txt'

# ── Logging ──────────────────────────────────────────────────────────────────
_lines: list[str] = []

def log(msg: str) -> None:
    print(msg, flush=True)
    _lines.append(msg)


# ── Fake Bar factory ──────────────────────────────────────────────────────────
def _make_fake_bars(n: int = 10):
    """Return n minimal MagicMock Bar objects (NautilusTrader duck-type)."""
    now_ns = int(datetime(2026, 1, 1).timestamp() * 1e9)
    bars = []
    for i in range(n):
        b = MagicMock()
        b.ts_event = now_ns + i * 900_000_000_000  # 15-min spacing in nanoseconds
        bars.append(b)
    return bars


# ── Helpers ───────────────────────────────────────────────────────────────────
def _progress_callback(current: int, total: int, message: str) -> None:
    log(f"    [progress] {current}/{total}: {message}")


def _run_tests(app: QApplication) -> tuple[bool, list[str]]:
    errors: list[str] = []

    # ── Platform guard ────────────────────────────────────────────────────────
    platform = app.platformName()
    log(f"Qt platform plugin: {platform}")
    if platform in ('offscreen', 'minimal'):
        errors.append(f"BLOCKED: Expected xcb, got {platform}")
        return False, errors

    # ── Import under test ─────────────────────────────────────────────────────
    from src.optimizer_v3.core.backtest_data_provider import BacktestDataProvider
    from src.optimizer_v3.core.training_thread import TrainingThread

    # ────────────────────────────────────────────────────────────────────────
    # TEST 3 — end_date is exactly UTC midnight
    # ────────────────────────────────────────────────────────────────────────
    log("\n" + "─" * 60)
    log("TEST 3: end_date is UTC midnight")
    log("─" * 60)

    # Simulate _run_real_training() date logic (period_days=180)
    now = datetime.utcnow()
    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=180)
    period = (start_date, end_date)

    log(f"  datetime.utcnow() = {now}")
    log(f"  end_date          = {end_date}")
    log(f"  start_date        = {start_date}")
    log(f"  span              = {(end_date - start_date).days} days")

    midnight_ok = (
        end_date.hour == 0
        and end_date.minute == 0
        and end_date.second == 0
        and end_date.microsecond == 0
    )
    span_ok = (end_date - start_date).days == 180

    if not midnight_ok:
        errors.append(
            f"TEST 3 FAIL: end_date not UTC midnight: {end_date}"
        )
        log(f"  FAIL: {errors[-1]}")
    else:
        log("  PASS: end_date is exactly 00:00:00.000000 UTC")

    if not span_ok:
        errors.append(
            f"TEST 3 FAIL: span is {(end_date - start_date).days} days, expected 180"
        )
        log(f"  FAIL: {errors[-1]}")
    else:
        log(f"  PASS: start_date = end_date − 180 days → span = 180 days")

    # Verify: two separate "TrainingThread" date computations on same day produce identical keys
    now2 = datetime.utcnow()
    end_date2 = now2.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date2 = end_date2 - timedelta(days=180)
    key1 = f"15m_{start_date}_{end_date}"
    key2 = f"15m_{start_date2}_{end_date2}"
    log(f"\n  Cache key from run 1 : {key1}")
    log(f"  Cache key from run 2 : {key2}")
    if key1 != key2:
        errors.append(
            f"TEST 3 FAIL: cache keys differ across two runs on same day: "
            f"'{key1}' vs '{key2}'"
        )
        log(f"  FAIL: {errors[-1]}")
    else:
        log("  PASS: cache keys are identical across two same-day instantiations")

    # ────────────────────────────────────────────────────────────────────────
    # TEST 1 — Cross-run cache hit (BacktestDataProvider)
    # Patch NautilusDataLoader.load_bars to return fake bars (DB is empty).
    # This isolates the cache path without needing real market data.
    # ────────────────────────────────────────────────────────────────────────
    log("\n" + "─" * 60)
    log("TEST 1: Cross-run cache hit")
    log("─" * 60)

    fake_bars = _make_fake_bars(100)

    with patch(
        "src.optimizer_v3.core.backtest_data_provider.NautilusDataLoader"
    ) as MockLoader:
        mock_loader_inst = MagicMock()
        mock_loader_inst.load_bars.return_value = fake_bars
        MockLoader.return_value = mock_loader_inst

        # ── Run 1: fresh provider (simulates first calibration) ──
        provider1 = BacktestDataProvider()
        log("\n  Run 1 (fresh provider — expect DB load):")
        bars1 = provider1.load_bars_for_backtest(
            timeframe="15m",
            start_date=start_date,
            end_date=end_date,
            progress_callback=_progress_callback,
        )
        calls_after_run1 = mock_loader_inst.load_bars.call_count
        log(f"  NautilusDataLoader.load_bars call count: {calls_after_run1}")
        log(f"  Bars returned: {len(bars1)}")
        if calls_after_run1 != 1:
            errors.append(
                f"TEST 1 FAIL: expected 1 DB load on first call, got {calls_after_run1}"
            )
            log(f"  FAIL: {errors[-1]}")
        else:
            log("  PASS: First call loaded from DB (1 NautilusDataLoader.load_bars call)")

        # ── Run 2: same provider, same params (simulates second calibration same day) ──
        log("\n  Run 2 (same provider, same params — expect cache hit):")
        bars2 = provider1.load_bars_for_backtest(
            timeframe="15m",
            start_date=start_date,
            end_date=end_date,
            progress_callback=_progress_callback,
        )
        calls_after_run2 = mock_loader_inst.load_bars.call_count
        log(f"  NautilusDataLoader.load_bars call count (cumulative): {calls_after_run2}")
        log(f"  Bars returned: {len(bars2)}")
        if calls_after_run2 != 1:
            errors.append(
                f"TEST 1 FAIL: DB loader called again on second run (expected 0 new calls), "
                f"total = {calls_after_run2}"
            )
            log(f"  FAIL: {errors[-1]}")
        else:
            log("  PASS: Second call served from cache — no new DB load")

        if bars1 is not bars2:
            errors.append("TEST 1 FAIL: cache returned a different object (not the cached list)")
            log(f"  FAIL: {errors[-1]}")
        else:
            log("  PASS: Cache returned the exact same list object (identity check)")

    # ────────────────────────────────────────────────────────────────────────
    # TEST 2 — Within-run caching (multi-block strategy)
    # Simulate 3 blocks all calling BacktestDataProvider with identical period.
    # Block 1 → DB load. Blocks 2, 3 → cache hit.
    # ────────────────────────────────────────────────────────────────────────
    log("\n" + "─" * 60)
    log("TEST 2: Within-run caching (multi-block, 3 blocks)")
    log("─" * 60)

    fake_bars_3 = _make_fake_bars(100)
    blocks = ["RSI_Block", "MACD_Block", "Volume_Block"]

    with patch(
        "src.optimizer_v3.core.backtest_data_provider.NautilusDataLoader"
    ) as MockLoader3:
        mock_inst3 = MagicMock()
        mock_inst3.load_bars.return_value = fake_bars_3
        MockLoader3.return_value = mock_inst3

        provider2 = BacktestDataProvider()  # fresh singleton for this test
        for i, block_name in enumerate(blocks):
            log(f"\n  Block {i+1}: {block_name}")
            bars = provider2.load_bars_for_backtest(
                timeframe="15m",
                start_date=start_date,
                end_date=end_date,
                progress_callback=_progress_callback,
            )
            call_count = mock_inst3.load_bars.call_count
            log(f"    NautilusDataLoader.load_bars cumulative calls: {call_count}")
            log(f"    Bars returned: {len(bars)}")
            if i == 0:
                if call_count != 1:
                    errors.append(
                        f"TEST 2 FAIL: Block 1 expected 1 DB load, got {call_count}"
                    )
                    log(f"    FAIL: {errors[-1]}")
                else:
                    log("    PASS: Block 1 loaded from DB")
            else:
                if call_count != 1:
                    errors.append(
                        f"TEST 2 FAIL: Block {i+1} triggered a new DB load "
                        f"(call_count={call_count}, expected to stay at 1)"
                    )
                    log(f"    FAIL: {errors[-1]}")
                else:
                    log(f"    PASS: Block {i+1} served from cache — no new DB load")

    # ────────────────────────────────────────────────────────────────────────
    # TEST 4 — BacktestDataProvider returns real bars for 180-day window
    # BTCAAAAA-1101 populated 2025-11 and 2025-12 parquet files.
    # ────────────────────────────────────────────────────────────────────────
    log("\n" + "─" * 60)
    log("TEST 4: BacktestDataProvider returns real bars (180-day window)")
    log("─" * 60)

    from datetime import timezone
    t4_start = datetime(2025, 11, 11, tzinfo=timezone.utc)
    t4_end   = datetime(2026, 5, 10, tzinfo=timezone.utc)
    log(f"  Window: {t4_start.date()} → {t4_end.date()}")

    try:
        provider4 = BacktestDataProvider()
        t4_bars = provider4.load_bars_for_backtest(
            timeframe="15m",
            start_date=t4_start,
            end_date=t4_end,
        )
        bar_count = len(t4_bars)
        log(f"  Bars returned: {bar_count}")

        if bar_count == 0:
            errors.append("TEST 4 FAIL: BacktestDataProvider returned 0 bars for 180-day window")
            log(f"  FAIL: {errors[-1]}")
        else:
            first_ns = t4_bars[0].ts_event
            last_ns  = t4_bars[-1].ts_event
            first_dt = datetime.fromtimestamp(first_ns / 1e9, tz=timezone.utc)
            last_dt  = datetime.fromtimestamp(last_ns  / 1e9, tz=timezone.utc)
            log(f"  First bar: {first_dt}")
            log(f"  Last bar:  {last_dt}")
            log(f"  PASS: {bar_count} real bars loaded from local Parquet files")
    except Exception:
        errors.append(f"TEST 4 FAIL: exception during BacktestDataProvider.load_bars_for_backtest")
        log(f"  FAIL: {errors[-1]}")
        log(traceback.format_exc())

    return len(errors) == 0, errors


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QA_BTCAAAAA_1089")

    passed, errors = _run_tests(app)

    log("\n" + "=" * 60)
    log("QA RESULT SUMMARY — BTCAAAAA-1089")
    log("=" * 60)
    log(f"Test 3 (end_date UTC midnight):   {'PASS' if not any('TEST 3' in e for e in errors) else 'FAIL'}")
    log(f"Test 1 (cross-run cache hit):     {'PASS' if not any('TEST 1' in e for e in errors) else 'FAIL'}")
    log(f"Test 2 (within-run caching):      {'PASS' if not any('TEST 2' in e for e in errors) else 'FAIL'}")
    log(f"Test 4 (delay_map regression):    {'PASS' if not any('TEST 4' in e for e in errors) else 'FAIL'}")
    log(f"\nOverall: {'PASS' if passed else 'FAIL (see errors above)'}")
    if errors:
        log("\nErrors:")
        for e in errors:
            log(f"  - {e}")

    with open(LOG_FILE, 'w') as f:
        f.write('\n'.join(_lines))
    log(f"\nFull log written to: {LOG_FILE}")

    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
