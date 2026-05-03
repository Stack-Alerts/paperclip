# Phase 3 Diagnostic & Tuning Plan

**Date**: December 28, 2025, 9:18 AM  
**Current Results**: -6.82% return (256 trades, 50.86% win rate)  
**Status**: NEEDS TUNING - HTF detection may not be working as expected

---

## 🔴 CURRENT RESULTS ANALYSIS

### Walk-Forward Results
```
Total Return: -6.82%
Win Rate: 50.86% (improved from 43.8%!)
Trades: 256 (reduced from 336)
Profit Factor: 2.18 (good!)
Fees: $349.39 (3.49% of capital)
```

### Key Observations

1. **Win Rate Improved** ✅
   - 43.8% → 50.86% (+7% improvement)
   - This suggests pattern quality improved

2. **Trade Count Reduced** ✅
   - 336 → 256 (-24% fewer trades)
   - Less overtrading is good

3. **Profit Factor Good** ✅
   - 2.18 means winners are 2.18x larger than losers
   - This is actually solid

4. **But Still Losing Money** ❌
   - -6.82% return (better than -8.98% but still negative)
   - Fees eating 3.49% of capital

### Diagnosis

The **core issue** is likely:
1. HTF pattern detection **not activating often enough**
2. When it does activate, targets may be **too far**
3. Or 15m patterns still dominating (not finding HTF matches)

---

## 🔍 DIAGNOSTIC STEPS

### Step 1: Check HTF Pattern Activation Rate

Add logging to see how often HTF patterns are found:

```python
# In src/layers/layer_tbd_method.py
# In _detect_pattern_on_higher_tf():

if htf_pattern:
    logger.info(f"✅ HTF pattern found on {htf_pattern['timeframe']}")
    return htf_pattern
else:
    logger.info(f"❌ No HTF pattern found, using 15m targets")
    return None
```

**Run backtest and check logs**:
```bash
python3 scripts/layer_testing/walk_forward_tbd.py 2>&1 | grep "HTF pattern"
```

**Expected**:
- If seeing "❌ No HTF pattern" 90%+ of time → HTF detection too strict
- If seeing "✅ HTF pattern found" often → targets may be issue

### Step 2: Analyze Exit Reasons

```bash
python3 scripts/layer_testing/analyze_trade_pnl.py
```

Check:
- Are TP1 exits still losing money? (was -$50 avg)
- Are stop-outs still high? (was 24.4%)
- Are pattern_change exits still high? (was 28.3%)

### Step 3: Check Individual Trade Performance

Look at worst trades - are they:
- Using HTF targets but still losing?
- Not finding HTF patterns and using 15m?
- Getting stopped out with wider stops?

---

## 🔧 TUNING STRATEGIES

### Strategy A: Relax HTF Pattern Detection (RECOMMENDED)

**Problem**: HTF detection may be too strict, not finding matches

**Solution**: Widen tolerance in HTF detection

```python
# In _detect_htf_m_pattern() and _detect_htf_w_pattern():

# CURRENT (strict):
if price_diff > self.layer_config.mw_peak_tolerance:  # 0.25
    return None

# RELAXED (find more patterns):
if price_diff > 0.35:  # Increase from 0.25 to 0.35
    return None
```

**Also relax breakout check**:
```python
# CURRENT:
break_threshold = self.layer_config.mw_neckline_break_threshold  # 0.003

# RELAXED:
break_threshold = 0.005  # 0.5% instead of 0.3%
if current_price > neckline * (1 - break_threshold):
    return None
```

### Strategy B: Adjust Target Multipliers

**Problem**: HTF targets may be too far, never hitting TP1

**Solution**: Bring TP1 closer

```python
# CURRENT in TBDConfig:
tp1_multiplier: float = 0.5  # 50% of pattern height
tp2_multiplier: float = 1.0  # 100%
tp3_multiplier: float = 1.5  # 150%

# ADJUSTED (more achievable):
tp1_multiplier: float = 0.3  # 30% of pattern height
tp2_multiplier: float = 0.6  # 60%
tp3_multiplier: float = 1.0  # 100%
```

### Strategy C: Reduce HTF Stop Width

**Problem**: 1H ATR * 2.0 may be too wide, eating too much risk budget

**Solution**: Use 1.5x instead of 2.0x

```python
# In _detect_m_pattern() where HTF pattern found:

# CURRENT:
stop_loss = max(peak1_price, peak2_price) + (atr * 2.0)  # 2.0x

# ADJUSTED:
stop_loss = max(peak1_price, peak2_price) + (atr * 1.5)  # 1.5x
```

### Strategy D: Hybrid Approach (15m + HTF Average)

**Problem**: Pure 15m too tight, pure 1H too wide

**Solution**: Use average of 15m and 1H measurements

```python
# When HTF pattern found:
if htf_pattern:
    # Calculate both
    pattern_height_15m = max(peak1_price, peak2_price) - neckline
    pattern_height_1h = htf_pattern['pattern_height']
    
    # Use average
    pattern_height = (pattern_height_15m + pattern_height_1h) / 2
    
    atr_15m = self._get_atr(data)
    atr_1h = htf_pattern['atr']
    atr = (atr_15m + atr_1h) / 2
    
    # Targets use blended height
    stop_loss = max(peaks) + (atr * 1.75)  # Between 1.5 and 2.0
    tp1 = neckline - (pattern_height * 0.4)  # Between 0.3 and 0.5
```

### Strategy E: Only Use HTF for Strongest Patterns

**Problem**: Applying HTF to all patterns, even weak ones

**Solution**: Only use HTF when pattern is strong on both TFs

```python
def _detect_pattern_on_higher_tf(self, pattern_type, current_price, 
                                  confidence_15m: float):
    """Only return HTF pattern if confidence is high enough"""
    
    # Check 15m confidence first
    if confidence_15m < 0.7:  # Require strong 15m pattern
        return None
    
    # Then check HTF
    htf_pattern = self._detect_htf_m_pattern(self.data_1h, current_price)
    if htf_pattern:
        # Also check HTF pattern quality
        # (add quality checks here)
        return htf_pattern
    
    return None
```

---

## 📋 RECOMMENDED TUNING SEQUENCE

### Round 1: Diagnostic (Understand the Problem)

1. **Add logging** to see HTF activation rate
2. **Run backtest** and check logs
3. **Analyze exit reasons** to see what's failing

### Round 2: First Tuning (Based on Round 1 Results)

**If HTF activating <20% of time**:
- Apply Strategy A (relax HTF detection)
- Widen peak tolerance to 0.35
- Widen breakout threshold to 0.005

**If HTF activating often but TP1 not hitting**:
- Apply Strategy B (adjust multipliers)
- Reduce TP1 to 0.3x pattern height
- Or apply Strategy D (hybrid approach)

**If stops too wide eating capital**:
- Apply Strategy C (reduce stop width)
- Use 1.5x instead of 2.0x

### Round 3: Fine Tuning

After Round 2 improvements:
- Adjust multipliers by 0.05 increments
- Test different ATR multipliers (1.3x, 1.5x, 1.7x)
- Consider Strategy E (quality filter)

---

## 🎯 TARGET METRICS (Realistic)

### Phase 1 Target (Achievable)
- Win Rate: 50%+ ✅ (Already achieved!)
- Total Return: +5-15% (break even after fees)
- Profit Factor: 2.0+ ✅ (Already achieved!)
- TP1 Exits: Breakeven or small profit

### Phase 2 Target (With Tuning)
- Win Rate: 52-55%
- Total Return: +15-35%
- Profit Factor: 2.5+
- TP1 Exits: Clearly profitable

### Phase 3 Target (Optimized)
- Win Rate: 55-60%
- Total Return: +50-100%
- Profit Factor: 3.0+
- Stop Outs: <15%

---

## 🔄 ITERATIVE TUNING PROCESS

```
1. Run Diagnostic
   ↓
2. Identify Bottleneck
   ↓
3. Apply ONE Strategy
   ↓
4. Run Backtest
   ↓
5. Compare Results
   ↓
6. If Better → Keep Change
   If Worse → Revert
   ↓
7. Repeat until Target Met
```

**Key Rule**: Change **ONE** parameter at a time to isolate effects

---

## 📊 PARAMETER TRACKING TABLE

| Param | Current | Round 1 | Round 2 | Round 3 | Final | Notes |
|-------|---------|---------|---------|---------|-------|-------|
| HTF Peak Tolerance | 0.25 | 0.35 | ? | ? | ? | Relaxed for more matches |
| HTF Break Threshold | 0.003 | 0.005 | ? | ? | ? | Wider acceptance |
| TP1 Multiplier | 0.5 | 0.3 | ? | ? | ? | Closer target |
| TP2 Multiplier | 1.0 | 0.6 | ? | ? | ? | Scaled down |
| TP3 Multiplier | 1.5 | 1.0 | ? | ? | ? | Scaled down |
| HTF ATR Mult | 2.0 | 1.5 | ? | ? | ? | Tighter stop |
| Min Confidence | None | 0.7 | ? | ? | ? | Quality filter |

---

## 🚀 NEXT ACTIONS

### Immediate (Next 30 minutes)

1. **Add Diagnostic Logging**
   ```python
   # In _detect_pattern_on_higher_tf():
   if htf_pattern:
       logger.info(f"🎯 HTF FOUND: {pattern_type.value} on {htf_pattern['timeframe']}")
   else:
       logger.debug(f"❌ No HTF: {pattern_type.value}, using 15m targets")
   ```

2. **Run Diagnostic Backtest**
   ```bash
   python3 scripts/layer_testing/walk_forward_tbd.py 2>&1 | tee htf_diagnostic.log
   grep "HTF" htf_diagnostic.log | wc -l  # Count activations
   ```

3. **Analyze Exit Reasons**
   ```bash
   python3 scripts/layer_testing/analyze_trade_pnl.py
   ```

### Round 1 Tuning (Next Hour)

Based on diagnostic results, apply **ONE** of:
- Strategy A (if HTF rarely activating)
- Strategy B (if TP1 not hitting)
- Strategy C (if stops too wide)
- Strategy D (hybrid approach)

Test and compare results.

### Round 2 Tuning (Next Session)

- Fine-tune the strategy that worked
- Test combinations
- Document improvements

---

## 💡 KEY INSIGHTS

### What's Working
- ✅ Win rate improved (43.8% → 50.86%)
- ✅ Fewer trades (336 → 256)
- ✅ Good profit factor (2.18)

### What Needs Work
- ❌ Still losing money (-6.82%)
- ❌ Fees eating profits (3.49%)
- ❌ Need to confirm HTF is activating

### Root Cause Hypothesis
1. **HTF detection too strict** → Not activating often enough → Still using 15m targets
2. **OR HTF targets too far** → Can't reach TP1 → Time exits with small losses
3. **OR Stop placement** → Getting stopped out more than before

---

## 📝 TUNING LOG TEMPLATE

```
=== TUNING ROUND N ===
Date: YYYY-MM-DD
Hypothesis: [What we think is wrong]
Change Made: [Specific parameter change]
Expected: [What we expect to happen]
Result: [Actual result]
Decision: [Keep/Revert/Iterate]
Next: [What to try next]
```

---

*Document Created: December 28, 2025, 9:18 AM*  
*Status: Diagnostic & Tuning Plan Ready*  
*Next: Run diagnostic to identify bottleneck*
