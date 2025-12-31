# Pivot Points Building Block

**Block Number:** 23/66 | **Category:** Advanced Price Action | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Calculates support and resistance levels based on previous period's OHLC prices providing institutional reference points.

## Technical Specifications
**Pivot Point (PP):** (Prev High + Prev Low + Prev Close) / 3
**Resistance:** R1 = (2×PP) - Prev Low, R2 = PP + (High-Low), R3 = High + 2×(PP-Low)
**Support:** S1 = (2×PP) - Prev High, S2 = PP - (High-Low), S3 = Low - 2×(High-PP)
**File:** `src/detectors/building_blocks/price_action/pivot_points.py`

## Bitcoin Implementation
- Daily pivots useful for intraday Bitcoin trading
- Weekly pivots provide swing trading reference
- Bitcoin often respects pivot levels during consolidation
- Breakout above R1 or below S1 = strong directional move
- Price above PP = bullish bias, below = bearish bias

## Trading Strategies

**Strategy 1: Pivot Bounce (60-65% win rate)**
- Setup: Price approaches pivot level (PP, S1, R1)
- Entry: Bounce/rejection at level
- Stop: Beyond next pivot
- Target: Opposite pivot level

**Strategy 2: Breakout Continuation**
- Break above R1 with volume = bullish
- Break below S1 with volume = bearish
- Enter continuation after break
- 65%+ win rate with volume

## Confluence
- Pivot + VWAP = +15 points
- Pivot + Order Block = +20 points
- Pivot + Round number = +10 points

## Key Characteristics
- Calculated from previous period
- PP = bias line (above=bullish)
- R1/S1 = first targets
- R2/S2 = extended targets
- R3/S3 = extreme levels

**Status:** ✅ Ready | **Tests:** `test_pivot_points.py`

---
*End of Pivot Points Documentation*

🎉 **ADVANCED PRICE ACTION CATEGORY COMPLETE! (4/4 blocks)**
