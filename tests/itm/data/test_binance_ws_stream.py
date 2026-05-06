"""
Unit tests for BinanceWebSocketStream.

Tests cover:
- TradeTick construction and properties
- StreamState transitions
- Message parsing (_handle_message)
- Subscriber registration / removal
- Dispatch mechanics
- Re-entrant edge cases

These tests run fully offline (no network, no WebSocket connection).
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/ is on path (mirrors conftest.py in tests/itm/)
import sys
import os

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.binance_ws_stream import (
    BinanceWebSocketStream,
    StreamState,
    TradeTick,
)


# ---------------------------------------------------------------------------
# TradeTick tests
# ---------------------------------------------------------------------------


class TestTradeTick:
    """Tests for the TradeTick value object."""

    def _make_tick(self, **overrides):
        defaults = dict(
            symbol="BTCUSDT",
            price=Decimal("95000.10"),
            quantity=Decimal("0.05"),
            is_buyer_maker=False,
            trade_id=99999,
            timestamp=datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc),
        )
        defaults.update(overrides)
        return TradeTick(**defaults)

    def test_side_buy_when_not_buyer_maker(self):
        tick = self._make_tick(is_buyer_maker=False)
        assert tick.side == "buy"

    def test_side_sell_when_buyer_maker(self):
        tick = self._make_tick(is_buyer_maker=True)
        assert tick.side == "sell"

    def test_notional(self):
        tick = self._make_tick(price=Decimal("100.00"), quantity=Decimal("2.0"))
        assert tick.notional == Decimal("200.00")

    def test_frozen(self):
        tick = self._make_tick()
        with pytest.raises((AttributeError, TypeError)):
            tick.symbol = "OTHER"

    def test_received_at_defaults_to_utc(self):
        tick = self._make_tick()
        assert tick.received_at.tzinfo is not None
        assert tick.received_at.tzinfo == timezone.utc or \
               tick.received_at.utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# BinanceWebSocketStream init and subscription tests
# ---------------------------------------------------------------------------


class TestStreamSubscription:
    """Tests for subscriber management."""

    def test_subscribe_adds_callback(self):
        stream = BinanceWebSocketStream()
        cb = MagicMock()
        stream.subscribe(cb)
        assert cb in stream._subscribers

    def test_subscribe_idempotent(self):
        stream = BinanceWebSocketStream()
        cb = MagicMock()
        stream.subscribe(cb)
        stream.subscribe(cb)
        assert stream._subscribers.count(cb) == 1

    def test_unsubscribe_removes_callback(self):
        stream = BinanceWebSocketStream()
        cb = MagicMock()
        stream.subscribe(cb)
        stream.unsubscribe(cb)
        assert cb not in stream._subscribers

    def test_unsubscribe_nonexistent_is_safe(self):
        stream = BinanceWebSocketStream()
        cb = MagicMock()
        stream.unsubscribe(cb)  # Should not raise

    def test_multiple_subscribers(self):
        stream = BinanceWebSocketStream()
        callbacks = [MagicMock() for _ in range(5)]
        for cb in callbacks:
            stream.subscribe(cb)
        assert len(stream._subscribers) == 5


# ---------------------------------------------------------------------------
# Message parsing tests
# ---------------------------------------------------------------------------


class TestHandleMessage:
    """Tests for the _handle_message method (offline tick parsing)."""

    def _make_stream(self):
        return BinanceWebSocketStream(symbol="BTCUSDT")

    def _make_agg_trade_msg(self, **overrides):
        msg = {
            "e": "aggTrade",
            "E": 1746518400000,  # event time ms
            "s": "BTCUSDT",
            "a": 12345678,
            "p": "95000.10",
            "q": "0.050",
            "f": 12345670,
            "l": 12345678,
            "T": 1746518399950,
            "m": False,
        }
        msg.update(overrides)
        return json.dumps(msg)

    def test_valid_tick_dispatched(self):
        stream = self._make_stream()
        received = []
        stream.subscribe(received.append)
        stream._handle_message(self._make_agg_trade_msg())
        assert len(received) == 1

    def test_tick_fields_correct(self):
        stream = self._make_stream()
        received = []
        stream.subscribe(received.append)
        stream._handle_message(
            self._make_agg_trade_msg(p="94500.50", q="0.123", m=True, a=99)
        )
        tick = received[0]
        assert tick.symbol == "BTCUSDT"
        assert tick.price == Decimal("94500.50")
        assert tick.quantity == Decimal("0.123")
        assert tick.is_buyer_maker is True
        assert tick.trade_id == 99
        assert tick.side == "sell"

    def test_non_agg_trade_event_ignored(self):
        stream = self._make_stream()
        received = []
        stream.subscribe(received.append)
        msg = json.dumps({"e": "bookTicker", "s": "BTCUSDT", "b": "94000", "a": "94001"})
        stream._handle_message(msg)
        assert len(received) == 0

    def test_invalid_json_does_not_raise(self):
        stream = self._make_stream()
        stream._handle_message("NOT JSON {{{{")  # Should log and not raise

    def test_missing_field_does_not_raise(self):
        stream = self._make_stream()
        msg = json.dumps({"e": "aggTrade", "s": "BTCUSDT"})  # missing p, q, etc.
        stream._handle_message(msg)  # Should log error and not raise

    def test_tick_count_increments(self):
        stream = self._make_stream()
        assert stream.ticks_received == 0
        stream._handle_message(self._make_agg_trade_msg())
        assert stream.ticks_received == 1

    def test_subscriber_exception_does_not_stop_stream(self):
        stream = self._make_stream()
        bad_cb = MagicMock(side_effect=RuntimeError("oops"))
        good_cb = MagicMock()
        stream.subscribe(bad_cb)
        stream.subscribe(good_cb)
        stream._handle_message(self._make_agg_trade_msg())
        good_cb.assert_called_once()


# ---------------------------------------------------------------------------
# State machine tests
# ---------------------------------------------------------------------------


class TestStreamState:
    """Tests for StreamState initial values and repr."""

    def test_initial_state_is_idle(self):
        stream = BinanceWebSocketStream()
        assert stream.state == StreamState.IDLE

    def test_repr_includes_state(self):
        stream = BinanceWebSocketStream()
        r = repr(stream)
        assert "IDLE" in r
        assert "BTCUSDT" in r

    def test_stop_from_idle_is_safe(self):
        stream = BinanceWebSocketStream()
        stream.stop()  # should not raise

    def test_double_start_warning(self):
        stream = BinanceWebSocketStream()
        # Manually set state to CONNECTING
        stream._state = StreamState.CONNECTING
        stream.start()  # Should log warning and not start a second thread
        assert stream._thread is None  # thread was never started
