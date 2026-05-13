"""
Regression tests for BTCAAAAA-997: fix P3 sanity check false-positive + bar_td scoping.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-997
Component: src/data_manager/unified_manager.py — verify_and_repair inline sanity check

The P3 post-ingest sanity check in verify_and_repair had two bugs:

1. Used abs() comparison which triggers false positives when the catalog
   extends past the repair window end_date. Fixed to one-directional: warn
   only when last_stored < expected_last_ts (data is too short). If
   last_stored >= expected_last_ts the catalog legitimately extends past
   end_date — no warning.

2. bar_td was only defined inside the inner ``for gap in gaps:`` try block,
   causing NameError when no gaps exist. Moved bar_td definition to the
   outer timeframe loop so the sanity check runs on both the gaps and
   no-gaps paths.

The sanity check:
  - Is called at the end of each timeframe iteration in verify_and_repair()
  - Uses get_last_bar_timestamp(tf) to find the latest bar on disk
  - Computes expected_last_ts as the last complete bar boundary before end_date
  - Warns when deficit = (expected_last_ts - last_stored) > 5s
  - Does NOT warn when last_stored >= expected_last_ts (catalog past end_date)
  - Logs an info message when the check passes
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-997"),
    pytest.mark.regression,
]


class TestVerifyAndRepairP3SanityCheck:
    """verify_and_repair's inline P3 sanity check must use one-directional
    comparison (deficit only — not abs()) and bar_td must be defined when no
    gaps exist.
    """

    @staticmethod
    def _make_manager():
        from src.data_manager.unified_manager import UnifiedDataManager

        return UnifiedDataManager(mode="backtest", startup_gap_check=False)

    def _run_repair(self, manager, last_stored, gaps=None, end_date=None):
        """Run verify_and_repair with heavy mocking to isolate the P3 check.

        We use *gaps=[]* (no gaps) so the gap-fetch loop is skipped entirely,
        avoiding the need to mock I/O.  The sanity check is then exercised
        with the mocked *last_stored* value.
        """
        if gaps is None:
            gaps = []
        if end_date is None:
            end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)

        patch_detect = patch.object(
            manager, "detect_gaps_in_binance_files", return_value=gaps
        )
        patch_last = patch.object(
            manager, "get_last_bar_timestamp", return_value=last_stored
        )
        with patch_detect, patch_last:
            return manager.verify_and_repair(
                timeframes=["15m"],
                start_date=end_date - timedelta(days=1),
                end_date=end_date,
                dry_run=False,
            )

    # ------------------------------------------------------------------
    # Scenario 1: catalog extends past end_date (the abs() false-positive)
    # ------------------------------------------------------------------

    def test_catalog_past_end_date_exact_match(self):
        """When last_stored == end_date (past expected bar boundary), the
        sanity check must NOT log an error.  The old abs() comparison would
        have triggered a false positive here because expected is one bar
        *before* end_date.
        """
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        last_stored = datetime(2026, 5, 13, 12, 0, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert not any("sanity FAILED" in e for e in errors), (
            f"False-positive sanity error when last_stored >= expected: {errors}"
        )

    def test_catalog_past_end_date_by_several_hours(self):
        """When last_stored is well past end_date, no error."""
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        last_stored = datetime(2026, 5, 13, 15, 0, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert not any("sanity FAILED" in e for e in errors), (
            f"False-positive when last_stored well past end_date: {errors}"
        )

    def test_catalog_past_end_date_equal_to_expected(self):
        """When last_stored == expected_last_ts (the bar before end_date),
        no error (exact match, deficit=0).
        """
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        # expected_last_ts = 2026-05-13 11:45:00 for 15m bars
        last_stored = datetime(2026, 5, 13, 11, 45, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert not any("sanity FAILED" in e for e in errors)

    # ------------------------------------------------------------------
    # Scenario 2: deficit detection (one-directional check is not broken)
    # ------------------------------------------------------------------

    def test_large_deficit_logs_error(self):
        """When data is too short (deficit >> 5s), the check must log an error."""
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        # expected is ~11:45, last_stored at 10:00 -> deficit ~105 min
        last_stored = datetime(2026, 5, 13, 10, 0, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert any("sanity FAILED" in e for e in errors), (
            f"Expected sanity error for large deficit, got: {errors}"
        )

    def test_small_deficit_within_tolerance_passes(self):
        """When deficit <= 5s, no error (borderline OK case)."""
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        # expected is ~11:45:00; last_stored at 11:44:59 -> deficit 1s -> OK
        last_stored = datetime(2026, 5, 13, 11, 44, 59)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert not any("sanity FAILED" in e for e in errors), (
            f"False sanity error for small deficit: {errors}"
        )

    # ------------------------------------------------------------------
    # Scenario 3: bar_td scoping (no NameError when gaps list is empty)
    # ------------------------------------------------------------------

    def test_no_gaps_no_nameerror(self):
        """When detect_gaps returns an empty list, the sanity check must
        still run without NameError (bar_td must be scoped at the outer
        timeframe loop, not inside the gap loop).
        """
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        last_stored = datetime(2026, 5, 13, 11, 45, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        # If bar_td was undefined (the scoping bug), this would raise
        # NameError before reaching the assert.  Getting a result proves
        # bar_td is properly scoped.
        assert "15m" in result, f"No '15m' key in result: {result}"
        # Sanity check ran (not silently skipped)
        errors = result.get("15m", {}).get("errors", [])
        assert not any("sanity FAILED" in e for e in errors)

    def test_no_gaps_deficit_still_detected(self):
        """bar_td scoping fix must not break deficit detection when no gaps."""
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        # last_stored way before expected -- deficit must be detected
        last_stored = datetime(2026, 5, 13, 8, 0, 0)

        result = self._run_repair(manager, last_stored, gaps=[], end_date=end_date)
        errors = result.get("15m", {}).get("errors", [])
        assert any("sanity FAILED" in e for e in errors), (
            f"Deficit not detected when no gaps: {errors}"
        )

    # ------------------------------------------------------------------
    # Scenario 4: None last_stored is handled (no crash)
    # ------------------------------------------------------------------

    def test_none_last_stored_skips_check(self):
        """When get_last_bar_timestamp returns None, the check is skipped
        (the ``if last_stored is not None`` guard).
        """
        manager = self._make_manager()
        end_date = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)

        result = self._run_repair(manager, None, gaps=[], end_date=end_date)
        assert "15m" in result
