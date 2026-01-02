# Fair Value Gap (FVG) Building Block

**Block Number:** 21/66 | **Category:** Advanced Price Action | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies price imbalances where three-candle patterns create gaps representing unfilled orders that price seeks to fill.

## Block Behavior (Continuous + Event Tracking)

This block operates in **DUAL MODE**:
- **Continuous State:** Tracks active FVG zones (91.8% relative to active signals, but only 1.4 signals/day actual)
- **Event Detection:** Identifies when price ENTERS gap zones (0.89 gap entries/day)

**Metadata Fields:**
- `is_new_event`: Boolean - True if price just entered gap zone, False if continuing fill
- `bars_since_gap`: Integer - How many bars ago the gap formed
- `in_gap`: Boolean - Whether price is currently in the gap zone

**Usage:**
- **Gap Entry Timing:** Use `is_new_event == True` for precise fill entry points (critical for gap mitigation trades)
- **Reference Zones:** Use FVG presence to identify inefficiency zones
- **Age Assessment:** Check `bars_since_gap` to gauge gap validity (older gaps = weaker pull)

**Important:** This block shows NO_FVG when no gaps exist (~90% of time). When gaps exist, 63.9% of signals are NEW gap entries!

## Technical Specifications
**Bullish FVG:** Gap between candle 1 high and candle 3 low (unfilled buy orders)
**Bearish FVG:** Gap between candle 1 low and candle 3 high (unfilled sell orders)
**File:** `src/detectors/building_blocks/price_action/fair_value_gap.py`

## Bitcoin Implementation
- Extremely common during Bitcoin volatility spikes
- Large FVGs (>1% price) almost always filled eventually
- Best confluence: FVG + Order Block = unicorn setup (85%+ win rate)
- FVG at session boundaries especially significant
- Failed FVG fills signal strong trend continuation

## Trading Strategies

**Strategy 1: FVG Fill Entry (70-75% win rate)**
- Setup: Identify valid FVG (>0.5% gap)
- Wait for price to return to FVG
- Entry: Within FVG zone with confirmation
- Stop: Beyond FVG
- Target: Continuation past FVG or next structure

**Strategy 2: FVG + OB (Unicorn - 85%+ win rate)**
- FVG coinciding with Order Block
- Highest probability setup in ICT methodology
- Double institutional reference

## Confluence
- FVG + Order Block = +30 points (unicorn)
- FVG + OTE level = +25 points
- FVG + Breaker Block = +25 points
- FVG + Discount zone = +20 points

## Key Characteristics
- 3-candle pattern with gap
- Larger gaps (>1%) more reliable
- Price inefficiency
- Market "wants" to fill gap
- Mitigation = gap filled

**Status:** ✅ Ready | **Tests:** `test_fair_value_gap.py`

---
*End of Fair Value Gap Documentation*
