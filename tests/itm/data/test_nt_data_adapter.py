"""
Unit tests for NTDataAdapter.

Tests cover:
- NTBarEvent and NTTickEvent construction
- NTDataAdapter initialization
- connect() / disconnect() wiring
- _to_nt_tick() — correct NT TradeTick fields
- _to_nt_bar() — correct NT Bar fields for 1m and 15m
- Subscriber registration and dispatch for bars and ticks
- ohlcv_to_nt_bar() and itm_tick_to_nt_tick() public helpers
- Conversion counter increments
- Filtered intervals (bars not in interval list are ignored)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.binance_ws_stream import TradeTick as ITMTradeTick, BinanceWebSocketStream, StreamState
from src.itm.data.data_freshness_gate import DataFreshnessGate
from src.itm.data.nt_data_adapter import NTBarEvent, NTDataAdapter, NTTickEvent
from src.itm.data.realtime_bar_builder import BarInterval, OHLCVBar, RealtimeBarBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 5, 6, h, m, s, tzinfo=timezone.utc)


def _make_itm_tick(
    price: str = "95000.0",
    qty: str = "0.050",
    ts: datetime = None,
    is_buyer_maker: bool = False,
    trade_id: int = 12345,
) -> ITMTradeTick:
    return ITMTradeTick(
        symbol="BTCUSDT",
        price=Decimal(price),
        quantity=Decimal(qty),
        is_buyer_maker=is_buyer_maker,
        trade_id=trade_id,
        timestamp=ts or _ts(10, 5, 30),
    )


def _make_itm_bar(interval: BarInterval = BarInterval.ONE_MIN, ts: datetime = None) -> OHLCVBar:
    return OHLCVBar(
        symbol="BTCUSDT",
        interval=interval,
        timestamp=ts or _ts(10, 5),
        open=Decimal("95000.0"),
        high=Decimal("95200.0"),
        low=Decimal("94900.0"),
        close=Decimal("95100.0"),
        volume=Decimal("1.500"),
        volume_quote=Decimal("142650.0"),
        trade_count=30,
    )


# ---------------------------------------------------------------------------
# NTBarEvent / NTTickEvent tests
# ---------------------------------------------------------------------------


class TestNTEventWrappers:
    def test_nt_bar_event_construction(self):
        itm_bar = _make_itm_bar()
        mock_nt_bar = MagicMock()
        event = NTBarEvent(nt_bar=mock_nt_bar, itm_bar=itm_bar)
        assert event.itm_bar is itm_bar
        assert event.nt_bar is mock_nt_bar
        assert event.received_at.tzinfo is not None

    def test_nt_tick_event_construction(self):
        itm_tick = _make_itm_tick()
        mock_nt_tick = MagicMock()
        event = NTTickEvent(nt_tick=mock_nt_tick, itm_tick=itm_tick)
        assert event.itm_tick is itm_tick
        assert event.nt_tick is mock_nt_tick


# ---------------------------------------------------------------------------
# NTDataAdapter init tests
# ---------------------------------------------------------------------------


class TestAdapterInit:
    def test_defaults(self):
        adapter = NTDataAdapter()
        assert adapter.symbol == "BTCUSDT"
        assert adapter.venue == "BINANCE"
        assert BarInterval.ONE_MIN in adapter.bar_intervals
        assert BarInterval.FIFTEEN_MIN in adapter.bar_intervals

    def test_symbol_uppercased(self):
        adapter = NTDataAdapter(symbol="btcusdt")
        assert adapter.symbol == "BTCUSDT"

    def test_initial_counters_zero(self):
        adapter = NTDataAdapter()
        assert adapter.ticks_converted == 0
        assert adapter.bars_converted == 0

    def test_repr(self):
        adapter = NTDataAdapter()
        r = repr(adapter)
        assert "BTCUSDT" in r
        assert "BINANCE" in r


# ---------------------------------------------------------------------------
# Conversion tests: _to_nt_tick
# ---------------------------------------------------------------------------


class TestToNTTick:
    def test_converts_buy_tick(self):
        adapter = NTDataAdapter()
        from nautilus_trader.model.enums import AggressorSide
        tick = _make_itm_tick(price="95000.1", qty="0.050", is_buyer_maker=False)
        nt_tick = adapter._to_nt_tick(tick)
        # NT TradeTick should have BUYER aggressor (taker was buyer)
        assert nt_tick.aggressor_side == AggressorSide.BUYER

    def test_converts_sell_tick(self):
        adapter = NTDataAdapter()
        from nautilus_trader.model.enums import AggressorSide
        tick = _make_itm_tick(is_buyer_maker=True)
        nt_tick = adapter._to_nt_tick(tick)
        assert nt_tick.aggressor_side == AggressorSide.SELLER

    def test_instrument_id_correct(self):
        adapter = NTDataAdapter(symbol="BTCUSDT", venue="BINANCE")
        tick = _make_itm_tick()
        nt_tick = adapter._to_nt_tick(tick)
        assert str(nt_tick.instrument_id) == "BTCUSDT.BINANCE"

    def test_trade_id_matches(self):
        adapter = NTDataAdapter()
        tick = _make_itm_tick(trade_id=987654)
        nt_tick = adapter._to_nt_tick(tick)
        assert str(nt_tick.trade_id) == "987654"

    def test_price_precision(self):
        adapter = NTDataAdapter(price_precision=1)
        tick = _make_itm_tick(price="95000.12345")
        nt_tick = adapter._to_nt_tick(tick)
        # Price should be rounded to 1 decimal
        from nautilus_trader.model.objects import Price
        expected = Price.from_str("95000.1")
        assert nt_tick.price == expected

    def test_public_helper_matches_internal(self):
        adapter = NTDataAdapter()
        tick = _make_itm_tick()
        internal = adapter._to_nt_tick(tick)
        public = adapter.itm_tick_to_nt_tick(tick)
        assert str(internal.price) == str(public.price)


# ---------------------------------------------------------------------------
# Conversion tests: _to_nt_bar
# ---------------------------------------------------------------------------


class TestToNTBar:
    def test_converts_1m_bar(self):
        adapter = NTDataAdapter()
        bar = _make_itm_bar(BarInterval.ONE_MIN)
        nt_bar = adapter._to_nt_bar(bar)
        assert "1-MINUTE" in str(nt_bar.bar_type)

    def test_converts_15m_bar(self):
        adapter = NTDataAdapter()
        bar = _make_itm_bar(BarInterval.FIFTEEN_MIN)
        nt_bar = adapter._to_nt_bar(bar)
        assert "15-MINUTE" in str(nt_bar.bar_type)

    def test_bar_ohlcv_values(self):
        adapter = NTDataAdapter(price_precision=1, qty_precision=3)
        bar = _make_itm_bar()
        nt_bar = adapter._to_nt_bar(bar)
        from nautilus_trader.model.objects import Price, Quantity
        assert nt_bar.open == Price.from_str("95000.0")
        assert nt_bar.high == Price.from_str("95200.0")
        assert nt_bar.low == Price.from_str("94900.0")
        assert nt_bar.close == Price.from_str("95100.0")
        assert nt_bar.volume == Quantity.from_str("1.500")

    def test_instrument_id_in_bar_type(self):
        adapter = NTDataAdapter(symbol="BTCUSDT", venue="BINANCE")
        bar = _make_itm_bar()
        nt_bar = adapter._to_nt_bar(bar)
        assert "BTCUSDT.BINANCE" in str(nt_bar.bar_type)

    def test_public_helper_works(self):
        adapter = NTDataAdapter()
        bar = _make_itm_bar()
        nt_bar = adapter.ohlcv_to_nt_bar(bar)
        assert nt_bar is not None


# ---------------------------------------------------------------------------
# Dispatch and counter tests
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_bar_callback_invoked(self):
        adapter = NTDataAdapter()
        events = []
        adapter.subscribe_bars(events.append)
        bar = _make_itm_bar(BarInterval.ONE_MIN)
        adapter._on_itm_bar(bar)
        assert len(events) == 1
        assert isinstance(events[0], NTBarEvent)
        assert events[0].itm_bar is bar

    def test_tick_callback_invoked(self):
        adapter = NTDataAdapter()
        events = []
        adapter.subscribe_ticks(events.append)
        tick = _make_itm_tick()
        adapter._on_itm_tick(tick)
        assert len(events) == 1
        assert isinstance(events[0], NTTickEvent)

    def test_bar_counter_increments(self):
        adapter = NTDataAdapter()
        adapter._on_itm_bar(_make_itm_bar())
        assert adapter.bars_converted == 1

    def test_tick_counter_increments(self):
        adapter = NTDataAdapter()
        adapter._on_itm_tick(_make_itm_tick())
        assert adapter.ticks_converted == 1

    def test_untracked_interval_ignored(self):
        adapter = NTDataAdapter(bar_intervals=[BarInterval.ONE_MIN])
        events = []
        adapter.subscribe_bars(events.append)
        # 15m bar should NOT trigger callback
        bar = _make_itm_bar(BarInterval.FIFTEEN_MIN)
        adapter._on_itm_bar(bar)
        assert len(events) == 0
        assert adapter.bars_converted == 0

    def test_unsubscribe_bars(self):
        adapter = NTDataAdapter()
        cb = MagicMock()
        adapter.subscribe_bars(cb)
        adapter.unsubscribe_bars(cb)
        adapter._on_itm_bar(_make_itm_bar())
        cb.assert_not_called()

    def test_unsubscribe_ticks(self):
        adapter = NTDataAdapter()
        cb = MagicMock()
        adapter.subscribe_ticks(cb)
        adapter.unsubscribe_ticks(cb)
        adapter._on_itm_tick(_make_itm_tick())
        cb.assert_not_called()

    def test_callback_exception_does_not_stop_dispatch(self):
        adapter = NTDataAdapter()
        bad_cb = MagicMock(side_effect=RuntimeError("oops"))
        good_cb = MagicMock()
        adapter.subscribe_bars(bad_cb)
        adapter.subscribe_bars(good_cb)
        adapter._on_itm_bar(_make_itm_bar())
        good_cb.assert_called_once()


# ---------------------------------------------------------------------------
# connect() / disconnect() integration tests
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    def test_connect_registers_callbacks(self):
        adapter = NTDataAdapter()
        stream = BinanceWebSocketStream()
        builder = RealtimeBarBuilder()
        gate = DataFreshnessGate()

        adapter.connect(stream, builder, gate)

        # stream → builder wiring
        assert builder.on_tick in stream._subscribers
        # adapter should be in stream's subscriber list
        assert adapter._on_itm_tick in stream._subscribers
        assert adapter._on_itm_bar in builder._closed_callbacks
        # gate callbacks also wired
        assert gate.record_tick in stream._subscribers
        assert gate.record_bar in builder._closed_callbacks

    def test_disconnect_removes_callbacks(self):
        adapter = NTDataAdapter()
        stream = BinanceWebSocketStream()
        builder = RealtimeBarBuilder()
        gate = DataFreshnessGate()

        adapter.connect(stream, builder, gate)
        adapter.disconnect()

        assert adapter._on_itm_tick not in stream._subscribers
        assert adapter._on_itm_bar not in builder._closed_callbacks
        assert builder.on_tick not in stream._subscribers
