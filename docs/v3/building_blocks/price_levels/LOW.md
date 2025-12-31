# LOW (Low of Week) Building Block

**Block Number:** 12/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies and tracks the lowest price reached during current trading week.

## Technical Specifications
**Calculation:** Lowest price from Monday 00:00 UTC to current time  
**Week:** Monday 00:00 UTC - Sunday 23:59 UTC  
**File:** `src/detectors/building_blocks/price_levels/low.py`

## Bitcoin Implementation
- Weekly lows provide strong support zones for swing entries
- Breakdown below LOW often signals weekly bearish trend
- Multiple tests without breaking = strong support
- Weekend price action can create artificial lows during thin liquidity
- Monday's WOR (Weekly Opening Range) critical for direction

## Trading Strategies

**Strategy 1: Weekly Support Bounce**
- Wait for LOW test
- Enter long on bounce with confirmation
- Stop: Below LOW
- Target: HOW or weekly midpoint

**Strategy 2: LOW Breakdown**
- Price breaks below LOW with volume
- Enter short on breakdown
- Stop: Above LOW
- Target: Previous week LOW or lower structure

## Confluence
- LOW + Previous week low = +20 points
- LOW + Monthly low = +25 points
- LOW + Demand Zone = +25 points
- Multiple tests without break = +15 points

**Status:** ✅ Ready | **Tests:** `test_low.py`

---
*End of LOW Documentation*
