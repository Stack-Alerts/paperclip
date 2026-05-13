"""
Regression tests for BTCAAAAA-995: post_ingest_sanity_check — assert the most
recent on-disk bar is within tolerance of the expected timestamp.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-995
Component: src/data_manager/unified_manager.py

post_ingest_sanity_check(timeframe, expected_last_ts, tolerance_s=5.0):
  - Uses get_last_bar_timestamp() to find the latest bar on disk.
  - Raises RuntimeError("no bars found") when get_last_bar_timestamp() returns None.
  - Normalises expected_last_ts to tz-naive UTC before comparison.
  - Raises RuntimeError when |actual - expected| > tolerance_s.
  - Logs an info message when the check passes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-995"),
    pytest.mark.regression,
]


class TestPostIngestSanityCheck:
    """UnifiedDataManager.post_ingest_sanity_check must verify the most recent
    bar timestamp is within tolerance of the expected value.

    The method is a P3 guard that catches silent truncation (API returning 0
    bars, cursor logic stopping early, wrong end_ts rounding, etc.).
    """

    @staticmethod
    def _make_manager():
        from src.data_manager.unified_manager import UnifiedDataManager
        return UnifiedDataManager(mode='backtest', startup_gap_check=False)

    # -- happy path ----------------------------------------------------------

    def test_within_tolerance_passes(self):
        """Delta < 5s must pass without raising."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 0, 3)  # 3s delta
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected)

    def test_exactly_at_tolerance_passes(self):
        """Delta == 5s must pass (the check is ``>``, not ``>=``)."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 0, 5)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected)

    def test_zero_delta_passes(self):
        """Exact match must pass."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=expected):
            manager.post_ingest_sanity_check('15m', expected)

    # -- delta exceeds tolerance ---------------------------------------------

    def test_delta_exceeds_tolerance_raises(self):
        """Delta > 5s must raise RuntimeError."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 0, 10)  # 10s delta
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            with pytest.raises(RuntimeError, match="post_ingest_sanity_check/15m"):
                manager.post_ingest_sanity_check('15m', expected)

    def test_negative_delta_exceeds_tolerance_raises(self):
        """Actual before expected by >5s must also raise (uses abs())."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 10)
        actual = datetime(2026, 5, 13, 12, 0, 0)  # -10s delta
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            with pytest.raises(RuntimeError, match="post_ingest_sanity_check/15m"):
                manager.post_ingest_sanity_check('15m', expected)

    # -- no bars on disk -----------------------------------------------------

    def test_no_bars_on_disk_raises(self):
        """When get_last_bar_timestamp returns None, must raise RuntimeError."""
        manager = self._make_manager()
        with patch.object(manager, 'get_last_bar_timestamp', return_value=None):
            with pytest.raises(RuntimeError, match="no bars found"):
                manager.post_ingest_sanity_check(
                    '15m', datetime(2026, 5, 13, 12, 0, 0),
                )

    # -- tz-aware expected timestamp -----------------------------------------

    def test_tz_aware_expected_normalised_by_strip(self):
        """A tz-aware expected timestamp is normalised by stripping tzinfo
        (not converting).  Passing 12:00 UTC and 12:00+02:00 both strip to
        12:00 naive, so the comparison uses the raw clock value."""
        manager = self._make_manager()
        expected_aware = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)
        actual = datetime(2026, 5, 13, 12, 0, 1)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected_aware)

    def test_tz_aware_expected_strips_without_converting(self):
        """Stripping tzinfo preserves the civil time — 12:00+02:00 becomes
        12:00 naive (not 10:00).  The actual must match the stripped value."""
        from datetime import timedelta

        manager = self._make_manager()
        # 12:00 +02:00 → strips to 12:00 naive
        expected_aware = datetime(2026, 5, 13, 12, 0, 0,
                                  tzinfo=timezone(timedelta(hours=2)))
        # actual must be close to 12:00 naive (not 10:00 UTC)
        actual = datetime(2026, 5, 13, 12, 0, 1)  # 1s after 12:00
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected_aware)

    def test_tz_aware_expected_pandas_timestamp(self):
        """A pd.Timestamp (tz-aware) expected value must be handled."""
        import pandas as pd
        manager = self._make_manager()
        expected_ts = pd.Timestamp('2026-05-13 12:00:00', tz='UTC')
        actual = datetime(2026, 5, 13, 12, 0, 2)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected_ts)

    # -- custom tolerance ----------------------------------------------------

    def test_custom_tolerance_respected(self):
        """A custom tolerance_s must be used instead of the default 5s."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 1, 0)  # 60s delta - would fail at 5s
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            manager.post_ingest_sanity_check('15m', expected, tolerance_s=120.0)

    def test_custom_tolerance_exceeded_raises(self):
        """When custom tolerance is exceeded, must raise."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 0, 51)  # 51s delta
        tolerance = 50.0
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            with pytest.raises(RuntimeError):
                manager.post_ingest_sanity_check(
                    '15m', expected, tolerance_s=tolerance,
                )

    # -- timeframe propagation -----------------------------------------------

    def test_timeframe_appears_in_error_message(self):
        """The timeframe must be included in the RuntimeError message."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 1, 0)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            with pytest.raises(RuntimeError, match=r"post_ingest_sanity_check/1h"):
                manager.post_ingest_sanity_check('1h', expected)

    def test_timeframe_logged_on_success(self, caplog):
        """On success, the timeframe must be logged."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 0, 2)
        with caplog.at_level(logging.INFO):
            with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
                manager.post_ingest_sanity_check('15m', expected)
        assert "post_ingest_sanity_check/15m OK" in caplog.text

    # -- delta values in error message ---------------------------------------

    def test_error_message_includes_delta_and_tolerance(self):
        """The RuntimeError message must contain both the delta and threshold
        so callers can diagnose the gap."""
        manager = self._make_manager()
        expected = datetime(2026, 5, 13, 12, 0, 0)
        actual = datetime(2026, 5, 13, 12, 1, 0)
        with patch.object(manager, 'get_last_bar_timestamp', return_value=actual):
            with pytest.raises(RuntimeError) as excinfo:
                manager.post_ingest_sanity_check('15m', expected, tolerance_s=30.0)
        msg = str(excinfo.value)
        assert "delta=60.0s" in msg
        assert "30.0s threshold" in msg
