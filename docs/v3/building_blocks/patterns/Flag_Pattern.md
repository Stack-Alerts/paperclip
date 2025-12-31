# Flag Pattern Building Block

**Block Number:** 43/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Short-term continuation pattern with sharp "flagpole" move followed by parallel channel consolidation (the "flag").

## Technical Specifications
**Flagpole:** Strong, near-vertical price move (10-30%+ in Bitcoin)  
**Flag:** Parallel channel consolidation counter to flagpole direction  
**File:** `src/detectors/building_blocks/patterns/flag_pattern.py`

## Bitcoin Implementation
- Extremely reliable short-term continuation (70-80% win rate)
- Common in parabolic Bitcoin rallies (bullish flags) and crashes (bearish flags)
- Flagpole forms during FOMO buying or panic selling
- Flag duration: 5-15 days on daily charts
- Target: Flagpole height added/subtracted from breakout

## Trading Strategy - Bullish Flag
- Identify upward flagpole with high volume
- Wait for downward/sideways flag on declining volume
- Entry: Breakout above flag upper boundary
- Stop: Below flag lower boundary
- Target: Flagpole height added to breakout (70-80% target hit)

## Confluence
- Flag + Kill Zone breakout = +20 points
- Strong flagpole (>15%) = +15 points

**Status:** ✅ Ready | **Tests:** `test_flag_pattern.py`
