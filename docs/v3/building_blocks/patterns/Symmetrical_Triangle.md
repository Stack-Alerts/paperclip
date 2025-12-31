# Symmetrical Triangle Building Block

**Block Number:** 42/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Neutral continuation pattern with converging trendlines (higher lows and lower highs), breakout direction determines trade.

## Technical Specifications
**File:** `src/detectors/building_blocks/patterns/symmetrical_triangle.py`

## Bitcoin Implementation
- Common Bitcoin consolidation pattern during trends
- Direction-neutral until breakout (75% break in direction of prior trend)
- Pattern duration: 2-6 weeks on daily Bitcoin charts
- Volume must confirm breakout (>2x average)
- Failed breakout (reversal back into triangle) = trade opposite direction

## Trading Strategy
- Wait for breakout at 50-75% completion
- Entry: Trade direction of breakout with volume confirmation
- Stop: Opposite side of triangle
- Target: Widest part of triangle added/subtracted from breakout

## Confluence
- Symmetrical Triangle + higher timeframe trend alignment = +20 points
- Volume confirmation = +15 points

**Status:** ✅ Ready | **Tests:** `test_symmetrical_triangle.py`
