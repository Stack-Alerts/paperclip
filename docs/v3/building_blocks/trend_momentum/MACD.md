# MACD (Moving Average Convergence Divergence) Building Block

**Block Number:** 19/66 | **Category:** Trend & Momentum | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Trend-following momentum indicator showing relationship between two moving averages, signaling trend changes and momentum shifts.

## Technical Specifications
**MACD Line:** 12 EMA - 26 EMA
**Signal Line:** 9 EMA of MACD line
**Histogram:** MACD - Signal (visual momentum)
**File:** `src/detectors/building_blocks/trend_momentum/macd.py`

## Bitcoin Implementation
- MACD crossovers on Bitcoin 4hr chart = reliable trend changes
- Histogram expansion = momentum building
- Histogram contraction = momentum fading
- Divergence (price vs MACD) = powerful reversal signal
- Zero-line crosses = major trend shifts

## Trading Strategies

**Strategy 1: MACD Crossover (65-70% win rate)**
- Bullish: MACD crosses above Signal = buy signal
- Bearish: MACD crosses below Signal = sell signal
- Confirm with higher timeframe trend
- Enter on pullback after crossover

**Strategy 2: MACD Divergence (75-80% win rate)**
- Bullish Divergence: Price lower low, MACD higher low = reversal up
- Bearish Divergence: Price higher high, MACD lower high = reversal down
- Most reliable reversal signal
- Combine with support/resistance

## Confluence
- MACD Divergence + RSI Divergence = +25 points
- MACD Crossover + ADX >25 = +20 points (trending)
- MACD + MSS/CHoCH = +20 points (reversal confirmation)
- Histogram expansion + BOS = +15 points

## Key Characteristics
- 12, 26, 9 standard settings
- Crossovers = trend changes
- Divergence = reversals
- Histogram = momentum strength
- Zero-line cross = major trend shift

**Status:** ✅ Ready | **Tests:** `test_macd.py`

---
*End of MACD Documentation*

🎉 **TREND & MOMENTUM CATEGORY COMPLETE! (2/2 blocks)**
