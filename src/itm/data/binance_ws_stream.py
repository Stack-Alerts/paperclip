"""
ITM Section B — Binance WebSocket Stream
=========================================
Real-time BTCUSDT Perpetual Futures tick-data feed via Binance WebSocket API.

Design
------
* Asyncio-based internally; exposes a thread-safe synchronous callback API so
  the caller does not need to manage an event loop.
* Reconnects automatically with exponential back-off (max 60 s).
* Emits :class:`TradeTick` dataclass objects to registered subscribers via
  thread-safe callbacks.
* ``StreamState`` tracks lifecycle: IDLE → CONNECTING → CONNECTED →
  RECONNECTING → STOPPED.
* The stream normalises Binance aggTrade fields to the ITM tick model so
  downstream components never depend on raw Binance wire format.

Usage
-----
::

    stream = BinanceWebSocketStream(symbol="BTCUSDT", testnet=False)
    stream.subscribe(my_tick_handler)  # callable(TradeTick) → None
    stream.start()           # starts background thread + asyncio loop
    ...
    stream.stop()

"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Binance WebSocket endpoint constants
# ---------------------------------------------------------------------------

_WS_FUTURES_BASE = "wss://fstream.binance.com"
_WS_FUTURES_TESTNET_BASE = "wss://stream.binancefuture.com"

# aggTrade stream: low-latency aggregate-trade events (1 per taker execution)
_STREAM_PATH = "/ws/{symbol}@aggTrade"

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


class StreamState(Enum):
    """Lifecycle state of the WebSocket stream."""

    IDLE = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    STOPPED = auto()


@dataclass(frozen=True)
class TradeTick:
    """A single normalised trade tick from the Binance aggTrade stream.

    All monetary values use :class:`decimal.Decimal` for precision.

    Attributes
    ----------
    symbol:       Binance symbol (e.g. "BTCUSDT")
    price:        Trade price in USDT (Decimal)
    quantity:     Trade quantity in BTC (Decimal)
    is_buyer_maker: True when the taker was the seller (i.e. a sell trade)
    trade_id:     Binance aggregate trade ID
    timestamp:    UTC datetime of the trade (from Binance event time)
    received_at:  Local UTC datetime when the tick was received (latency ref)
    """

    symbol: str
    price: Decimal
    quantity: Decimal
    is_buyer_maker: bool  # True ⇒ seller is taker; side = SELL
    trade_id: int
    timestamp: datetime
    received_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def side(self) -> str:
        """'buy' or 'sell' from the taker's perspective."""
        return "sell" if self.is_buyer_maker else "buy"

    @property
    def notional(self) -> Decimal:
        """Trade value in USDT."""
        return self.price * self.quantity


# ---------------------------------------------------------------------------
# BinanceWebSocketStream
# ---------------------------------------------------------------------------


class BinanceWebSocketStream:
    """Manages a Binance aggTrade WebSocket feed for a single symbol.

    Thread safety
    -------------
    * ``start()`` and ``stop()`` are safe to call from any thread.
    * Subscriber callbacks are invoked from the internal asyncio thread.
      Callbacks must be non-blocking; off-load any heavy work to a queue.

    Reconnection
    ------------
    Exponential back-off: 1 s → 2 s → 4 s → … → 60 s (cap).  The stream
    resets the back-off counter on each successful connection.

    Parameters
    ----------
    symbol:      Binance symbol string (default: "BTCUSDT")
    testnet:     Route to Binance Futures testnet (default: False)
    ping_interval: Seconds between keepalive pings (default: 20)
    ping_timeout:  Seconds before a missed pong is treated as a disconnect
                   (default: 10)
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        testnet: bool = False,
        ping_interval: int = 20,
        ping_timeout: int = 10,
    ) -> None:
        self.symbol = symbol.upper()
        self.testnet = testnet
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout

        self._subscribers: List[Callable[[TradeTick], None]] = []
        self._lock = threading.Lock()
        self._state = StreamState.IDLE
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = asyncio.Event()  # set in the loop thread

        # Reconnection state
        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 60.0

        # Metrics (simple counters for monitoring)
        self.ticks_received: int = 0
        self.reconnect_count: int = 0

        logger.info(
            "BinanceWebSocketStream initialised: symbol=%s testnet=%s",
            self.symbol,
            testnet,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> StreamState:
        return self._state

    def subscribe(self, callback: Callable[[TradeTick], None]) -> None:
        """Register a callback that will receive every :class:`TradeTick`.

        The callback is invoked synchronously on the stream's internal thread.
        It must be fast and non-blocking.
        """
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)
                logger.debug("Subscriber added: %s", callback)

    def unsubscribe(self, callback: Callable[[TradeTick], None]) -> None:
        """Remove a previously registered callback."""
        with self._lock:
            try:
                self._subscribers.remove(callback)
                logger.debug("Subscriber removed: %s", callback)
            except ValueError:
                pass

    def start(self) -> None:
        """Start the WebSocket stream in a background daemon thread."""
        if self._state not in (StreamState.IDLE, StreamState.STOPPED):
            logger.warning(
                "BinanceWebSocketStream.start() called in state %s — ignored",
                self._state,
            )
            return
        self._state = StreamState.CONNECTING
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"BinanceWS-{self.symbol}",
            daemon=True,
        )
        self._thread.start()
        logger.info("BinanceWebSocketStream started (thread: %s)", self._thread.name)

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop the stream and wait for the background thread."""
        if self._state == StreamState.STOPPED:
            return
        logger.info("BinanceWebSocketStream stopping…")
        self._state = StreamState.STOPPED
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("BinanceWebSocketStream stopped.")

    # ------------------------------------------------------------------
    # Internal loop management
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Entry point for the background thread: create + run event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        try:
            self._loop.run_until_complete(self._stream_manager())
        except Exception:  # noqa: BLE001
            logger.exception("Unhandled exception in BinanceWebSocketStream loop")
        finally:
            self._loop.close()
            self._state = StreamState.STOPPED

    async def _stream_manager(self) -> None:
        """Top-level coroutine: reconnect loop with exponential back-off."""
        while not self._stop_event.is_set():
            try:
                self._state = StreamState.CONNECTING
                logger.info(
                    "Connecting to Binance WebSocket (attempt %d)…",
                    self.reconnect_count + 1,
                )
                await self._connect_and_consume()
                # Clean disconnect — no reconnect needed
                break
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                if self._stop_event.is_set():
                    break
                self.reconnect_count += 1
                self._state = StreamState.RECONNECTING
                logger.warning(
                    "WebSocket error: %s. Reconnecting in %.1f s (attempt %d)…",
                    exc,
                    self._reconnect_delay,
                    self.reconnect_count,
                )
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._reconnect_delay
                    )
                except asyncio.TimeoutError:
                    pass
                # Exponential back-off
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

    async def _connect_and_consume(self) -> None:
        """Open the WebSocket and pump messages until disconnected."""
        import websockets  # imported here so module loads without websockets installed

        base = _WS_FUTURES_TESTNET_BASE if self.testnet else _WS_FUTURES_BASE
        url = base + _STREAM_PATH.format(symbol=self.symbol.lower())
        logger.info("WebSocket URL: %s", url)

        async with websockets.connect(
            url,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            close_timeout=5,
        ) as ws:
            self._state = StreamState.CONNECTED
            # Reset back-off on successful connect
            self._reconnect_delay = 1.0
            logger.info("Connected to Binance WebSocket: %s", url)

            while not self._stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # Check stop event
                self._handle_message(raw)

    def _handle_message(self, raw: str) -> None:
        """Parse a raw aggTrade message and notify subscribers."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON WebSocket message: %.100s", raw)
            return

        # aggTrade event schema:
        #   e: "aggTrade"  a: agg trade id  E: event time (ms)  s: symbol
        #   p: price       q: quantity      m: is_buyer_maker
        if msg.get("e") != "aggTrade":
            logger.debug("Ignoring non-aggTrade event: %s", msg.get("e"))
            return

        try:
            tick = TradeTick(
                symbol=msg["s"],
                price=Decimal(msg["p"]),
                quantity=Decimal(msg["q"]),
                is_buyer_maker=bool(msg["m"]),
                trade_id=int(msg["a"]),
                timestamp=datetime.fromtimestamp(
                    int(msg["E"]) / 1000.0, tz=timezone.utc
                ),
                received_at=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError, Exception) as exc:  # noqa: BLE001
            logger.error("Failed to parse aggTrade tick: %s — msg: %s", exc, msg)
            return

        self.ticks_received += 1
        self._dispatch(tick)

    def _dispatch(self, tick: TradeTick) -> None:
        """Call all registered subscribers with the new tick."""
        with self._lock:
            subscribers = list(self._subscribers)
        for cb in subscribers:
            try:
                cb(tick)
            except Exception:  # noqa: BLE001
                logger.exception("Subscriber %s raised an exception on tick", cb)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"BinanceWebSocketStream("
            f"symbol={self.symbol!r}, "
            f"state={self._state.name}, "
            f"ticks={self.ticks_received}, "
            f"reconnects={self.reconnect_count})"
        )
