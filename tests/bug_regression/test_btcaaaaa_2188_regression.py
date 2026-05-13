"""
Regression tests for BTCAAAAA-2188: Cache-poisoning guard in data_cache_manager.py.

Issue: BTCAAAAA-2188
Fixed in commit: a3413ec
Component: src/optimizer_v3/core/data_cache_manager.py

Root cause: DataCacheManager.cache_bars() would cache truncated bar data
(e.g. only 1,500 bars from Binance limit=1500 without startTime), poisoning
the cache for subsequent same-day runs. Day-boundary rounding in the config
hash made every same-day run a cache HIT on truncated data.

Fix: Added _is_truncated() guard that estimates expected bar count from the
date range and timeframe, and refuses to cache if actual count < 50% of expected.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytest

from src.optimizer_v3.core.data_cache_manager import DataCacheManager

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2188"),
    pytest.mark.regression,
]


class TestCachePoisoningGuard:
    """Verify the cache-poisoning truncation guard in DataCacheManager."""

    @pytest.fixture
    def mgr(self):
        return DataCacheManager()

    @pytest.fixture
    def thirty_day_config(self):
        now = datetime(2026, 5, 12)
        return {
            "lookback_days": 30,
            "timeframe": "15m",
            "start_date": now - timedelta(days=30),
            "end_date": now,
        }

    def test_truncated_bars_not_cached(self, mgr, thirty_day_config):
        bars = [1] * 100
        mgr.cache_bars(bars, thirty_day_config)
        assert mgr._cache is None

    def test_healthy_bars_cached(self, mgr, thirty_day_config):
        bars = [1] * 2800
        mgr.cache_bars(bars, thirty_day_config)
        assert mgr._cache is not None
        assert len(mgr._cache) == 2800

    def test_empty_bars_not_cached(self, mgr, thirty_day_config):
        mgr.cache_bars([], thirty_day_config)
        assert mgr._cache is None

    def test_missing_dates_allows_cache(self, mgr):
        config = {"lookback_days": 30, "timeframe": "15m"}
        mgr.cache_bars([1, 2, 3], config)
        assert mgr._cache is not None

    def test_warning_logged_on_guard_trip(self, mgr, thirty_day_config, caplog):
        caplog.set_level(logging.WARNING)
        mgr.cache_bars([1] * 50, thirty_day_config)
        assert "Cache-poisoning guard" in caplog.text
        assert "refusing to cache" in caplog.text

    def test_hit_miss_counts_unaffected(self, mgr, thirty_day_config):
        mgr.cache_bars([1] * 50, thirty_day_config)
        assert mgr._hits == 0
        assert mgr._misses == 0

    def test_exact_threshold_bars_cached(self, mgr, thirty_day_config):
        expected = int((30 * 86400) / (15 * 60))
        threshold = int(expected * DataCacheManager.TRUNCATION_THRESHOLD)
        mgr.cache_bars([1] * threshold, thirty_day_config)
        assert mgr._cache is not None

    def test_just_below_threshold_not_cached(self, mgr, thirty_day_config):
        expected = int((30 * 86400) / (15 * 60))
        just_below = int(expected * DataCacheManager.TRUNCATION_THRESHOLD) - 1
        mgr.cache_bars([1] * max(just_below, 0), thirty_day_config)
        assert mgr._cache is None

    def test_timeframe_to_minutes(self):
        assert DataCacheManager._timeframe_to_minutes("15m") == 15
        assert DataCacheManager._timeframe_to_minutes("1h") == 60
        assert DataCacheManager._timeframe_to_minutes("30m") == 30
        assert DataCacheManager._timeframe_to_minutes("1d") == 1440
        assert DataCacheManager._timeframe_to_minutes("") == 15
        assert DataCacheManager._timeframe_to_minutes("invalid") == 1440

    def test_is_truncated_with_no_bars(self, mgr, thirty_day_config):
        assert mgr._is_truncated([], thirty_day_config) is True

    def test_is_truncated_with_no_dates(self, mgr):
        config = {"timeframe": "15m"}
        assert mgr._is_truncated([1, 2, 3], config) is False
