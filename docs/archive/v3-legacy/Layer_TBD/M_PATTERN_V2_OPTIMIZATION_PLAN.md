# M-Pattern v2 Parameter Optimization Plan

**Status**: In Progress  
**Date**: December 29, 2025  
**Version**: 2.0.1  
**Current Performance**: Recall 52%, Precision 17%, F1 0.254

---

## Current Validation Results

### Overall Performance
- **Ground Truth**: 634 M-patterns
- **Detected**: 1,969 M-patterns
- **True Positives**: 330 (52.05% recall) ✅
- **False Positives**: 1,639 (83.25% of detections)
- **False Negatives**: 304 (47.95% missed)

**Precision**: 16.76% ⚠️ (Too many false positives)  
**Recall**: 52.05% ✅ (Detecting half the patterns)  
**F1 Score**: 0.254 (Needs improvement)

### Per-Timeframe Breakdown

| TF | Precision | Recall | F1 | TP | FP | FN | Pattern Count |
|----|-----------|--------|-----|----|----|----|----|
| 15m | 22.41% | 50.95% | 0.311 | 188 | 651 | 181 | 839 |
| 30m | 17.06% | 56.21% | 0.262 | 95 | 462 | 74 | 557 |
| 1h | 9.18% | 47.54% | 0.154 | 29 | 287 | 32 | 316 |
| 2h | 8.19% | 60.87% | 0.144 | 14 | 157 | 9 | 171 |
| 4h | 4.65% | 33.33% | 0.082 | 4 | 82 | 8 | 86 |

**Key Insights**:
- 15m performs best (22% precision)
- 2h has highest recall (61%) but worst precision (8%)
- 4h has too few patterns and worst F1
- **Problem**: System is too permissive across all timeframes

---

## Root Cause Analysis

### Why Low Precision?

**Current Parameters** (Too Loose):
```python
peak_tolerance = 0.25          # 25% peak difference allowed
min_pattern_depth = 0.01       # 1% minimum depth
max_pattern_depth = 0.25       # 25% maximum depth
pattern_length_min = 8         # Very short patterns
pattern_length_max = 80        # Very long patterns
volume_breakout_min = 0.1      # Effectively disabled
volume_breakout_max = 100.0    # Effectively disabled
```

**Issues**:
1. **Peak tolerance too wide**: 25% allows very asymmetric "M" shapes
2. **Depth too shallow**: 1% catches noise patterns
3. **Length range too broad**: 8-80 bars catches too many variations
4. **Volume disabled**: No quality filter on patterns

---

## Optimization Strategy

### Phase 1: Tighten Core Parameters (Quick Win)

**Goal**: Reduce false positives by 50-70%  
**Target**: Precision 40-50%, Recall 45-50%, F1 0.45+

**Parameter Changes**:
```python
# Symmetry: Require tighter peak alignment
peak_tolerance: 0.25 → 0.12       # 25% → 12% (50% tighter)

# Depth: Require deeper patterns
min_pattern_depth: 0.01 → 0.025   # 1% → 2.5% (2.5x deeper)
max_pattern_depth: 0.25 → 0.20    # 25% → 20% (filter extremes)

# Length: Tighten pattern window
pattern_length_min: 8 → 15        # Longer minimum (filter noise)
pattern_length_max: 80 → 50       # Shorter maximum (filter stretched)

# Volume: Re-enable with relaxed threshold
volume_breakout_min: 0.1 → 0.5    # Require minimum volume
volume_breakout_max: 100.0 → 5.0  # Cap maximum volume
```

**Expected Impact**:
- False Positives: 1,639 → 600-800 (50-65% reduction)
- True Positives: 330 → 280-300 (10-15% reduction)
- Precision: 17% → 35-45%
- Recall: 52% → 45-48%
- F1: 0.25 → 0.40-0.47

---

### Phase 2: Timeframe-Specific Tuning

After Phase 1, apply timeframe-specific parameters:

**15m/30m** (Higher frequency, clearer patterns):
```python
peak_tolerance = 0.12
min_pattern_depth = 0.025
pattern_length_min = 15
```

**1h** (Medium frequency):
```python
peak_tolerance = 0.10       # Tighter symmetry
min_pattern_depth = 0.030   # Deeper patterns
pattern_length_min = 12
```

**2h/4h** (Lower frequency, need quality):
```python
peak_tolerance = 0.08       # Much tighter
min_pattern_depth = 0.035   # Deepest patterns
pattern_length_min = 10
pattern_length_max = 40     # Shorter window
```

---

### Phase 3: Add Quality Filters

**Pattern Quality Score** (0-1):
```python
def calculate_pattern_quality(pattern):
    score = 0.0
    
    # Peak cleanliness (sharp highs)
    if has_clean_peaks(pattern):
        score += 0.3
    
    # Neckline clarity (clear valley)
    if has_clear_neckline(pattern):
        score += 0.3
    
    # Volume profile (distribution decreasing)
    if has_proper_volume(pattern):
        score += 0.2
    
    # Time-of-day (avoid low liquidity)
    if in_high_liquidity_period(pattern):
        score += 0.2
    
    return score

# Only detect if quality >= 0.6
```

---

### Phase 4: Advanced Filters

**Rejection Criteria**:
1. **Overlapping peaks**: Reject if peaks overlap
2. **Irregular neckline**: Reject if neckline too jagged
3. **Low liquidity times**: Reject Asian session patterns on low TFs
4. **Recent similar pattern**: Extend cooldown for similar patterns

---

## Implementation Plan

### Step 1: Phase 1 Parameters (Immediate)

1. Update `MPatternConfig` in `m_pattern_layer.py`
2. Run validation with Phase 1 parameters
3. Compare results to baseline
4. Document improvements

**Files to Modify**:
- `src/layers/tbd_v2/m_pattern_layer.py` (MPatternConfig defaults)
- `config/strategies/m_pattern_only_v2.py` (strategy config)

### Step 2: Validation & Analysis

```bash
# Run optimized validation
python3 scripts/validation/pattern_validator_v2.py \
  --ground-truth data/validation/ground_truth_2025_fixed.json \
  --start-date 2025-01-01 \
  --end-date 2025-12-01 \
  --output data/validation/validation_m_v2_optimized.json

# Compare results
diff data/validation/validation_m_pattern_v2_FINAL.json \
     data/validation/validation_m_v2_optimized.json
```

### Step 3: Iterate

- If precision < 40%: Tighten more (peak_tolerance → 0.10)
- If recall < 40%: Loosen slightly (peak_tolerance → 0.15)
- Target sweet spot: 45% precision, 48% recall, F1 0.46+

### Step 4: Phase 2 & 3 (If Needed)

Only proceed if Phase 1 doesn't achieve targets.

---

## Success Metrics

### Minimum Acceptable (Phase 1)
- ✅ Precision ≥ 40%
- ✅ Recall ≥ 45%
- ✅ F1 Score ≥ 0.42
- ✅ False Positives reduced by 50%

### Target Performance (Phase 2)
- ✅ Precision ≥ 55%
- ✅ Recall ≥ 50%
- ✅ F1 Score ≥ 0.52

### Ideal Performance (Phase 3+)
- ✅ Precision ≥ 70%
- ✅ Recall ≥ 60%
- ✅ F1 Score ≥ 0.65

### Ultimate Goal (Long-term)
- ✅ Precision ≥ 95% (original target)
- ✅ Recall ≥ 90% (original target)
- ✅ F1 Score ≥ 0.92

---

## Parameter Testing Matrix

For systematic optimization, test these combinations:

| Test | peak_tol | min_depth | length_min | Expected Precision | Expected Recall |
|------|----------|-----------|------------|-------------------|-----------------|
| Baseline | 0.25 | 0.010 | 8 | 17% | 52% |
| Test 1 | 0.20 | 0.015 | 10 | 22% | 50% |
| Test 2 | 0.15 | 0.020 | 12 | 30% | 48% |
| **Test 3** | **0.12** | **0.025** | **15** | **40%** | **46%** |
| Test 4 | 0.10 | 0.030 | 15 | 50% | 42% |
| Test 5 | 0.08 | 0.035 | 18 | 60% | 38% |

**Recommended**: Start with Test 3, adjust based on results.

---

## Validation Commands

```bash
# Phase 1: Optimized parameters
python3 scripts/validation/pattern_validator_v2.py \
  --ground-truth data/validation/ground_truth_2025_fixed.json \
  --start-date 2025-01-01 \
  --end-date 2025-12-01 \
  --output data/validation/validation_m_v2_phase1.json

# Quick test (January only)
python3 scripts/validation/pattern_validator_v2.py \
  --ground-truth data/validation/ground_truth_2025_fixed.json \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --output data/validation/validation_m_v2_jan_test.json
```

---

## Next Steps

1. **Immediate**: Implement Phase 1 parameters
2. **Test**: Run quick validation (January)
3. **Analyze**: Check precision improvement
4. **Full Run**: If good, run full year validation
5. **Document**: Update results in completion doc
6. **Iterate**: Adjust if targets not met

---

**Status**: Ready to implement Phase 1  
**Expected Time**: 30 minutes implementation + 10 minutes validation  
**Expected Improvement**: 17% → 40% precision, 52% → 46% recall

---

*"From 0% to 52% was the breakthrough. From 52% to 90% is optimization."*

**End of Document**
