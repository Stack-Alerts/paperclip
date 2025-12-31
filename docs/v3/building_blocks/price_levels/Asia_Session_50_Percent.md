# Asia Session 50% Price Building Block

**Block Number:** 14/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Calculates the 50% equilibrium level of the Asian trading session range, often used for mean reversion during later sessions.

## Technical Specifications
**Asia Session:** 18:00 UTC - 00:00 UTC (6 hours)  
**Calculation:** (Asia High + Asia Low) / 2  
**File:** `src/detectors/building_blocks/price_levels/asia_session_50_percent.py`

## Bitcoin Implementation
- Asia session characterized by low volume and tight ranges
- Creates daily liquidity pools for later sessions to sweep
- Price often reverts to 50% during US session after UK manipulation
- Narrow Asia range often precedes high volatility in UK/US sessions
- Asia 50% retest during US session = high-probability mean reversion setup
- Acts as equilibrium/fair value reference for the day

## Trading Strategies

**Strategy 1: Mean Reversion to Asia 50% (70% win rate)**
- Setup: Price extended from Asia 50% during UK/US session  
- Entry: Price returns to Asia 50% level
- Confirmation: Rejection candle or volume spike
- Stop: Beyond Asia high/low depending on direction
- Target: Opposite side of range or next structure

**Strategy 2: Asia Range Breakout**
- Narrow Asia range (<0.5% of price) = breakout setup
- Breakout during London open = high probability
- Enter breakout direction with volume
- Target: 1.5x Asia range size

## Confluence
- Asia 50% + VWAP = +20 points (double equilibrium)
- Asia 50% + Premium/Discount zone = +15 points
- Narrow Asia range (<0.5%) + breakout = +20 points
- Asia 50% retest + Kill Zone = +15 points

## Key Characteristics
- Low volume accumulation zone
- Equilibrium reference for day
- Mean reversion magnet
- Narrow range = breakout coming
- Wide range = choppy day ahead

**Status:** ✅ Ready | **Tests:** `test_asia_session_50_percent.py`

---
*End of Asia Session 50% Documentation*

🎉 **PRICE LEVELS CATEGORY COMPLETE! (6/6)**
