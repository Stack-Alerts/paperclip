"""
Regression tests for BTCAAAAA-893.

Bug: _determine_dual_signals() on EMA200Trend was called with a single string
argument ('INSUFFICIENT_DATA') instead of the required 4 positional args
(crossed_above, crossed_below, current_position, simple_signal), causing a
TypeError when the insufficient-data code path was hit.

Fix: line 310 of ema_200_trend.py — pass (False, False, 'NEUTRAL', 'INSUFFICIENT_DATA')
instead of ('INSUFFICIENT_DATA').
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend


pytestmark = [
    pytest.mark.bug("BTCAAAAA-893"),
    pytest.mark.regression,
]


def _price_data(n_periods: int, seed: int = 42) -> pd.DataFrame:
    dates = pd.date_range(start="2025-01-01", periods=n_periods, freq="15min")
    rng = np.random.default_rng(seed)
    base = 45000.0
    trend = np.linspace(0, 3000, n_periods)
    return pd.DataFrame({
        "timestamp": dates,
        "close": base + trend + rng.normal(0, 100, n_periods).cumsum(),
        "open": base + trend,
        "high": base + trend + 200,
        "low": base + trend - 200,
        "volume": rng.uniform(100, 1000, n_periods),
    })


class TestDetermineDualSignals:
    """Direct unit tests for _determine_dual_signals — the bug site."""

    def test_insufficient_data_returns_correct_pair(self):
        """INSUFFICIENT_DATA path must return (INSUFFICIENT_DATA, NEUTRAL)."""
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, False, "NEUTRAL", "INSUFFICIENT_DATA")
        assert granular == "INSUFFICIENT_DATA"
        assert simple == "NEUTRAL"

    def test_error_path_returns_correct_pair(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, False, "NEUTRAL", "ERROR")
        assert granular == "ERROR"
        assert simple == "NEUTRAL"

    def test_bullish_cross(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(True, False, "ABOVE_200EMA", "BULLISH")
        assert granular == "BULLISH_CROSS"
        assert simple == "BULLISH"

    def test_bearish_cross(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, True, "BELOW_200EMA", "BEARISH")
        assert granular == "BEARISH_CROSS"
        assert simple == "BEARISH"

    def test_above_position_no_cross(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, False, "ABOVE_200EMA", "BULLISH")
        assert granular == "ABOVE_200EMA"
        assert simple == "BULLISH"

    def test_below_position_no_cross(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, False, "BELOW_200EMA", "BEARISH")
        assert granular == "BELOW_200EMA"
        assert simple == "BEARISH"

    def test_at_ema_position_no_cross(self):
        ema = EMA200Trend()
        granular, simple = ema._determine_dual_signals(False, False, "AT_200EMA", "NEUTRAL")
        assert granular == "AT_200EMA"
        assert simple == "NEUTRAL"


class TestCalculateEMA:
    def test_ema_length_matches_input(self):
        ema = EMA200Trend(period=200)
        close = pd.Series(np.linspace(40000, 50000, 250))
        result = ema.calculate_ema(close)
        assert len(result) == len(close)

    def test_ema_trends_in_same_direction(self):
        ema = EMA200Trend(period=200)
        close = pd.Series(np.linspace(40000, 50000, 250))
        result = ema.calculate_ema(close)
        assert result.iloc[-1] > result.iloc[0]

    def test_ema_is_smoothed_not_equal_to_close(self):
        ema = EMA200Trend(period=200)
        close = pd.Series(np.linspace(40000, 50000, 250))
        result = ema.calculate_ema(close)
        assert not np.isclose(result.iloc[-1], close.iloc[-1], atol=1000)


class TestCalculateSlope:
    def test_rising_ema_returns_uptrend(self):
        ema = EMA200Trend()
        s = pd.Series(np.linspace(44000, 46000, 50))
        slope = ema.calculate_slope(s, lookback=20)
        assert slope in ("UPTREND", "STRONG_UPTREND")

    def test_falling_ema_returns_downtrend(self):
        ema = EMA200Trend()
        s = pd.Series(np.linspace(46000, 44000, 50))
        slope = ema.calculate_slope(s, lookback=20)
        assert slope in ("DOWNTREND", "STRONG_DOWNTREND")

    def test_flat_ema_returns_sideways(self):
        ema = EMA200Trend()
        s = pd.Series([45000.0] * 30)
        slope = ema.calculate_slope(s, lookback=20)
        assert slope == "SIDEWAYS"

    def test_insufficient_data_returns_insufficient(self):
        ema = EMA200Trend()
        s = pd.Series([45000.0] * 3)
        slope = ema.calculate_slope(s, lookback=20)
        assert slope == "INSUFFICIENT_DATA"


class TestClassifyPosition:
    def test_price_above_ema(self):
        ema = EMA200Trend()
        assert ema.classify_position(46000, 45000) == "ABOVE_200EMA"

    def test_price_below_ema(self):
        ema = EMA200Trend()
        assert ema.classify_position(44000, 45000) == "BELOW_200EMA"

    def test_price_within_touching_threshold(self):
        ema = EMA200Trend()
        assert ema.classify_position(45180, 45000) == "AT_200EMA"

    def test_price_at_exact_ema(self):
        ema = EMA200Trend()
        assert ema.classify_position(45000, 45000) == "AT_200EMA"


class TestClassifyDistance:
    def test_touching(self):
        ema = EMA200Trend()
        assert ema.classify_distance(0.3) == "TOUCHING"

    def test_near(self):
        ema = EMA200Trend()
        assert ema.classify_distance(1.0) == "NEAR"

    def test_moderate(self):
        ema = EMA200Trend()
        assert ema.classify_distance(3.0) == "MODERATE"

    def test_extended(self):
        ema = EMA200Trend()
        assert ema.classify_distance(7.0) == "EXTENDED"

    def test_overextended(self):
        ema = EMA200Trend()
        assert ema.classify_distance(12.0) == "OVEREXTENDED"


class TestDetermineTrendFilter:
    def test_above_with_uptrend_longs_only(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter("ABOVE_200EMA", "UPTREND") == "LONGS_ONLY"

    def test_above_with_downtrend_longs_preferred(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter("ABOVE_200EMA", "DOWNTREND") == "LONGS_PREFERRED"

    def test_below_with_downtrend_shorts_only(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter("BELOW_200EMA", "DOWNTREND") == "SHORTS_ONLY"

    def test_below_with_uptrend_shorts_preferred(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter("BELOW_200EMA", "UPTREND") == "SHORTS_PREFERRED"

    def test_at_ema_neutral(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter("AT_200EMA", "SIDEWAYS") == "NEUTRAL"


class TestReversalPatterns:
    def test_bullish_higher_highs_confirmed(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"high": [100, 102, 104, 106, 108], "low": [98, 99, 100, 101, 102]})
        assert ema.check_bullish_reversal_pattern(df) is True

    def test_bullish_lower_low_fails(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"high": [100, 102, 104, 103, 108], "low": [98, 99, 100, 98, 102]})
        assert ema.check_bullish_reversal_pattern(df) is False

    def test_bearish_lower_highs_confirmed(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"high": [108, 106, 104, 102, 100], "low": [102, 101, 100, 99, 98]})
        assert ema.check_bearish_reversal_pattern(df) is True

    def test_bearish_higher_low_fails(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"high": [108, 106, 104, 102, 100], "low": [102, 101, 103, 99, 98]})
        assert ema.check_bearish_reversal_pattern(df) is False

    def test_insufficient_data_returns_false(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"high": [100, 102], "low": [98, 99]})
        assert ema.check_bullish_reversal_pattern(df) is False


class TestAnalyzeEdgeCases:
    """Edge cases in analyze() — the bug-triggering paths."""

    def test_insufficient_data_does_not_raise_typeerror(self):
        """The exact bug scenario: insufficient data must not raise TypeError."""
        ema = EMA200Trend(period=200)
        df = _price_data(50)
        result = ema.analyze(df)
        assert result["signal"] == "INSUFFICIENT_DATA"
        assert result["signal_simple"] == "NEUTRAL"
        assert "Need 220 periods" in result["metadata"]["error"]

    def test_missing_close_column_returns_error(self):
        ema = EMA200Trend()
        df = pd.DataFrame({"open": [1, 2, 3]})
        result = ema.analyze(df)
        assert result["signal"] == "ERROR"

    def test_sufficient_data_returns_valid_result(self):
        ema = EMA200Trend(period=200)
        df = _price_data(250)
        result = ema.analyze(df)
        assert "signal" in result
        assert "signal_simple" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))

    def test_sufficient_data_has_all_metadata_keys(self):
        ema = EMA200Trend(period=200)
        df = _price_data(250)
        result = ema.analyze(df)
        meta = result["metadata"]
        expected = {"ema_200", "current_price", "current_position", "prev_position",
                    "crossed_above", "crossed_below", "slope", "distance_pct",
                    "distance_class", "trend_filter", "period", "is_overextended",
                    "signal_simple", "signal_granular"}
        assert expected.issubset(meta.keys())

    def test_determine_dual_signals_never_raises_typeerror(self):
        """All call sites in analyze() must pass correct arity."""
        ema = EMA200Trend(period=200)
        try:
            ema.analyze(_price_data(50))
            ema.analyze(_price_data(250))
        except TypeError as exc:
            pytest.fail(f"_determine_dual_signals raised TypeError: {exc}")


class TestAnalyzeBehavioral:
    def test_confidence_within_bounds(self):
        ema = EMA200Trend(period=10)
        result = ema.analyze(_price_data(50))
        assert 0 <= result["confidence"] <= 100

    def test_signal_and_simple_are_strings(self):
        ema = EMA200Trend(period=200)
        result = ema.analyze(_price_data(250))
        assert isinstance(result["signal"], str)
        assert isinstance(result["signal_simple"], str)

    def test_slope_in_metadata_is_valid(self):
        ema = EMA200Trend(period=200)
        result = ema.analyze(_price_data(250))
        assert result["metadata"]["slope"] in (
            "UPTREND", "STRONG_UPTREND", "DOWNTREND", "STRONG_DOWNTREND", "SIDEWAYS", "INSUFFICIENT_DATA"
        )
