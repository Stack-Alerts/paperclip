# Displacement Building Block

**Block Number:** 30/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies rapid, decisive price movements signaling strong institutional activity and creating Fair Value Gaps.

## Technical Specifications
**Displacement:** Aggressive candle(s) moving price quickly with minimal retracement, creating FVGs
**Characteristics:** Large bodies (2-3x average), minimal wicks, high volume, gaps between candles
**File:** `src/detectors/building_blocks/smc_ict/displacement.py`

## Bitcoin Implementation
- Bitcoin displacement often during Kill Zones (NY AM especially)
- News-driven displacement = strongest follow-through
- Displacement >3% on 15min = highly significant
- After displacement, first pullback to FVG or OB = ideal entry
- Weekend gaps can create false signals
- Strongest on BOS or MSS

## Trading Strategies

**Strategy 1: Displacement + FVG Retest (75-80% win rate)**
- Setup: Displacement creates FVG
- Wait for initial momentum to exhaust
- Entry: Retracement to FVG within displacement
- Stop: Beyond FVG or displacement extreme
- Target: Continuation to next structure

**Strategy 2: Breakout Confirmation**
- Displacement through resistance/support = strong breakout
- Enter on pullback
- Expect continuation

## Confluence
- Displacement + FVG = +25 points
- Displacement + BOS/MSS = +20 points (structure confirmation)
- Displacement + Kill Zone = +15 points
- Displacement + Volume spike (>2x) = +15 points

## Key Characteristics
- 2-3x average candle size
- Minimal wicks (conviction)
- Often gaps (FVG creation)
- High volume
- Institutional order flow

**Status:** ✅ Ready | **Tests:** `test_displacement.py`

---
*End of Displacement Documentation*
