# US Settlement Price Building Block

**Block Number:** 13/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Tracks Bitcoin price at US market close (4:00 PM EST / 21:00 UTC), which sets daily candle close and affects CME futures/ETF pricing.

## Technical Specifications
**Settlement Time:** 16:00 EST (21:00 UTC)  
**Settlement Range:** 16:00-17:00 EST for averaging  
**File:** `src/detectors/building_blocks/price_levels/us_settlement.py`

## Bitcoin Implementation
- Bitcoin often shows increased volatility around US market close
- CME Bitcoin futures settle at 16:00 EST, impacting spot price
- Bitcoin ETF NAV calculated based on 16:00 EST prices
- Institutional flows often concentrate near settlement time
- Post-settlement (17:00-18:00 EST) often shows low liquidity "dead zone"
- Settlement price becomes reference point for next day's trading

## Trading Strategies

**Strategy 1: Pre-Settlement Positioning**
- Identify trend approaching settlement (15:30-16:00 EST)
- Enter in direction of settlement push
- Exit at settlement or shortly after
- Scalp 0.3-0.5% moves

**Strategy 2: Post-Settlement Mean Reversion**
- Wait for settlement volatility to subside
- Price often reverts to pre-settlement levels
- Enter counter-move 17:00-18:00 EST
- Target return to pre-settlement price

## Confluence
- Settlement + Round number = +15 points
- Settlement + Kill Zone end = +10 points
- Large settlement move (>1%) = next day volatility signal

## Key Characteristics
- Daily reference point for institutions
- Affects Bitcoin derivatives pricing
- Volatility spike common 15:45-16:15 EST
- 17:00-18:00 EST = low liquidity window

**Status:** ✅ Ready | **Tests:** `test_us_settlement.py`

---
*End of US Settlement Documentation*
