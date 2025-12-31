# 55 EMA Vector Break Building Block

**Block Number:** 3/66 | **Category:** Moving Average Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Alternative to 50 EMA with slight lag advantage, reduces false signals in choppy Bitcoin markets.

## Technical Specifications
**EMA Period:** 55  
**Vector Candle:** Volume > 1.5x average  
**File:** `src/detectors/building_blocks/moving_averages/ema_55_vector.py`

## Bitcoin Implementation
- Less commonly used than 50 EMA but provides slight lag advantage
- Useful for reducing false signals in choppy markets
- Middle ground between 50 EMA (faster) and 200 EMA (slower)
- Fibonacci-based period (55 is Fibonacci number)
- Some institutional traders prefer 55 over 50

## Trading Strategy
- Same as 50 EMA but with ~10% fewer signals
- Fewer false breaks due to slightly slower response
- Best during volatile Bitcoin periods (high ATR)

## Confluence
- 55 EMA + 200 EMA alignment = +20 points
- Less popular = fewer traders = fewer stop hunts

**Status:** ✅ Ready | **Tests:** `test_ema_55_vector.py`

---
*End of 55 EMA Documentation*
