"""
ITM Section G — Rate Limiter
==============================
Tracks Binance REST API weight usage and enforces the
1 200 weight/minute budget.

Binance limits
--------------
* 1 200 request weight per minute (rolling window)
* HTTP 429 → back off per ``Retry-After`` header (at least 60s)
* HTTP 418 → IP ban; back off for a longer period

Design
------
``RateLimiter`` is a simple token-bucket over a 60-second rolling window.
A ``RateLimitExceeded`` exception is raised before any request that would
exceed the budget so that callers can queue/throttle instead of hitting
the exchange.

Thread safety: the ``consume()`` / ``on_rate_limit_response()`` methods
are protected by a threading lock.

Usage
-----
::

    limiter = RateLimiter(limit=1200, window_secs=60)
    limiter.consume(weight=1)   # raises RateLimitExceeded if over budget
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Deque, Tuple

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a request would exceed the Binance weight limit."""


class RateLimiter:
    """Rolling-window rate limiter for Binance REST API weight tracking.

    Parameters
    ----------
    limit:        Maximum weight units allowed per window (default 1200).
    window_secs:  Rolling window duration in seconds (default 60).
    """

    def __init__(
        self,
        limit: int = 1200,
        window_secs: float = 60.0,
    ) -> None:
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        if window_secs <= 0:
            raise ValueError(f"window_secs must be positive, got {window_secs}")
        self._limit = limit
        self._window = window_secs
        self._lock = threading.Lock()
        # Deque of (timestamp, weight) pairs
        self._entries: Deque[Tuple[float, int]] = deque()
        # If non-zero, all requests are blocked until this time
        self._backoff_until: float = 0.0

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def consume(self, weight: int = 1) -> None:
        """Record weight consumption before a request.

        Raises ``RateLimitExceeded`` if the current window budget is exhausted
        or if a backoff period is active.

        Parameters
        ----------
        weight:  Request weight (1 for most endpoints; varies by endpoint).
        """
        with self._lock:
            now = time.monotonic()

            # Check backoff first
            if now < self._backoff_until:
                wait_secs = self._backoff_until - now
                raise RateLimitExceeded(
                    f"Rate limit backoff active for {wait_secs:.1f}s more — "
                    f"request blocked"
                )

            # Expire old entries
            self._prune(now)

            current_weight = self._current_weight()
            if current_weight + weight > self._limit:
                raise RateLimitExceeded(
                    f"Rate limit would be exceeded: "
                    f"current={current_weight}, request={weight}, "
                    f"limit={self._limit}/window"
                )

            self._entries.append((now, weight))
            logger.debug(
                "RateLimiter: consumed %d weight (total=%d/%d)",
                weight, current_weight + weight, self._limit,
            )

    def on_rate_limit_response(self, status_code: int, retry_after_secs: int) -> None:
        """Called by the REST client when a 429 or 418 response is received.

        Activates a backoff period so subsequent ``consume()`` calls are
        blocked until the backoff expires.

        Parameters
        ----------
        status_code:       HTTP status (429 or 418)
        retry_after_secs:  Seconds from the ``Retry-After`` header
        """
        with self._lock:
            backoff = float(retry_after_secs)
            if status_code == 418:
                # IP ban — add a safety buffer on top of the header value
                backoff = max(backoff, 120.0)
                logger.error(
                    "Binance 418 IP ban — applying %ds backoff", int(backoff)
                )
            else:
                logger.warning(
                    "Binance 429 rate limit — applying %ds backoff", int(backoff)
                )
            self._backoff_until = time.monotonic() + backoff

    @property
    def current_weight(self) -> int:
        """Current consumed weight within the rolling window (thread-safe)."""
        with self._lock:
            self._prune(time.monotonic())
            return self._current_weight()

    @property
    def available_weight(self) -> int:
        """Remaining weight budget within the current window."""
        return self._limit - self.current_weight

    @property
    def is_in_backoff(self) -> bool:
        """True if a rate-limit backoff is currently active."""
        return time.monotonic() < self._backoff_until

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _prune(self, now: float) -> None:
        """Remove entries older than the rolling window."""
        cutoff = now - self._window
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()

    def _current_weight(self) -> int:
        return sum(w for _, w in self._entries)
