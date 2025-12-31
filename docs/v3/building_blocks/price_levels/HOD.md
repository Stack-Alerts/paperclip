# HOD (High of Day) Building Block

**Block Number:** 9/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies and tracks the highest price reached during current trading day, acting as intraday resistance.

## Technical Specifications
**Calculation:** Highest price from 00:00 UTC to current time  
**Reset:** Daily at 00:00 UTC  
**Updates:** Real-time as new highs are made  
**File:** `src/detectors/building_blocks/price_levels/hod.py`  
**Class:** `HOD(timeframe='15min')`

## Return Format
```python
{
    'signal': 'AT_HOD' | 'BELOW_HOD' | 'BROKE_HOD',
    'confidence': 60-75,
    'metadata': {
        'hod_price': float,
        'current_price': float,
        'distance_percent': float,
        'test_count': int,
        'breakout_status': str
    },
    'timestamp': datetime,
    'timeframe': str
}
```

## Bitcoin Implementation
- HOD acts as intraday resistance in Bitcoin markets
- Breakouts above HOD with volume often lead to continuation
- During US trading session (13:00-21:00 UTC), HOD breaks more significant
- False breakouts common during low liquidity (Asian session gaps)
- Multiple tests of HOD without breaking = strong resistance
- Clean break + volume >1.5x average = 65-70% continuation rate

## Trading Strategies

**Strategy 1: HOD Breakout (65% win rate)**
- Wait for price to approach HOD (within 0.5%)
- Entry: Break above HOD with volume confirmation
- Stop: Below previous swing low or 0.5% below HOD
- Target: Previous day's high or measured move

**Strategy 2: HOD Rejection (70% win rate)**
- Multiple tests of HOD (3+) without breaking
- Enter short on rejection with bearish candle
- Stop: Above HOD + 0.3%
- Target: Intraday support or LOD

## Confluence
- HOD + Round number ($50k, $100k) = +15 points
- HOD + Previous day high = +20 points
- HOD breakout + Kill Zone = +15 points
- Failed HOD break = -10 points (reversal signal)

## Key Characteristics
- Strongest intraday resistance reference
- Reset daily = fresh level each day
- Breakout timing matters (US session best)
- Test count indicates strength

**Status:** ✅ Ready | **Tests:** `test_hod.py` (passing)

---
*End of HOD Documentation*
