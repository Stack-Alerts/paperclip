# Layer 0 Tuning Progress Report

## Summary
Systematic tuning of Layer 0 trend detection to achieve 85%+ accuracy against ground truth.

## Starting Point
- **Initial Accuracy**: 14.8% (using resampled data with broken MA detection)
- **Target Accuracy**: 85%+

## Iteration History

### Iteration 1: Fix Data Loading (14.8% → 14.8%)
**Changes:**
- Implemented actual 4H/2H data loading (vs resampling from 1H)
- Added `_analyze_timeframe_actual()` method

**Result:**
- Accuracy unchanged at 14.8%
- Fixed architecture but revealed deeper scoring issues

**Key Finding:** Resampling problem was real, but not the only issue.

---

### Iteration 2: Fix MA Column Names (14.8% → 22.2%)
**Changes:**
- Fixed MA alignment to use correct EMA periods (9, 20, 50 instead of 9, 21, 50)
- MA scores were ALL 0.0 because `ema_21` doesn't exist - it's `ema_20`!
- Lowered thresholds: weak 0.5→0.3, strong 1.2→0.8
- Made MA alignment more sensitive (increased partial alignment scores)

**Result:**
- ✅ **Accuracy: 22.2%** (+7.4 percentage points)
- Uptrend: 7.7% (1/13)
- Downtrend: 35.7% (5/14)

**Key Finding:** MA component now functional but system has **downtrend bias**.

---

## Current Issues

### 1. Downtrend Bias (35.7% vs 7.7%)
The system is 4.6x better at identifying downtrends than uptrends. Possible causes:
- Structure detection may favor bearish swings
- MACD/RSI may be asymmetric
- Threshold calibration needs adjustment

### 2. Low Absolute Accuracy (22.2%)
While MA scores now work, overall accuracy is still far from 85% target.

### 3. Component Score Distribution
From diagnostic analysis:
- Average 4H score magnitude: 0.562
- Max 4H score magnitude: 1.289
- Most trends classified as NEUTRAL (18/26)

**Current Thresholds:**
- Weak: 0.3 (borderline too low)
- Strong: 0.8 (appropriate for data distribution)

---

## Next Steps

### Priority 1: Fix Uptrend Detection Bias
**Root Cause Analysis Needed:**
1. Check if structure detection has asymmetric logic
2. Verify MACD scoring is symmetric
3. Ensure RSI thresholds are balanced (55-80 bull vs 20-45 bear)

**Proposed Fix:**
- Review `_analyze_market_structure()` for bias
- May need to adjust swing detection sensitivity differently for up vs down

### Priority 2: Improve Structure Detection Sensitivity
Currently too many "ranging" classifications. Need to:
- Lower swing detection threshold
- Consider trend-following indicators alongside swings
- Add volume confirmation

### Priority 3: Multi-TF Weight Rebalancing
Current weights:
- 4H: 50%
- 2H: 25%
- 1H: 15%

May need to increase 2H/1H influence for shorter trends (<10 days).

---

## Test Methodology

**Ground Truth:** 27 manually identified trends from price action analysis
- 13 uptrends
- 14 downtrends
- Duration: 1.5 to 39.6 days
- Coverage: 6.3 years (2019-2025)

**Validation:** Compare Layer 0 classification at trend midpoint vs ground truth.

---

## Code Changes Summary

### Files Modified
1. `src/layers/layer0_multi_tf_trend.py`
   - Added `_analyze_timeframe_actual()` method
   - Fixed MA alignment to use ema_20 (not ema_21)
   - Lowered thresholds (0.5→0.3, 1.2→0.8)
   - Increased MA partial alignment scores

2. `compare_layer0_vs_groundtruth.py`
   - Updated to use full dataset (not just 365 days)
   - Added actual data support

3. `debug_layer0_components.py` (NEW)
   - Created diagnostic tool to analyze component scores
   - Identifies why trends are misclassified

---

## Accuracy Breakdown

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| **Overall** | 6 | 27 | **22.2%** |
| Uptrends | 1 | 13 | 7.7% ❌ |
| Downtrends | 5 | 14 | 35.7% |
| Short (<10d) | 3 | 17 | 17.6% |
| Medium (10-30d) | 3 | 9 | 33.3% |
| Long (30d+) | 0 | 1 | 0.0% |

**Gap to Target:** Need 62.8 percentage points more (22.2% → 85%)

---

## Recommendations for Next Iteration

### Quick Wins (Expected +20-30%)
1. **Fix uptrend bias** - Investigate asymmetric logic in structure/MACD/RSI
2. **Tune structure sensitivity** - Reduce "ranging" over-classification
3. **Adjust RSI thresholds** - Currently 55-80 (bull) vs 20-45 (bear)

### Medium Effort (Expected +10-20%)
4. **Add trend momentum** - Once in trend, require stronger counter-evidence
5. **Improve partial alignment scoring** - Fine-tune the 0.2/0.4/0.6 levels
6. **Volume confirmation** - Add volume trend as 5th pillar (10% weight)

### Research Needed (Expected +5-10%)
7. **Dynamic thresholds** - Adjust based on volatility regime
8. **Multi-TF weight optimization** - ML-based weight tuning
9. **Structure detection alternatives** - Test other swing identification methods

---

## Timeline

- **Iteration 1-2:** ✅ Complete (22.2% accuracy)
- **Iteration 3:** Fix uptrend bias → Target 40-50%
- **Iteration 4:** Tune structure detection → Target 60-70%
- **Iteration 5:** Add momentum/volume → Target 75-80%
- **Iteration 6:** Final calibration → Target 85%+

**Estimated Time:** 2-3 more iterations (1-2 hours)

---

## Status: 🟡 IN PROGRESS

**Current:** 22.2% accuracy
**Target:** 85%+ accuracy
**Progress:** 26% of goal achieved
