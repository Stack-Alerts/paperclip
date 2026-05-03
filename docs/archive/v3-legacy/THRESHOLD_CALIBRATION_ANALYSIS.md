# Threshold Calibration Analysis

**Date**: December 17, 2025  
**Issue**: Zero/minimal trades in backtesting due to overly restrictive thresholds

## Problem Summary

The backtest system generated only **1 trade in 60 days (1,344 bars)** due to cascading threshold restrictions:

1. **Compositor Score Threshold**: 0.03 (too high)
2. **Compositor Confidence Threshold**: 0.15 (too high) 
3. **Layer 1 Confidence Threshold**: 0.15 (too high)

## Evidence from Backtest

### Single Trade That Passed
```
Entry: 2025-10-30 09:00 SHORT
Composite Signal:
  - Score: -0.169
  - Confidence: 15.3%
  - Agreement: 90.8%
  
Result: +1.39% ($11.87 profit)
```

### Typical Rejected Signals
Most signals showed:
- Scores: -0.134 to +0.134 range
- Confidence: 0.000 to 0.130 range
- Most fell below 0.15 confidence threshold

### Example Strong Signals That Were Rejected:
```
Bar 1170: score=-0.134, confidence=0.127 → REJECTED (confidence < 0.15)
Bar 1246: score=+0.131, confidence=0.106 → REJECTED (confidence < 0.15)
Bar 1178: score=-0.106, confidence=0.093 → REJECTED (confidence < 0.15)
```

## Root Causes

### 1. Layer Compositor (`src/layers/layer_compositor.py`)
```python
# Current thresholds (Lines 70-71):
MIN_SCORE_THRESHOLD = 0.03      # Too restrictive
MIN_CONFIDENCE_THRESHOLD = 0.15  # Too restrictive
```

**Impact**: Most signals classified as "neutral" before reaching strategies.

### 2. Layer 1 Traditional (`src/layers/layer1_traditional.py`)
```python
# Current logic (Lines 154-162):
if direction > 0.08 and confidence > 0.15:
    final_direction = "long"
elif direction < -0.08 and confidence > 0.15:
    final_direction = "short"
else:
    final_direction = "neutral"
```

**Impact**: Even when compositor passes signal, Layer 1 can still block it.

## Recommended Calibration

### Phase 1: Conservative Loosening
```python
# Compositor thresholds:
MIN_SCORE_THRESHOLD = 0.02      # Was 0.03
MIN_CONFIDENCE_THRESHOLD = 0.10  # Was 0.15

# Layer 1 thresholds:
direction_threshold = 0.05       # Was 0.08
confidence_threshold = 0.10      # Was 0.15
```

**Expected Impact**: 5-15 trades per 60 days

### Phase 2: Data-Driven Calibration
After Phase 1 testing:
1. Analyze signal distributions
2. Calculate optimal thresholds using historical performance
3. Consider percentile-based thresholds (e.g., top 20% of signals)

### Phase 3: Strategy-Specific Thresholds
Different strategies may need different sensitivities:
- **Scalp Aggressive**: Lower thresholds (more trades)
- **Scalp Conservative**: Higher thresholds (fewer, higher-confidence trades)
- **Scalp ML Heavy**: ML confidence-weighted thresholds

## Implementation Priority

1. ✅ **IMMEDIATE**: Lower compositor thresholds to 0.02/0.10
2. ✅ **IMMEDIATE**: Lower Layer 1 thresholds to 0.05/0.10
3. **NEXT**: Run backtest validation
4. **THEN**: Data-driven optimization based on results
5. **FUTURE**: Per-strategy threshold configuration

## Testing Protocol

1. Run 60-day backtest with new thresholds
2. Validate:
   - Trade frequency: 5-20 trades
   - Win rate: >45%
   - Drawdown: <10%
3. If successful, run 180-day validation
4. Document optimal thresholds for each strategy

## Notes

- Current system was calibrated for **quality over quantity**
- Need to find balance between signal frequency and reliability
- ML layers (4 & 5) may need retraining with more aggressive labeling
- Consider implementing adaptive thresholds based on market volatility

---

**Status**: Analysis Complete  
**Next Action**: Implement Phase 1 threshold adjustments
