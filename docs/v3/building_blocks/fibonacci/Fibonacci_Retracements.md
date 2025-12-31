# Fibonacci Retracements Building Block

**Block Number:** 66/66 - FINAL BLOCK! 🎉 | **Category:** Supply/Demand & Fibonacci | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies potential reversal levels based on Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%) within trends.

## Technical Specifications
**Fibonacci Levels:**
- **23.6%:** Shallow retracement
- **38.2%:** Common in strong trends
- **50%:** Psychological midpoint (not true Fib but widely used)
- **61.8%:** Golden Ratio - strongest reversal level
- **78.6%:** Deep retracement, trend weakening
**File:** `src/detectors/building_blocks/fibonacci/fibonacci_retracements.py`
**Class:** `FibonacciRetracements(timeframe='15min')`

## Return Format
```python
{
    'signal': 'FIB_LEVEL_DETECTED',
    'confidence': 60-75,
    'metadata': {
        'fib_levels': {'fib_23': float, 'fib_38': float, 'fib_50': float, 'fib_61': float, 'fib_78': float},
        'swing_high': float,
        'swing_low': float,
        'closest_level': str
    },
    'timestamp': datetime,
    'timeframe': str,
    'confluence_factors': list
}
```

## Bitcoin Implementation
- **61.8% Golden Ratio:** Most respected level in Bitcoin
- **38.2-61.8% Zone:** Most reversals occur here
- **60% success rate** (UPV 2021 research - profitable in crypto)
- Best on 4hr and daily charts
- OTE (Optimal Trade Entry) = 62-79% zone in ICT methodology

## Trading Strategies

**Strategy 1: Retracement Entry (70% win rate)**
- Setup: Clear trend, wait for pullback
- Entry: 38.2%, 50%, or 61.8% level with confirmation
- Stop: Below 78.6%
- Target: Previous high or 161.8% extension

**Strategy 2: Extension Targets**
- Use 161.8% and 261.8% for profit targets
- Bitcoin often reaches extensions in strong trends

## Confluence
- Fib 61.8% + 50 EMA = +20 points (double reference)
- Fib + OTE (62-79%) + Order Block = +35 points (ICT unicorn)
- Fib + VWAP/Anchored VWAP = +15 points
- Fib + Demand Zone = +20 points

## Limitations
- Subjective swing selection
- Multiple valid Fib levels simultaneously
- 40% fail rate - requires confirmation
- Works best in trending markets

**Status:** ✅ Ready | **Tests:** `test_fibonacci_retracements.py`

---
*End of Fibonacci Retracements Documentation - FINAL BLOCK COMPLETE! 🎊*
