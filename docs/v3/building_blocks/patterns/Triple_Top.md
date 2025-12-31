# Triple Top Pattern Building Block

**Block Number:** 38/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Strong bearish reversal pattern with three peaks at approximately same resistance level - extension of double top.

## Technical Specifications
**Components:** Three peaks + Neckline  
**File:** `src/detectors/building_blocks/patterns/triple_top.py`

## Bitcoin Implementation
- Rarer than double top, more reliable when forms (75-79% success rate)
- Often at major Bitcoin resistance zones ($60k, $70k regions)
- Third peak rejection = strong seller control
- Pattern spans 4-8 weeks on daily charts
- Volume declining at each peak confirms distribution

## Trading Strategy
- Entry: SHORT on neckline break with volume
- Stop: Above highest peak + 2-3%
- Target: Measured move (peak height to neckline)
- Risk-Reward: 1:2 to 1:3

## Confluence
- Triple Top + bearish divergence on all three peaks = +30 points
- Pattern at major resistance = +20 points

**Status:** ✅ Ready | **Tests:** `test_triple_top.py`
