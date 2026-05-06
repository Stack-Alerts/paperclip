"""
Unit tests for DataFreshnessGate.

Tests cover:
- FreshnessStatus enum
- StaleDataError construction
- DataFreshnessGate initialization
- record_tick() and record_bar()
- tick_status() and bar_status()
- last_tick_age() and last_bar_age()
- check_tick_freshness() — fresh, stale, no data
- check_bar_freshness() — fresh, stale, no data
- guard() context manager
- Clock injection for deterministic testing
- Thread-safety smoke test
- summary()
"""

from __future__ import annotations

import sys
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.binance_ws_stream import TradeTick
from src.itm.data.data_freshness_gate import (
    DataFreshnessGate,
    FreshnessStatus,
    StaleDataError,
)
from src.itm.data.realtime_bar_builder import BarInterval, OHLCVBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tick(
    ts: datetime,
    symbol: str = "BTCUSDT",
    price: str = "95000.0",
    qty: str = "0.01",
) -> TradeTick:
    return TradeTick(
        symbol=symbol,
        price=Decimal(price),
        quantity=Decimal(qty),
        is_buyer_maker=False,
        trade_id=1,
        timestamp=ts,
    )


def _make_bar(ts: datetime, interval: BarInterval = BarInterval.ONE_MIN) -> OHLCVBar:
    return OHLCVBar(
        symbol="BTCUSDT",
        interval=interval,
        timestamp=ts,
        open=Decimal("95000"),
        high=Decimal("95100"),
        low=Decimal("94900"),
        close=Decimal("95050"),
        volume=Decimal("1.0"),
        volume_quote=Decimal("95000"),
        trade_count=10,
    )


def _frozen_clock(ts: datetime):
    """Return a clock function that always returns *ts*."""
    return lambda: ts


# ---------------------------------------------------------------------------
# StaleDataError tests
# ---------------------------------------------------------------------------


class TestStaleDataError:
    def test_construction(self):
        err = StaleDataError(age_seconds=90.0, max_age_seconds=60, source="tick")
        assert err.age_seconds == 90.0
        assert err.max_age_seconds == 60
        assert err.source == "tick"
        assert "90.0" in str(err)
        assert "60" in str(err)

    def test_detail_included_in_message(self):
        err = StaleDataError(90.0, 60, source="bar", detail="symbol=BTCUSDT")
        assert "symbol=BTCUSDT" in str(err)


# ---------------------------------------------------------------------------
# DataFreshnessGate init tests
# ---------------------------------------------------------------------------


class TestGateInit:
    def test_default_max_age(self):
        gate = DataFreshnessGate()
        assert gate.max_age_seconds == 60

    def test_custom_max_age(self):
        gate = DataFreshnessGate(max_age_seconds=30)
        assert gate.max_age_seconds == 30

    def test_invalid_max_age_raises(self):
        with pytest.raises(ValueError):
            DataFreshnessGate(max_age_seconds=0)

    def test_repr(self):
        gate = DataFreshnessGate()
        assert "60" in repr(gate)


# ---------------------------------------------------------------------------
# tick_status() and check_tick_freshness() tests
# ---------------------------------------------------------------------------


class TestTickFreshness:
    def test_no_data_returns_no_data_status(self):
        gate = DataFreshnessGate()
        assert gate.tick_status() == FreshnessStatus.NO_DATA

    def test_fresh_tick_returns_fresh(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        # Tick 30s ago — fresh
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=30)))
        assert gate.tick_status() == FreshnessStatus.FRESH

    def test_stale_tick_returns_stale(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        # Tick 90s ago — stale
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=90)))
        assert gate.tick_status() == FreshnessStatus.STALE

    def test_exactly_at_max_age_is_fresh(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=60)))
        assert gate.tick_status() == FreshnessStatus.FRESH

    def test_check_tick_freshness_no_data_raises(self):
        gate = DataFreshnessGate()
        with pytest.raises(StaleDataError) as exc_info:
            gate.check_tick_freshness()
        assert exc_info.value.source == "tick"

    def test_check_tick_freshness_stale_raises(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=90)))
        with pytest.raises(StaleDataError):
            gate.check_tick_freshness()

    def test_check_tick_freshness_fresh_does_not_raise(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=10)))
        gate.check_tick_freshness()  # should not raise

    def test_last_tick_age(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=25)))
        age = gate.last_tick_age()
        assert abs(age - 25.0) < 0.01

    def test_last_tick_age_no_data_returns_none(self):
        gate = DataFreshnessGate()
        assert gate.last_tick_age() is None

    def test_multiple_symbols_tracked_independently(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=10), symbol="BTCUSDT"))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=90), symbol="ETHUSDT"))
        assert gate.tick_status("BTCUSDT") == FreshnessStatus.FRESH
        assert gate.tick_status("ETHUSDT") == FreshnessStatus.STALE


# ---------------------------------------------------------------------------
# bar_status() and check_bar_freshness() tests
# ---------------------------------------------------------------------------


class TestBarFreshness:
    def test_no_data_returns_no_data(self):
        gate = DataFreshnessGate()
        assert gate.bar_status() == FreshnessStatus.NO_DATA

    def test_fresh_bar_returns_fresh(self):
        now = datetime(2026, 5, 6, 10, 5, 30, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        # Bar opened at 10:05 — that's 30s ago; within max_age + interval
        gate.record_bar(_make_bar(ts=datetime(2026, 5, 6, 10, 5, 0, tzinfo=timezone.utc)))
        assert gate.bar_status() == FreshnessStatus.FRESH

    def test_stale_bar_returns_stale(self):
        now = datetime(2026, 5, 6, 10, 10, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        # Bar from 10:00 — that's 600s ago; exceeds max_age(60) + interval(60) = 120s
        gate.record_bar(_make_bar(ts=datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)))
        assert gate.bar_status() == FreshnessStatus.STALE

    def test_check_bar_freshness_stale_raises(self):
        now = datetime(2026, 5, 6, 10, 10, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_bar(_make_bar(ts=datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)))
        with pytest.raises(StaleDataError) as exc_info:
            gate.check_bar_freshness()
        assert exc_info.value.source == "bar"


# ---------------------------------------------------------------------------
# guard() context manager tests
# ---------------------------------------------------------------------------


class TestGuardContextManager:
    def test_fresh_data_does_not_raise(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=10)))
        with gate.guard():
            pass  # should not raise

    def test_stale_data_raises_in_guard(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=90)))
        with pytest.raises(StaleDataError):
            with gate.guard():
                pass

    def test_no_data_raises_in_guard(self):
        gate = DataFreshnessGate(max_age_seconds=60)
        with pytest.raises(StaleDataError):
            with gate.guard():
                pass

    def test_guard_check_ticks_false_skips_tick_check(self):
        gate = DataFreshnessGate(max_age_seconds=60)
        # No ticks recorded — but check_ticks=False should not raise
        with gate.guard(check_ticks=False, check_bars=False):
            pass


# ---------------------------------------------------------------------------
# summary() test
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_format(self):
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        gate.record_tick(_make_tick(ts=now - timedelta(seconds=5)))
        gate.record_bar(_make_bar(ts=now - timedelta(seconds=30)))
        s = gate.summary()
        assert "max_age_seconds" in s
        assert "tick_ages" in s
        assert "bar_ages" in s
        assert "BTCUSDT" in s["tick_ages"]


# ---------------------------------------------------------------------------
# Thread-safety smoke test
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_record_and_check(self):
        """Quick smoke test: multiple threads recording ticks simultaneously."""
        now = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
        gate = DataFreshnessGate(max_age_seconds=60, clock=_frozen_clock(now))
        errors = []

        def record_lots():
            for i in range(100):
                try:
                    gate.record_tick(
                        _make_tick(ts=now - timedelta(seconds=1))
                    )
                    gate.tick_status()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=record_lots) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
