# Order Block Building Block

**Block Number:** 20/66 | **Category:** Advanced Price Action | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies consolidation zones where institutions placed large orders before major moves - represents institutional accumulation/distribution.

## Technical Specifications
**Bullish Order Block:** Last bearish candle before bullish impulse move (accumulation zone)
**Bearish Order Block:** Last bullish candle before bearish impulse move (distribution zone)
**File:** `src/detectors/building_blocks/price_action/order_block.py`

## Bitcoin Implementation
- Particularly effective on Bitcoin 15min-4hr timeframes
- Valid OBs provide high-probability entry zones (70%+ reaction rate)
- OBs near swing highs/lows most significant
- Fresh (untested) OBs most reliable
- Priority: OBs take precedence over FVGs

## Trading Strategies

**Strategy 1: OB Retest Entry (70%+ win rate)**
- Setup: Identify OB before impulse move
- Wait for price to return to OB
- Entry: At OB with confirmation (engulfing, pin bar)
- Stop: Beyond OB
- Target: Previous high/low or next structure

**Strategy 2: OB + FVG (Unicorn Model - 85%+ win rate)**
- OB coinciding with FVG
- Highest probability ICT setup
- Double institutional confluence

## Confluence
- OB + FVG = +30 points (unicorn setup)
- OB + OTE (62-79%) = +25 points
- OB + Discount/Premium zone = +20 points
- OB + Kill Zone timing = +15 points

## Key Characteristics
- Last opposite candle before impulse
- At swing lows (bullish) or highs (bearish)
- Represents institutional positioning
- High reaction rate on retest
- Fresh OBs most powerful

**Status:** ✅ Ready | **Tests:** `test_order_block.py`

---
*End of Order Block Documentation*
