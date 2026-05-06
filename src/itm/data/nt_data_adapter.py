"""
ITM Section B — NautilusTrader Data Feed Adapter
==================================================
Bridges the live ITM data layer (BinanceWebSocketStream + RealtimeBarBuilder)
into NautilusTrader-compatible data types so NT Actors and Strategies can
consume real-time bars and ticks directly.

Design
------
* ``NTDataAdapter`` wires itself into the ``BinanceWebSocketStream`` and
  ``RealtimeBarBuilder`` callbacks and converts each event to the
  corresponding NT type.
* NT-typed events are delivered to registered subscribers via
  :class:`NTBarEvent` and :class:`NTTickEvent` wrapper dataclasses.
* The adapter is stateless from NT's perspective — it does NOT push data into
  a live NT node's DataEngine (that is the role of the NautilusTrader Actor
  in Section J).  Instead it acts as a *conversion + fan-out* layer that
  produces NT-typed objects for any consumer that needs them.
* When running inside an NT backtest or live node, consumers can register and
  receive the same objects without modifying the strategy code.

NautilusTrader type mapping
---------------------------
+-----------------------+----------------------------+
| ITM type              | NT type                    |
+=======================+============================+
| ``TradeTick``         | ``NTTradeTick``            |
| ``OHLCVBar`` (1m)     | ``Bar`` (MINUTE, step=1)   |
| ``OHLCVBar`` (15m)    | ``Bar`` (MINUTE, step=15)  |
| ``OHLCVBar`` (5m)     | ``Bar`` (MINUTE, step=5)   |
| ``OHLCVBar`` (1h)     | ``Bar`` (HOUR, step=1)     |
+-----------------------+----------------------------+

All NautilusTrader type construction follows the mandatory type system rules:
* Prices use ``Price.from_str()``
* Quantities use ``Quantity.from_str()``
* Timestamps use ``dt_to_unix_nanos()``
* No raw floats or string literals for enum values

Usage
-----
::

    stream = BinanceWebSocketStream()
    builder = RealtimeBarBuilder()
    gate = DataFreshnessGate()

    adapter = NTDataAdapter(
        symbol="BTCUSDT",
        venue="BINANCE",
        bar_intervals=[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN],
    )
    adapter.connect(stream, builder, gate)

    adapter.subscribe_bars(my_strategy.on_bar)
    adapter.subscribe_ticks(my_strategy.on_tick)

    stream.start()
    ...
    stream.stop()
    adapter.disconnect()

"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Tuple

from .binance_ws_stream import BinanceWebSocketStream
from .binance_ws_stream import TradeTick as ITMTradeTick
from .data_freshness_gate import DataFreshnessGate
from .realtime_bar_builder import BarInterval, OHLCVBar, RealtimeBarBuilder

logger = logging.getLogger(__name__)

# Lazy NT imports — keep this module importable without NT installed in test env.
# These are resolved at call time, not at import time.
def _nt_imports() -> dict:
    from nautilus_trader.model.data import (
        Bar,
        BarSpecification,
        BarType,
        TradeTick as NTTradeTick,
    )
    from nautilus_trader.model.enums import AggressorSide, BarAggregation, PriceType
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, TradeId, Venue
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.core.datetime import dt_to_unix_nanos

    return {
        "Bar": Bar,
        "BarSpecification": BarSpecification,
        "BarType": BarType,
        "NTTradeTick": NTTradeTick,
        "AggressorSide": AggressorSide,
        "BarAggregation": BarAggregation,
        "PriceType": PriceType,
        "InstrumentId": InstrumentId,
        "Symbol": Symbol,
        "TradeId": TradeId,
        "Venue": Venue,
        "Price": Price,
        "Quantity": Quantity,
        "dt_to_unix_nanos": dt_to_unix_nanos,
    }


# ---------------------------------------------------------------------------
# NT event wrappers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NTBarEvent:
    """Wraps a NautilusTrader ``Bar`` with its source :class:`OHLCVBar`.

    Attributes
    ----------
    nt_bar:    The NautilusTrader ``Bar`` object (NT-typed, ready for strategies).
    itm_bar:   The original :class:`OHLCVBar` from the realtime builder.
    received_at: UTC timestamp of when this event was created.
    """

    nt_bar: object          # nautilus_trader.model.data.Bar (typed at runtime)
    itm_bar: OHLCVBar
    received_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class NTTickEvent:
    """Wraps a NautilusTrader ``TradeTick`` with its source :class:`~itm.data.binance_ws_stream.TradeTick`.

    Attributes
    ----------
    nt_tick:   The NautilusTrader ``TradeTick`` object.
    itm_tick:  The original :class:`TradeTick` from the WebSocket stream.
    received_at: UTC timestamp of when this event was created.
    """

    nt_tick: object         # nautilus_trader.model.data.TradeTick
    itm_tick: ITMTradeTick
    received_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Interval → NT BarAggregation mapping
# ---------------------------------------------------------------------------

# Resolved at call time to avoid NT import at module load
_INTERVAL_TO_NT_SPEC: Dict[BarInterval, Tuple[int, str]] = {
    BarInterval.ONE_MIN: (1, "MINUTE"),
    BarInterval.FIVE_MIN: (5, "MINUTE"),
    BarInterval.FIFTEEN_MIN: (15, "MINUTE"),
    BarInterval.ONE_HOUR: (1, "HOUR"),
}


# ---------------------------------------------------------------------------
# NTDataAdapter
# ---------------------------------------------------------------------------


class NTDataAdapter:
    """Converts ITM data events to NautilusTrader-typed objects and fans them out.

    Parameters
    ----------
    symbol:         Binance symbol string (default: ``"BTCUSDT"``).
    venue:          NT venue string (default: ``"BINANCE"``).
    bar_intervals:  Intervals to bridge (default: 1m and 15m).
    price_precision: Decimal places for NT Price objects (default: 1 for BTC).
    qty_precision:  Decimal places for NT Quantity objects (default: 3).
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        venue: str = "BINANCE",
        bar_intervals: Optional[List[BarInterval]] = None,
        price_precision: int = 1,
        qty_precision: int = 3,
    ) -> None:
        self.symbol = symbol.upper()
        self.venue = venue.upper()
        self.bar_intervals = bar_intervals or [
            BarInterval.ONE_MIN,
            BarInterval.FIFTEEN_MIN,
        ]
        self.price_precision = price_precision
        self.qty_precision = qty_precision

        # Subscriber lists (thread-safe access via _lock)
        self._bar_callbacks: List[Callable[[NTBarEvent], None]] = []
        self._tick_callbacks: List[Callable[[NTTickEvent], None]] = []
        self._lock = threading.Lock()

        # Connected components (set in connect())
        self._stream: Optional[BinanceWebSocketStream] = None
        self._builder: Optional[RealtimeBarBuilder] = None
        self._gate: Optional[DataFreshnessGate] = None

        # Statistics
        self.bars_converted: int = 0
        self.ticks_converted: int = 0

        logger.info(
            "NTDataAdapter initialised: symbol=%s venue=%s intervals=%s",
            self.symbol,
            self.venue,
            [iv.label for iv in self.bar_intervals],
        )

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    def subscribe_bars(self, callback: Callable[[NTBarEvent], None]) -> None:
        """Register a callback that receives :class:`NTBarEvent` on every closed bar."""
        with self._lock:
            if callback not in self._bar_callbacks:
                self._bar_callbacks.append(callback)

    def unsubscribe_bars(self, callback: Callable[[NTBarEvent], None]) -> None:
        """Remove a bar callback."""
        with self._lock:
            try:
                self._bar_callbacks.remove(callback)
            except ValueError:
                pass

    def subscribe_ticks(self, callback: Callable[[NTTickEvent], None]) -> None:
        """Register a callback that receives :class:`NTTickEvent` on every tick."""
        with self._lock:
            if callback not in self._tick_callbacks:
                self._tick_callbacks.append(callback)

    def unsubscribe_ticks(self, callback: Callable[[NTTickEvent], None]) -> None:
        """Remove a tick callback."""
        with self._lock:
            try:
                self._tick_callbacks.remove(callback)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(
        self,
        stream: BinanceWebSocketStream,
        builder: RealtimeBarBuilder,
        gate: Optional[DataFreshnessGate] = None,
    ) -> None:
        """Wire the adapter into the stream, builder, and optional gate.

        Wiring diagram::

            stream ──► builder.on_tick         (stream → bar assembly)
            stream ──► adapter._on_itm_tick    (stream → NT tick conversion)
            stream ──► gate.record_tick        (stream → freshness tracking)
            builder ──► adapter._on_itm_bar   (bar assembly → NT bar conversion)
            builder ──► gate.record_bar        (bar assembly → freshness tracking)

        Must be called before starting the stream.
        """
        self._stream = stream
        self._builder = builder
        self._gate = gate

        # Wire stream → bar builder (this is the core data flow)
        stream.subscribe(builder.on_tick)
        # Wire stream → adapter tick conversion
        stream.subscribe(self._on_itm_tick)
        # Wire builder → adapter bar conversion
        builder.subscribe_closed(self._on_itm_bar)

        if gate is not None:
            stream.subscribe(gate.record_tick)
            builder.subscribe_closed(gate.record_bar)

        logger.info("NTDataAdapter connected to stream and builder")

    def disconnect(self) -> None:
        """Unregister callbacks from stream and builder."""
        if self._stream is not None:
            if self._builder is not None:
                self._stream.unsubscribe(self._builder.on_tick)
            self._stream.unsubscribe(self._on_itm_tick)
        if self._builder is not None:
            self._builder.unsubscribe_closed(self._on_itm_bar)
        if self._gate is not None and self._stream is not None:
            self._stream.unsubscribe(self._gate.record_tick)
        if self._gate is not None and self._builder is not None:
            self._builder.unsubscribe_closed(self._gate.record_bar)
        logger.info("NTDataAdapter disconnected")

    # ------------------------------------------------------------------
    # Internal conversion: TradeTick
    # ------------------------------------------------------------------

    def _on_itm_tick(self, tick: ITMTradeTick) -> None:
        """Convert ITM TradeTick → NT TradeTick and dispatch."""
        try:
            nt_tick = self._to_nt_tick(tick)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to convert ITM tick to NT tick: %s", tick)
            return

        event = NTTickEvent(nt_tick=nt_tick, itm_tick=tick)
        self.ticks_converted += 1
        self._dispatch_tick(event)

    def _to_nt_tick(self, tick: ITMTradeTick) -> object:
        """Convert one :class:`~itm.data.binance_ws_stream.TradeTick` to NT type."""
        nt = _nt_imports()
        instrument_id = nt["InstrumentId"](
            nt["Symbol"](self.symbol), nt["Venue"](self.venue)
        )
        ts_ns = nt["dt_to_unix_nanos"](tick.timestamp)
        price_str = f"{tick.price:.{self.price_precision}f}"
        qty_str = f"{tick.quantity:.{self.qty_precision}f}"

        # Aggressor side: seller is taker when is_buyer_maker=True
        aggressor = (
            nt["AggressorSide"].SELLER
            if tick.is_buyer_maker
            else nt["AggressorSide"].BUYER
        )

        return nt["NTTradeTick"](
            instrument_id=instrument_id,
            price=nt["Price"].from_str(price_str),
            size=nt["Quantity"].from_str(qty_str),
            aggressor_side=aggressor,
            trade_id=nt["TradeId"](str(tick.trade_id)),
            ts_event=ts_ns,
            ts_init=int(tick.received_at.timestamp() * 1_000_000_000),
        )

    # ------------------------------------------------------------------
    # Internal conversion: OHLCV Bar
    # ------------------------------------------------------------------

    def _on_itm_bar(self, bar: OHLCVBar) -> None:
        """Convert ITM OHLCVBar → NT Bar and dispatch."""
        if bar.interval not in self.bar_intervals:
            return  # not a tracked interval
        try:
            nt_bar = self._to_nt_bar(bar)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to convert ITM bar to NT bar: %s", bar)
            return

        event = NTBarEvent(nt_bar=nt_bar, itm_bar=bar)
        self.bars_converted += 1
        self._dispatch_bar(event)

    def _to_nt_bar(self, bar: OHLCVBar) -> object:
        """Convert one :class:`OHLCVBar` to a NautilusTrader ``Bar``."""
        nt = _nt_imports()
        instrument_id = nt["InstrumentId"](
            nt["Symbol"](self.symbol), nt["Venue"](self.venue)
        )
        step, agg_name = _INTERVAL_TO_NT_SPEC[bar.interval]
        aggregation = getattr(nt["BarAggregation"], agg_name)

        spec = nt["BarSpecification"](step, aggregation, nt["PriceType"].LAST)
        bar_type = nt["BarType"](instrument_id, spec)

        ts_event_ns = nt["dt_to_unix_nanos"](bar.timestamp)
        ts_init_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

        def _p(val: Decimal) -> object:
            return nt["Price"].from_str(f"{val:.{self.price_precision}f}")

        def _q(val: Decimal) -> object:
            return nt["Quantity"].from_str(f"{val:.{self.qty_precision}f}")

        return nt["Bar"](
            bar_type=bar_type,
            open=_p(bar.open),
            high=_p(bar.high),
            low=_p(bar.low),
            close=_p(bar.close),
            volume=_q(bar.volume),
            ts_event=ts_event_ns,
            ts_init=ts_init_ns,
        )

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    def _dispatch_bar(self, event: NTBarEvent) -> None:
        with self._lock:
            callbacks = list(self._bar_callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Bar callback %s raised for %s", cb, event)

    def _dispatch_tick(self, event: NTTickEvent) -> None:
        with self._lock:
            callbacks = list(self._tick_callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception:  # noqa: BLE001
                logger.exception("Tick callback %s raised for %s", cb, event)

    # ------------------------------------------------------------------
    # Conversion utilities (public, for use by Actors / tests)
    # ------------------------------------------------------------------

    def ohlcv_to_nt_bar(self, bar: OHLCVBar) -> object:
        """Public conversion helper: OHLCVBar → NT Bar.

        Useful for backfill / warmup: convert historical bars fetched by
        ``GapBackfiller`` into NT-typed objects for strategy warmup.
        """
        return self._to_nt_bar(bar)

    def itm_tick_to_nt_tick(self, tick: ITMTradeTick) -> object:
        """Public conversion helper: ITM TradeTick → NT TradeTick."""
        return self._to_nt_tick(tick)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"NTDataAdapter("
            f"symbol={self.symbol!r}, "
            f"venue={self.venue!r}, "
            f"ticks_converted={self.ticks_converted}, "
            f"bars_converted={self.bars_converted})"
        )
