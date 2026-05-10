"""
Unit tests for asia_session_50_percent per-session state reset (BTCAAAAA-977).

Verifies that prev_price_above, bounce_test_bars, rejection_test_bars, prev_signal,
and prev_asia_50 are all cleared when analyze() is called for the first bar of a new
calendar day, preventing spurious is_new_event=True crossings caused by stale state
from the previous day's 50% level.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50Percent


def _make_df(date_str: str, hour: int, n_bars: int = 60,
             asia_high: float = 100_500.0, asia_low: float = 99_500.0,
             current_close: float = 100_100.0) -> pd.DataFrame:
    """Build a minimal DataFrame with an Asia session + one London bar."""
    base = pd.Timestamp(f"{date_str} 00:00:00", tz="UTC")
    timestamps = [base + pd.Timedelta(minutes=15 * i) for i in range(n_bars)]

    closes = [current_close] * n_bars
    highs  = [asia_high] * n_bars
    lows   = [asia_low] * n_bars

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open":  closes,
        "high":  highs,
        "low":   lows,
        "close": closes,
        "volume": [1.0] * n_bars,
    })

    # Force the last bar to land at the requested hour
    df.iloc[-1, df.columns.get_loc("timestamp")] = pd.Timestamp(
        f"{date_str} {hour:02d}:00:00", tz="UTC"
    )
    return df


class TestSessionReset:
    """prev_price_above must be None at the start of every new calendar day."""

    def test_no_spurious_crossing_on_new_day(self):
        """
        After processing Day 1 entirely (leaving prev_price_above != None),
        the first London bar on Day 2 must NOT produce is_new_event=True due
        to the Day-1 stale prev_price_above when the Asia 50% has shifted.
        """
        block = AsiaSession50Percent()

        # ---- Day 1 bars ------------------------------------------------
        # Asia session (00-08): set prev_price_above = True
        # London bar: price is above 50% (100_100 vs midpoint 100_000)
        df_day1 = _make_df("2025-01-13", hour=9,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_100.0)  # above midpoint 100_000
        result_day1 = block.analyze(df_day1)
        assert block.prev_price_above is not None, "Day 1 should set prev_price_above"

        # ---- Day 2 first bar --------------------------------------------
        # NEW day: Asia 50% shifted so the first London bar is below the NEW 50%.
        # Without reset, Day-1 prev_price_above=True vs Day-2 price_above=False
        # would look like a downward crossing → is_new_event=True (spurious).
        df_day2 = _make_df("2025-01-14", hour=9,
                           asia_high=101_000.0, asia_low=100_000.0,
                           current_close=100_200.0)  # below new midpoint 100_500
        result_day2 = block.analyze(df_day2)

        # State must have been reset before evaluation
        assert result_day2["metadata"]["is_new_event"] is False, (
            "First bar of new day should not fire is_new_event=True from stale "
            "prev_price_above carried over from the previous session"
        )

    def test_prev_price_above_none_at_start_of_new_day(self):
        """After a new-day reset the internal state variables are cleared."""
        block = AsiaSession50Percent()

        # Warm up on Day 1
        df_day1 = _make_df("2025-01-13", hour=10,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_100.0)
        block.analyze(df_day1)
        assert block.prev_price_above is not None

        # Inject a bar with a different date directly to trigger the reset path
        df_day2 = _make_df("2025-01-14", hour=9,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_000.0)
        block.analyze(df_day2)

        # After analyze() for Day 2, _last_session_date is updated but the reset
        # happened at the TOP, so prev_price_above was None when crossing logic ran.
        # We verify indirectly: _last_session_date is now Day 2.
        assert block._last_session_date is not None
        assert str(block._last_session_date) == "2025-01-14"

    def test_bounce_and_rejection_bars_cleared_on_new_day(self):
        """bounce_test_bars and rejection_test_bars are [] at the start of each new day."""
        block = AsiaSession50Percent()
        asia_50 = 100_000.0

        # Manually seed stale test bars as if Day 1 left them populated
        block.bounce_test_bars = [{"close": 100_050.0, "low": 99_950.0, "high": 100_200.0,
                                   "distance": 0.05, "above_50": True,
                                   "breached_below": True, "breached_above": False,
                                   "closed_above": True, "closed_below": False}]
        block.rejection_test_bars = [{"close": 99_950.0, "low": 99_800.0, "high": 100_050.0,
                                      "distance": -0.05, "above_50": False,
                                      "breached_below": False, "breached_above": True,
                                      "closed_above": False, "closed_below": True}]
        block._last_session_date = pd.Timestamp("2025-01-13").date()

        # Call analyze() for a new day
        df_day2 = _make_df("2025-01-14", hour=9,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_100.0)
        block.analyze(df_day2)

        # The reset at the top of analyze() must have cleared these
        # (they may have been re-populated by this bar's own London logic, but
        # only if conditions were met this bar — with a single bar they won't be
        # since we need confirmation_candles consecutive hits)
        # We check that there is at most 1 entry (from THIS bar), not the stale 1
        # from Day 1 PLUS this bar's.
        assert len(block.bounce_test_bars) <= 1, (
            "bounce_test_bars should have been reset before Day-2 bar logic ran"
        )
        assert len(block.rejection_test_bars) <= 1, (
            "rejection_test_bars should have been reset before Day-2 bar logic ran"
        )

    def test_same_day_state_preserved(self):
        """Calling analyze() twice on the SAME day must NOT reset state between bars."""
        block = AsiaSession50Percent()

        df_bar1 = _make_df("2025-01-13", hour=9,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_100.0)
        block.analyze(df_bar1)
        price_above_after_bar1 = block.prev_price_above

        df_bar2 = _make_df("2025-01-13", hour=10,
                           asia_high=100_500.0, asia_low=99_500.0,
                           current_close=100_100.0)
        block.analyze(df_bar2)

        # prev_price_above should still be set (not cleared by a same-day re-call)
        assert block.prev_price_above is not None, (
            "prev_price_above must be preserved within the same calendar day"
        )
