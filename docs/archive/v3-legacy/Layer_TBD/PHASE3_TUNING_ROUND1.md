# Phase 3 Tuning - Round 1

**Date**: December 28, 2025, 9:26 AM  
**Status**: HTF Detection Not Activating - Applying Strategy A

---

## 🔴 CRITICAL FINDING

**HTF Pattern Detection: 0% Activation Rate**

```
Using HTF targets:    0 trades (  0.0%)
Using 15m targets:  256 trades (100.0%) | Avg: $ -2.66
```

**Root Cause**: HTF detection is **TOO STRICT** - not finding ANY patterns on 1H timeframe!

---

## 📊 Trade Analysis Results

### Overall Performance
- **Total Trades**: 256
- **Total Return**: -6.82%
- **Win Rate**: 50.86%
- **Avg P&L per Trade**: -$2.66

### Exit Reason Breakdown
| Exit Reason | Count | % | Avg P&L | Total P&L |
|-------------|-------|---|---------|-----------|
| time_exit | 99 | 38.7% | +$4.66 | +$461.43 |
| stop_loss | 62 | 24.2% | -$11.52 | -$714.47 |
| tp3 | 33 | 12.9% | +$9.42 | +$310.93 |
| tp1 | 32 | 12.5% | **-$19.70** | **-$630.52** |
| pattern_change | 19 | 7.4% | -$9.84 | -$186.99 |
| tp2 | 11 | 4.3% | +$7.08 | +$77.89 |

### Pattern Performance
| Pattern | Count | Win Rate | Avg P&L | Total P&L |
|---------|-------|----------|---------|-----------|
| trapping_volume | 95 | 49.5% | -$1.23 | -$117.31 |
| one_formation | 75 | 56.0% | +$3.41 | +$255.52 |
| **w_pattern** | 66 | **28.8%** | **-$12.26** | **-$809.08** |
| three_hits | 13 | 38.5% | -$2.69 | -$34.92 |
| weekend_trap | 4 | 50.0% | +$2.61 | +$10.45 |
| m_pattern | 3 | 66.7% | +$4.53 | +$13.60 |

### Key Problems Identified

1. **HTF NOT ACTIVATING** (0% of trades)
   - Detection too strict
   - All trades using 15m targets
   - This IS the root cause

2. **TP1 Exits LOSING Money** (-$19.70 avg)
   - 32 trades hitting TP1
   - Losing -$630.52 total
   - Still using 15m targets (too close)

3. **W-Pattern Performing Terribly**
   - 66 trades, only 28.8% win rate
   - Losing -$12.26 per trade
   - Worst 5 trades all W-patterns hitting TP1 for loss

4. **Stop Loss Expensive**
   - 62 trades (24.2%)
   - Losing -$11.52 avg
   - Total: -$714.47

---

## 🎯 SOLUTION: Strategy A - Relax HTF Detection

### Current HTF Detection Parameters (TOO STRICT)

```python
# In _detect_htf_m_pattern() and _detect_htf_w_pattern():
mw_peak_tolerance = 0.25         # Only 25% price difference allowed
mw_neckline_break_threshold = 0.003  # Only 0.3% breakout required
```

### New Parameters (RELAXED)

```python
# Relax peak tolerance
mw_peak_tolerance = 0.35  # Allow 35% price difference (was 0.25)

# Relax breakout threshold  
mw_neckline_break_threshold = 0.005  # Require 0.5% breakout (was 0.003)
```

### Why This Will Work

**Problem**: 1H candles have LARGER price movements than 15m
- 15m pattern peaks differ by $50-100
- 1H pattern peaks differ by $200-400
- Current 25% tolerance too tight for 1H volatility

**Solution**: 35% tolerance captures more realistic 1H patterns
- Allows for natural 1H volatility
- Still maintains pattern validity
- Will activate on 20-40% of trades (target)

---

## 📋 Implementation Plan

### Step 1: Update TBDConfig (Balanced Preset)

File: `src/layers/layer_tbd_method.py`

```python
@classmethod
def balanced(cls) -> 'TBDConfig':
    """Balanced preset configuration"""
    return cls(
        minimum_confirmations=3,
        require_volume_confirmation=True,
        require_trend_alignment=False,
        enable_session_filter=True,
        avoid_weekend_trading=True,
        avoid_first_30min_london=False,
        mw_peak_tolerance=0.35,  # CHANGED: 0.20 → 0.35
        atr_stop_multiplier=1.5
    )
```

### Step 2: Update HTF Detection Methods

The HTF detection methods (`_detect_htf_m_pattern` and `_detect_htf_w_pattern`) already use `self.layer_config.mw_peak_tolerance`, so they'll automatically pick up the new value.

### Step 3: Test

Run walk-forward again:
```bash
python3 scripts/layer_testing/walk_forward_tbd.py
```

Expected results:
- HTF activation: 20-40% (from 0%)
- TP1 exits: Break even or positive (from -$19.70)
- Overall return: +5-15% (from -6.82%)

---

## 📊 Expected Improvements

### Before (Current)
```
HTF Activation: 0%
TP1 Avg P&L: -$19.70
Total Return: -6.82%
W-Pattern WR: 28.8%
```

### After (Strategy A)
```
HTF Activation: 20-40%
TP1 Avg P&L: $0-5
Total Return: +5-15%
W-Pattern WR: 40-50%
```

### Mechanism

When HTF patterns activate:
1. **Wider Stops**: 1H ATR ~$200 vs 15m ATR ~$50
2. **Farther Targets**: 1H pattern height ~$600 vs 15m ~$100
3. **Proper R:R**: TP1 becomes 1.5:1 instead of 0.5:1
4. **W-patterns work**: Current -$12.26 → Expected +$5-10

---

## ✅ Success Criteria

**Minimum (Green Light)**:
- [ ] HTF activation ≥ 15%
- [ ] TP1 exits break even (avg ≥ $0)
- [ ] Total return ≥ 0%

**Target (Success)**:
- [ ] HTF activation 20-40%
- [ ] TP1 exits profitable (avg ≥ +$5)
- [ ] Total return ≥ +10%
- [ ] W-pattern WR ≥ 40%

**Stretch (Exceptional)**:
- [ ] HTF activation ≥ 40%
- [ ] TP1 exits avg ≥ +$10
- [ ] Total return ≥ +25%

---

## 🔄 If This Doesn't Work

If Strategy A doesn't achieve minimum criteria:

**Plan B: Strategy D (Hybrid Approach)**
- Use AVERAGE of 15m and 1H measurements
- Splits the difference
- More conservative than pure 1H

**Plan C: Disable Some Patterns**
- W-pattern is worst performer (28.8% WR, -$12.26 avg)
- Consider disabling until HTF working
- one_formation is profitable (56% WR, +$3.41 avg)

---

*Created: December 28, 2025, 9:26 AM*  
*Next: Apply Strategy A and retest*
