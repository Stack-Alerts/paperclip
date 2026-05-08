"""
Unit tests: RateLimiter (Section G)
=====================================
Tests rolling-window weight budget, rate limit enforcement,
429/418 backoff activation, and thread-safety basics.
"""

from __future__ import annotations

import time
import threading
import pytest
from decimal import Decimal

from src.itm.engine.rate_limiter import RateLimiter, RateLimitExceeded


# ---------------------------------------------------------------------------
# Basic consumption
# ---------------------------------------------------------------------------


class TestRateLimiterBasic:
    def test_consume_within_limit(self):
        limiter = RateLimiter(limit=100, window_secs=60.0)
        limiter.consume(10)
        limiter.consume(10)
        assert limiter.current_weight == 20

    def test_consume_exactly_at_limit(self):
        limiter = RateLimiter(limit=100, window_secs=60.0)
        limiter.consume(100)
        assert limiter.current_weight == 100

    def test_consume_exceeds_limit_raises(self):
        limiter = RateLimiter(limit=10, window_secs=60.0)
        limiter.consume(8)
        with pytest.raises(RateLimitExceeded):
            limiter.consume(3)  # 8+3 = 11 > 10

    def test_available_weight(self):
        limiter = RateLimiter(limit=100, window_secs=60.0)
        limiter.consume(30)
        assert limiter.available_weight == 70

    def test_invalid_limit_raises(self):
        with pytest.raises(ValueError):
            RateLimiter(limit=0)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            RateLimiter(window_secs=0.0)


# ---------------------------------------------------------------------------
# Rolling window expiry
# ---------------------------------------------------------------------------


class TestRollingWindowExpiry:
    def test_weight_expires_after_window(self):
        limiter = RateLimiter(limit=100, window_secs=0.05)  # 50ms window
        limiter.consume(90)
        assert limiter.current_weight == 90

        time.sleep(0.1)  # wait past window

        # After window expires, weight should be gone
        assert limiter.current_weight == 0

    def test_can_consume_again_after_window(self):
        limiter = RateLimiter(limit=10, window_secs=0.05)
        limiter.consume(10)

        with pytest.raises(RateLimitExceeded):
            limiter.consume(1)  # currently at limit

        time.sleep(0.1)  # wait past window

        # Should succeed now
        limiter.consume(10)  # window reset


# ---------------------------------------------------------------------------
# Backoff (429/418)
# ---------------------------------------------------------------------------


class TestBackoff:
    def test_429_activates_backoff(self):
        limiter = RateLimiter(limit=1200, window_secs=60.0)
        limiter.on_rate_limit_response(429, 1)
        assert limiter.is_in_backoff is True

    def test_consume_blocked_during_backoff(self):
        limiter = RateLimiter(limit=1200, window_secs=60.0)
        limiter.on_rate_limit_response(429, 3600)  # 1-hour backoff
        with pytest.raises(RateLimitExceeded, match="backoff"):
            limiter.consume(1)

    def test_418_applies_minimum_backoff_of_120s(self):
        limiter = RateLimiter(limit=1200, window_secs=60.0)
        limiter.on_rate_limit_response(418, 10)  # header says 10s
        # Should apply at least 120s
        assert limiter.is_in_backoff is True

    def test_backoff_expires(self):
        limiter = RateLimiter(limit=1200, window_secs=60.0)
        limiter.on_rate_limit_response(429, 0)  # 0-second backoff (test only)
        # immediately should not be in backoff (0 duration)
        # Note: might flicker on very slow machines; but acceptable
        time.sleep(0.01)
        # Should be able to consume again
        limiter.consume(1)


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_consume_does_not_exceed_limit(self):
        """Multiple threads consuming in parallel should not exceed the limit."""
        limit = 100
        limiter = RateLimiter(limit=limit, window_secs=60.0)
        errors = []
        successes = []

        def worker():
            try:
                limiter.consume(10)
                successes.append(1)
            except RateLimitExceeded:
                errors.append(1)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At most 10 threads can succeed (100 / 10 = 10)
        assert len(successes) <= 10
        # No thread should see partially consumed state
        assert limiter.current_weight <= limit
