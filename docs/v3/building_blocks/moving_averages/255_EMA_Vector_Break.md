# 255 EMA Vector Break Building Block

**Block Number:** 4/66 | **Category:** Moving Average Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Approximately 1-year moving average on daily charts, identifies very long-term trend shifts.

## Technical Specifications
**EMA Period:** 255 (~1 year on daily)  
**Vector Candle:** Volume > 1.5x average  
**File:** `src/detectors/building_blocks/moving_averages/ema_255_vector.py`

## Bitcoin Implementation
- Approximately 1-year moving average on daily charts
- Identifies macro Bitcoin cycle trends
- Less noise than 200 EMA but slower to react
- Used for multi-month position trading
- Bitcoin above weekly 255 EMA = strong bull cycle

## Trading Strategy
- Position trading (months-long holds)
- Enter on vector break with volume
- Rarely breaks - highly significant when it does
- Best for identifying Bitcoin cycle tops/bottoms

## Confluence
- 255 EMA + 200 EMA both broken = +30 points (extreme trend)
- Weekly 255 EMA break = +20 points (cycle change)

**Status:** ✅ Ready | **Tests:** `test_ema_255_vector.py`

---
*End of 255 EMA Documentation*
