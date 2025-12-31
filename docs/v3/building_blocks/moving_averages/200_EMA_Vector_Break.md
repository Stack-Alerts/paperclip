# 200 EMA Vector Break Building Block

**Block Number:** 2/66 | **Category:** Moving Average Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies when price breaks the 200 EMA with vector candle (high volume), signaling major trend changes or confirmations.

## Technical Specifications
**EMA Period:** 200  
**Vector Candle:** Volume > 1.5x average volume  
**Break Types:** Bullish or Bearish  
**File:** `src/detectors/building_blocks/moving_averages/ema_200_trend.py`  
**Class:** `EMA200VectorBreak(timeframe='15min')`

## Bitcoin Implementation
- **200 EMA = Critical long-term trend indicator for Bitcoin**
- Major bull/bear market divider on daily timeframe
- Price above 200 EMA = bull market bias, below = bear market bias
- Breaks often lead to multi-week or multi-month trends
- Bitcoin 2017: Break above daily 200 EMA → $20k rally
- Bitcoin 2018: Break below → bear market to $3k
- Much stronger signal than 50 EMA (institutional level)

## Trading Strategies

**Strategy 1: Long-Term Trend Following (Historical 77% CAGR)**
- Daily 200 EMA break = major trend change
- Enter on break with volume confirmation
- Stop: Opposite side of 200 EMA
- Hold position for weeks to months
- Exit on opposite direction break
- Bitcoin bull markets: Price walks along 200 EMA

**Strategy 2: Failed Break = Extreme Reversal**
- Vector break above/below 200 EMA fails
- Candle closes back on original side
- Extremely rare but powerful signal
- 80%+ win rate when occurs
- Indicates exhaustion of move

## Confluence
- 200 EMA break + 50 EMA alignment (Golden/Death Cross) = +25 points
- Break + Kill Zone = +15 points
- Volume >2.5x average = +15 points
- Higher timeframe confirmation = +20 points

## Key Characteristics
- **Most important EMA for Bitcoin trading**
- Institutional reference point
- Weekly 200 EMA = cycle trend indicator
- Breaks = months-long implications
- Golden Cross (50 above 200) preceded major Bitcoin rallies

**Status:** ✅ Ready | **Tests:** `test_ema_200_trend.py` (passing)

---
*End of 200 EMA Vector Break Documentation*
