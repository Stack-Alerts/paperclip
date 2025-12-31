# Head and Shoulders Pattern Building Block

**Block Number:** 34/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bearish reversal pattern with three peaks: left shoulder, head (highest), right shoulder, with neckline support.

## Technical Specifications
**Components:** Left Shoulder + Head + Right Shoulder + Neckline  
**Confirmation:** Break below neckline with volume  
**File:** `src/detectors/building_blocks/patterns/head_and_shoulders.py`

## Bitcoin Implementation
- One of most reliable Bitcoin reversal patterns (75-82% success rate)
- Pattern formation typically 3-8 weeks on daily charts
- Often forms at cycle tops ($20k 2017, $64k 2021)
- Volume declining at right shoulder = distribution signal
- Neckline becomes resistance after break

## Trading Strategy
- Entry: SHORT on neckline break with volume >1.5x average
- Stop: Above right shoulder high
- Target: Measured move (head-to-neckline distance)
- Risk-Reward: 1:2 to 1:3

## Confluence
- H&S + RSI bearish divergence = +25 points
- Pattern at resistance = +15 points

**Status:** ✅ Ready | **Tests:** `test_head_and_shoulders.py`

---
*End of Head and Shoulders Documentation*
