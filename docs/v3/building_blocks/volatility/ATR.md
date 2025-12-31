# ATR (Average True Range) Building Block

**Block Number:** 54/66 | **Category:** Volatility | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Measures market volatility by calculating average range between high and low prices over specified period.

## Technical Specifications
**ATR:** Average of True Range over 14 periods (default)
**True Range:** Max of (High-Low, |High-PrevClose|, |Low-PrevClose|)
**File:** `src/detectors/building_blocks/volatility/atr.py`

## Bitcoin Implementation
- Bitcoin ATR on 15min chart typically $100-300 (during 2024)
- Use for position sizing: Higher ATR = smaller position
- Stop-loss placement: 1.5-2x ATR from entry
- ATR expansion = volatility increasing (trending or news)
- ATR contraction = volatility decreasing (consolidation)

## Trading Strategies

**Strategy 1: Stop-Loss Placement**
- Buy Bitcoin at $50,000, ATR = $200
- Stop-loss: Entry - (2 × ATR) = $50,000 - $400 = $49,600
- Accounts for normal volatility

**Strategy 2: Position Sizing**
- High ATR (>$300) = reduce position 50%
- Low ATR (<$150) = can use larger position
- Risk management based on volatility

## Confluence
- ATR expansion + Breakout = +15 points (volatility confirms)
- ATR contraction + Range trading = +10 points

## Key Characteristics
- 14-period standard
- Higher ATR = higher volatility
- Use for stop-loss placement
- Position sizing tool
- Expansion/contraction signals

**Status:** ✅ Ready | **Tests:** `test_atr.py`

---
*End of ATR Documentation*
