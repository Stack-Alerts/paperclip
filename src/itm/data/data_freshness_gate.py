"""
ITM Section B — Data Freshness Gate
=====================================
Enforces the <60-second freshness rule: downstream consumers (strategy signals,
execution engine) must never process stale market data.

Design
------
* ``DataFreshnessGate`` tracks the last tick and last bar timestamps for each
  registered instrument/interval combination.
* ``check_tick_freshness()`` raises :class:`StaleDataError` (or returns
  ``FreshnessStatus.STALE``) if the most recently received tick is older than
  ``max_age_seconds`` (default: 60 s).
* ``check_bar_freshness()`` performs the same check against the last closed bar
  timestamp.
* ``gate()`` context manager: raises ``StaleDataError`` if the data is stale,
  otherwise executes the guarded block.
* Fully thread-safe.
* ``FreshnessStatus`` enum provides a non-exception signal path for callers
  that prefer polling.

Clock injection
---------------
The gate accepts an optional ``clock`` callable (``() → datetime``) so that
tests can inject a frozen or fast-forward clock without patching global time.

Usage
-----
::

    gate = DataFreshnessGate(max_age_seconds=60)
    stream.subscribe(gate.record_tick)
    builder.subscribe_closed(gate.record_bar)

    # Raise on stale
    gate.check_tick_freshness()  # raises StaleDataError if > 60 s since last tick

    # Non-raising poll
    status = gate.tick_status()
    if status == FreshnessStatus.STALE:
        ...

    # Context manager
    with gate.guard():
        strategy.on_bar(bar)

"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Callable, Dict, Generator, Optional, Tuple

from .binance_ws_stream import TradeTick
from .realtime_bar_builder import BarInterval, OHLCVBar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class FreshnessStatus(Enum):
    """Result of a freshness check."""

    FRESH = auto()     # data is within the allowed age window
    STALE = auto()     # data is older than max_age_seconds
    NO_DATA = auto()   # no data has been received yet


class StaleDataError(RuntimeError):
    """Raised when downstream code attempts to consume stale market data.

    Attributes
    ----------
    age_seconds:    How old the data is (in seconds).
    max_age_seconds: The configured maximum age.
    source:         ``'tick'`` or ``'bar'`` — which check triggered the error.
    """

    def __init__(
        self,
        age_seconds: float,
        max_age_seconds: int,
        source: str = "tick",
        detail: str = "",
    ) -> None:
        self.age_seconds = age_seconds
        self.max_age_seconds = max_age_seconds
        self.source = source
        msg = (
            f"StaleDataError: {source} data is {age_seconds:.1f}s old "
            f"(max allowed: {max_age_seconds}s)"
        )
        if detail:
            msg += f" — {detail}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# DataFreshnessGate
# ---------------------------------------------------------------------------

# Key type for bar freshness tracking: (symbol, BarInterval)
_BarKey = Tuple[str, BarInterval]


class DataFreshnessGate:
    """Enforces the <60s data freshness rule for the ITM data layer.

    Parameters
    ----------
    max_age_seconds:
        Maximum age (in seconds) of a tick or bar before it is considered
        stale.  Default: 60.
    clock:
        Optional callable that returns the current UTC datetime.  Inject a
        custom clock in tests to avoid real-time dependencies.  Default:
        ``datetime.now(timezone.utc)``.
    """

    def __init__(
        self,
        max_age_seconds: int = 60,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self.max_age_seconds = max_age_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()

        # Last received tick timestamps: symbol → datetime
        self._last_tick_ts: Dict[str, datetime] = {}
        # Last closed bar timestamps: (symbol, BarInterval) → datetime
        self._last_bar_ts: Dict[_BarKey, datetime] = {}

        logger.info(
            "DataFreshnessGate initialised: max_age_seconds=%d", max_age_seconds
        )

    # ------------------------------------------------------------------
    # Data ingestion (subscribe these to stream / builder)
    # ------------------------------------------------------------------

    def record_tick(self, tick: TradeTick) -> None:
        """Record the timestamp of an incoming tick.

        Register as a ``BinanceWebSocketStream`` subscriber::

            stream.subscribe(gate.record_tick)
        """
        with self._lock:
            self._last_tick_ts[tick.symbol] = tick.timestamp

    def record_bar(self, bar: OHLCVBar) -> None:
        """Record the timestamp of a closed bar.

        Register as a ``RealtimeBarBuilder`` closed-bar subscriber::

            builder.subscribe_closed(gate.record_bar)
        """
        key: _BarKey = (bar.symbol, bar.interval)
        with self._lock:
            self._last_bar_ts[key] = bar.timestamp

    # ------------------------------------------------------------------
    # Freshness checks (non-raising)
    # ------------------------------------------------------------------

    def tick_status(self, symbol: str = "BTCUSDT") -> FreshnessStatus:
        """Return the freshness status for tick data of *symbol*.

        Does not raise — use :meth:`check_tick_freshness` for the
        exception-raising variant.
        """
        with self._lock:
            last = self._last_tick_ts.get(symbol)
        if last is None:
            return FreshnessStatus.NO_DATA
        age = (self._clock() - last).total_seconds()
        return FreshnessStatus.FRESH if age <= self.max_age_seconds else FreshnessStatus.STALE

    def bar_status(
        self,
        symbol: str = "BTCUSDT",
        interval: BarInterval = BarInterval.ONE_MIN,
    ) -> FreshnessStatus:
        """Return the freshness status for bar data.

        Note: the bar timestamp is the *open time* of the bar; the bar
        is considered fresh if it was opened within the freshness window
        (i.e. we expect at most one interval of age for a current bar).
        """
        key: _BarKey = (symbol, interval)
        with self._lock:
            last = self._last_bar_ts.get(key)
        if last is None:
            return FreshnessStatus.NO_DATA
        # A bar is fresh if its open time is within (max_age + interval) seconds ago
        effective_max_age = self.max_age_seconds + interval.seconds
        age = (self._clock() - last).total_seconds()
        return FreshnessStatus.FRESH if age <= effective_max_age else FreshnessStatus.STALE

    def last_tick_age(self, symbol: str = "BTCUSDT") -> Optional[float]:
        """Return the age in seconds of the most recent tick, or None."""
        with self._lock:
            last = self._last_tick_ts.get(symbol)
        if last is None:
            return None
        return (self._clock() - last).total_seconds()

    def last_bar_age(
        self,
        symbol: str = "BTCUSDT",
        interval: BarInterval = BarInterval.ONE_MIN,
    ) -> Optional[float]:
        """Return the age in seconds of the most recent closed bar, or None."""
        key: _BarKey = (symbol, interval)
        with self._lock:
            last = self._last_bar_ts.get(key)
        if last is None:
            return None
        return (self._clock() - last).total_seconds()

    # ------------------------------------------------------------------
    # Freshness checks (raising)
    # ------------------------------------------------------------------

    def check_tick_freshness(self, symbol: str = "BTCUSDT") -> None:
        """Assert that tick data for *symbol* is fresh.

        Raises
        ------
        StaleDataError
            If no tick has been received yet, or the last tick is older than
            ``max_age_seconds``.
        """
        status = self.tick_status(symbol)
        if status == FreshnessStatus.NO_DATA:
            raise StaleDataError(
                age_seconds=float("inf"),
                max_age_seconds=self.max_age_seconds,
                source="tick",
                detail=f"No tick data received for {symbol}",
            )
        if status == FreshnessStatus.STALE:
            age = self.last_tick_age(symbol) or float("inf")
            logger.warning(
                "Tick data stale: symbol=%s age=%.1fs max=%ds",
                symbol,
                age,
                self.max_age_seconds,
            )
            raise StaleDataError(
                age_seconds=age,
                max_age_seconds=self.max_age_seconds,
                source="tick",
                detail=f"symbol={symbol}",
            )

    def check_bar_freshness(
        self,
        symbol: str = "BTCUSDT",
        interval: BarInterval = BarInterval.ONE_MIN,
    ) -> None:
        """Assert that bar data is fresh.

        Raises
        ------
        StaleDataError
            If no bar has been closed yet, or the last bar is older than
            ``max_age_seconds + interval.seconds``.
        """
        status = self.bar_status(symbol, interval)
        if status == FreshnessStatus.NO_DATA:
            raise StaleDataError(
                age_seconds=float("inf"),
                max_age_seconds=self.max_age_seconds,
                source="bar",
                detail=f"No bar data for {symbol}/{interval.label}",
            )
        if status == FreshnessStatus.STALE:
            age = self.last_bar_age(symbol, interval) or float("inf")
            logger.warning(
                "Bar data stale: symbol=%s interval=%s age=%.1fs",
                symbol,
                interval.label,
                age,
            )
            raise StaleDataError(
                age_seconds=age,
                max_age_seconds=self.max_age_seconds,
                source="bar",
                detail=f"symbol={symbol} interval={interval.label}",
            )

    # ------------------------------------------------------------------
    # Context manager / guard
    # ------------------------------------------------------------------

    @contextmanager
    def guard(
        self,
        symbol: str = "BTCUSDT",
        check_ticks: bool = True,
        check_bars: bool = False,
        interval: BarInterval = BarInterval.ONE_MIN,
    ) -> Generator[None, None, None]:
        """Context manager that raises :class:`StaleDataError` if data is stale.

        Parameters
        ----------
        symbol:       Symbol to check (default: ``"BTCUSDT"``).
        check_ticks:  Check tick freshness (default: ``True``).
        check_bars:   Check bar freshness (default: ``False``).
        interval:     Bar interval to check when ``check_bars=True``.

        Example
        -------
        ::

            with gate.guard(check_ticks=True, check_bars=True):
                strategy.evaluate(bar)
        """
        if check_ticks:
            self.check_tick_freshness(symbol)
        if check_bars:
            self.check_bar_freshness(symbol, interval)
        yield

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Return a snapshot dict of all tracked freshness state."""
        now = self._clock()
        with self._lock:
            tick_ages = {
                sym: (now - ts).total_seconds()
                for sym, ts in self._last_tick_ts.items()
            }
            bar_ages = {
                f"{sym}/{iv.label}": (now - ts).total_seconds()
                for (sym, iv), ts in self._last_bar_ts.items()
            }
        return {
            "max_age_seconds": self.max_age_seconds,
            "tick_ages": tick_ages,
            "bar_ages": bar_ages,
        }

    def __repr__(self) -> str:
        n_ticks = len(self._last_tick_ts)
        n_bars = len(self._last_bar_ts)
        return (
            f"DataFreshnessGate("
            f"max_age={self.max_age_seconds}s, "
            f"symbols={n_ticks}, "
            f"bar_series={n_bars})"
        )
