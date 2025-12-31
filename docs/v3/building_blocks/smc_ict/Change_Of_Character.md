# Change of Character (CHoCH) Building Block

**Block Number:** 29/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Signals potential trend reversal by identifying when market fails to maintain momentum - early warning before MSS.

## Technical Specifications
**Bullish CHoCH:** In downtrend, price breaks above most recent lower high → early bullish reversal signal
**Bearish CHoCH:** In uptrend, price breaks below most recent higher low → early bearish reversal signal
**File:** `src/detectors/building_blocks/smc_ict/change_of_character.py`

## Similar to Quasimodo Pattern
Same concept, different name - both identify character/momentum shift

## Bitcoin Implementation
- CHoCH on Bitcoin daily = major reversals (early warning system)
- Precedes MSS (CHoCH is earlier, MSS confirms)
- Wait for CHoCH + Order Block/FVG retest before entering
- False CHoCH possible - use confluence
- Best on higher timeframes (4hr+)

## Trading Strategies

**Strategy 1: CHoCH + Supply/Demand Retest (70-75% win rate)**
- Setup: CHoCH occurs
- Mark supply/demand zone from recent wave
- Wait for retracement to zone
- Entry: In direction of CHoCH with confirmation
- Stop: Beyond supply/demand zone
- Target: Opposite CHoCH or structure level

**Strategy 2: CHoCH → MSS Confirmation**
- CHoCH = early signal
- Wait for MSS to confirm reversal
- Enter after MSS with tighter stop

## Confluence
- CHoCH + Order Block = +25 points
- CHoCH + FVG = +20 points
- CHoCH + Premium/Discount = +15 points
- CHoCH → MSS = +20 points (confirmation)

## Key Characteristics
- Earlier than MSS
- Less reliable than MSS (needs confirmation)
- Often at supply/demand zones
- Reversal warning signal

**Status:** ✅ Ready | **Tests:** `test_change_of_character.py`

---
*End of Change of Character Documentation*
