# Wedge Patterns (Rising/Falling) Building Block

**Block Number:** 45/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Reversal patterns with converging trendlines - Rising Wedge (bearish), Falling Wedge (bullish).

## Technical Specifications
**Rising Wedge:** Both lines rising, converging upward (bearish reversal)  
**Falling Wedge:** Both lines falling, converging downward (bullish reversal)  
**File:** `src/detectors/building_blocks/patterns/rising_wedge.py`, `falling_wedge.py`

## Bitcoin Implementation

**Rising Wedge (Bearish - 81% success in bull markets):**
- Forms at Bitcoin tops before corrections in uptrends
- Both support and resistance rising, but narrowing
- Volume declining = buying momentum weakening
- Breakdown can be violent (5-15% quick drops)

**Falling Wedge (Bullish - 74% success in bull markets):**
- Forms during Bitcoin bear market bottoms
- Both lines falling but converging
- Volume declining = selling exhaustion
- Breakouts often explosive (15-30%+ rallies)

## Trading Strategy - Rising Wedge
- Entry: SHORT on break below support with volume
- Stop: Above recent high within wedge
- Target: Widest part subtracted from breakdown

## Trading Strategy - Falling Wedge
- Entry: LONG on break above resistance with volume spike
- Stop: Below recent low within wedge
- Target: Widest part added to breakout

## Confluence
- Rising Wedge + RSI divergence = +25 points
- Falling Wedge after decline = +25 points

**Status:** ✅ Ready | **Tests:** `test_flags_pennants.py`
