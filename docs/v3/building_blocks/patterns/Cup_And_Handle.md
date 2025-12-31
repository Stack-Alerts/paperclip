# Cup and Handle Pattern Building Block

**Block Number:** 46/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bullish continuation pattern shaped like tea cup with handle, signaling consolidation before upward breakout.

## Technical Specifications
**Cup:** U-shaped rounded bottom (not V-shaped), 30-50% retracement  
**Handle:** Slight downward drift or sideways consolidation in upper half of cup  
**Duration:** Weeks to months (3-6 months typical)  
**File:** `src/detectors/building_blocks/patterns/cup_and_handle.py`

## Bitcoin Implementation
- Powerful bullish continuation in Bitcoin bull markets (70-75% win rate)
- Forms during corrections within larger uptrends
- Cup represents accumulation after profit-taking
- Handle shakes out late buyers before breakout
- Target: Cup depth added to breakout point (often exceeded in Bitcoin)
- Best on daily/weekly timeframes

## Trading Strategy
- Wait for U-shaped cup after uptrend
- Identify handle formation in upper half of cup
- Entry: Buy on breakout above handle resistance with volume >2x average
- Stop: Below handle low (tight) or cup 50% level
- Take Profit 1: Cup depth added to breakout (measured move)
- Take Profit 2: Previous ATH or next major resistance

## Confluence
- Cup & Handle + bullish trend = +25 points
- Handle near resistance = +15 points
- Volume spike on breakout = +15 points

**Status:** ✅ Ready | **Tests:** `test_cup_rounding.py`
