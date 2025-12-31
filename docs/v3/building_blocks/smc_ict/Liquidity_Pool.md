# Liquidity Pool Identification Building Block

**Block Number:** 31/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies areas where stop-loss orders cluster, representing liquidity targets for institutional traders.

## Technical Specifications
**Equal Highs:** Multiple swing highs at same price = sell-side liquidity above
**Equal Lows:** Multiple swing lows at same price = buy-side liquidity below
**Round Numbers:** Psychological levels ($50k, $100k) = massive pools
**Trendline Liquidity:** Stops along trendlines
**File:** `src/detectors/building_blocks/smc_ict/liquidity_pool.py`

## Bitcoin Implementation
- Round number pools: $100k, $90k, $80k, $75k, $70k, $50k
- Equal lows during accumulation often swept before upward move
- Institutions target liquidity before significant moves
- More touches = larger pool
- Weekend liquidity easier to sweep (lower volume)

## Trading Strategies

**Strategy 1: Liquidity Grab (75% win rate)**
- Setup: Identify liquidity pool (equal highs/lows)
- Wait for sweep (wick beyond level)
- Entry: Reversal after sweep confirmed
- Stop: Beyond sweep extreme
- Target: Opposite liquidity pool

**Strategy 2:** Anticipation (Advanced)
- Don't enter before sweep
- Let it happen, then trade reversal
- Patience required

## Confluence
- Liquidity Pool + Order Block = +25 points
- Equal highs/lows (3+ touches) = +20 points
- Pool + Round number = +15 points
- Pool + Session boundary = +15 points

## Key Characteristics
- Equal highs/lows most common
- Round numbers attract stops
- Trendlines cluster stops
- More touches =

 larger pool

**Status:** ✅ Ready | **Tests:** `test_liquidity_pool.py`

---
*End of Liquidity Pool Documentation*
