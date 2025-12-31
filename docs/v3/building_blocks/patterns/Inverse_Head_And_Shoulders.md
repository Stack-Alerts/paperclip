# Inverse Head and Shoulders Pattern Building Block

**Block Number:** 35/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bullish reversal pattern (mirror of H&S) with three troughs: left shoulder, head (lowest), right shoulder, with neckline resistance.

## Technical Specifications
**Components:** Left Shoulder + Head (lowest) + Right Shoulder + Neckline  
**Confirmation:** Break above neckline with volume  
**File:** `src/detectors/building_blocks/patterns/inverse_head_and_shoulders.py`

## Bitcoin Implementation
- Extremely reliable bullish reversal (86% success rate - altFINS study)
- Forms after significant Bitcoin downtrends (accumulation bottoms)
- Pattern duration: 2-6 months on daily charts
- Common at cycle bottoms ($3k 2018, $29k 2021)
- Volume spike on breakout essential (>2x average)

## Trading Strategy
- Entry: LONG on neckline breakout or retest
- Stop: Below right shoulder low
- Target: Measured move (head-to-neckline distance added to breakout)
- Risk-Reward: 1:2 to 1:4

## Confluence
- Inverse H&S + bullish divergence = +30 points
- Pattern at support = +20 points

**Status:** ✅ Ready | **Tests:** `test_inverse_head_and_shoulders.py`

---
*End of Inverse Head and Shoulders Documentation*
