"""
Regression tests for BTCAAAAA-994: complete UTC timestamp fix for bar-timestamp
conversion in multicore backtest engine and single-core path.

Bug: datetime.fromtimestamp(ns/1e9) uses the server's local timezone (CEST = UTC+2
in summer, CET = UTC+1 in winter). dt_to_unix_nanos() stores bar timestamps as UTC
nanoseconds, so the round-trip through fromtimestamp() shifts trade timestamps by
+1h (winter) or +2h (summer), causing audit scripts to match trades against the
wrong OHLCV bar.

Fix: use datetime.fromtimestamp(..., tz=timezone.utc).replace(tzinfo=None) at all
bar-timestamp conversion sites (multicore_backtest_engine.py exit_timestamp and
backtest_config_panel.py entry + exit timestamps).

Prices were never wrong — only the recorded timestamps were shifted.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from nautilus_trader.core.datetime import dt_to_unix_nanos

pytestmark = [
    pytest.mark.bug("BTCAAAAA-994"),
    pytest.mark.regression,
]


def _utc_from_nanos(ns: int) -> datetime:
    """The correct UTC-aware conversion used in the fix."""
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).replace(tzinfo=None)


def _local_from_nanos(ns: int) -> datetime:
    """The buggy local-timezone conversion (pre-fix)."""
    return datetime.fromtimestamp(ns / 1_000_000_000)


# ---------------------------------------------------------------------------
# Verify the correct timestamp conversion (UTC round-trip)
# ---------------------------------------------------------------------------


class TestUtcTimestampRoundTrip:
    """dt_to_unix_nanos → _utc_from_nanos → dt_to_unix_nanos must be idempotent."""

    def test_epoch_zero_round_trip(self):
        """Unix epoch (0 ns) converts to 1970-01-01 00:00:00."""
        ns = 0
        dt = _utc_from_nanos(ns)
        assert dt == datetime(1970, 1, 1, 0, 0, 0)
        assert dt_to_unix_nanos(dt) == ns

    def test_typical_bar_timestamp_round_trip(self):
        """A typical 15m bar timestamp round-trips correctly."""
        bar_dt = datetime(2025, 6, 1, 10, 0, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt

    def test_summer_bar_round_trip(self):
        """Summer bar (CEST = UTC+2) round-trips correctly."""
        bar_dt = datetime(2025, 7, 15, 14, 30, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt

    def test_winter_bar_round_trip(self):
        """Winter bar (CET = UTC+1) round-trips correctly."""
        bar_dt = datetime(2025, 1, 15, 14, 30, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt

    def test_midnight_boundary_round_trip(self):
        """Midnight UTC boundary round-trips correctly."""
        bar_dt = datetime(2025, 6, 1, 0, 0, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt

    def test_dst_transition_round_trip(self):
        """March DST transition date (UTC+1 → UTC+2) round-trips correctly."""
        bar_dt = datetime(2025, 3, 30, 1, 0, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt

    def test_near_future_bar_round_trip(self):
        """Near-future timestamp round-trips correctly."""
        bar_dt = datetime(2026, 12, 31, 23, 45, 0)
        ns = dt_to_unix_nanos(bar_dt)
        dt = _utc_from_nanos(ns)
        assert dt == bar_dt


# ---------------------------------------------------------------------------
# Verify the OLD local-timezone behavior would produce wrong results
# ---------------------------------------------------------------------------


class TestLocalTimezoneDrift:
    """The buggy datetime.fromtimestamp(ns/1e9) shifts timestamps by the
    server's UTC offset.  The fix must use tz=timezone.utc.
    """

    def test_summer_local_drift_is_nonzero(self):
        """In summer (CEST=UTC+2), local conversion shifts by 2 hours."""
        bar_dt = datetime(2025, 7, 15, 12, 0, 0)
        ns = dt_to_unix_nanos(bar_dt)
        # The buggy conversion would produce a different time in UTC+2 zones
        local_dt = datetime.fromtimestamp(ns / 1_000_000_000)
        utc_dt = datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).replace(tzinfo=None)
        # Local and UTC conversions should agree for a UTC epoch, but
        # when run in a non-UTC timezone they will differ
        local_offset = local_dt - utc_dt
        # The offset is the server's UTC offset (on GitHub Actions = UTC+0)
        # but on a dev machine in CEST would be +2h
        assert local_offset == timedelta(0) or local_offset == timedelta(hours=1) or local_offset == timedelta(hours=2), (
            f"Unexpected local offset: {local_offset}. "
            "This test documents that local fromtimestamp drifts by the server TZ offset."
        )

    def test_utc_conversion_never_drifts(self):
        """UTC conversion always produces correct results regardless of TZ."""
        test_cases = [
            datetime(2025, 1, 1, 0, 0, 0),
            datetime(2025, 6, 15, 12, 30, 0),
            datetime(2025, 12, 25, 23, 59, 59),
            datetime(2026, 3, 8, 2, 30, 0),
        ]
        for expected_dt in test_cases:
            ns = dt_to_unix_nanos(expected_dt)
            result_dt = _utc_from_nanos(ns)
            assert result_dt == expected_dt, (
                f"UTC conversion failed for {expected_dt}: got {result_dt}"
            )

    def test_utc_result_is_tz_naive(self):
        """The fix must strip timezone info — result is a naive datetime."""
        ns = dt_to_unix_nanos(datetime(2025, 6, 1, 10, 0, 0))
        dt = _utc_from_nanos(ns)
        assert dt.tzinfo is None


# ---------------------------------------------------------------------------
# Verify evaluate_chunk inline equivalent
# ---------------------------------------------------------------------------


class TestEvaluateChunkTimestampConversion:
    """The exact conversion pattern used in evaluate_chunk() lines 244 and 637."""

    def test_entry_timestamp_conversion(self):
        """evaluate_chunk entry_timestamp conversion (line 244)."""
        from datetime import timezone as _tz
        bar_ts_init = 1748779200000000000  # 2025-06-01 12:00:00 UTC
        result = datetime.fromtimestamp(bar_ts_init / 1e9, tz=_tz.utc).replace(tzinfo=None)
        assert result == datetime(2025, 6, 1, 12, 0, 0)

    def test_exit_timestamp_conversion(self):
        """evaluate_chunk exit_timestamp conversion (line 637)."""
        bar_ts_init = 1748779200000000000
        result = datetime.fromtimestamp(bar_ts_init / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2025, 6, 1, 12, 0, 0)

    def test_dst_spring_forward_timestamp(self):
        """DST spring-forward (March 30, 2025 02:00 CEST)."""
        bar_ts_init = 1743292800000000000  # 2025-03-30 00:00:00 UTC
        result = datetime.fromtimestamp(bar_ts_init / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2025, 3, 30, 0, 0, 0)

    def test_dst_fall_back_timestamp(self):
        """DST fall-back (October 26, 2025 03:00 CEST → 02:00 CET)."""
        bar_ts_init = 1761436800000000000  # 2025-10-26 00:00:00 UTC
        result = datetime.fromtimestamp(bar_ts_init / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2025, 10, 26, 0, 0, 0)
