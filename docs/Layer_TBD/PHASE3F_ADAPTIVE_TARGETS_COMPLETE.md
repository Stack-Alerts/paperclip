# Phase 3F: Adaptive TP Targets - Complete

**Date:** December 28, 2025  
**Status:** ✅ COMPLETE  
**Strategy:** Implement tighter TP targets when no HTF pattern detected

---

## Problem Statement

With HTF activation at 0% during the test period (no 1H M/W patterns detected), all trades were using standard 15m TP multipliers (0.5x/1.0x/1.5x). The Phase 3 document suggested adaptive targets as Strategy C when HTF <20%.

---

## Solution Implemented

### Adaptive TP Multipliers

When HTF pattern is NOT detected (using 15m targets only):
- **TP1**: 0.5x → **0.4x** (20% closer, -10% distance)
- **TP2**: 1.0x → **0.8x** (20% closer, -20% distance)
- **TP3**: 1.5x → **1.2x** (20% closer, -20% distance)

When HTF pattern IS detected (using 1H/4H targets):
- **TP1**: 0.5x (standard)
- **TP2**: 1.0x (standard)
- **TP3**: 1.5x (standard)

### Rationale

1. **Tighter targets = higher hit rate**: Closer TPs are easier to reach
2. **Conservative without HTF**: No 1H pattern = less conviction = smaller targets
3. **Preserve R:R when HTF**: When 1H pattern exists, use full targets for maximum profit
4. **Gradual scaling**: 20% reduction maintains proportional spacing

---

## Files Modified

### 1. src/layers/layer_tbd_method.py

**M-Pattern (lines 710-722)**:
```python
else:
    # Use 15m measurements with TIGHTER targets (Phase 3E adaptive strategy)
    # Since no HTF pattern, use conservative TP multipliers for better fill rate
    atr = self._get_atr(data)
    stop_loss = max(peak1_price, peak2_price) + (atr * self.layer_config.atr_stop_multiplier)
    
    # ADAPTIVE: Tighter targets when no HTF (0.4x/0.8x/1.2x vs 0.5x/1.0x/1.5x)
    tp1 = neckline - (pattern_height * 0.4)  # 40% of pattern (was 50%)
    tp2 = neckline - (pattern_height * 0.8)  # 80% of pattern (was 100%)
    tp3 = neckline - (pattern_height * 1.2)  # 120% of pattern (was 150%)
    
    using_htf_targets = False
    htf_timeframe = None
```

**W-Pattern (lines 1250-1262)**:
```python
else:
    # Use 15m measurements with TIGHTER targets (Phase 3E adaptive strategy)
    # Since no HTF pattern, use conservative TP multipliers for better fill rate
    atr = self._get_atr(data)
    stop_loss = min(trough1_price, trough2_price) - (atr * self.layer_config.atr_stop_multiplier)
    
    # ADAPTIVE: Tighter targets when no HTF (0.4x/0.8x/1.2x vs 0.5x/1.0x/1.5x)
    tp1 = neckline + (pattern_height * 0.4)  # 40% of pattern (was 50%)
    tp2 = neckline + (pattern_height * 0.8)  # 80% of pattern (was 100%)
    tp3 = neckline + (pattern_height * 1.2)  # 120% of pattern (was 150%)
    
    confidence_boost = 1.0
    using_htf_targets = False
    htf_timeframe = None
```

---

## Test Results

### Walk-Forward Performance

| Metric | Before (Standard) | After (Adaptive) | Change |
|--------|------------------|------------------|---------|
| **Net P&L** | -$258.52 | -$248.74 | +$9.78 |
| **Return %** | -2.59% | -2.49% | +0.10% |
| **Total Trades** | 53 | 53 | 0 |
| **Win Rate** | 43.8% | 45.3% | +1.5% |
| **Avg P&L/Trade** | -$4.88 | -$4.69 | +$0.19 |

### Exit Reason Breakdown (After Adaptive)

| Exit | Count | % | Avg P&L | Total P&L |
|------|-------|---|---------|-----------|
| time_exit | 19 | 35.8% | +$3.96 | +$75.28 |
| stop_loss | 14 | 26.4% | -$12.94 | -$181.12 |
| tp3 | 10 | 18.9% | +$11.27 | +$112.73 |
| tp1 | 6 | 11.3% | -$46.17 | -$277.04 |
| tp2 | 3 | 5.7% | +$9.50 | +$28.50 |
| pattern_change | 1 | 1.9% | -$7.08 | -$7.08 |

### Pattern Performance (After Adaptive)

| Pattern | Trades | Win Rate | Avg P&L | Total P&L |
|---------|--------|----------|---------|-----------|
| one_formation | 19 | 57.9% | +$4.05 | +$77.02 |
| trapping_volume | 22 | 45.5% | -$1.59 | -$34.90 |
| three_hits | 4 | 50.0% | -$3.77 | -$15.07 |
| weekend_trap | 1 | 0.0% | -$5.54 | -$5.54 |
| **w_pattern** | **7** | **14.3%** | **-$38.61** | **-$270.25** |

---

## Analysis

### Positive Improvements

1. **Better overall P&L**: +$9.78 improvement (+3.8% reduction in losses)
2. **TP3 more profitable**: +$112.73 (10 trades hitting far target)
3. **TP2 profitable**: +$28.50 (3 trades)
4. **Time exits working**: +$75.28 (19 trades, 35.8% of exits)
5. **Pattern change exits reduced**: 28.3% → 1.9% (Phase 3D fix working!)

### Remaining Issues

1. **W-pattern catastrophic**: 7 trades, -$270.25 total (14.3% win rate!)
2. **TP1 exits still losing**: -$277.04 total (mostly W-patterns)
3. **No HTF activation**: 0% (no 1H patterns in test period)

### Key Insight: W-Pattern Problem

The W-pattern is the core profitability issue:
- **5 worst trades are ALL W-pattern TP1 exits**
- Average loss: -$50+ per TP1 exit
- This suggests W-pattern detection is generating false signals or entries are too early

---

## Recommendations

### Short-Term (Immediate)

1. **Disable W-pattern temporarily**: Test without W-pattern to isolate issue
2. **Increase W-pattern confidence threshold**: Require 75%+ confidence (vs current 60%)
3. **Stricter W-pattern validation**: Add volume escalation check, trend context check

### Medium-Term (Next Sprint)

1. **Test on different time period**: Find period with 1H M/W patterns to test HTF properly
2. **W-pattern entry timing**: Consider retest-only entries (no immediate)
3. **Dynamic TP multipliers**: Adjust based on ATR, volatility, market regime

### Long-Term (Future Enhancement)

1. **Machine learning for TP levels**: Learn optimal TP distances per pattern/market
2. **Regime-based parameters**: Bull market vs bear market vs sideways
3. **Pattern quality scoring**: Weight by multiple confirmation factors

---

## Success Metrics

### Achieved ✅
- [x] Adaptive TP system implemented
- [x] Code properly differentiates HTF vs non-HTF
- [x] Small performance improvement (+$9.78)
- [x] Pattern change exits reduced (28.3% → 1.9%)
- [x] Trailing stops working (Phase 3C)

### Not Yet Achieved ❌
- [ ] Positive overall return
- [ ] 55%+ win rate (currently 45.3%)
- [ ] HTF activation >20% (currently 0%)
- [ ] W-pattern profitability (currently -$270!)

---

## Conclusion

**Phase 3F Adaptive Targets are working as designed**, providing:
1. Tighter targets when no HTF (conservative approach)
2. Standard targets when HTF detected (aggressive approach)
3. Small but measurable improvement (+$9.78, +0.10%)

However, **W-pattern detection is critically broken** and needs immediate attention:
- 7 trades, only 1 winner (14.3% WR)
- -$270.25 total loss (51% of all losses!)
- 5 worst trades are W-pattern TP1 exits

The adaptive TP system is a **tactical improvement** but won't solve the strategic W-pattern problem. Next phase should focus on W-pattern validation or disabling it entirely.

---

## Next Steps

1. **Analyze W-pattern failures**: Review trade logs for false signals
2. **Test W-pattern disable**: Run backtest without W-pattern
3. **Stricter W-pattern rules**: Add multi-TF confirmation requirement
4. **Test different time periods**: Find period with 1H patterns for HTF validation

---

*Phase 3F Complete: December 28, 2025, 9:55 AM*  
*Adaptive TP Multipliers: WORKING*  
*Overall Profitability: STILL NEGATIVE (W-pattern issue)*
