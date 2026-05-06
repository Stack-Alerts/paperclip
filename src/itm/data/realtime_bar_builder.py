"""
ITM Section B — Real-Time Bar Builder
======================================
Assembles time-based OHLCV bars from a live :class:`TradeTick` stream.

Design
------
* Supports configurable bar intervals (default: 1 m and 15 m).
* Each interval maintains its own independent bar state so that 1 m and 15 m
  bars are constructed in a single pass over the same tick stream.
* Bars are *closed* (finalised) when the first tick of a new period arrives or
  when :meth:`flush` is called explicitly.
* Closed-bar callbacks fire synchronously on the tick-delivery thread; keep
  them non-blocking.
* Thread-safe: a single ``threading.Lock`` guards mutable bar state.

Bar labelling
-------------
Bar timestamps represent the **bar open time** (left edge of the period),
aligned to UTC midnight boundaries.  E.g., the 15 m bar starting at 14:00 UTC
has ``timestamp = 2026-05-06 14:00:00 UTC``.

Usage
-----
::

    builder = RealtimeBarBuilder(intervals=[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN])
    builder.subscribe_closed(on_bar_closed)   # callable(OHLCVBar) → None
    stream.subscribe(builder.on_tick)         # wire into BinanceWebSocketStream
    ...
    open_bars = builder.flush()               # forcibly close all open bars

"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional

from .binance_ws_stream import TradeTick

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bar interval enum
# ---------------------------------------------------------------------------


class BarInterval(Enum):
    """Supported real-time bar aggregation intervals."""

    ONE_MIN = 60          # 1-minute bars
    FIFTEEN_MIN = 900     # 15-minute bars
    FIVE_MIN = 300        # 5-minute bars (optional, often useful)
    ONE_HOUR = 3600       # 1-hour bars

    @property
    def seconds(self) -> int:
        """Duration of one bar in seconds."""
        return self.value

    @property
    def label(self) -> str:
        """Human-readable label matching Binance REST interval strings."""
        _labels = {
            BarInterval.ONE_MIN: "1m",
            BarInterval.FIVE_MIN: "5m",
            BarInterval.FIFTEEN_MIN: "15m",
            BarInterval.ONE_HOUR: "1h",
        }
        return _labels[self]


# ---------------------------------------------------------------------------
# OHLCVBar
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OHLCVBar:
    """A completed (closed) OHLCV bar.

    All price / volume fields use :class:`~decimal.Decimal` for precision.

    Attributes
    ----------
    symbol:        Instrument symbol (e.g. "BTCUSDT")
    interval:      Bar interval (``BarInterval`` enum)
    timestamp:     Bar open time (UTC, left-edge aligned)
    open:          First trade price in the bar
    high:          Highest trade price in the bar
    low:           Lowest trade price in the bar
    close:         Last trade price in the bar
    volume:        Total base-currency (BTC) volume
    volume_quote:  Total quote-currency (USDT) volume
    trade_count:   Number of raw trades aggregated into this bar
    closed:        True — a bar object is always a *closed* bar
    """

    symbol: str
    interval: BarInterval
    timestamp: datetime  # bar open time (UTC)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    volume_quote: Decimal
    trade_count: int
    closed: bool = True

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(
                f"OHLCVBar: high ({self.high}) < low ({self.low}) — "
                f"symbol={self.symbol} timestamp={self.timestamp}"
            )
        if self.open > self.high or self.open < self.low:
            raise ValueError(
                f"OHLCVBar: open ({self.open}) outside [low, high] range — "
                f"symbol={self.symbol} timestamp={self.timestamp}"
            )
        if self.close > self.high or self.close < self.low:
            raise ValueError(
                f"OHLCVBar: close ({self.close}) outside [low, high] range — "
                f"symbol={self.symbol} timestamp={self.timestamp}"
            )
        if self.volume < Decimal("0"):
            raise ValueError("OHLCVBar: volume cannot be negative")
        if self.trade_count < 0:
            raise ValueError("OHLCVBar: trade_count cannot be negative")

    @property
    def bar_end(self) -> datetime:
        """UTC timestamp of the bar's close edge (exclusive)."""
        return self.timestamp + timedelta(seconds=self.interval.seconds)

    def __repr__(self) -> str:
        return (
            f"OHLCVBar({self.symbol} {self.interval.label} "
            f"{self.timestamp:%Y-%m-%d %H:%M} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} "
            f"V={self.volume:.4f} trades={self.trade_count})"
        )


# ---------------------------------------------------------------------------
# Internal mutable bar state
# ---------------------------------------------------------------------------


@dataclass
class _MutableBar:
    """Internal accumulator for a bar under construction."""

    symbol: str
    interval: BarInterval
    bar_open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal("0")
    volume_quote: Decimal = Decimal("0")
    trade_count: int = 0

    def update(self, tick: TradeTick) -> None:
        """Incorporate a new tick into this bar."""
        self.high = max(self.high, tick.price)
        self.low = min(self.low, tick.price)
        self.close = tick.price
        self.volume += tick.quantity
        self.volume_quote += tick.notional
        self.trade_count += 1

    def to_ohlcv(self) -> OHLCVBar:
        """Finalise and return an immutable :class:`OHLCVBar`."""
        return OHLCVBar(
            symbol=self.symbol,
            interval=self.interval,
            timestamp=self.bar_open_time,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            volume_quote=self.volume_quote,
            trade_count=self.trade_count,
        )


def _align_bar_open(ts: datetime, interval: BarInterval) -> datetime:
    """Return the UTC start of the bar period that contains *ts*."""
    secs = int(ts.replace(tzinfo=timezone.utc).timestamp())
    aligned = (secs // interval.seconds) * interval.seconds
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


# ---------------------------------------------------------------------------
# RealtimeBarBuilder
# ---------------------------------------------------------------------------


class RealtimeBarBuilder:
    """Builds OHLCV bars from a real-time tick stream.

    Parameters
    ----------
    intervals:
        List of :class:`BarInterval` values to aggregate simultaneously.
        Defaults to ``[BarInterval.ONE_MIN, BarInterval.FIFTEEN_MIN]``.
    symbol:
        Expected symbol string — used for validation and bar labelling.
        Defaults to ``"BTCUSDT"``.
    """

    def __init__(
        self,
        intervals: Optional[List[BarInterval]] = None,
        symbol: str = "BTCUSDT",
    ) -> None:
        self.symbol = symbol
        self.intervals: List[BarInterval] = intervals or [
            BarInterval.ONE_MIN,
            BarInterval.FIFTEEN_MIN,
        ]
        # Per-interval mutable bar state
        self._open_bars: Dict[BarInterval, Optional[_MutableBar]] = {
            iv: None for iv in self.intervals
        }
        # Closed-bar subscribers
        self._closed_callbacks: List[Callable[[OHLCVBar], None]] = []
        self._lock = threading.Lock()

        # Statistics
        self.ticks_processed: int = 0
        self.bars_closed: int = 0

        logger.info(
            "RealtimeBarBuilder initialised: symbol=%s intervals=%s",
            symbol,
            [iv.label for iv in self.intervals],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe_closed(self, callback: Callable[[OHLCVBar], None]) -> None:
        """Register a callback that fires when a bar is closed.

        The callback receives the finalised :class:`OHLCVBar`.  It is called
        synchronously on the tick-delivery thread; keep it non-blocking.
        """
        with self._lock:
            if callback not in self._closed_callbacks:
                self._closed_callbacks.append(callback)

    def unsubscribe_closed(self, callback: Callable[[OHLCVBar], None]) -> None:
        """Remove a closed-bar callback."""
        with self._lock:
            try:
                self._closed_callbacks.remove(callback)
            except ValueError:
                pass

    def on_tick(self, tick: TradeTick) -> None:
        """Process a single :class:`TradeTick`.

        This method is designed to be registered directly as a
        :class:`~itm.data.binance_ws_stream.BinanceWebSocketStream` subscriber::

            stream.subscribe(builder.on_tick)
        """
        if tick.symbol != self.symbol:
            return  # ignore ticks for other symbols

        bars_to_dispatch: List[OHLCVBar] = []
        with self._lock:
            for interval in self.intervals:
                closed = self._process_tick_for_interval(tick, interval)
                if closed is not None:
                    bars_to_dispatch.append(closed)
            self.ticks_processed += 1

        # Dispatch closed bars OUTSIDE the lock to avoid deadlock
        for bar in bars_to_dispatch:
            self._dispatch_closed(bar)

    def flush(self) -> List[OHLCVBar]:
        """Close all currently open bars and return them.

        Useful when stopping the stream to finalise any partial bars.
        """
        closed: List[OHLCVBar] = []
        with self._lock:
            for interval in self.intervals:
                bar_state = self._open_bars[interval]
                if bar_state is not None:
                    bar = bar_state.to_ohlcv()
                    self._open_bars[interval] = None
                    closed.append(bar)
        for bar in closed:
            self._dispatch_closed(bar)
        logger.info("Flush closed %d partial bar(s)", len(closed))
        return closed

    def get_open_bar(self, interval: BarInterval) -> Optional[OHLCVBar]:
        """Return a *snapshot* of the currently open bar (may be None)."""
        with self._lock:
            state = self._open_bars.get(interval)
            if state is None:
                return None
            return state.to_ohlcv()

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------

    def _process_tick_for_interval(
        self, tick: TradeTick, interval: BarInterval
    ) -> Optional[OHLCVBar]:
        """Update or rotate the bar for *interval*.  Caller holds ``_lock``.

        Returns the closed :class:`OHLCVBar` if a bar was completed, else None.
        The caller is responsible for dispatching outside the lock.
        """
        bar_open_time = _align_bar_open(tick.timestamp, interval)
        state = self._open_bars[interval]

        if state is None:
            # First tick — open a new bar
            self._open_bars[interval] = self._new_bar(
                tick, interval, bar_open_time
            )
            return None

        if bar_open_time > state.bar_open_time:
            # Tick belongs to a new bar — close the current one first
            closed_bar = state.to_ohlcv()
            self._open_bars[interval] = self._new_bar(
                tick, interval, bar_open_time
            )
            self.bars_closed += 1
            return closed_bar
        else:
            # Same bar — update
            state.update(tick)
            return None

    @staticmethod
    def _new_bar(
        tick: TradeTick, interval: BarInterval, bar_open_time: datetime
    ) -> _MutableBar:
        return _MutableBar(
            symbol=tick.symbol,
            interval=interval,
            bar_open_time=bar_open_time,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
            volume=tick.quantity,
            volume_quote=tick.notional,
            trade_count=1,
        )

    def _dispatch_closed(self, bar: OHLCVBar) -> None:
        """Invoke all registered closed-bar callbacks."""
        with self._lock:
            callbacks = list(self._closed_callbacks)
        for cb in callbacks:
            try:
                cb(bar)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Closed-bar callback %s raised an exception for %s", cb, bar
                )

    def __repr__(self) -> str:
        open_info = {
            iv.label: (
                self._open_bars[iv].bar_open_time.isoformat()
                if self._open_bars[iv]
                else "none"
            )
            for iv in self.intervals
        }
        return (
            f"RealtimeBarBuilder(symbol={self.symbol!r}, "
            f"ticks={self.ticks_processed}, "
            f"bars_closed={self.bars_closed}, "
            f"open={open_info})"
        )
