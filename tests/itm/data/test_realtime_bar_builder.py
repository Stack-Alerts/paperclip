"""
Unit tests for RealtimeBarBuilder.

Tests cover:
- OHLCVBar construction and validation
- BarInterval properties
- Bar alignment (_align_bar_open)
- Single-interval bar building (1m)
- Multi-interval bar building (1m + 15m)
- Bar closing on period boundary
- Flush semantics
- Subscriber management
- Edge cases: empty stream, single tick, duplicate ticks
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.binance_ws_stream import TradeTick
from src.itm.data.realtime_bar_builder import (
    BarInterval,
    OHLCVBar,
    RealtimeBarBuilder,
    _align_bar_open,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tick(
    price: str = "95000.0",
    qty: str = "0.010",
    ts: datetime = None,
    symbol: str = "BTCUSDT",
    is_buyer_maker: bool = False,
    trade_id: int = 1,
) -> TradeTick:
    if ts is None:
        ts = datetime(2026, 5, 6, 10, 0, 30, tzinfo=timezone.utc)
    return TradeTick(
        symbol=symbol,
        price=Decimal(price),
        quantity=Decimal(qty),
        is_buyer_maker=is_buyer_maker,
        trade_id=trade_id,
        timestamp=ts,
    )


def _ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 5, 6, h, m, s, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# BarInterval tests
# ---------------------------------------------------------------------------


class TestBarInterval:
    def test_one_min_seconds(self):
        assert BarInterval.ONE_MIN.seconds == 60

    def test_fifteen_min_seconds(self):
        assert BarInterval.FIFTEEN_MIN.seconds == 900

    def test_labels(self):
        assert BarInterval.ONE_MIN.label == "1m"
        assert BarInterval.FIFTEEN_MIN.label == "15m"
        assert BarInterval.FIVE_MIN.label == "5m"
        assert BarInterval.ONE_HOUR.label == "1h"


# ---------------------------------------------------------------------------
# _align_bar_open tests
# ---------------------------------------------------------------------------


class TestAlignBarOpen:
    def test_align_one_min_on_boundary(self):
        ts = _ts(10, 5, 0)
        aligned = _align_bar_open(ts, BarInterval.ONE_MIN)
        assert aligned == datetime(2026, 5, 6, 10, 5, 0, tzinfo=timezone.utc)

    def test_align_one_min_mid_bar(self):
        ts = _ts(10, 5, 45)
        aligned = _align_bar_open(ts, BarInterval.ONE_MIN)
        assert aligned == datetime(2026, 5, 6, 10, 5, 0, tzinfo=timezone.utc)

    def test_align_fifteen_min_boundary(self):
        ts = _ts(10, 30, 0)
        aligned = _align_bar_open(ts, BarInterval.FIFTEEN_MIN)
        assert aligned == datetime(2026, 5, 6, 10, 30, 0, tzinfo=timezone.utc)

    def test_align_fifteen_min_mid_bar(self):
        ts = _ts(10, 37, 30)
        aligned = _align_bar_open(ts, BarInterval.FIFTEEN_MIN)
        assert aligned == datetime(2026, 5, 6, 10, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# OHLCVBar tests
# ---------------------------------------------------------------------------


class TestOHLCVBar:
    def _make_bar(self, **overrides):
        defaults = dict(
            symbol="BTCUSDT",
            interval=BarInterval.ONE_MIN,
            timestamp=_ts(10, 5),
            open=Decimal("95000"),
            high=Decimal("95200"),
            low=Decimal("94900"),
            close=Decimal("95100"),
            volume=Decimal("1.5"),
            volume_quote=Decimal("142650"),
            trade_count=30,
        )
        defaults.update(overrides)
        return OHLCVBar(**defaults)

    def test_valid_bar_constructs(self):
        bar = self._make_bar()
        assert bar.symbol == "BTCUSDT"
        assert bar.closed is True

    def test_bar_end(self):
        bar = self._make_bar(timestamp=_ts(10, 5))
        assert bar.bar_end == _ts(10, 6)

    def test_bar_end_fifteen_min(self):
        bar = self._make_bar(interval=BarInterval.FIFTEEN_MIN, timestamp=_ts(10, 15))
        assert bar.bar_end == _ts(10, 30)

    def test_invalid_high_less_than_low(self):
        with pytest.raises(ValueError, match="high"):
            self._make_bar(high=Decimal("94000"), low=Decimal("95000"))

    def test_invalid_open_above_high(self):
        with pytest.raises(ValueError, match="open"):
            self._make_bar(
                open=Decimal("95300"),
                high=Decimal("95200"),
                low=Decimal("94900"),
                close=Decimal("95100"),
            )

    def test_invalid_close_above_high(self):
        with pytest.raises(ValueError, match="close"):
            self._make_bar(
                open=Decimal("95000"),
                high=Decimal("95200"),
                low=Decimal("94900"),
                close=Decimal("95300"),
            )

    def test_negative_volume_rejected(self):
        with pytest.raises(ValueError, match="volume"):
            self._make_bar(volume=Decimal("-1"))

    def test_repr_contains_key_info(self):
        bar = self._make_bar()
        r = repr(bar)
        assert "BTCUSDT" in r
        assert "1m" in r


# ---------------------------------------------------------------------------
# RealtimeBarBuilder tests
# ---------------------------------------------------------------------------


class TestRealtimeBarBuilder:
    def test_initial_state(self):
        builder = RealtimeBarBuilder()
        assert builder.ticks_processed == 0
        assert builder.bars_closed == 0

    def test_single_tick_opens_bar(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        tick = _make_tick(ts=_ts(10, 5, 30))
        builder.on_tick(tick)
        bar = builder.get_open_bar(BarInterval.ONE_MIN)
        assert bar is not None
        assert bar.open == Decimal("95000.0")
        assert bar.close == Decimal("95000.0")
        assert bar.trade_count == 1

    def test_multiple_ticks_same_bar(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        ts = _ts(10, 5)
        ticks = [
            _make_tick("95000", "0.01", ts=_ts(10, 5, 10), trade_id=1),
            _make_tick("95100", "0.02", ts=_ts(10, 5, 20), trade_id=2),
            _make_tick("94900", "0.03", ts=_ts(10, 5, 40), trade_id=3),
            _make_tick("95050", "0.01", ts=_ts(10, 5, 55), trade_id=4),
        ]
        for t in ticks:
            builder.on_tick(t)
        bar = builder.get_open_bar(BarInterval.ONE_MIN)
        assert bar.open == Decimal("95000")
        assert bar.high == Decimal("95100")
        assert bar.low == Decimal("94900")
        assert bar.close == Decimal("95050")
        assert bar.trade_count == 4
        assert bar.volume == Decimal("0.07")

    def test_bar_closes_on_new_period(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        closed_bars = []
        builder.subscribe_closed(closed_bars.append)

        # Tick in minute 5
        builder.on_tick(_make_tick("95000", "0.01", ts=_ts(10, 5, 30), trade_id=1))
        assert len(closed_bars) == 0

        # Tick in minute 6 — triggers close of minute 5
        builder.on_tick(_make_tick("95100", "0.01", ts=_ts(10, 6, 1), trade_id=2))
        assert len(closed_bars) == 1
        closed = closed_bars[0]
        assert closed.timestamp == _ts(10, 5)
        assert closed.open == Decimal("95000")
        assert closed.interval == BarInterval.ONE_MIN

    def test_fifteen_min_bar_independent(self):
        builder = RealtimeBarBuilder(
            intervals=[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN]
        )
        closed_1m = []
        closed_15m = []
        builder.subscribe_closed(
            lambda b: closed_1m.append(b) if b.interval == BarInterval.ONE_MIN else closed_15m.append(b)
        )

        # Fill minute 10:05 and close it (tick in 10:06)
        builder.on_tick(_make_tick("95000", "0.01", ts=_ts(10, 5, 30), trade_id=1))
        builder.on_tick(_make_tick("95100", "0.01", ts=_ts(10, 6, 1), trade_id=2))

        assert len(closed_1m) == 1   # 1m bar for 10:05 closed
        assert len(closed_15m) == 0  # 15m bar still open (in 10:00–10:15 period)

        # Advance to 10:16 to close the 15m bar
        builder.on_tick(_make_tick("95200", "0.01", ts=_ts(10, 16, 1), trade_id=3))
        assert len(closed_15m) == 1

    def test_flush_closes_open_bars(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        closed_bars = []
        builder.subscribe_closed(closed_bars.append)
        builder.on_tick(_make_tick("95000", "0.01", ts=_ts(10, 5, 30), trade_id=1))
        flushed = builder.flush()
        assert len(flushed) == 1
        assert flushed[0].interval == BarInterval.ONE_MIN

    def test_flush_empty_is_safe(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        flushed = builder.flush()
        assert flushed == []

    def test_tick_for_different_symbol_ignored(self):
        builder = RealtimeBarBuilder(symbol="BTCUSDT")
        other_tick = _make_tick(symbol="ETHUSDT", ts=_ts(10, 5, 30))
        builder.on_tick(other_tick)
        assert builder.ticks_processed == 0

    def test_subscribe_and_unsubscribe(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        cb = MagicMock()
        builder.subscribe_closed(cb)
        builder.on_tick(_make_tick(ts=_ts(10, 5, 30), trade_id=1))
        builder.on_tick(_make_tick(ts=_ts(10, 6, 1), trade_id=2))
        cb.assert_called_once()
        builder.unsubscribe_closed(cb)
        builder.on_tick(_make_tick(ts=_ts(10, 7, 1), trade_id=3))
        # Still only called once
        assert cb.call_count == 1

    def test_repr(self):
        builder = RealtimeBarBuilder()
        r = repr(builder)
        assert "BTCUSDT" in r

    def test_volume_quote_accumulates(self):
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        # price=100, qty=0.01 → notional=1.0
        # price=200, qty=0.02 → notional=4.0
        builder.on_tick(_make_tick("100", "0.01", ts=_ts(10, 5, 10), trade_id=1))
        builder.on_tick(_make_tick("200", "0.02", ts=_ts(10, 5, 20), trade_id=2))
        bar = builder.get_open_bar(BarInterval.ONE_MIN)
        assert bar.volume_quote == Decimal("1.00") + Decimal("4.00")
