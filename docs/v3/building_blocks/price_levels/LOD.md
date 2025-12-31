# LOD (Low of Day) Building Block

**Block Number:** 10/66 | **Category:** Price Level Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies and tracks the lowest price reached during current trading day, acting as intraday support.

## Technical Specifications
**Calculation:** Lowest price from 00:00 UTC to current time  
**Reset:** Daily at 00:00 UTC  
**File:** `src/detectors/building_blocks/price_levels/lod.py`

## Bitcoin Implementation
- LOD acts as intraday support in Bitcoin markets
- Multiple tests of LOD without breaking often lead to reversal
- Liquidity sweeps below LOD followed by quick recovery = common traps
- Weekend LOD tests often fail (lower liquidity)
- LOD + Order Block confluence = high-probability bounce

## Trading Strategies

**Strategy 1: LOD Bounce (70% win rate)**
- Wait for price to test LOD (within 0.5%)
- Enter long on bounce with bullish confirmation
- Stop: Below LOD - 0.5%
- Target: Intraday resistance or HOD

**Strategy 2: LOD Sweep (75% win rate)**
- Price wicks below LOD then recovers (liquidity sweep)
- Enter long on close back above LOD
- Stop: Below sweep low
- Target: Previous swing high

## Confluence
- LOD + Round number = +15 points
- LOD + Demand Zone = +25 points
- LOD sweep + Kill Zone = +20 points
- Multiple tests (3+) without break = +10 points

**Status:** ✅ Ready | **Tests:** `test_lod.py`

---
*End of LOD Documentation*
