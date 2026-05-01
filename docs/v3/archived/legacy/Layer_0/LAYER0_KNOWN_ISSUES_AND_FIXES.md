# Layer 0: Known Issues and Required Fixes

**Date**: December 17, 2025  
**Status**: ⚠️ IMPLEMENTATION COMPLETE BUT NEEDS FIXES

---

## ✅ What Works

1. **Layer 0 trend detection is CORRECT**
   - Properly detects bearish trends (-19.55% decline)
   - 4-pillar analysis working (Structure, MA, MACD, RSI)
   - Multi-timeframe hierarchy working (4H > 2H > 1H)

2. **Framework integration complete**
   - All files created and connected
   - JSON serialization working
   - Reports generating correctly

---

## ❌ Critical Issues to Fix

### Issue 1: Compositor Ignores Strategy Thresholds

**Problem**: The compositor is initialized without strategy config thresholds:

```python
# In backtest_runner.py line ~475
compositor = LayerCompositor(weights=weights, verbose_logging=verbose)
```

**Missing**: The thresholds from strategy config aren't passed:
- `confidence_threshold`: 0.50
- `score_threshold`: 0.30  
- `min_layers_agreeing`: 2

**Fix Needed**:
```python
compositor = LayerCompositor(
    weights=weights,
    confidence_threshold=strategy_config.get('confidence_threshold', 0.5),
    score_threshold=strategy_config.get('score_threshold', 0.3),
    min_agreeing=strategy_config.get('min_layers_agreeing', 2),
    verbose_logging=verbose
)
```

---

### Issue 2: Layer 1 RSI Backwards

**Problem**: Layer 1 RSI thresholds are inverted in `layer0_layer1_test.py`:

```python
'rsi_oversold': 52,   # WRONG: This triggers LONGs when RSI > 52
'rsi_overbought': 48, # WRONG: This triggers SHORTs when RSI < 48
```

**This explains why**:
- Only 1 LONG trade generated (RSI was > 52 once)
- Zero SHORT trades (RSI never went < 48 in downtrend)

**Fix Needed**:
```python
'rsi_oversold': 30,   # CORRECT: Look for bounces when RSI < 30
'rsi_overbought': 70, # CORRECT: Look for rejections when RSI > 70
```

**OR for opportunity generator mode** (catches any movement):
```python
'rsi_oversold': 45,   # Slightly below neutral
'rsi_overbought': 55, # Slightly above neutral
```

---

### Issue 3: Layer 1 Only Generates LONG Signals

**Problem**: In `src/layers/layer1_traditional.py`, the signal generation logic needs to generate BOTH long and short signals based on conditions.

**Current behavior**: Generates signal when conditions met, but direction logic may be one-sided.

**Fix Needed**: Review `generate_signal()` method to ensure it generates:
- LONG signals when: RSI < oversold threshold, price near support, etc.
- SHORT signals when: RSI > overbought threshold, price near resistance, etc.

---

## 🔧 Required Code Changes

### 1. Fix Compositor Initialization

**File**: `src/cli/backtest_runner.py` (around line 475)

```python
# BEFORE
compositor = LayerCompositor(weights=weights, verbose_logging=verbose)

# AFTER
compositor = LayerCompositor(
    weights=weights,
    confidence_threshold=strategy_config.get('confidence_threshold', 0.5),
    score_threshold=strategy_config.get('score_threshold', 0.3),
    min_agreeing=strategy_config.get('min_layers_agreeing', 2),
    verbose_logging=verbose
)
```

### 2. Fix Layer 1 RSI Thresholds

**File**: `config/strategies/layer0_layer1_test.py`

```python
# BEFORE (WRONG - backwards!)
'rsi_oversold': 52,
'rsi_overbought': 48,

# AFTER (CORRECT - for scalping opportunities)
'rsi_oversold': 45,   # Look for longs when RSI drops below 45
'rsi_overbought': 55, # Look for shorts when RSI rises above 55
```

### 3. Verify Layer 1 Signal Direction Logic

**File**: `src/layers/layer1_traditional.py`

Ensure the `generate_signal()` method generates:
- **direction = "long"** when bullish conditions (RSI < oversold, etc.)
- **direction = "short"** when bearish conditions (RSI > overbought, etc.)
- **direction = "neutral"** when no clear signal

---

## 📊 Expected Results After Fixes

### Before Fixes
- **Trades**: 1 LONG only
- **Win Rate**: 0%
- **Issue**: Filtered nothing, wrong RSI, no shorts

### After Fixes
- **Trades**: 5-10 trades (mix of LONG and SHORT)
- **Win Rate**: 40-60% (trend-aligned trades)
- **Behavior**: 
  - Layer 0 blocks counter-trend
  - Layer 1 generates both directions
  - Compositor filters low-quality signals

---

## 🎯 Testing Plan

1. **Fix compositor thresholds** → Retest
2. **Fix RSI thresholds** → Retest
3. **Compare results**:
   - Layer 1 alone: 20 trades, 20% win rate
   - Layer 0 + Layer 1: 8-12 trades, 50%+ win rate

---

## 📝 Additional Notes

### Why Only 1 Trade?

The backtest generated only 1 trade because:
1. **RSI backwards**: RSI > 52 only happened once (looking for LONGS in downtrend)
2. **No SHORT logic**: RSI < 48 never triggered (would need to in downtrend)
3. **Layer 1 bias**: May have LONG-only bias in current code

### What Should Happen

In a -19.55% downtrend:
- **Layer 0**: Should output SHORT_ONLY most of the time
- **Layer 1**: Should generate SHORT signals when RSI > 55 (rejection opportunities)
- **Compositor**: Should filter to keep only high-quality SHORTs
- **Expected**: 5-10 SHORT trades with 50-60% win rate

---

## ⏰ Priority

**HIGH PRIORITY** - These fixes are critical for Layer 0 to function as designed.

Without these fixes:
- ❌ Compositor doesn't filter
- ❌ RSI generates wrong signals
- ❌ Only catches LONG in downtrends (worst possible)

With these fixes:
- ✅ Compositor filters properly
- ✅ RSI generates correct signals
- ✅ Catches SHORT opportunities in downtrends

---

**Implementation Status**: Documented, awaiting code changes
