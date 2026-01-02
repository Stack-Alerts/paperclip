# Break of Structure (BOS) Building Block

**Block Number:** 28/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies when price breaks through recent swing highs/lows, confirming trend continuation.

## Technical Specifications
**Bullish BOS:** In uptrend, price breaks above most recent higher high → bullish continuation
**Bearish BOS:** In downtrend, price breaks below most recent lower low → bearish continuation  
**File:** `src/detectors/building_blocks/smc_ict/break_of_structure.py`

## Block Behavior (Continuous + Event Tracking)
This block operates in **DUAL MODE**:
- **Continuous State:** Tracks current market structure (BULLISH/BEARISH/NEUTRAL)
- **Event Detection:** Identifies when NEW BOS events occur vs continuing state

**Metadata Fields:**
- `is_new_event`: Boolean - True if BOS just occurred on current bar, False if continuing
- `bars_since_bos`: Integer - How many bars ago the current BOS occurred
- `bos_timestamp`: Datetime - When the current BOS occurred

**Usage:**
- **Trade Entry:** Use `is_new_event == True` to enter on fresh BOS
- **Position Filter:** Use continuous signal to stay WITH structure
- **Exit Signal:** When `is_new_event == True` in opposite direction


## Difference from MSS/CHoCH
- **BOS:** Confirms CONTINUATION (trend in same direction)
- **MSS/CHoCH:** Signal REVERSAL (trend change)

## Bitcoin Implementation
- Bitcoin BOS on 4hr/daily = strong trending conditions
- Multiple BOS without CHoCH = ride the trend
- After BOS, pullbacks to Order Blocks = re-entry opportunities
- BOS during Kill Zones more reliable
- Series of BOS = very strong trend

## Trading Strategies

**Strategy 1: BOS Continuation (70-75% win rate)**
- Setup: BOS occurs in established trend
- Wait for pullback to Order Block
- Entry: OB retest with confirmation
- Stop: Below OB
- Target: Next structure level

**Strategy 2: Multiple BOS = Momentum**  
- 3+ BOS in row = extremely strong trend
- Trail stops using Order Blocks
- Hold until opposite CHoCH/MSS

## Confluence
- BOS + Order Block pullback = +25 points
- BOS + FVG = +20 points
- BOS + Volume spike = +15 points
- Multiple BOS (3+) = +20 points (momentum)

## Key Characteristics
- Close beyond swing high/low
- Preferably with volume
- In direction of existing trend
- Validates trend strength

**Status:** ✅ Ready | **Tests:** `test_break_of_structure.py`

---
*End of Break of Structure Documentation*
