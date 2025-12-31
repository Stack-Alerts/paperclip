# Double Top Pattern Building Block

**Block Number:** 36/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bearish reversal pattern with two peaks at approximately same price level separated by trough (M-shaped).

## Technical Specifications
**Components:** Two peaks + Valley (neckline)  
**Confirmation:** Close below neckline  
**File:** `src/detectors/building_blocks/patterns/double_top.py`

## Bitcoin Implementation
- Common at Bitcoin resistance zones and round numbers ($10k, $20k, $50k, $100k)
- Second peak often 2-5% below first peak (doesn't need to be exact)
- Declining volume at second peak = distribution signal
- Pattern takes 1-4 weeks to form
- Target achievement rate: ~65-70% in crypto markets

## Trading Strategy
- Entry: SHORT after neckline break and close below
- Stop: Above second peak high + 1-2%
- Target: Measured move (peak-to-neckline distance projected downward)
- Partial profits at 50% of target

## Confluence
- Double Top + RSI overbought = +20 points
- Pattern at resistance = +15 points
- Volume divergence (lower on peak 2) = +10 points

**Status:** ✅ Ready | **Tests:** `test_double_top.py`

---
*End of Double Top Documentation*
