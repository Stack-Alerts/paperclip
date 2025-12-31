# Diamond Pattern Building Block

**Block Number:** 49/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Rare reversal pattern with expanding then contracting price action forming diamond shape.

## Technical Specifications
**Diamond Top (Bearish):** At market top after uptrend  
**Diamond Bottom (Bullish):** At market bottom after downtrend  
**Structure:** Four trendlines form diamond/rhombus shape  
**File:** `src/detectors/building_blocks/patterns/diamond_pattern.py` (Note: Implemented in test_final_blocks.py)

## Formation

**Left Side - Expansion:**
- Higher highs and lower lows (broadening)
- Upper resistance line rising
- Lower support line declining

**Right Side - Contraction:**
- Lower highs and higher lows (narrowing)
- Upper resistance line declining
- Lower support line rising

## Bitcoin Implementation
- Rare in Bitcoin but highly significant when properly formed
- Diamond tops occasionally appear at Bitcoin cycle peaks
- Pattern reflects extreme volatility followed by consolidation
- Requires manual identification - difficult to automate
- Volume erratic during formation confirms indecision
- Target: Widest part of diamond projected from break
- Best on weekly/monthly Bitcoin charts at major turning points

## Trading Strategy - Diamond Top
- Identify broadening formation (left side)
- Confirm contraction phase (right side forming)
- Entry: SHORT on confirmed breakdown with volume spike
- Stop: Above highest point of diamond
- Target: Diamond width subtracted from breakdown
- Risk-Reward: Wide stops require careful position sizing

## Confluence
- Diamond + volume confirmation = +25 points
- Pattern at major turning point = +20 points
- Multiple timeframe confirmation = +15 points

**Status:** ✅ Ready | **Tests:** `test_final_blocks.py`
