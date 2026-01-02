# 20/50 EMA Trend Tracker - Continuous Position Indicator

**Category:** Moving Averages  
**Type:** Signal Block (Continuous)  
**File:** `src/detectors/building_blocks/moving_averages/ema_20_50_trend.py`  
**Class:** `EMA2050Trend`

## Overview

Continuous trend tracking system based on EMA alignment. Signals on **every bar** based on relative position of Price, Fast EMA, and Slow EMA.

**Critical Distinction:** This is the CONTINUOUS version. For event-driven cross detection only, use `ema_20_50_cross` instead.

## Block Behavior (Continuous + Event Tracking)

This block operates in **DUAL MODE**:
- **Continuous State:** Tracks current trend position (BULLISH/BEARISH) on every bar
- **Event Detection:** Identifies when trend direction CHANGES (bullish ↔ bearish)

**Metadata Fields:**
- `is_new_event`: Boolean - True if trend just changed direction, False if continuing
- `bars_since_trend_change`: Integer - How many bars ago the current trend started
- `trend`: String - Current trend classification (STRONG_UPTREND, EARLY_UPTREND, etc.)

**Usage:**
- **Trend Change Entry:** Use `is_new_event == True` for timing trend reversal entries
- **Trend Filter:** Use continuous signal to only trade WITH current trend
- **Trend Age:** Check `bars_since_trend_change` to assess trend maturity

**Important:** 100% signal rate is expected - this block always maintains directional bias!

## Signals (Continuous)

- **BULLISH**: When in uptrend position or early uptrend
  - Strong Uptrend: Price > Fast EMA > Slow EMA (perfect alignment)
  - Early Uptrend: Price > Fast EMA, but Fast < Slow (awaiting cross)
  - Golden Cross: Active crossover event

- **BEARISH**: When in downtrend position or early downtrend
  - Strong Downtrend: Price < Fast EMA < Slow EMA (perfect alignment)
  - Early Downtrend: Price < Fast EMA, but Fast > Slow (awaiting cross)
  - Death Cross: Active crossover event

- **NEUTRAL**: Rare (only when EMAs conflict with price position)

## Parameters (Optimized)

```python
fast_period: int = 15      # Optimized (was 20)
slow_period: int = 45      # Optimized (was 50)
cross_lookback: int = 2    # Confirmation bars
volume_threshold: float = 1.1  # Volume multiplier
```

## Expected Performance

- **Signals:** ~17,000 signals per 180 days (continuous)
- **Signal Rate:** ~100% of bars (always signaling)
- **Confidence:** 65-95% (varies by trend strength and volume)

## Trend Classification

1. **Strong Uptrend (75% conf)**: Price > Fast > Slow (perfect bullish alignment)
2. **Strong Downtrend (75% conf)**: Price < Fast < Slow (perfect bearish alignment)
3. **Early Uptrend (65% conf)**: Price > Fast, waiting for Fast to cross above Slow
4. **Early Downtrend (65% conf)**: Price < Fast, waiting for Fast to cross below Slow
5. **Golden Cross (85-95% conf)**: Active bullish crossover event
6. **Death Cross (85-95% conf)**: Active bearish crossover event

## Volume Impact

- **With volume confirmation:** +10% confidence
- **Without volume (when required):** -10% confidence

## Usage Example

```python
from src.detectors.building_blocks.moving_averages.ema_20_50_trend import EMA2050Trend

trend = EMA2050Trend()
result = trend.analyze(df)

# result['signal'] will be BULLISH or BEARISH on nearly every bar
# Based on current trend position, not just crosses
```

## Production Status

✅ **PRODUCTION READY** (Renamed 2026-01-02)

- Originally named "ema_20_50_cross" but misnamed (was always a trend tracker)
- Renamed to accurately reflect continuous trend tracking behavior
- Signals: 16,431 in 180 days (91.3/day confirmed)
- Optimized parameters (15/45 outperform 20/50)

## Related Blocks

- **ema_20_50_cross**: Event-driven crossover detector (NEW - use this for actual crosses)
- **ema_50_vector**: 50 EMA vector break detector
- **ema_200_trend**: 200 EMA major trend detector

## When to Use

- **Use ema_20_50_trend when:** You want continuous position tracking for trend-following strategies
- **Use ema_20_50_cross when:** You only want to act on actual crossover events
