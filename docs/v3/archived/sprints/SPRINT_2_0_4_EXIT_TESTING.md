# SPRINT 2.0.4: EXIT MANAGEMENT & TESTING
**Implement Real Exit Detection & Complete Integration Testing**

**Parent Sprint**: Sprint 2.0 - Real Data Integration  
**Duration**: 2 days  
**Tasks**: 7  
**Status**: ☐ Not Started  
**Priority**: 🔴 CRITICAL - Final integration & validation  
**Dependencies**: Sprint 2.0.1, 2.0.2, 2.0.3 Complete

---

## 🎯 SPRINT OBJECTIVE

Implement real exit detection, replace all remaining fake data, complete integration testing.

**Current State** (Fake exits & prices):
```python
# Line 188: Predetermined win/loss
is_win = trade_id <= 14  # First 14 are wins - FAKE!

# Line 156: Fake prices
entry_price = 50000 + (trade_id * 100)  # FAKE!

# Line 157: Fake timestamps
entry_timestamp = datetime.now() - timedelta(...)  # FAKE!
```

**Target State** (Real exits & data):
```python
# Check real TP/SL hits
if bar.low <= position.stop_loss:
    close_position(position, position.stop_loss, 'SL')
elif bar.high >= position.take_profit:
    close_position(position, position.take_profit, 'TP')

# Real prices from bars
entry_price = float(bar.close)  # REAL!

# Real timestamps from bars
entry_timestamp = bar.ts_event  # REAL!

# Real PnL calculation
pnl = (exit_price - entry_price) * position.size  # REAL!
```

---

## ✅ TASK CHECKLIST

- [ ] 2.0.4.1: Implement TP/SL hit detection
- [ ] 2.0.4.2: Implement exit condition evaluation
- [ ] 2.0.4.3: Replace fake prices with real bar prices
- [ ] 2.0.4.4: Replace fake timestamps with real bar timestamps
- [ ] 2.0.4.5: Calculate real PnL (not predetermined)
- [ ] 2.0.4.6: Complete integration testing
- [ ] 2.0.4.7: Functional & data accuracy validation

---

## 📝 DETAILED TASK IMPLEMENTATION

### **Task 2.0.4.1: Implement TP/SL Hit Detection**
**Duration**: 3 hours  
**File**: `src/strategy_builder/ui/backtest_config_panel.py`  
**Dependencies**: Sprint 2.0.3

**Objective**: Detect when price hits TP or SL levels

**Implementation**:

```python
# In BacktestWorker.run()
# Inside main bar processing loop

for i, bar in enumerate(bars):
    # ... signal evaluation (from Sprint 2.0.2) ...
    
    # === CHECK EXITS FOR OPEN POSITIONS ===
    for pos_id, position in list(open_positions.items()):
        
        # Check if SL hit (bar low touched SL)
        if bar.low <= position.stop_loss:
            # SL HIT!
            exit_price = position.stop_loss
            exit_reason = 'SL'
            exit_timestamp = bar.ts_event
            
            # Calculate PnL
            if position.side == 'LONG':
                pnl = (exit_price - position.entry_price) * position.size
            else:
                pnl = (position.entry_price - exit_price) * position.size
            
            # Close position
            self._close_position(
                pos_id,
                position,
                exit_price,
                exit_reason,
                exit_timestamp,
                pnl
            )
            
            # Remove from open positions
            del open_positions[pos_id]
            
            self.live_message.emit(
                f"Position {pos_id} closed: {exit_reason} at {exit_price:.2f} "
                f"(PnL: ${pnl:.2f})",
                "TRADE",
                "EXIT"
            )
            
            continue  # Position closed, skip other checks
        
        # Check if TP hit (bar high touched TP)
        elif bar.high >= position.take_profit:
            # TP HIT!
            exit_price = position.take_profit
            exit_reason = 'TP'
            exit_timestamp = bar.ts_event
            
            # Calculate PnL
            if position.side == 'LONG':
                pnl = (exit_price - position.entry_price) * position.size
            else:
                pnl = (position.entry_price - exit_price) * position.size
            
            # Close position
            self._close_position(
                pos_id,
                position,
                exit_price,
                exit_reason,
                exit_timestamp,
                pnl
            )
            
            # Remove from open positions
            del open_positions[pos_id]
            
            self.live_message.emit(
                f"Position {pos_id} closed: {exit_reason} at {exit_price:.2f} "
                f"(PnL: ${pnl:.2f})",
                "TRADE",
                "EXIT"
            )
            
            continue
        
        # If Adaptive SL enabled, update SL
        elif self.config.get('sl_mode') == 'Adaptive v2.0':
            bars_since_entry = i - position.entry_bar_index
            
            sl_result = adaptive_sl_manager.update_sl(
                position_entry_price=position.entry_price,
                current_bar=bar,
                bars_since_entry=bars_since_entry,
                lookback_bars=bars[max(0, i-20):i],
                config=self.config,
                entry_side=position.side
            )
            
            # Update SL if changed
            if sl_result.new_sl != position.stop_loss:
                old_sl = position.stop_loss
                position.stop_loss = sl_result.new_sl
                
                self.live_message.emit(
                    f"Position {pos_id}: SL updated {old_sl:.2f} → {sl_result.new_sl:.2f} "
                    f"({sl_result.reason})",
                    "INFO",
                    "RISK"
                )

def _close_position(
    self,
    pos_id: int,
    position: Position,
    exit_price: float,
    exit_reason: str,
    exit_timestamp: datetime,
    pnl: float
):
    """Close position and emit trade data"""
    
    # Calculate metrics
    bars_held = position.bars_held
    duration_minutes = bars_held * 15  # 15m bars
    
    # Emit closed trade to Trades panel
    self.trade_data_emit.emit({
        'id': str(pos_id),
        'entry_timestamp': position.entry_timestamp,
        'entry_price': position.entry_price,
        'exit_timestamp': exit_timestamp,
        'exit_price': exit_price,
        'side': position.side,
        'size': position.size,
        'pnl': pnl,
        'exit_reason': exit_reason,
        'bars_held': bars_held,
        'duration_minutes': duration_minutes,
        'status': 'CLOSED'
    })
```

**Testing**:
```python
def test_sl_hit_detection():
    """Test SL hit detection"""
    # Create position with SL at 49500
    position = create_test_position(
        entry_price=50000,
        stop_loss=49500,
        side='LONG'
    )
    
    # Create bar that touches SL
    bar = create_bar(low=49450, high=50100, close=49900)
    
    # Check SL hit
    assert bar.low <= position.stop_loss  # Should trigger SL
    
def test_tp_hit_detection():
    """Test TP hit detection"""
    # Create position with TP at 51000
    position = create_test_position(
        entry_price=50000,
        take_profit=51000,
        side='LONG'
    )
    
    # Create bar that touches TP
    bar = create_bar(low=50500, high=51100, close=51050)
    
    # Check TP hit
    assert bar.high >= position.take_profit  # Should trigger TP
```

**Acceptance Criteria**:
- [ ] SL hit detection working
- [ ] TP hit detection working
- [ ] Positions close on TP/SL hits
- [ ] Exit price = TP/SL level (not bar close)
- [ ] PnL calculated correctly
- [ ] All tests passing

**Functional Test**:
- [ ] Open position with SL at 49500
- [ ] Bar touches 49450 (below SL)
- [ ] Verify position closes
- [ ] Verify exit price = 49500 (SL level)
- [ ] Verify exit reason = 'SL'

**Data Accuracy Test**:
- [ ] Entry: 50000, SL: 49500, Size: 0.1 BTC
- [ ] Bar touches SL at 49450
- [ ] Verify exit_price = 49500 (exactly)
- [ ] Verify PnL = (49500 - 50000) × 0.1 = -50 USD
- [ ] Verify exit_reason = 'SL'

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.4.2: Implement Exit Condition Evaluation**
**Duration**: 3 hours  
**File**: `src/strategy_builder/ui/backtest_config_panel.py`  
**Dependencies**: 2.0.4.1

**Objective**: Support exit based on opposite signal or max bars held

**Implementation**:

```python
# In exit checking loop (after TP/SL checks)

# Check exit conditions
elif self.config.get('use_exit_conditions', False):
    # Evaluate opposite signals
    exit_result = self.signal_evaluator.evaluate_exit_signals(
        current_bar=bar,
        lookback_bars=bars[max(0, i-100):i],
        position_side=position.side
    )
    
    if exit_result.should_exit:
        # Exit condition triggered!
        exit_price = bar.close
        exit_reason = f'EXIT_CONDITION: {exit_result.reason}'
        exit_timestamp = bar.ts_event
        
        # Calculate PnL
        if position.side == 'LONG':
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size
        
        self._close_position(
            pos_id,
            position,
            exit_price,
            exit_reason,
            exit_timestamp,
            pnl
        )
        
        del open_positions[pos_id]
        continue

# Check max bars held
max_bars = self.config.get('max_bars_held', 96)  # Default 24 hours (96 × 15m)
bars_held = i - position.entry_bar_index

if bars_held >= max_bars:
    # Max duration reached
    exit_price = bar.close
    exit_reason = f'MAX_DURATION ({bars_held} bars)'
    exit_timestamp = bar.ts_event
    
    # Calculate PnL
    if position.side == 'LONG':
        pnl = (exit_price - position.entry_price) * position.size
    else:
        pnl = (position.entry_price - exit_price) * position.size
    
    self._close_position(
        pos_id,
        position,
        exit_price,
        exit_reason,
        exit_timestamp,
        pnl
    )
    
    del open_positions[pos_id]
```

**Acceptance Criteria**:
- [ ] Exit conditions implemented
- [ ] Max bars held enforced
- [ ] Exits at bar close (not TP/SL price)
- [ ] Exit reasons logged
- [ ] All tests passing

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.4.3-2.0.4.5: Replace Fake Data**

**Task 2.0.4.3**: Replace fake prices (2 hours)
```python
# REMOVE:
# entry_price = 50000 + (trade_id * 100)  # FAKE!

# USE:
entry_price = float(bar.close)  # REAL from bar!
```

**Task 2.0.4.4**: Replace fake timestamps (1 hour)
```python
# REMOVE:
# entry_timestamp = datetime.now() - timedelta(...)  # FAKE!

# USE:
entry_timestamp = bar.ts_event  # REAL from bar!
```

**Task 2.0.4.5**: Calculate real PnL (2 hours)
```python
# REMOVE:
# is_win = trade_id <= 14  # Predetermined!

# USE:
# Real PnL calculation
if position.side == 'LONG':
    pnl = (exit_price - entry_price) * position.size
else:
    pnl = (entry_price - exit_price) * position.size

is_win = pnl > 0  # Real win/loss determination!
```

**Acceptance Criteria** (All 3 tasks):
- [ ] No fake prices anywhere
- [ ] No fake timestamps anywhere
- [ ] No predetermined win/loss
- [ ] All prices from real bars
- [ ] All timestamps from real bars
- [ ] PnL calculated from actual prices

**Verification Commands**:
```bash
# Search for fake data patterns
grep -n "50000 +" src/strategy_builder/ui/backtest_config_panel.py  # Should be 0
grep -n "datetime.now() -" src/strategy_builder/ui/backtest_config_panel.py  # Should be 0
grep -n "is_win = trade_id" src/strategy_builder/ui/backtest_config_panel.py  # Should be 0
grep -n "trade_schedule" src/strategy_builder/ui/backtest_config_panel.py  # Should be 0
grep -n "14040" src/strategy_builder/ui/backtest_config_panel.py  # Should be 0
```

**Sign-off**: ☐ Developer ☐ QA ☐ Lead

---

### **Task 2.0.4.6: Complete Integration Testing**
**Duration**: 6 hours  
**Dependencies**: ALL previous tasks

**Objective**: End-to-end testing of complete system

**Test Scenarios**:

**1. Complete Backtest Flow** (Happy Path):
- [ ] Create strategy with 2 building blocks
- [ ] Set date range: Dec 1-31, 2025
- [ ] Set TP/SL mode: Fibonacci
- [ ] Set SL mode: Adaptive v2.0
- [ ] Click "Run Test"
- [ ] Verify:
  - Real bars load from DataManager
  - Signals evaluate on each bar
  - Entries triggered by real signals
  - TP/SL calculated from real bars
  - Adaptive SL updates each candle
  - Exits triggered by TP/SL hits
  - Real PnL calculated
  - All tabs populate with real data

**2. Multiple Trades Lifecycle**:
- [ ] Run backtest with aggressive strategy
- [ ] Verify multiple positions open simultaneously
- [ ] Verify each position managed independently
- [ ] Verify SL updates for each position
- [ ] Verify exits handled correctly

**3. Different TP/SL Modes**:
- [ ] Test Fibonacci mode
- [ ] Test Hybrid mode
- [ ] Test Fixed mode
- [ ] Verify different TP/SL levels

**4. Adaptive SL Lifecycle**:
- [ ] Position opens
- [ ] Verify emergency SL (bars 0-9)
- [ ] Verify transition to adaptive (bar 10+)
- [ ] Verify SL trails with price
- [ ] Verify min/max constraints

**5. Performance Testing**:
- [ ] 30-day backtest - complete < 30s
- [ ] 90-day backtest - complete < 90s
- [ ] 180-day backtest - complete < 180s
- [ ] Memory usage < 500MB

**6. Edge Cases**:
- [ ] No signals fire - verify 0 trades
- [ ] All signals fire - verify many trades
- [ ] TP/SL both touched same bar - verify SL priority
- [ ] Position held max duration - verify forced close

**Acceptance Criteria**:
- [ ] All test scenarios passing
- [ ] No hardcoded data remaining
- [ ] Performance acceptable
- [ ] Memory usage acceptable
- [ ] No crashes or errors

**Sign-off**: ☐ Developer ☐ QA ☐ Lead

---

### **Task 2.0.4.7: Functional & Data Accuracy Validation**
**Duration**: 4 hours  
**Dependencies**: 2.0.4.6

**Objective**: Rigorous validation of data accuracy

**Validation Tests**:

**1. Price Accuracy**:
- [ ] Manual verification: Select random trade
- [ ] Check entry bar in raw data
- [ ] Verify entry_price = bar.close (exactly)
- [ ] Check exit bar in raw data
- [ ] Verify exit_price = TP or SL level (exactly)
- [ ] No price discrepancies

**2. Timestamp Accuracy**:
- [ ] Verify entry_timestamp = entry bar ts_event
- [ ] Verify exit_timestamp = exit bar ts_event
- [ ] Verify chronological order
- [ ] Verify 15m intervals

**3. PnL Accuracy**:
- [ ] Manual PnL calculation for random trades
- [ ] Compare to system PnL
- [ ] Verify exact match
- [ ] Test winning and losing trades
- [ ] Verify sum(PnL) = total PnL

**4. Trade Count Validation**:
- [ ] Run same strategy twice
- [ ] Verify identical trade count
- [ ] Verify identical entry/exit points
- [ ] Verify deterministic behavior

**5. Metrics Validation**:
- [ ] Verify win rate = wins / total
- [ ] Verify avg win = sum(winning_pnl) / wins
- [ ] Verify avg loss = sum(losing_pnl) / losses
- [ ] Verify max drawdown calculation
- [ ] Verify Sharpe ratio (if applicable)

**6. Tab Population**:
- [ ] Trades tab: All trades listed
- [ ] Metrics tab: All metrics accurate
- [ ] Live Output: All messages logged
- [ ] AI Recommendations: Based on real metrics

**Acceptance Criteria**:
- [ ] All prices match real bars (100%)
- [ ] All timestamps match real bars (100%)
- [ ] All PnL calculations accurate (100%)
- [ ] Deterministic behavior verified
- [ ] All metrics accurate
- [ ] All tabs populate correctly

**Sign-off**: ☐ Developer ☐ QA ☐ Data Analyst ☐ Lead

---

## 📊 SPRINT 2.0.4 COMPLETION CRITERIA

**Complete When**:
- [ ] All 7 tasks complete
- [ ] TP/SL hit detection working
- [ ] Exit conditions implemented
- [ ] No fake data anywhere
- [ ] Real prices, timestamps, PnL
- [ ] All integration tests passing
- [ ] All data accuracy tests passing
- [ ] Performance acceptable

**Final Verification Checklist**:
- [ ] No hardcoded 14040
- [ ] No hardcoded trade_schedule
- [ ] No fake prices (50000 + offset)
- [ ] No fake timestamps
- [ ] No predetermined win/loss
- [ ] All 5 hardcoded sources GONE
- [ ] System runs 100% on real data

**Sign-off Required**:
- [ ] Developer
- [ ] QA (Functional)
- [ ] QA (Data Accuracy)
- [ ] Lead
- [ ] Nautilus Expert
- [ ] Risk Manager

---

## 🎉 SPRINT 2.0 COMPLETE!

**When Sprint 2.0.4 is complete, the entire Sprint 2.0 is DONE:**

✅ Sprint 2.0.1: Data Loading (COMPLETE)  
✅ Sprint 2.0.2: Signal Evaluation (COMPLETE)  
✅ Sprint 2.0.3: TP/SL Management (COMPLETE)  
✅ Sprint 2.0.4: Exit Management & Testing (COMPLETE)

**System State**:
- ✅ 100% real data integration
- ✅ 0% hardcoded data
- ✅ Real bars from DataManager
- ✅ Real signal evaluation
- ✅ Real TP/SL calculation
- ✅ Real exit detection
- ✅ Real pricing and timestamps
- ✅ Real PnL calculation

**Next Phase**: Production deployment or Sprint 2.1+ features!
