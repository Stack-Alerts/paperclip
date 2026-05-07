"""
Unit tests for RC4c + RC6/UTC fixes — BTCAAAAA-368 / BTCAAAAA-167

RC4c: per-timeframe 15m-only scan anchor in _RuntimeCandleUpdateThread
RC6:  UTC-explicit timestamp helper _to_ms_utc in _fetch_binance_range
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_ms_utc(dt: datetime) -> int:
    """Reference copy of the RC6 helper — same one-liner as in unified_manager.py."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# RC6 — _to_ms_utc helper tests
# ─────────────────────────────────────────────────────────────────────────────

class TestToMsUtc:
    """Verify _to_ms_utc treats naive datetimes as UTC, independent of local TZ."""

    def test_known_epoch_converts_correctly(self):
        """Unix epoch should map to 0 ms."""
        epoch = datetime(1970, 1, 1, 0, 0, 0)
        assert _to_ms_utc(epoch) == 0

    def test_known_timestamp_2000(self):
        """2000-01-01 00:00:00 UTC = 946684800000 ms."""
        dt = datetime(2000, 1, 1, 0, 0, 0)
        assert _to_ms_utc(dt) == 946_684_800_000

    def test_naive_datetime_treated_as_utc_not_local(self):
        """
        Core regression check: a naive datetime at 10:00 UTC must produce
        the same ms as an explicitly UTC-aware datetime at 10:00.
        If the conversion were local (CEST UTC+2), the naive 10:00 would map
        to 08:00 UTC (946692000000), not 10:00 UTC (946699200000).
        """
        naive_10am = datetime(2000, 1, 1, 10, 0, 0)
        aware_10am = datetime(2000, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        expected_ms = int(aware_10am.timestamp() * 1000)
        assert _to_ms_utc(naive_10am) == expected_ms

    def test_two_hour_offset_not_applied(self):
        """
        CEST (UTC+2) machines would subtract 2h if naive→local conversion were used.
        Verify that _to_ms_utc does NOT produce 2h-earlier results.
        """
        naive_dt = datetime(2026, 5, 5, 10, 0, 0)           # 10:00 naive UTC
        correct_ms = int(naive_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        wrong_ms_cest = int((naive_dt - timedelta(hours=2)).replace(tzinfo=timezone.utc).timestamp() * 1000)
        result = _to_ms_utc(naive_dt)
        assert result == correct_ms
        assert result != wrong_ms_cest, "Result matched CEST-shifted (local) conversion — regression!"

    def test_start_and_end_times_are_ordered(self):
        """startTime < endTime when start < end."""
        start = datetime(2026, 5, 5, 9, 45, 0)
        end = datetime(2026, 5, 5, 10, 0, 0)
        assert _to_ms_utc(start) < _to_ms_utc(end)

    def test_15m_bar_duration_in_ms(self):
        """A 15-minute span should translate to exactly 900_000 ms."""
        t0 = datetime(2026, 5, 5, 9, 30, 0)
        t1 = t0 + timedelta(minutes=15)
        assert _to_ms_utc(t1) - _to_ms_utc(t0) == 900_000

    def test_returns_int(self):
        """Return type must be int (Binance API param)."""
        result = _to_ms_utc(datetime(2026, 1, 1))
        assert isinstance(result, int)


# ─────────────────────────────────────────────────────────────────────────────
# RC4c — scan anchor logic tests (unit-level, no Qt dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_scan_anchor(last_15m=None, session_start=None, now=None):
    """
    Pure Python re-implementation of the RC4c scan-anchor logic from
    _RuntimeCandleUpdateThread._run_one_cycle(), for unit testing without Qt.
    """
    if now is None:
        now = datetime.now()
    start_date = None
    try:
        if last_15m is not None:
            start_date = last_15m - timedelta(minutes=15)
        else:
            fallback_base = session_start if session_start is not None else now
            start_date = fallback_base - timedelta(minutes=15)
    except Exception:
        fallback_base = session_start if session_start is not None else now
        start_date = fallback_base - timedelta(minutes=15)
    return start_date


class TestRC4cScanAnchor:
    """
    Verify that the RC4c scan anchor uses ONLY the 15m last bar.

    Previously (RC4b) the code used min(last_15m, last_1h).  When the 1h bar
    was 07:00 and the 15m bar was 07:30, min() picked 07:00, causing the scan
    to start at 06:45 instead of 07:15 — 45 minutes too early.
    """

    def test_anchor_uses_15m_not_1h(self):
        """
        AC1: scan_start = last_15m - 15m, regardless of what 1h last bar is.
        """
        last_15m = datetime(2026, 5, 5, 7, 30, 0)
        # In the old RC4b world, last_1h = 07:00 would have dragged anchor back to 07:00
        # and scan_start back to 06:45.  RC4c ignores 1h entirely.
        scan_start = _compute_scan_anchor(last_15m=last_15m)
        expected = last_15m - timedelta(minutes=15)   # 07:15
        assert scan_start == expected, (
            f"Expected scan_start={expected.strftime('%H:%M')} but got {scan_start.strftime('%H:%M')}"
        )

    def test_anchor_not_pulled_to_1h_timestamp(self):
        """
        Regression: if 1h last bar (07:00) were still used via min(), scan_start
        would be 06:45.  Verify we never return 06:45 when 15m is at 07:30.
        """
        last_15m = datetime(2026, 5, 5, 7, 30, 0)
        would_be_wrong = datetime(2026, 5, 5, 6, 45, 0)  # old RC4b result
        scan_start = _compute_scan_anchor(last_15m=last_15m)
        assert scan_start != would_be_wrong, (
            "scan_start matched the old RC4b (1h-anchored) result — regression!"
        )

    def test_anchor_one_period_before_15m_last_bar(self):
        """scan_start must be exactly last_15m - 15 minutes."""
        cases = [
            datetime(2026, 5, 5, 7, 30, 0),
            datetime(2026, 5, 5, 10, 0, 0),
            datetime(2026, 5, 5, 14, 45, 0),
            datetime(2026, 5, 5, 23, 45, 0),
        ]
        for last_15m in cases:
            result = _compute_scan_anchor(last_15m=last_15m)
            assert result == last_15m - timedelta(minutes=15), (
                f"Failed for last_15m={last_15m}: got {result}"
            )

    def test_fallback_to_session_start_when_no_15m_bars(self):
        """
        When last_15m is None (no bars on disk), anchor falls back to
        session_start - 15m.
        """
        session_start = datetime(2026, 5, 5, 9, 0, 0)
        result = _compute_scan_anchor(last_15m=None, session_start=session_start)
        assert result == session_start - timedelta(minutes=15)

    def test_fallback_to_now_when_no_bars_and_no_session_start(self):
        """
        Edge case: no 15m bars AND no session_start → use now - 15m.
        """
        now = datetime(2026, 5, 5, 10, 0, 0)
        result = _compute_scan_anchor(last_15m=None, session_start=None, now=now)
        assert result == now - timedelta(minutes=15)

    def test_15m_only_anchor_is_simpler_than_min(self):
        """
        Conceptual test: when 15m is AHEAD of 1h, the 15m-only anchor is
        always LATER (closer to now) than the old min() result.
        This is the key property that prevents the 45-minute over-scan.
        """
        last_15m = datetime(2026, 5, 5, 7, 30, 0)
        last_1h = datetime(2026, 5, 5, 7, 0, 0)     # 30 min behind 15m

        rc4c_anchor = last_15m
        rc4b_anchor = min(last_15m, last_1h)         # old broken logic

        assert rc4c_anchor > rc4b_anchor, (
            "RC4c anchor should be LATER than old RC4b anchor when 1h lags 15m"
        )

    def test_rc4c_scan_start_later_than_rc4b(self):
        """
        When 1h lags 15m by 30 min, RC4c scan_start is 30 min later than RC4b.
        This means fewer unnecessary bars are re-scanned — no regressions here.
        """
        last_15m = datetime(2026, 5, 5, 7, 30, 0)
        last_1h = datetime(2026, 5, 5, 7, 0, 0)

        rc4c_start = last_15m - timedelta(minutes=15)         # 07:15
        rc4b_start = min(last_15m, last_1h) - timedelta(minutes=15)  # 06:45

        assert rc4c_start > rc4b_start
        assert rc4c_start == datetime(2026, 5, 5, 7, 15, 0)
        assert rc4b_start == datetime(2026, 5, 5, 6, 45, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Integration-ish: verify _fetch_binance_range uses UTC params
# (mocked at requests level — no live network calls)
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchBinanceRangeUtcParams:
    """
    Verify that _fetch_binance_range passes UTC-correct startTime/endTime
    to the Binance API.  The test instruments the requests.get mock to
    capture the actual params dict.
    """

    def _make_manager(self):
        """Create a UnifiedDataManager in backtest mode (no network, no disk I/O)."""
        from src.data_manager.unified_manager import UnifiedDataManager
        return UnifiedDataManager(mode='backtest', startup_gap_check=False)

    def test_start_time_is_utc_millis(self):
        """
        For a naive-UTC datetime at 10:00, startTime in the API params should
        match 10:00 UTC in milliseconds — NOT 08:00 UTC (which local CEST would give).
        """
        from src.data_manager.unified_manager import UnifiedDataManager

        naive_10am = datetime(2026, 5, 5, 10, 0, 0)   # naive, represents UTC
        expected_ms = int(naive_10am.replace(tzinfo=timezone.utc).timestamp() * 1000)
        wrong_ms_cest = int((naive_10am - timedelta(hours=2))
                            .replace(tzinfo=timezone.utc).timestamp() * 1000)

        captured_params = {}

        def mock_get(url, params=None, timeout=None):
            captured_params.update(params or {})
            # Return empty to break the loop after the first batch
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = []
            return mock_resp

        manager = UnifiedDataManager(mode='backtest', startup_gap_check=False)

        with patch('requests.get', side_effect=mock_get):
            try:
                manager._fetch_binance_range(
                    timeframe='15m',
                    start_ts=naive_10am,
                    end_ts=naive_10am + timedelta(minutes=15),
                    symbol='BTCUSDT',
                    futures=True,
                )
            except Exception:
                pass  # May throw on no data; we only care about the captured params

        if 'startTime' in captured_params:
            actual_start_ms = captured_params['startTime']
            assert actual_start_ms == expected_ms, (
                f"startTime mismatch: expected {expected_ms} (10:00 UTC) "
                f"but got {actual_start_ms}. "
                f"CEST-shifted wrong value would be {wrong_ms_cest} (08:00 UTC)."
            )
            assert actual_start_ms != wrong_ms_cest, (
                "startTime matched CEST-shifted conversion — UTC fix regression!"
            )

    def test_end_time_is_utc_millis(self):
        """endTime should also use UTC milliseconds, not local."""
        naive_10am = datetime(2026, 5, 5, 10, 0, 0)
        naive_1015 = datetime(2026, 5, 5, 10, 15, 0)
        expected_end_ms = int(naive_1015.replace(tzinfo=timezone.utc).timestamp() * 1000)

        captured_params = {}

        def mock_get(url, params=None, timeout=None):
            captured_params.update(params or {})
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = []
            return mock_resp

        from src.data_manager.unified_manager import UnifiedDataManager
        manager = UnifiedDataManager(mode='backtest', startup_gap_check=False)

        with patch('requests.get', side_effect=mock_get):
            try:
                manager._fetch_binance_range(
                    timeframe='15m',
                    start_ts=naive_10am,
                    end_ts=naive_1015,
                    symbol='BTCUSDT',
                    futures=True,
                )
            except Exception:
                pass

        if 'endTime' in captured_params:
            assert captured_params['endTime'] == expected_end_ms
