# 50 EMA Vector Break Building Block

**Block Number:** 1/66 | **Category:** Moving Average Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies when price breaks the 50 EMA with high-volume candle (vector candle), signaling potential trend changes or continuations.

## Technical Specifications
**EMA Period:** 50  
**Vector Candle:** Volume > 1.5x average volume  
**Break Types:** Bullish (price crosses above from below) or Bearish (price crosses below from above)  
**File:** `src/detectors/building_blocks/moving_averages/ema_50_vector.py`  
**Class:** `EMA50VectorBreak(timeframe='15min')`

## Return Format
```python
{
    'signal': 'BULLISH_BREAK' | 'BEARISH_BREAK' | 'NO_BREAK',
    'confidence': 65-80,
    'metadata': {
        'ema_value': float,
        'volume_ratio': float,
        'break_count': int,
        'candle_close': float
    },
    'timestamp': datetime,
    'timeframe': str,
    'confluence_factors': list
}
```

## Bitcoin Implementation
- Bitcoin respects 50 EMA on 4hr and daily timeframes
- During bull markets, 50 EMA acts as dynamic support
- Vector breaks with 2x volume have 65%+ follow-through rate
- Multiple breaks before candle close = indecision (lower reliability)
- Combine with higher timeframe 200 EMA for directional bias

## Trading Strategies

**Strategy 1: Vector Break Continuation (65-70% win rate)**
- Setup: Trend established (price above/below 50 EMA for 10+ candles)
- Entry: Vector break in trend direction
- Stop: Opposite side of 50 EMA
- Target: Next structure level or 1.5x ATR

**Strategy 2: Failed Break = Reversal**
- Vector break occurs but candle closes back on original side
- Failed break signals strong opposition
- Enter opposite direction
- Higher win rate (70-75%) as trap gets reversed

## Confluence
- Vector Break + 200 EMA alignment = +20 points
- Vector Break + Kill Zone timing = +15 points
- Volume >2x average = +10 points
- Higher timeframe EMA agreement = +15 points

## Key Characteristics
- 50 EMA = medium-term trend reference
- Vector candle confirms institutional participation
- Single clean break more reliable than multiple touches
- Best on 4hr and daily Bitcoin charts
- Failed breaks = powerful reversal signals

**Status:** ✅ Ready | **Tests:** `test_ema_50_vector.py` (passing)

---
*End of 50 EMA Vector Break Documentation*
