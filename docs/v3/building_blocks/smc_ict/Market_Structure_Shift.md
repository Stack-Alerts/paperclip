# Market Structure Shift (MSS) Building Block

**Block Number:** 27/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies significant market structure changes signaling potential trend reversals when price decisively breaks key structure levels.

## Technical Specifications
**Bullish MSS:** In downtrend, price breaks above most recent lower high → potential reversal
**Bearish MSS:** In uptrend, price breaks below most recent higher low → potential reversal
**File:** `src/detectors/building_blocks/smc_ict/market_structure_shift.py`

## Block Behavior (Continuous + Event Tracking)
This block operates in **DUAL MODE**:
- **Continuous State:** Tracks current market structure (BULLISH/BEARISH reversal state)
- **Event Detection:** Identifies when NEW MSS events occur vs continuing reversal state

**Metadata Fields:**
- `is_new_event`: Boolean - True if MSS just occurred on current bar, False if continuing  
- `bars_since_mss`: Integer - How many bars ago the current MSS occurred
- `mss_timestamp`: Datetime - When the current MSS occurred

**Usage:**
- **Reversal Entry:** Use `is_new_event == True` to enter on fresh MSS (critical timing!)
- **Trend Filter:** Use continuous signal to avoid counter-trend trades
- **Exit Signal:** When opposite `is_new_event == True` (structure reversed again)

**Important:** MSS marks REVERSAL points - new event timing is critical for entries!

## Difference from BOS
- **MSS:** Signals potential REVERSAL
- **BOS:** Signals trend CONTINUATION

## Bitcoin Implementation
- MSS on daily chart = major trend changes (weeks to months)
- 4hr MSS = swing trading signals (days to weeks)
- 15min/1hr MSS = intraday trading
- Bitcoin MSS often occurs during Kill Zones (London/NY open)
- False MSS possible - wait for retest confirmation
- After MSS, previous resistance becomes support (vice versa)

## Trading Strategies

**Strategy 1: MSS Retest Entry (70-75% win rate)**
- Setup: MSS occurs (structure break)
- Wait for pullback to broken structure
- Entry: Retest with rejection confirmation
- Stop: Beyond MSS break point
- Target: Next structure level

**Strategy 2: MSS + Order Block**
- MSS with Order Block at break level
- Highest probability reversal
- 80%+ win rate with OB confluence

## Confluence
- MSS + Order Block = +25 points
- MSS + Liquidity Sweep (precedes MSS) = +20 points
- MSS + FVG at break = +20 points
- MSS + Volume confirmation = +15 points
- Higher timeframe MSS = +15 points per TF

## Key Characteristics
- Decisive break with momentum
- Close beyond structure (not just wick)
- Preferably with volume increase
- Often preceded by liquidity sweep
- Retest provides safer entry

**Status:** ✅ Ready | **Tests:** `test_market_structure_shift.py`

---
*End of Market Structure Shift Documentation*
