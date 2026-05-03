# CRITICAL DISCOVERY: PARTIAL EXITS NOT IMPLEMENTED
**Date**: February 13, 2026  
**Analyst**: NAUTILUS EXPERT  
**Status**: ROOT CAUSE CONFIRMED - Feature Not Implemented

---

## 🚨 CRITICAL FINDING

**PARTIAL EXITS ARE NOT IMPLEMENTED** - The system is treating ALL TPs as full position exits, not partial exits.

### Evidence from Trades Panel Log:

**ALL 95 trades show**:
```json
{
  "size": 0.1,  // Full position size
  "exit_type": "STOP_LOSS" | "TAKE_PROFIT" | "TIME_LIMIT",
  "exit_condition_name": "SL" | "TP3" | "MAX_BARS",
  "partial_exit_percentage": null  // ← ALWAYS NULL!
}
```

**What this means**:
- Every trade has exactly ONE exit (full position close)
- No incremental/partial exits at TP1, TP2
- When TP3 hits, entire position closes (not just remaining 34%)

---

## 📊 ACTUAL VS EXPECTED BEHAVIOR

### EXPECTED (User's Design):

```
Entry: 0.1 BTC SHORT at $90,000

Bar  27: Price $88,500 → TP1 HIT
         → Exit 33% (0.033 BTC) at $88,500
         → SL moves to breakeven ($90,000)
         → Remaining: 0.067 BTC

Bar  45: Price $87,800 → TP2 HIT
         → Exit 33% (0.033 BTC) at $87,800
         → SL moves to TP1 ($88,500)
         → Remaining: 0.034 BTC

Bar  78: Price $87,000 → TP3 HIT
         → Exit 34% (0.034 BTC) at $87,000
         → Position CLOSED
         → Total exits: 3 partial exits

Final: 3 separate exit transactions, progressive profit locking
```

### ACTUAL (Current Implementation):

```
Entry: 0.1 BTC SHORT at $90,000

Bar 200: Price $77,000 → TP3 HIT
         → Exit 100% (0.1 BTC) at $77,000
         → Position CLOSED
         → Total exits: 1 full exit

Final: Single exit transaction, all-or-nothing
```

---

##🔍 WHY TP1/TP2 SHOW AS "0"

The "TP/SL Adjustments" counter is **NOT** counting partial exits. It's counting:
- **TP1: 0** → TP1 never used (no partial exit feature)
- **TP2: 0** → TP2 never used (no partial exit feature)  
- **TP3: 44** → TP3 hit 44 times as FULL exit
- **SL: 3025** → SL adjustments DURING trades (trailing, breakeven moves)

**"SL adjustments"** = Moving SL during trade (e.g., to breakeven after TP1)
**"TP hits"** = Final full exit at that level

---

## 🔧 WHAT NEEDS TO BE IMPLEMENTED

### 1. Partial Exit Logic in Simulator

**File**: `src/strategies/universal_optimizer/modules/ultra_hybrid_simulator.py`

**Required Changes**:
```python
# CURRENT (BROKEN):
if bar['low'] <= current_position['tp1']:
    # Close entire position
    exit_price = bar['close']
    close_position(100%)

# REQUIRED (CORRECT):
if bar['low'] <= current_position['tp1'] and not current_position['tp1_hit']:
    # Partial exit 33%
    partial_exit_size = position_size * 0.33
    exit_price = bar['close']
    
    # Record partial exit
    registry.add_trade(
        id=f"{trade_id}_TP1",
        size=partial_exit_size,
        exit_price=exit_price,
        exit_type="PARTIAL_TP1",
        partial_exit_percentage=33
    )
    
    # Update position
    current_position['remaining_size'] -= partial_exit_size
    current_position['tp1_hit'] = True
    
    # Move SL to breakeven
    current_position['sl'] = entry_price
```

### 2. Position Size Tracking

Track remaining position size:
```python
current_position = {
    'entry_size': 0.1,
    'remaining_size': 0.1,  # Decreases with each partial
    'exits': [
        {'level': 'TP1', 'size': 0.033, 'price': 88500},
        {'level': 'TP2', 'size': 0.033, 'price': 87800},
        {'level': 'TP3', 'size': 0.034, 'price': 87000}
    ]
}
```

### 3. Trade Registry Updates

**File**: `src/optimizer_v3/core/trade_registry.py`

Support multiple exit records for one entry:
```python
# One entry signal
registry.open_trade(id="TRADE_1", entry_price=90000, size=0.1)

# Multiple exit records
registry.add_partial_exit(id="TRADE_1_TP1", size=0.033, price=88500, exit_type="TP1")
registry.add_partial_exit(id="TRADE_1_TP2", size=0.033, price=87800, exit_type="TP2")
registry.close_trade(id="TRADE_1_TP3", size=0.034, price=87000, exit_type="TP3")
```

### 4. SL Protection Logic

After each TP hit:
```python
if tp1_hit:
    # Move SL to breakeven
    current_position['sl'] = entry_price

if tp2_hit:
    # Move SL to TP1 price (protect partial profits)
    current_position['sl'] = current_position['tp1_price']

if near_tp3:  
    # Trailing SL to maximize TP3
    trailing_sl = calculate_trailing(best_price, trailing_pct=0.5%)
    if trailing_sl > current_position['sl']:
        current_position['sl'] = trailing_sl
```

---

## 📋 IMPLEMENTATION CHECKLIST

**To implement proper partial exits**:

- [ ] Modify `ultra_hybrid_simulator.py` to handle partial exits
- [ ] Add `remaining_size` tracking to position dict
- [ ] Implement partial exit execution (33%, 33%, 34%)
- [ ] Add SL adjustment after TP1 hit (move to breakeven)
- [ ] Add SL adjustment after TP2 hit (move to TP1)
- [ ] Add trailing SL logic near TP3
- [ ] Update trade_registry to support multiple exits per entry
- [ ] Add partial_exit_percentage field to trade records
- [ ] Test partial exit flow with real data
- [ ] Verify PnL calculation across multiple exits

---

## ⚠️  WHY MY FIXES DIDN'T WORK

I was trying to fix TP calculation when the real issue is:
- **TPs are calculated correctly**
- **But partial exit EXECUTION is not implemented**
- System uses TPs as full-exit triggers, not partial-exit triggers

Changing Fibonacci multipliers just changed WHERE the full exit happens, not HOW MANY exits happen.

---

## 🎯 NEXT STEPS

1. **Confirm this finding with user**
2. **Review sprint docs to see if partial exits were planned**
3. **Implement partial exit logic in simulator**
4. **Test with small dataset first**
5. **Validate metrics match expectations**

---

**Status**: Partial exits are a MISSING FEATURE, not a bug  
**Complexity**: MEDIUM - Requires multi-exit position tracking  
**Impact**: HIGH - Fundamental to trading strategy design  
**Estimated Effort**: 4-6 hours to implement correctly

