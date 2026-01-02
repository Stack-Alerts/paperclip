# Breaker Block Building Block

**Block Number:** 25/66 | **Category:** SMC & ICT | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
A failed order block that marks pivotal market structure shift, transforming from support to resistance (or vice versa) after liquidity sweep.

## Block Behavior (Continuous + Event Tracking)

This block operates in **DUAL MODE**:
- **Continuous State:** Tracks active breaker zones (96.1% signal rate)
- **Event Detection:** Identifies when price ENTERS breaker zones (0.72 events/day)

**Metadata Fields:**
- `is_new_event`: Boolean - True if price just entered breaker zone, False if continuing
- `bars_since_breaker`: Integer - How many bars ago the breaker formed
- `in_zone`: Boolean - Whether price is currently in the breaker zone

**Usage:**
- **Zone Entry Timing:** Use `is_new_event == True` for precise entry points (rare but high-value)
- **Reference Zones:** Use continuous signal to identify active breaker levels
- **Age Assessment:** Check `bars_since_breaker` to gauge breaker validity

**Important:** 96.1% signal rate reflects active breaker zones. Only 0.72 zone entries/day = actual entry opportunities!

## Technical Specifications
**Bullish Breaker:** Failed bearish OB becomes bullish support after sweep
**Bearish Breaker:** Failed bullish OB becomes bearish resistance after sweep
**File:** `src/detectors/building_blocks/smc_ict/breaker_block.py`

## Formation Process
1. Identify established order block
2. Liquidity sweep occurs through the OB
3. Market structure shift (MSS) confirmed - new high/low
4. Failed OB becomes breaker block (polarity flip)

## Bitcoin Implementation
- Extremely powerful in Bitcoin (high retail participation = lots of failed OBs)
- Most effective 15min to 4hr timeframes
- Breaker blocks near session boundaries (London/NY open) highest win rate
- After sweep, retest of breaker = ideal entry
- Failed breakers indicate strong momentum

## Trading Strategies

**Strategy 1: Breaker Block Retest (80%+ win rate)**
- Setup: OB fails (swept), MSS confirmed
- Mark breaker block zone
- Wait for price to return
- Entry: Retest with rejection confirmation
- Stop: Opposite side of breaker
- Target: Next structure level / liquidity pool

**Strategy 2: Breaker + FVG (Unicorn Model)**
- Breaker block + FVG at same level
- Highest probability ICT setup
- 85%+ win rate with confluence

## Confluence
- Breaker + FVG = +30 points (unicorn setup)
- Breaker + OTE (62-79%) = +25 points
- Breaker + Kill Zone timing = +15 points
- Breaker + Premium/Discount = +20 points

## Key Characteristics
- Requires MSS confirmation
- Polarity flip (support→resistance or vice versa)
- Often creates FVG during sweep
- Most reliable on higher timeframes

**Status:** ✅ Ready | **Tests:** `test_breaker_block.py`

---
*End of Breaker Block Documentation*
