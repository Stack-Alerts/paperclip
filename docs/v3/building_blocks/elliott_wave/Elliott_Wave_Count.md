# Elliott Wave Count Building Block

**Block Number:** 52/66 | **Category:** Elliott Wave | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies and tracks 5-wave impulse patterns and 3-wave corrective patterns based on Elliott Wave Theory.

## Technical Specifications
**Impulse Structure:** 5 waves in trend direction (1-2-3-4-5)  
**Corrective Structure:** 3 waves against trend (A-B-C)  
**File:** `src/detectors/building_blocks/elliott_wave/elliott_wave_count.py`

## Wave Rules
- Wave 2 never retraces more than 100% of Wave 1
- Wave 3 is never the shortest wave (often longest at 161.8% of Wave 1)
- Wave 4 never overlaps with price territory of Wave 1

## Bitcoin Implementation
- Elliott Waves visible during Bitcoin trending phases
- 2017 bull run: Textbook 5-wave impulse to $20k
- 2020-2021: Clear Elliott structure to $64k
- Wave 3 in Bitcoin often shows 200%+ extensions (high volatility)
- Wave 5 exhaustion shows bearish RSI divergence
- ABC corrective waves = accumulation opportunities

## Trading Strategy - Wave 3
- Most profitable wave (highest momentum)
- Enter on Wave 2 completion
- Target: 161.8% extension of Wave 1
- Stop: Below Wave 2 low
- Highest profit potential

## Confluence
- Wave 3 + MACD momentum spike = +30 points
- Wave 5 + RSI divergence = +25 points (exit signal)
- ABC correction + support = +20 points (re-entry)

**Status:** ✅ Ready | **Tests:** `test_elliott_wave.py`
