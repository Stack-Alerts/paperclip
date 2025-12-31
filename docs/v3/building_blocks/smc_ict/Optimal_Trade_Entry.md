# Optimal Trade Entry (OTE) Building Block

**Block Number:** 26/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Uses Fibonacci 62-79% retracement zone to identify highest probability entry during price pullbacks in trending markets.

## Technical Specifications
**OTE Zone:** 62% to 79% Fibonacci retracement
**Precise OTE:** 70.5% (equilibrium between 62% and 79%)
**File:** `src/detectors/building_blocks/smc_ict/optimal_trade_entry.py`

## ICT Fibonacci Settings
- 0 = First profit target
- 0.5 = Equilibrium  
- 0.618 = Golden zone start (OTE)
- 0.705 = Precise OTE
- 0.786 = Golden zone end (OTE)
- 1.0 = Starting position
- -0.5, -1, -2 = Targets

## Bitcoin Implementation
- Particularly effective during Bitcoin trending phases
- Best on 4hr and daily charts for position trading
- Bitcoin often respects 70.5% precisely in strong trends
- Higher timeframe trend + lower timeframe OTE = optimal
- Entry at OTE provides best risk-to-reward (typically 1:3+)

## Trading Strategies

**Strategy 1: OTE Entry (Bullish - 75-80% win rate)**
- Setup: Confirm uptrend on higher timeframe
- Wait for pullback after BOS
- Apply Fib from swing low to swing high
- Entry: Buy at 70.5% or within 62-79% zone
- Confirm: Bullish OB, FVG, or price rejection
- Stop: Below 100% Fib (swing low)
- Target: Previous high or -0.5 extension

**Strategy 2: OTE + Kill Zone**
- OTE entry during NY AM Kill Zone
- 30-40% higher win rate with timing
- Best confluence available

## Confluence
- OTE + Order Block = +30 points
- OTE + FVG = +25 points
- OTE + Kill Zone = +25 points
- OTE + Discount Zone = +20 points
- Full confluence (all 4) = 100+ points (rare unicorn)

## Key Characteristics
- 62-79% is the "sweet spot"
- 70.5% most precise level
- Works in both directions
- Requires trending market
- Best during Kill Zones

**Status:** ✅ Ready | **Tests:** `test_optimal_trade_entry.py`

---
*End of Optimal Trade Entry Documentation*
