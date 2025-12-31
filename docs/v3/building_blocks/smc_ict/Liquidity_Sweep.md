# Liquidity Sweep / Stop Hunt Building Block

**Block Number:** 24/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies when smart money deliberately triggers stop-loss clusters to create liquidity for large positions before reversing direction.

## Technical Specifications
**Bullish Sweep:** Price spikes below support/swing low, triggers stops, quickly reverses upward
**Bearish Sweep:** Price spikes above resistance/swing high, triggers stops, quickly reverses downward
**File:** `src/detectors/building_blocks/smc_ict/liquidity_sweep.py`

## Bitcoin Implementation
- Extremely common in 24/7 Bitcoin markets
- Most frequent during low liquidity (Asian session, weekends, session gaps)
- Stop clusters typically 5-10 pips below support or above resistance
- Institutions sweep liquidity before major directional moves
- Common at HOD/LOD, round numbers ($50k, $60k, $100k)

## Trading Strategies

**Strategy 1: Sweep Reversal (75-80% win rate)**
- Setup: Identify obvious swing high/low with stops
- Wait for wick beyond level + quick reversal
- Entry: Close back inside range = sweep confirmed
- Stop: Beyond sweep extreme + buffer
- Target: Opposite liquidity pool / range opposite

**Strategy 2: Failed Sweep = Strong Trend**
- If sweep doesn't reverse = extremely strong trend
- Enter continuation in sweep direction
- Institutional flow overwhelming

## Confluence
-Sweep + Order Block = +25 points (institutional accumulation)
- Sweep + FVG = +20 points
- Sweep + Premium/Discount zone = +20 points
- Sweep during Kill Zone = +15 points

## Key Characteristics
- Sharp move beyond key level (1-3%)
- Low volume on break, high volume on reversal
- 1-2 candle reversal (quick)
- At obvious technical levels

**Status:** ✅ Ready | **Tests:** `test_liquidity_sweep.py`

---
*End of Liquidity Sweep Documentation*
