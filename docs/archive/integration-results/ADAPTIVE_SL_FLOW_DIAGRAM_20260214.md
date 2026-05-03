# ADAPTIVE SL V2.0 - COMPLETE FLOW DIAGRAM
**Date:** 2026-02-14  
**Analysis:** Code-Based Implementation Flow

---

## OVERVIEW

Adaptive SL v2.0 protects trades using two modes:
1. **Emergency SL** (during delay period) - Fixed % from entry
2. **Adaptive SL** (post-delay) - ATR-based trailing stop

---

## COMPLETE FLOW DIAGRAM

```
┌────────────────────────────────────────────────────────────────┐
│ TRADE ENTRY - Bar N                                            │
│                                                                │
│ 1. Signal fires → Enter trade                                 │
│ 2. tpsl_calculator.calculate_levels()                         │
│    → Sets INITIAL SL (from Fibonacci/Fixed/ATR mode)          │
│ 3. Store: trade.tpsl_levels.stop_loss                         │
│ 4. Store: trade.initial_sl                                    │
│ 5. Store: trade.entry_bar = N                                 │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ EVERY SUBSEQUENT BAR (N+1, N+2, N+3...)                       │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ STEP 1: UPDATE SL                                        │  │
│ │                                                          │  │
│ │ if adaptive_sl_config.get('enabled') == True:           │  │
│ │     adaptive_sl_manager.update_sl(...)                  │  │
│ │                                                          │  │
│ │     Calculate: bars_since_entry = current_bar - N       │  │
│ │     Get: delay_bars from config (e.g., 2)               │  │
│ │                                                          │  │
│ │     ┌────────────────────────────────────────┐          │  │
│ │     │ DECISION: Which SL Mode?               │          │  │
│ │     │                                        │          │  │
│ │     │ if bars_since_entry < delay_bars:     │          │  │
│ │     │     → EMERGENCY SL MODE                │          │  │
│ │     │ else:                                  │          │  │
│ │     │     → ADAPTIVE SL MODE                 │          │  │
│ │     └────────────────────────────────────────┘          │  │
│ └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ EMERGENCY SL MODE (Bars 0 to delay_bars-1)                    │
│                                                                │
│ Purpose: Tight protection during initial bars                 │
│                                                                │
│ Calculation:                                                   │
│   emergency_sl_pct = config.get('emergency_sl_pct', 1.0)      │
│   emergency_sl_percent = emergency_sl_pct / 100.0             │
│                                                                │
│   if side == 'LONG':                                           │
│       new_sl = entry_price * (1 - emergency_sl_percent)       │
│   else:  # SHORT                                               │
│       new_sl = entry_price * (1 + emergency_sl_percent)       │
│                                                                │
│ Example (SHORT @ $100,000, emergency_sl_pct=1):               │
│   emergency_sl_percent = 1.0 / 100 = 0.01 (1%)                │
│   new_sl = $100,000 * 1.01 = $101,000                         │
│   → If price rises to $101,000, EXIT!                         │
│                                                                │
│ Example (SHORT @ $100,000, emergency_sl_pct=5):               │
│   emergency_sl_percent = 5.0 / 100 = 0.05 (5%)                │
│   new_sl = $100,000 * 1.05 = $105,000                         │
│   → If price rises to $105,000, EXIT!                         │
│                                                                │
│ Return: AdaptiveSLResult(                                     │
│     new_sl = emergency_sl,                                    │
│     sl_mode = 'EMERGENCY',                                    │
│     atr_value = 0.0,                                          │
│     sl_distance = abs(entry_price - emergency_sl)             │
│ )                                                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ ADAPTIVE SL MODE (Bars >= delay_bars)                         │
│                                                                │
│ Purpose: ATR-based trailing stop that adapts to volatility    │
│                                                                │
│ Step 1: Calculate ATR                                         │
│   vol_lookback = config.get('volatility_lookback', 20)        │
│   atr = _calculate_atr(lookback_bars[-vol_lookback:])         │
│                                                                │
│ Step 2: Calculate SL Distance                                 │
│   vol_multi = config.get('volatility_multiplier', 1.5)        │
│   sl_distance = atr * vol_multi                               │
│                                                                │
│ Step 3: Apply Min/Max Constraints                             │
│   min_sl_pct = config.get('min_sl_pct', 0.7) / 100.0          │
│   max_sl_pct = config.get('max_sl_pct', 2.0) / 100.0          │
│                                                                │
│   min_distance = entry_price * min_sl_pct                     │
│   max_distance = entry_price * max_sl_pct                     │
│                                                                │
│   sl_distance = max(sl_distance, min_distance)                │
│   sl_distance = min(sl_distance, max_distance)                │
│                                                                │
│ Step 4: Calculate SL Level (TRAILING)                         │
│   if side == 'LONG':                                           │
│       new_sl = current_bar.close - sl_distance                │
│       new_sl = min(new_sl, entry_price * 0.998)  # Cap        │
│   else:  # SHORT                                               │
│       new_sl = current_bar.close + sl_distance                │
│       new_sl = max(new_sl, entry_price * 1.002)  # Cap        │
│                                                                │
│ Example (SHORT @ $100,000 entry, current $95,000):            │
│   ATR = $500, vol_multi = 1.5                                 │
│   sl_distance = $500 * 1.5 = $750                             │
│   new_sl = $95,000 + $750 = $95,750                           │
│   → If price rises to $95,750, EXIT!                          │
│   → SL TRAILS price down (gets tighter as profit increases)   │
│                                                                │
│ Return: AdaptiveSLResult(                                     │
│     new_sl = new_sl,                                          │
│     sl_mode = 'ADAPTIVE',                                     │
│     atr_value = atr,                                          │
│     sl_distance = sl_distance                                 │
│ )                                                              │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: APPLY NEW SL TO TRADE                                 │
│                                                                │
│ trade.tpsl_levels.stop_loss = sl_result.new_sl                │
│ trade.sl_mode = sl_result.sl_mode                             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: CHECK IF PRICE HIT SL                                 │
│                                                                │
│ current_price = current_bar.close                             │
│ tpsl = trade.tpsl_levels                                      │
│                                                                │
│ if side == 'LONG':                                             │
│     if current_price <= tpsl.stop_loss:                       │
│         → EXIT TRADE (Stop Loss Hit)                          │
│ else:  # SHORT                                                 │
│     if current_price >= tpsl.stop_loss:                       │
│         → EXIT TRADE (Stop Loss Hit)                          │
│                                                                │
│ If NO SL hit:                                                  │
│     → Continue to next bar                                    │
│     → Repeat from STEP 1                                      │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ FALLBACK: MAX BARS CHECK                                      │
│                                                                │
│ if not result.should_exit:  # No SL/TP hit                    │
│     max_bars = config.get('max_bars_held', 200)               │
│     if bars_held >= max_bars:                                 │
│         → EXIT TRADE (Time Limit)                             │
└────────────────────────────────────────────────────────────────┘
```

---

## EXAMPLE TRADE LIFECYCLE

**Configuration:**
- Strategy: SHORT (Bearish)
- Emergency SL: 1% (bar 0-1)
- Delay Bars: 2
- Volatility Lookback: 20
- Volatility Multiplier: 1.5
- Min SL: 0.7%, Max SL: 2.0%

**Trade Execution:**

```
BAR 0 (Entry):
  Entry Price: $100,000
  Initial SL: $101,000 (from tpsl_calculator, 1% Fibonacci)
  
  → adaptive_sl_manager.update_sl()
  bars_since_entry = 0
  0 < 2 (delay_bars) → EMERGENCY MODE
  emergency_sl_percent = 1.0 / 100 = 0.01
  new_sl = $100,000 * 1.01 = $101,000
  
  trade.tpsl_levels.stop_loss = $101,000 ✅
  trade.sl_mode = 'EMERGENCY'
  
  Check: current_price ($100,000) >= $101,000? NO
  → Continue

BAR 1:
  Current Price: $99,500 (down $500, PROFIT!)
  
  → adaptive_sl_manager.update_sl()
  bars_since_entry = 1
  1 < 2 → EMERGENCY MODE
  new_sl = $100,000 * 1.01 = $101,000 (unchanged)
  
  trade.tpsl_levels.stop_loss = $101,000 ✅
  
  Check: current_price ($99,500) >= $101,000? NO
  → Continue

BAR 2:
  Current Price: $98,000 (down $2,000, MORE PROFIT!)
  
  → adaptive_sl_manager.update_sl()
  bars_since_entry = 2
  2 >= 2 → ADAPTIVE MODE! ⭐
  
  ATR (20 bars) = $500
  sl_distance = $500 * 1.5 = $750
  
  min_distance = $100,000 * 0.007 = $700
  max_distance = $100,000 * 0.02 = $2,000
  sl_distance = max($750, $700) = $750
  sl_distance = min($750, $2,000) = $750 ✅
  
  new_sl = $98,000 + $750 = $98,750
  new_sl = max($98,750, $100,000 * 1.002) = $100,200
  
  trade.tpsl_levels.stop_loss = $100,200 ✅
  trade.sl_mode = 'ADAPTIVE'
  
  Check: current_price ($98,000) >= $100,200? NO
  → Continue

BAR 3:
  Current Price: $97,000 (down $3,000, TRAILING!)
  
  → adaptive_sl_manager.update_sl()
  bars_since_entry = 3
  3 >= 2 → ADAPTIVE MODE
  
  ATR = $520
  sl_distance = $520 * 1.5 = $780
  [constraints: $700 < $780 < $2,000] ✅
  
  new_sl = $97,000 + $780 = $97,780
  new_sl = max($97,780, $100,200) = $100,200  # Can't widen!
  
  trade.tpsl_levels.stop_loss = $100,200 ✅ (unchanged)
  
  Check: current_price ($97,000) >= $100,200? NO
  → Continue

BAR 4:
  Current Price: $101,500 (REVERSAL! Price rising!)
  
  → adaptive_sl_manager.update_sl()
  bars_since_entry = 4
  3 >= 2 → ADAPTIVE MODE
  
  ATR = $600
  sl_distance = $600 * 1.5 = $900
  
  new_sl = $101,500 + $900 = $102,400
  new_sl = max($102,400, $100,200) = $102,400  # Widens to trail!
  
  trade.tpsl_levels.stop_loss = $102,400 ✅
  
  Check: current_price ($101,500) >= $102,400? NO
  → Continue

BAR 5:
  Current Price: $102,500 (RISING FURTHER!)
  
  → adaptive_sl_manager.update_sl()
  ATR = $650
  sl_distance = $975
  new_sl = $102,500 + $975 = $103,475
  
  trade.tpsl_levels.stop_loss = $103,475 ✅
  
  Check: current_price ($102,500) >= $103,475? NO
  → Continue

BAR 6:
  Current Price: $104,000 (HIT SL!)
  
  → adaptive_sl_manager.update_sl()
  new_sl = $104,000 + $975 = $104,975
  
  trade.tpsl_levels.stop_loss = $104,975 ✅
  
  Check: current_price ($104,000) >= $104,975? NO...
  
  **WAIT! Let's check with high:**
  current_bar.high = $104,500
  
  Check: $104,500 >= $104,975? NO
  
  **Actually checking close:**
  current_bar.close = $104,100
  
  Check: $104,100 >= $104,975? NO
  → Continue

BAR 7:
  Current Price: $105,100
  new_sl = $105,100 + $1,000 = $106,100
  
  Check: $105,100 >= $106,100? NO
  → Continue

(Trade continues until SL hit or max_bars reached)
```

---

## KEY INSIGHTS

### 🔍 Why SL Might Not Trigger

1. **Emergency SL Only Active During Delay** (Bars 0 to delay_bars-1)
   - If delay_bars = 2, emergency only bars 0-1
   - Bar 2+ uses adaptive (can be looser!)

2. **Adaptive SL Trails With Price**
   - SHORT: SL above current price
   - If price falls (profit), SL follows down
   - If price rises (loss), SL widens to give room
   - BUT: Capped by entry_price * 1.002 (can't be below entry initially)

3. **Min/Max Constraints Widen SL**
   - min_sl_pct = 0.7% → minimum $700 distance @ $100k
   - max_sl_pct = 2.0% → maximum $2,000 distance @ $100k
   - Even if ATR * vol_multi = $300, min forces $700!

4. **SHORT Strategy Math**
   - Entry: $100,000
   - 5% Emergency SL: $105,000
   - **Price needs to RISE $5,000 to hit!**
   - If strategy wins (price falls), SL never hits!

### ⚠️ CURRENT BUG HYPOTHESIS

**If still not working after fixes:**

Check if delay_bars is being read correctly:
```python
delay_bars = config.get('delay_bars', config.get('delay_period', 10))
```

If UI sends `delay_period` but code expects `delay_bars`, emergency mode never activates!

**Verification Command:**
```bash
grep "delay_bars\|delay_period" logs/wiring-test/config_received.log
```

---

## DEBUGGING CHECKLIST

- [ ] Emergency SL calculated correctly (no double division)
- [ ] bars_since_entry counting from 0
- [ ] delay_bars read from correct config key
- [ ] SL check runs BEFORE max_bars check
- [ ] Price comparison uses correct direction (>= for SHORT, <= for LONG)
- [ ] adaptive_sl_config.get('enabled') == True
- [ ] SL update applied to trade.tpsl_levels.stop_loss
- [ ] current_price uses bar.close (not bar.high/low)

---

**END OF FLOW DIAGRAM**
