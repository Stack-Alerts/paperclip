# Ascending Triangle Building Block

**Block Number:** 40/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bullish continuation pattern with horizontal resistance and rising support (higher lows).

## Technical Specifications
**File:** `src/detectors/building_blocks/patterns/ascending_triangle.py`

## Bitcoin Implementation
- High-reliability bullish continuation (70-75% success rate)
- Common during Bitcoin bull market corrections
- Pattern duration: 3-8 weeks on daily charts
- Each resistance test absorbs sellers → breakout when exhausted
- Volume declining into apex = coiling energy for breakout

## Trading Strategy
- Entry: Buy on breakout above resistance with volume
- Stop: Below most recent higher low
- Target: Triangle height added to breakout point
- Risk-Reward: 1:2 to 1:3

## Confluence
- Ascending Triangle + ADX >25 = +20 points
- Pattern near previous ATH = +15 points

**Status:** ✅ Ready | **Tests:** `test_ascending_triangle.py`
