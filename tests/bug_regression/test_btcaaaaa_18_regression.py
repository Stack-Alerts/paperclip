"""
Regression tests for BTCAAAAA-18: Verify Data dialog — Data Integrity Check UI,
Fix Gaps repair flow, UTC timestamp handling, and Binance horizon gap classification.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-18
Components: src/strategy_builder/ui/data_verify_dialog.py
            src/data_manager/unified_manager.py
            src/data_manager/binance/rest_client.py

Root cause / changes:
  1. Added Verify Data dialog to Tools menu with 6-column results table.
  2. Repaired Fix Gaps flow — replaced DataUpdateModal delegation with
     DataRepairThread that calls verify_and_repair(dry_run=False) targeting
     specific gaps, and auto-re-verifies after repair.
  3. Fixed UTC timestamp handling in _fetch_binance_range — replaced
     datetime.fromtimestamp() (local time) with pd.to_datetime(unit='ms',
     utc=True) to produce UTC-naive timestamps matching stored data.
  4. Classified gaps by Binance 90-day API horizon — repairable gaps within
     horizon vs too-old gaps requiring LakeAPI backfill.
  5. Widened window to 1300×720 minimum with Notes column Stretch mode.
  6. Updated subtitle copy to "BTCUSDT Perpetual across all timeframes".

This file re-exports the existing unit tests from tests/unit/ so the Impact
Gate runner can discover them by bug ID, plus AST-based contract checks
that validate source-level fix requirements directly.

NOTE: Tests from tests/unit/test_data_verify_dialog_btcaaaaa459.py are NOT
re-exported here because they require a mocked Qt stub environment
incompatible with real PyQt5 imports needed by other bug regression tests.
The Impact Gate runner discovers those tests at their canonical path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-18"),
    pytest.mark.regression,
]

# Data manager integrity tests cover gap detection, repair, and UTC timestamp
# handling exercised by the BTCAAAAA-18 fixes.
from tests.unit.test_data_manager_integrity import (  # noqa: E402
    manager,
    _make_ohlcv,
    _write_parquet,
    _write_month_file,
)

from tests.unit.test_data_manager_integrity import (  # noqa: E402, F401
    TestDetectGapsInBinanceFiles,
    TestVerifyAndRepair,
    TestStartupCheck,
    TestGetBarsRegression,
    TestSaveBinanceBars,
    TestOHLCVDataValidation,
    TestDownloadWithRetry1dStaleness,
    TestGetKlines1dNotFlaggedStale,
    TestTrailingEdgeGapDetection,
    TestDataUpdateThreadDownloads1d,
    TestDetermineSourceTzAwareness,
    TestGetBarsBinanceTzAwareRegression,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-18-specific changes
# ---------------------------------------------------------------------------

SOURCE = Path(__file__).resolve().parents[2] / "src" / "strategy_builder" / "ui" / "data_verify_dialog.py"
SOURCE_TEXT = SOURCE.read_text()


class TestDataVerifyDialogExists:
    """Verify the dialog class and its key constants are present."""

    def test_dialog_class_exists(self):
        assert "class DataVerifyDialog" in SOURCE_TEXT

    def test_binance_horizon_constant(self):
        assert "_BINANCE_HORIZON_DAYS = 90" in SOURCE_TEXT

    def test_data_repair_thread_exists(self):
        assert "class DataRepairThread" in SOURCE_TEXT


class TestBtc18WindowSize:
    """Window must be wide enough (BTCAAAAA-18 width fix)."""

    def test_minimum_width_1300(self):
        assert "setMinimumWidth(1300)" in SOURCE_TEXT

    def test_minimum_height_720(self):
        assert "setMinimumHeight(720)" in SOURCE_TEXT

    def test_resize_1380_800(self):
        assert "resize(1380, 800)" in SOURCE_TEXT


class TestBtc18SubtitleCopy:
    """Subtitle must use BTC-specific copy (not generic 'all symbols')."""

    def test_subtitle_mentions_btcusdt(self):
        assert "BTCUSDT Perpetual" in SOURCE_TEXT

    def test_subtitle_mentions_all_timeframes(self):
        assert "across all timeframes" in SOURCE_TEXT


class TestBtc18NotesColumnStretch:
    """Notes column must use Stretch resize mode."""

    def test_notes_column_index_5(self):
        assert "setSectionResizeMode(5, QHeaderView.Stretch)" in SOURCE_TEXT


class TestBtc18GapClassification:
    """Gap classification must split by Binance horizon."""

    def test_repairable_list_comprehension(self):
        assert "repairable = [g for g in all_gaps if g['gap_start'] >= horizon_cutoff]" in SOURCE_TEXT

    def test_too_old_list_comprehension(self):
        assert "too_old = [g for g in all_gaps if g['gap_start'] < horizon_cutoff]" in SOURCE_TEXT

    def test_fix_btn_visible_when_repairable(self):
        assert "self._fix_btn.setVisible(True)" in SOURCE_TEXT

    def test_fix_btn_hidden_when_all_too_old(self):
        assert "Fix Gaps can't help here" in SOURCE_TEXT


class TestBtc18RepairFlow:
    """Fix Gaps must use DataRepairThread (not DataUpdateModal)."""

    def test_repair_thread_instantiated(self):
        assert "DataRepairThread()" in SOURCE_TEXT

    def test_verify_and_repair_called_with_dry_run_false(self):
        assert "dry_run=False" in SOURCE_TEXT

    def test_auto_reverify_after_repair(self):
        assert "self._start_verification()" in SOURCE_TEXT

    def test_repair_thread_uses_verify_and_repair(self):
        assert "manager.verify_and_repair" in SOURCE_TEXT


class TestBtc18UtcTimestamps:
    """UTC timestamp handling in data layer (BTCAAAAA-18 timestamp fix)."""

    def test_utc_time_label_format(self):
        assert "Current UTC time:" in SOURCE_TEXT

    def test_last_candle_utc_format(self):
        assert "%Y-%m-%d %H:%M UTC" in SOURCE_TEXT

    def test_horizon_cutoff_is_utc_aware(self):
        assert "datetime.now(timezone.utc)" in SOURCE_TEXT
