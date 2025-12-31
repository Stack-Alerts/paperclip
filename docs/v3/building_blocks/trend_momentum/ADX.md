# ADX (Average Directional Index) Building Block

**Block Number:** 18/66 | **Category:** Trend & Momentum | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Measures trend strength regardless of direction, helping identify trending vs ranging markets.

## Technical Specifications
**ADX:** Based on 14-period smoothed DI+ and DI-
**Values:** 0-100 scale
- **0-25:** Weak or no trend (range/consolidation)
- **25-50:** Strong trend developing
- **50-75:** Very strong trend
- **75-100:** Extremely strong trend (rare)
**File:** `src/detectors/building_blocks/trend_momentum/adx.py`

## Bitcoin Implementation
- ADX >25 on Bitcoin 4hr chart = strong trending phase
- Use for filter: Only trade trend strategies when ADX >25
- ADX <20 = range trading strategies preferred
- Rising ADX = strengthening trend (regardless of direction)
- Falling ADX = weakening trend or consolidation forming

## Trading Strategies

**Strategy 1: Trend Filter**
- ADX >25 = trade trend strategies (BOS, OTE entries)
- ADX <25 = trade range strategies (S/R bounces, mean reversion)
- Risk management: Larger positions in high ADX trends

**Strategy 2: Trend Exhaustion**
- ADX >70 = extreme trend (caution - near exhaustion)
- Wait for ADX peak and decline = reversal signal
- Combine with RSI divergence

## Confluence
- ADX >25 + BOS = +15 points (trend confirmed)
- ADX >50 + Momentum setup = +20 points (very strong)
- ADX <20 = ignore trend setups, focus on range

## Key Characteristics
- Measures strength, not direction
- 14-period standard
- >25 = tradable trend
- <20 = ranging market
- Rising/falling shows strengthening/weakening

**Status:** ✅ Ready | **Tests:** `test_adx.py`

---
*End of ADX Documentation*
