"""
Regression tests for BTCAAAAA-795: _determine_source() tz-awareness crash.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-795
Component: src/data_manager/unified_manager.py

Root cause: _determine_source() compared tz-aware end_date (from
Quick Preview's datetime.now(timezone.utc)) against tz-naive internal
timestamps, raising TypeError: can't compare offset-naive and offset-aware
datetimes.

Fix: normalize tz-naive incoming start_date/end_date to UTC-aware via
.replace(tzinfo=timezone.utc) before any comparison.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-795"),
    pytest.mark.regression,
]


@pytest.fixture()
def manager(tmp_path):
    """Return a UnifiedDataManager with isolated temp directories."""
    from src.data_manager.unified_manager import UnifiedDataManager
    mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
    mgr.binance_dir = tmp_path / "binance"
    mgr.binance_dir.mkdir(parents=True, exist_ok=True)
    mgr.lakeapi_dir = tmp_path / "lakeapi"
    mgr.lakeapi_dir.mkdir(parents=True, exist_ok=True)
    return mgr


class TestDetermineSourceTzAwareness:
    """
    Regression tests ensuring _determine_source() never raises TypeError when
    end_date / start_date are tz-aware (UTC), tz-naive, or mixed.
    Quick Preview passes datetime.now(timezone.utc) so all three cases must work.
    """

    def test_utc_aware_end_date_does_not_raise(self, manager):
        """UTC-aware end_date must not crash."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=40)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_naive_end_date_does_not_raise(self, manager):
        """Naive end_date (legacy callers) must still work after the tz fix."""
        end = datetime.now()
        start = end - timedelta(days=40)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_mixed_aware_start_naive_end_does_not_raise(self, manager):
        """Mixed tz inputs are normalized internally — no TypeError allowed."""
        end = datetime.now()  # naive
        start = datetime.now(timezone.utc) - timedelta(days=40)  # aware
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_mixed_naive_start_aware_end_does_not_raise(self, manager):
        """Reverse-mixed case: naive start, aware end."""
        end = datetime.now(timezone.utc)  # aware
        start = datetime.now() - timedelta(days=40)  # naive
        result = manager._determine_source(start_date=start, end_date=end)
        assert result is not None

    def test_recent_range_returns_binance(self, manager):
        """end_date in the recent window should route to BINANCE."""
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result == DataSource.BINANCE

    def test_old_range_returns_lakeapi(self, manager):
        """end_date well outside the Binance threshold should route to LAKEAPI."""
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc) - timedelta(days=manager.binance_threshold_days + 10)
        start = end - timedelta(days=10)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result == DataSource.LAKEAPI

    def test_hybrid_range_returns_auto(self, manager):
        """Range spanning both sides of the threshold returns AUTO."""
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=manager.binance_threshold_days + 10)
        result = manager._determine_source(start_date=start, end_date=end)
        assert result == DataSource.AUTO

    def test_start_date_none_returns_binance(self, manager):
        """start_date=None should default to BINANCE (recent data request)."""
        from src.data_manager.unified_manager import DataSource
        end = datetime.now(timezone.utc)
        result = manager._determine_source(start_date=None, end_date=end)
        assert result == DataSource.BINANCE

    def test_end_date_none_with_recent_start(self, manager):
        """end_date=None should default to now — recent range returns BINANCE."""
        from src.data_manager.unified_manager import DataSource
        start = datetime.now(timezone.utc) - timedelta(days=5)
        result = manager._determine_source(start_date=start, end_date=None)
        assert result == DataSource.BINANCE

    def test_end_date_none_with_old_start_hybrid(self, manager):
        """end_date=None defaults to now — span is hybrid → AUTO."""
        from src.data_manager.unified_manager import DataSource
        start = datetime.now(timezone.utc) - timedelta(days=manager.binance_threshold_days + 20)
        result = manager._determine_source(start_date=start, end_date=None)
        assert result == DataSource.AUTO

    def test_very_old_both_dates_returns_lakeapi(self, manager):
        """Both dates well past the threshold should route to LAKEAPI."""
        from src.data_manager.unified_manager import DataSource
        base = datetime.now(timezone.utc) - timedelta(days=manager.binance_threshold_days + 100)
        end = base + timedelta(days=10)
        result = manager._determine_source(start_date=base, end_date=end)
        assert result == DataSource.LAKEAPI

    def test_equal_dates_recent_returns_binance(self, manager):
        """start_date == end_date in recent window should route to BINANCE."""
        from src.data_manager.unified_manager import DataSource
        now = datetime.now(timezone.utc)
        result = manager._determine_source(start_date=now - timedelta(days=1), end_date=now - timedelta(days=1))
        assert result == DataSource.BINANCE

    def test_equal_dates_old_returns_lakeapi(self, manager):
        """start_date == end_date in old window should route to LAKEAPI."""
        from src.data_manager.unified_manager import DataSource
        old = datetime.now(timezone.utc) - timedelta(days=manager.binance_threshold_days + 50)
        result = manager._determine_source(start_date=old, end_date=old)
        assert result == DataSource.LAKEAPI
