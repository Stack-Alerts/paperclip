"""
Integration tests for Section B — Data Management & Synchronization Layer.

These tests exercise the full pipeline:
  BinanceWebSocketStream → RealtimeBarBuilder → DataFreshnessGate → NTDataAdapter

All tests run offline (no live network connections).  WebSocket messages are
injected directly via _handle_message().

Integration paths tested:
1. Tick → Builder → Gate → Adapter (full pipeline)
2. Gap detection on historical bar sequence
3. Freshness gate blocks stale downstream processing via guard()
4. NT bar and tick conversion round-trips
5. Multi-interval bar construction (1m and 15m from same tick stream)
"""

from __future__ import annotations

import sys
import os
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_SRC = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.itm.data.binance_ws_stream import BinanceWebSocketStream, StreamState, TradeTick
from src.itm.data.data_freshness_gate import DataFreshnessGate, FreshnessStatus, StaleDataError
from src.itm.data.gap_detector import GapDetector, GapBackfiller, BarGap
from src.itm.data.nt_data_adapter import NTDataAdapter, NTBarEvent, NTTickEvent
from src.itm.data.realtime_bar_builder import BarInterval, OHLCVBar, RealtimeBarBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2026, 5, 6, h, m, s, tzinfo=timezone.utc)


def _inject_tick(
    stream: BinanceWebSocketStream,
    price: str,
    qty: str,
    ts: datetime,
    trade_id: int,
    is_buyer_maker: bool = False,
) -> None:
    """Inject a synthetic aggTrade message directly into the stream."""
    msg = {
        "e": "aggTrade",
        "E": int(ts.timestamp() * 1000),
        "s": "BTCUSDT",
        "a": trade_id,
        "p": price,
        "q": qty,
        "f": trade_id,
        "l": trade_id,
        "T": int(ts.timestamp() * 1000),
        "m": is_buyer_maker,
    }
    stream._handle_message(json.dumps(msg))


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
        volume_quote=Decimal("95025"),
        trade_count=10,
    )


# ---------------------------------------------------------------------------
# Integration Test 1: Full pipeline — tick → builder → gate → adapter
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Verify the complete stream → builder → gate → adapter pipeline."""

    def _setup_pipeline(self, max_age_seconds: int = 60, now: datetime = None):
        now = now or datetime(2026, 5, 6, 10, 6, 0, tzinfo=timezone.utc)
        stream = BinanceWebSocketStream()
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN])
        gate = DataFreshnessGate(max_age_seconds=max_age_seconds, clock=lambda: now)
        adapter = NTDataAdapter(bar_intervals=[BarInterval.ONE_MIN])
        adapter.connect(stream, builder, gate)
        return stream, builder, gate, adapter, now

    def test_tick_received_and_gate_records_it(self):
        stream, builder, gate, adapter, now = self._setup_pipeline()
        ts = now - timedelta(seconds=5)

        _inject_tick(stream, "95000.0", "0.050", ts, trade_id=1)

        assert gate.tick_status() == FreshnessStatus.FRESH

    def test_tick_dispatched_as_nt_tick_event(self):
        stream, builder, gate, adapter, now = self._setup_pipeline()
        events = []
        adapter.subscribe_ticks(events.append)
        ts = now - timedelta(seconds=5)

        _inject_tick(stream, "95000.0", "0.050", ts, trade_id=1)

        assert len(events) == 1
        assert isinstance(events[0], NTTickEvent)
        from nautilus_trader.model.objects import Price
        assert events[0].nt_tick.price == Price.from_str("95000.0")

    def test_bar_closes_and_dispatched_as_nt_bar_event(self):
        stream, builder, gate, adapter, now = self._setup_pipeline()
        bar_events = []
        adapter.subscribe_bars(bar_events.append)

        # Tick in minute 10:05
        _inject_tick(stream, "95000.0", "0.050", _ts(10, 5, 10), trade_id=1)
        _inject_tick(stream, "95200.0", "0.030", _ts(10, 5, 40), trade_id=2)

        assert len(bar_events) == 0  # bar not yet closed

        # Tick in minute 10:06 — closes 10:05 bar
        _inject_tick(stream, "95100.0", "0.010", _ts(10, 6, 1), trade_id=3)

        assert len(bar_events) == 1
        event = bar_events[0]
        assert isinstance(event, NTBarEvent)
        assert event.itm_bar.timestamp == _ts(10, 5)
        assert event.itm_bar.open == Decimal("95000.0")
        assert event.itm_bar.high == Decimal("95200.0")

        from nautilus_trader.model.objects import Price
        assert event.nt_bar.open == Price.from_str("95000.0")
        assert "1-MINUTE" in str(event.nt_bar.bar_type)

    def test_stale_gate_blocks_downstream(self):
        """Gate blocks processing after max_age_seconds elapses with no new ticks."""
        # Clock is 2 minutes ahead of the last tick
        now = _ts(10, 7, 0)
        stream, builder, gate, adapter, _ = self._setup_pipeline(
            max_age_seconds=60, now=now
        )

        # Record an old tick (2 minutes old — stale)
        gate.record_tick(TradeTick(
            symbol="BTCUSDT",
            price=Decimal("95000"),
            quantity=Decimal("0.01"),
            is_buyer_maker=False,
            trade_id=99,
            timestamp=_ts(10, 5, 0),  # 2 min old
        ))

        assert gate.tick_status() == FreshnessStatus.STALE
        with pytest.raises(StaleDataError):
            gate.check_tick_freshness()

    def test_adapter_counter_tracks_both_bars_and_ticks(self):
        stream, builder, gate, adapter, now = self._setup_pipeline()

        # 3 ticks total
        for i in range(3):
            _inject_tick(stream, "95000.0", "0.010", _ts(10, 5, 10 + i), trade_id=i)
        assert adapter.ticks_converted == 3

        # Close a bar
        _inject_tick(stream, "95100.0", "0.010", _ts(10, 6, 1), trade_id=99)
        assert adapter.bars_converted == 1


# ---------------------------------------------------------------------------
# Integration Test 2: Multi-interval bar construction from the same tick stream
# ---------------------------------------------------------------------------


class TestMultiIntervalPipeline:
    def test_1m_and_15m_from_same_ticks(self):
        stream = BinanceWebSocketStream()
        builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN])
        adapter = NTDataAdapter(bar_intervals=[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN])
        adapter.connect(stream, builder)

        bars_1m = []
        bars_15m = []
        adapter.subscribe_bars(
            lambda e: bars_1m.append(e) if e.itm_bar.interval == BarInterval.ONE_MIN
            else bars_15m.append(e)
        )

        # Inject ticks spanning 16 minutes: 10:00 to 10:16
        # Each minute gets a tick; minute boundary closes 1m bars
        for minute in range(17):
            _inject_tick(stream, "95000.0", "0.010", _ts(10, minute, 1), trade_id=minute)

        # 16 1m bars should have been closed (10:00–10:15)
        assert len(bars_1m) == 16

        # 1 15m bar should have been closed (10:00–10:14 closed when 10:15 tick arrives)
        assert len(bars_15m) == 1
        assert "15-MINUTE" in str(bars_15m[0].nt_bar.bar_type)


# ---------------------------------------------------------------------------
# Integration Test 3: Gap detection on a realistic bar series
# ---------------------------------------------------------------------------


class TestGapDetectionIntegration:
    def test_gap_detected_after_reconnect_scenario(self):
        """Simulate a stream reconnect that creates a gap in the bar series."""
        # Simulate bars from a connected stream, then a reconnect gap
        pre_disconnect = [_make_bar(_ts(10, i)) for i in range(10)]   # 10:00–10:09
        post_reconnect = [_make_bar(_ts(10, 15))]                       # skip 10:10–10:14

        all_bars = pre_disconnect + post_reconnect
        detector = GapDetector(BarInterval.ONE_MIN)
        gaps = detector.find_gaps(all_bars)

        assert len(gaps) == 1
        assert gaps[0].missing_count == 5
        assert gaps[0].gap_start == _ts(10, 10)
        assert gaps[0].gap_end == _ts(10, 14)

    def test_gap_backfiller_called_for_detected_gaps(self):
        """GapBackfiller.fill() is invoked for each detected gap."""
        detector = GapDetector(BarInterval.ONE_MIN)
        filler = GapBackfiller()

        bars = [_make_bar(_ts(10, 0)), _make_bar(_ts(10, 5))]  # 4-bar gap
        gaps = detector.find_gaps(bars)
        assert len(gaps) == 1

        with patch.object(filler, "_fetch_binance_rest", return_value=[
            _make_bar(_ts(10, i)) for i in range(1, 5)
        ]):
            result = filler.fill(gaps[0])

        assert result.success is True
        assert result.bars_fetched == 4


# ---------------------------------------------------------------------------
# Integration Test 4: Section B __init__ exports are accessible
# ---------------------------------------------------------------------------


class TestSectionBPackageExports:
    def test_all_exports_importable(self):
        from src.itm.data import (
            BinanceWebSocketStream,
            DataFreshnessGate,
            FreshnessStatus,
            GapBackfillResult,
            GapDetector,
            NTBarEvent,
            NTDataAdapter,
            NTTickEvent,
            OHLCVBar,
            RealtimeBarBuilder,
            BarInterval,
            BarGap,
            StaleDataError,
            StreamState,
            TradeTick,
        )
        # Verify they're the right types
        assert BinanceWebSocketStream is not None
        assert RealtimeBarBuilder is not None
        assert GapDetector is not None
        assert DataFreshnessGate is not None
        assert NTDataAdapter is not None

    def test_itm_package_version_updated(self):
        import src.itm as itm
        assert itm.__version__ == "0.2.0"
