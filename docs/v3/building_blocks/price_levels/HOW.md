# HOW (High of Week) Building Block

**Block Number:** 11/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies and tracks the highest price reached during current trading week.

## Technical Specifications
**Calculation:** Highest price from Monday 00:00 UTC to current time  
**Week:** Monday 00:00 UTC - Sunday 23:59 UTC  
**File:** `src/detectors/building_blocks/price_levels/how.py`

## Bitcoin Implementation
- Weekly highs/lows more significant than daily for swing trading
- Monday's range (WOR - Weekly Opening Range) often determines weekly bias
- Clear break above HOW on Monday signals strong weekly bullish trend
- Weekend gaps can significantly impact Monday opening
- HOW provides multi-day resistance reference

## Trading Strategies

**Strategy 1: Weekly Breakout**
- HOW break on Monday = strong week ahead signal
- Enter long on break with volume
- Hold position for days
- Target: Next weekly structure level

**Strategy 2: HOW Rejection**
- Multiple tests without breaking = weekly top forming
- Enter short on rejection
- Stop: Above HOW
- Target: Weekly support or LOW

## Confluence
- HOW + Previous week high = +20 points
- HOW + Monthly high = +25 points
- Monday HOW break = +15 points (WOR signal)

**Status:** ✅ Ready | **Tests:** `test_how.py`

---
*End of HOW Documentation*
