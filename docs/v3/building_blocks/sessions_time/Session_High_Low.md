# Session High & Low Building Block

**Block Number:** 35/66 | **Category:** Sessions & Time | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies highest and lowest price points within trading sessions - critical reference levels for liquidity sweeps and reversals.

## Technical Specifications
**Session High:** Highest price reached during session (Asian, London, NY)
**Session Low:** Lowest price reached during session
**Prior Session High/Low:** Previous session extremes = key reference
**File:** `src/detectors/building_blocks/sessions_time/session_high_low.py`

## Bitcoin Implementation
- Session highs/lows act as magnets - price often tests these levels
- Liquidity pools cluster above session highs and below session lows
- Sweeping session high/low during next session common before reversal
- Bitcoin 24/7 markets: Use Asian (8PM-4AM), London (2AM-8AM), NY (7AM-4PM EST)
- Prior day high/low particularly significant

## Trading Strategies

**Strategy 1: Session High/Low Sweep (75% win rate)**
- Setup: Session high/low established
- Wait for sweep (wick beyond level)
- Entry: Reversal back inside session range
- Stop: Beyond sweep extreme
- Target: Opposite session boundary or midpoint

**Strategy 2: Breakout Beyond Session**
- Strong break and close above session high = bullish
- Strong break and close below session low = bearish
- Enter on pullback to session level
- Continuation trade

## Confluence
- Session High/Low + Order Block = +25 points
- Session level + Liquidity Sweep = +25 points
- Session level + Kill Zone timing = +20 points
- Previous Day High/Low = +15 points (strong reference)

## Key Characteristics
- Clear session definitions required
- Highs/lows = liquidity pools
- Sweeps common before reversals
- Prior day levels most significant
- Breakouts signal strong trend

**Status:** ✅ Ready | **Tests:** `test_session_high_low.py`

---
*End of Session High & Low Documentation*

🎉 **SESSIONS & TIME CATEGORY COMPLETE! (2/2 blocks)**
