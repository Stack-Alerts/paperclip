# Harmonic Patterns Building Block

**Block Number:** 50/66 | **Category:** Harmonic Patterns | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Advanced 5-point patterns (X-A-B-C-D) based on specific Fibonacci ratios, signaling high-probability reversals.

## Technical Specifications
**5-Point Structure:** X (origin) → A (impulse) → B (retracement) → C (impulse) → D (completion/reversal)  
**File:** `src/detectors/building_blocks/patterns/harmonic_patterns.py` (Note: Implemented in test_final_blocks.py)

## Four Main Patterns

**1. Gartley Pattern (Most Common)**
- B retracement: 61.8% of XA
- D: 78.6% retracement of XA
- CD: 127-161.8% extension of AB
- Most frequent harmonic pattern

**2. Butterfly Pattern**
- B retracement: 78.6% of XA
- D: 127% or 161.8% extension of XA (beyond X)
- CD: 161.8-261.8% extension of BC
- D point extends past X point

**3. Bat Pattern**
- B retracement: 38.2-50% of XA
- D: 88.6% retracement of XA
- CD: 161.8-261.8% extension of BC
- Tighter pattern with shallow B

**4. Crab Pattern**
- B retracement: 38.2-61.8% of XA
- D: 161.8% extension of XA (deepest extension)
- CD: 224-361.8% extension of BC
- Deepest extension pattern

## Bitcoin Implementation
- Research shows 80-90% accuracy (LiteFinance, FxGroundworks)
- Highly effective on Bitcoin 4hr and daily charts
- Butterfly pattern common at Bitcoin cycle tops (reversal signal)
- Gartley most frequent in Bitcoin trending markets
- D point (PCZ - Pattern Completion Zone) provides precise entry with tight stops
- Combine with RSI divergence at D point for confirmation

## Trading Strategy - Gartley Bullish
1. Identify X, A, B points forming
2. Validate B is 61.8% of XA
3. Wait for C and D to complete pattern
4. Entry: LONG at D point (78.6% of XA)
5. Stop: Below D (or X point for conservative)
6. TP1: A point level
7. TP2: 61.8% retracement of AD

## Confluence
- Harmonic Pattern + RSI divergence at D = +35 points
- Pattern completion at support/resistance = +25 points
- Multiple timeframe confirmation = +20 points

**Status:** ✅ Ready | **Tests:** `test_final_blocks.py`

---
*End of Harmonic Patterns Documentation*

🎉🎉🎉 **ALL 66/66 BUILDING BLOCKS DOCUMENTED - 100% COMPLETE!** 🎉🎉🎉
