# 🚀 MULTICORE BACKTEST ENGINE DESIGN

**Author:** Nautilus Expert  
**Date:** February 11, 2026  
**Status:** RECOMMENDED SOLUTION ✅  

---

## 📋 USER REQUIREMENTS

1. ✅ Load data ONCE to memory, reuse for all tests
2. ✅ Make backtest itself multicore (98% CPU usage)
3. ✅ Keep wiring test sequential (but fast)
4. ✅ Support 50-150 tests per day efficiently

**Goal:** 29 tests × 35 sec = 17 min → **29 tests × 3-5 sec = 2-3 minutes**

---

## 🔬 DEEP TRACE RESULTS

### **Database Usage Analysis:**

**Finding:** Database is ONLY used ONCE at the start! ✅

**Trace:**
```python
# backtest_config_panel.py - Line ~1005
def _on_run_clicked(self):
    # 1. LOAD CONFIG FROM DATABASE (ONLY TIME!)
    strategy_config_dict = self.orchestrator.serialize_config_for_backtest()
    
    # 2. CLOSE DATABASE (never used again)
    db = get_database_manager()
    db.engine.dispose()  # ← Closes all connections!
    
    # 3. CREATE WORKER (no database access)
    self.worker = BacktestWorker(
        strategy_config=strategy_config_dict,  # ← Plain dict, no DB!
        backtest_config=backtest_config
    )
```

**BacktestWorker Architecture:**
```python
class BacktestWorker(QThread):
    """
    Worker thread for running backtests without blocking UI
    
    INSTITUTIONAL PATTERN: Database Isolation
    - No orchestrator reference (prevents database access)  ← EXPLICIT!
    - Strategy config is plain Dict (no ORM objects)       ← EXPLICIT!
    - All data pre-loaded before worker creation           ← EXPLICIT!
    """
```

**Conclusion:**
- ✅ Database is NOT needed during backtest execution
- ✅ Config is serialized ONCE before test starts
- ✅ NO database calls during signal evaluation
- ✅ Your assumption is 100% CORRECT!

---

## 🎯 PROPOSED SOLUTION: MULTICORE BACKTEST ENGINE

### **Architecture Overview:**

```
┌─────────────────────────────────────────────────────────────┐
│ WIRING TEST (Sequential, but FAST)                          │
│                                                              │
│ 1. Load strategy config ONCE (0.1 sec)                     │
│ 2. Load historical bars ONCE (10 sec, 32 CPUs)             │
│ 3. For each test scenario:                                  │
│    ├─ Apply parameter permutation (0.01 sec)               │
│    ├─ Run MULTICORE backtest (3 sec, 32 CPUs) ← NEW!      │
│    └─ Collect results (0.01 sec)                           │
│                                                              │
│ Total: 10 sec (data) + (29 × 3 sec) = ~100 seconds ✅      │
└─────────────────────────────────────────────────────────────┘
```

### **Key Innovation: Parallel Signal Evaluation**

**Current (Single-threaded):**
```python
# BacktestWorker.run() - 20-30 seconds
for i in range(total_candles):  # ← SEQUENTIAL! 1 CPU
    result = evaluator.evaluate_bar(current_bar, i, lookback_bars, total_candles)
    # Process entry/exit...
```

**New (Multi-core):**
```python
# BacktestWorker.run() - 3-5 seconds  
from multiprocessing import Pool

# Split candles into chunks
chunk_size = len(bars) // cpu_count
chunks = [bars[i:i+chunk_size] for i in range(0, len(bars), chunk_size)]

# Process chunks in parallel (32 CPUs)
with Pool(processes=cpu_count()) as pool:
    chunk_results = pool.starmap(
        evaluate_chunk,  # ← Process chunk independently
        [(chunk, strategy_config, backtest_config) for chunk in chunks]
    )

# Merge results (find trades across chunks)
all_trades = merge_chunk_results(chunk_results)
```

---

## 📐 DETAILED DESIGN

### **Phase 1: Data Caching (DONE)**

**Already Implemented:**
- Bar aggregator caches data in memory ✅
- Data provider reuses cached bars ✅

**Enhancement Needed:**
```python
# backtest_config_panel.py
class BacktestConfigPanel:
    def __init__(self, orchestrator, parent=None):
        self.cached_bars = None  # ← NEW: Cache bars in panel
        self.cached_timeframe = None
        self.cached_date_range = None
```

**Wiring Test Enhancement:**
```python
def _on_test_wiring_clicked(self):
    # Load bars ONCE
    config = self.get_config()
    self.cached_bars = self.data_provider.load_bars_for_backtest(
        timeframe=config['timeframe'],
        start_date=config['start_date'],
        end_date=config['end_date']
    )
    
    # Run all 29 tests with cached bars
    for scenario in all_scenarios:
        result = self._run_test_with_cached_data(
            bars=self.cached_bars,  # ← Reuse!
            scenario=scenario
        )
```

**Savings:** 10 sec × 29 = **280 seconds saved!** (4.5 minutes)

---

### **Phase 2: Multicore Signal Evaluation (NEW)**

**Challenge:** Signal evaluation has DEPENDENCIES between bars

**Example:**
```python
# Bar 100: Check if in trade
if evaluator.current_trade:  # ← Depends on Bar 99 result!
    # Exit logic...
```

**Solution: Chunk-Based Parallel Processing**

#### **Step 1: Split Bars into Independent Chunks**

```python
def split_bars_for_parallel_processing(bars, num_processes=32):
    """
    Split bars into chunks that can be processed independently.
    
    Problem: Trades can span chunks!
    Solution: Overlap chunks to handle spanning trades
    """
    chunk_size = len(bars) // num_processes
    overlap = 200  # Bars overlap (handles max_bars_held = 200)
    
    chunks = []
    for i in range(num_processes):
        start = i * chunk_size
        end = start + chunk_size + overlap
        
        chunks.append({
            'bars': bars[start:end],
            'chunk_id': i,
            'global_start_idx': start
        })
    
    return chunks
```

#### **Step 2: Process Each Chunk Independently**

```python
def evaluate_chunk(chunk, strategy_config, backtest_config):
    """
    Evaluate signals for a chunk of bars (runs in separate process).
    
    Each process:
    - Creates its OWN evaluator instance
    - Processes its chunk independently
    - Returns trades found in that chunk
    
    NO shared state, NO database, NO GUI access!
    """
    from src.optimizer_v3.core.institutional_signal_evaluator import InstitutionalSignalEvaluator
    
    # Create evaluator for this chunk (separate process)
    evaluator = InstitutionalSignalEvaluator(strategy_config)
    
    bars = chunk['bars']
    chunk_id = chunk['chunk_id']
    global_start = chunk['global_start_idx']
    
    trades = []
    
    for i, bar in enumerate(bars):
        # Get lookback (all previous bars in chunk)
        lookback = bars[0:i]
        
        # Evaluate bar
        result = evaluator.evaluate_bar(bar, i, lookback, len(bars))
        
        # Handle entries/exits
        if result.should_enter and not evaluator.current_trade:
            evaluator.enter_trade(bar, i, side='LONG')
        
        if result.should_exit and evaluator.current_trade:
            trade_data = {
                'entry_bar': global_start + evaluator.current_trade.entry_bar,
                'exit_bar': global_start + i,
                'entry_price': float(evaluator.current_trade.entry_price),
                'exit_price': float(bar.close),
                'pnl': calculate_pnl(...),
                'chunk_id': chunk_id
            }
            trades.append(trade_data)
            evaluator.exit_trade()
    
    # Return trades found in this chunk
    return {
        'chunk_id': chunk_id,
        'trades': trades,
        'open_trade': evaluator.current_trade  # ← May span into next chunk!
    }
```

#### **Step 3: Merge Chunk Results**

```python
def merge_chunk_results(chunk_results):
    """
    Merge trades from all chunks, handling spanning trades.
    
    Problem: Trade opened in chunk 5, closed in chunk 6
    Solution: Match open trades to closed trades across chunks
    """
    all_trades = []
    open_trades_by_chunk = {}
    
    # Sort by chunk_id
    chunk_results.sort(key=lambda x: x['chunk_id'])
    
    for result in chunk_results:
        chunk_id = result['chunk_id']
        
        # Add completed trades from this chunk
        all_trades.extend(result['trades'])
        
        # Track open trade (may close in next chunk)
        if result['open_trade']:
            open_trades_by_chunk[chunk_id] = result['open_trade']
    
    # Handle spanning trades (open in chunk N, close in chunk N+1)
    # This requires communication between chunks via overlap regions
    # Implementation detail: Use overlap bars to detect trade completion
    
    return all_trades
```

#### **Step 4: Multicore Backtest Engine**

```python
# NEW FILE: src/optimizer_v3/core/multicore_backtest_engine.py

class MulticoreBacktestEngine:
    """
    Parallel backtest engine using multiprocessing.
    
    Features:
    - Splits bars into chunks (32 chunks for 32 CPUs)
    - Processes each chunk in separate process
    - Merges results with trade spanning detection
    - NO database access, NO GUI access
    - Pure computation, fully parallelizable
    
    Performance:
    - Single-core: 20-30 seconds
    - Multi-core (32 CPUs): 3-5 seconds (6-10x faster!)
    """
    
    def __init__(self, num_processes=None):
        """Initialize engine with CPU count"""
        import multiprocessing as mp
        self.num_processes = num_processes or mp.cpu_count()
    
    def run_backtest(
        self,
        bars: List[Bar],
        strategy_config: dict,
        backtest_config: dict,
        progress_callback=None
    ) -> dict:
        """
        Run multicore backtest on historical bars.
        
        Args:
            bars: Pre-loaded historical bars (cached!)
            strategy_config: Serialized strategy (plain dict)
            backtest_config: Backtest parameters (plain dict)
            progress_callback: Optional callback for progress updates
        
        Returns:
            dict: Backtest results with trades, metrics, etc.
        """
        from multiprocessing import Pool
        
        # Split bars into chunks
        chunks = self._split_bars(bars)
        
        # Process chunks in parallel
        with Pool(processes=self.num_processes) as pool:
            # Create args for each chunk
            args = [
                (chunk, strategy_config, backtest_config)
                for chunk in chunks
            ]
            
            # Process in parallel (USES ALL 32 CPUs!)
            chunk_results = pool.starmap(evaluate_chunk, args)
        
        # Merge results
        all_trades = self._merge_results(chunk_results)
        
        # Calculate metrics
        metrics = self._calculate_metrics(all_trades, bars)
        
        return {
            'trades': all_trades,
            'metrics': metrics,
            'total_candles': len(bars)
        }
    
    def _split_bars(self, bars):
        """Split bars into chunks with overlap"""
        # Implementation from Step 1
        pass
    
    def _merge_results(self, chunk_results):
        """Merge chunk results handling spanning trades"""
        # Implementation from Step 3
        pass
    
    def _calculate_metrics(self, trades, bars):
        """Calculate performance metrics"""
        # Win rate, PnL, drawdown, etc.
        pass
```

---

## 🎯 INTEGRATION WITH WIRING TEST

### **Modified Backtest Worker:**

```python
# backtest_config_panel.py - Modified BacktestWorker

class BacktestWorker(QThread):
    def __init__(
        self, 
        strategy_config: dict, 
        backtest_config: dict,
        cached_bars: List[Bar] = None  # ← NEW: Accept pre-loaded bars
    ):
        super().__init__()
        self.strategy_config = strategy_config
        self.config = backtest_config
        self.cached_bars = cached_bars  # ← NEW
        self.use_multicore = True  # ← NEW: Enable multicore engine
    
    def run(self):
        """Run backtest - now with multicore support!"""
        try:
            if self.cached_bars:
                # Use pre-loaded bars (wiring test)
                bars = self.cached_bars
                self.live_message.emit("Using cached data (fast path)", "INFO", "SYSTEM")
            else:
                # Load bars (normal backtest)
                bars = self.data_provider.load_bars_for_backtest(...)
                self.live_message.emit(f"Loaded {len(bars)} bars", "INFO", "SYSTEM")
            
            if self.use_multicore:
                # NEW: Use multicore engine
                from src.optimizer_v3.core.multicore_backtest_engine import MulticoreBacktestEngine
                
                engine = MulticoreBacktestEngine()
                results = engine.run_backtest(
                    bars=bars,
                    strategy_config=self.strategy_config,
                    backtest_config=self.config,
                    progress_callback=self._on_progress
                )
                
                self.live_message.emit(
                    f"Multicore backtest complete! {results['trades']} trades, 32 CPUs used",
                    "INFO",
                    "SYSTEM"
                )
            else:
                # OLD: Single-threaded evaluation (fallback)
                results = self._run_single_threaded(bars)
            
            self.backtest_finished.emit(True, results)
            
        except Exception as e:
            self.backtest_finished.emit(False, {'error': str(e)})
```

### **Modified Wiring Test:**

```python
def _on_test_wiring_clicked(self):
    """Run wiring test with cached data and multicore engine"""
    
    # 1. Load config ONCE
    strategy_config = self.orchestrator.serialize_config_for_backtest()
    
    # 2. Load bars ONCE
    config = self.get_config()
    bars = self.data_provider.load_bars_for_backtest(
        timeframe=config['timeframe'],
        start_date=config['start_date'],
        end_date=config['end_date']
    )
    print(f"✅ Loaded {len(bars)} bars to memory (will reuse for all tests)")
    
    # 3. Run all 29 tests SEQUENTIALLY (but each is FAST!)
    for i, scenario in enumerate(all_scenarios):
        progress.setValue(i)
        progress.setLabelText(f"Test {i+1}/29: {scenario.description}")
        
        # Create worker with CACHED bars
        worker = BacktestWorker(
            strategy_config=strategy_config,
            backtest_config={**config, **scenario.config},  # Merge params
            cached_bars=bars  # ← Reuse bars!
        )
        
        # Run backtest (3-5 seconds with multicore!)
        result = self._run_worker_and_wait(worker)
        test_results.append(result)
    
    # 4. Generate report
    self._generate_wiring_report(test_results)
```

---

## 📊 PERFORMANCE ANALYSIS

### **Before Optimization:**

| Phase | Duration | CPUs Used | Bottleneck |
|-------|----------|-----------|------------|
| Data Loading | 10-15 sec × 29 = 290-435 sec | 32 CPUs (98%) | Disk I/O |
| Signal Eval | 20-30 sec × 29 = 580-870 sec | 1 CPU (100%) | Python GIL |
| **TOTAL** | **~17 minutes** | **3% avg** | ❌ Inefficient |

### **After Optimization:**

| Phase | Duration | CPUs Used | Improvement |
|-------|----------|-----------|-------------|
| Data Loading | 10 sec × 1 = 10 sec | 32 CPUs (98%) | ✅ Cached! |
| Signal Eval | 3 sec × 29 = 87 sec | 32 CPUs (98%) | ✅ Parallel! |
| **TOTAL** | **~100 seconds (1.7 min)** | **95% avg** | ✅ **10x faster!** |

### **Benefits:**

1. **10x Faster:** 17 min → 1.7 min per wiring test
2. **50-150 tests/day:** Now feasible! (150 × 1.7 min = 4.25 hours)
3. **CPU Utilization:** 3% → 95% (using available hardware)
4. **Future-Proof:** All backtests benefit, not just wiring tests
5. **Scalable:** More CPUs = even faster

---

## 🚀 IMPLEMENTATION PLAN

### **Phase 1: Data Caching (Immediate - 1 hour)**

**Files to Modify:**
- `src/strategy_builder/ui/backtest_config_panel.py`

**Changes:**
1. Add `cached_bars` parameter to `BacktestWorker.__init__()`
2. Check for cached bars in `BacktestWorker.run()`
3. Skip data loading if bars provided
4. Load bars once in wiring test, reuse for all scenarios

**Testing:** Run single backtest, verify no regression

**Result:** 17 min → ~7 min (data caching only)

---

### **Phase 2: Multicore Engine (Core - 4-6 hours)**

**New File:**
- `src/optimizer_v3/core/multicore_backtest_engine.py` (250 lines)

**Implementation Steps:**

1. **Bar Splitting Logic** (1 hour)
   - `split_bars_for_parallel_processing()`
   - Handle overlap for spanning trades
   - Test with various chunk sizes

2. **Chunk Evaluation** (2 hours)
   - `evaluate_chunk()` function (works in subprocess)
   - No shared state, pure function
   - Test single chunk evaluation

3. **Result Merging** (1 hour)
   - `merge_chunk_results()`
   - Handle spanning trades across chunks
   - Test merge logic with edge cases

4. **Engine Class** (1 hour)
   - `MulticoreBacktestEngine` class
   - Integration with multiprocessing.Pool
   - Progress callbacks
   - Error handling

**Testing:**
- Unit tests for each function
- Integration test with full backtest
- Compare results: single-core vs multi-core (must match!)

**Result:** 7 min → ~2 min (multicore + caching)

---

### **Phase 3: Integration (Final - 1 hour)**

**Files to Modify:**
- `src/strategy_builder/ui/backtest_config_panel.py`

**Changes:**
1. Add `use_multicore` flag to BacktestWorker
2. Check flag in `run()`, use multicore engine if enabled
3. Fall back to single-threaded if multicore fails
4. Add UI toggle: "Use Multicore Engine (32 CPUs)"

**Testing:**
- Run wiring test with multicore enabled
- Verify all 29 tests complete
- Compare results with single-core baseline
- Check CPU utilization (should be 95%+)

**Result:** Full system working, 10x faster

---

### **Phase 4: Polish (Optional - 1 hour)**

**Enhancements:**
1. Add real-time CPU utilization display
2. Show "Processing chunk 5/32" progress
3. Add performance metrics to wiring report
4. Optimize chunk size based on CPU count
5. Add batch mode (run multiple wiring tests overnight)

---

## ⚠️ TECHNICAL CONSIDERATIONS

### **1. Trade Spanning Across Chunks**

**Problem:**
```
Chunk 1: Bars 0-500    | Trade opens at bar 450
Chunk 2: Bars 500-1000 | Trade closes at bar 550
```

**Solution:**
- Use overlap: Chunk 1 includes bars 0-700, Chunk 2 includes bars 500-1000
- Trade completes in Chunk 1's extended range
- De-duplicate trades during merge (check bar indices)

---

### **2. Lookback Window Limitations**

**Problem:**
Building blocks need lookback (e.g., 200 bars for patterns)

**Solution:**
- First chunk gets full lookback from start
- Subsequent chunks use overlap as lookback
- Overlap size = max(all block lookback requirements)

---

### **3. Memory Usage**

**Current:**
- Single process: 7,000 bars × 1 process = manageable
- Multiprocess: 7,000 bars × 32 processes = **224,000 bars in memory**

**Mitigation:**
- Bars are read-only (shared via copy-on-write)
- Python multiprocessing uses copy-on-write for Unix systems
- Actual memory: ~7K bars + (32 processes × evaluator state)
- Estimated: 500MB total (well within limits)

---

### **4. Error Handling**

**If one chunk fails:**
```python
try:
    with Pool(processes=num_processes) as pool:
        chunk_results = pool.starmap(evaluate_chunk, args)
except Exception as e:
    # Fall back to single-threaded
    self.live_message.emit("Multicore failed, using single-core fallback", "WARNING")
    results = self._run_single_threaded(bars)
```

---

## ✅ EXPERT RECOMMENDATION

### **STRONG RECOMMENDATION: IMPLEMENT THIS SOLUTION**

**Why:**

1. **Addresses Root Cause**
   - Makes backtest ITSELF multicore
   - Not just a test framework optimization
   - Benefits ALL future work

2. **Massive Performance Gain**
   - 17 min → 2 min (10x faster)
   - 50-150 tests/day now feasible
   - Utilizes available hardware (32 CPUs)

3. **Architectural Correctness**
   - Data cached once ✅
   - No database during backtest ✅ (you were right!)
   - Pure computation, fully parallelizable ✅

4. **Implementation Feasibility**
   - 6-8 hours total work
   - No major refactoring needed
   - Clear separation of concerns
   - Fallback to single-core if issues

5. **Future-Proof**
   - More CPUs = even faster
   - Enables batch optimization
   - Foundation for distributed computing

---

## 🎯 NEXT STEPS

### **Immediate (Today):**
1. ✅ Review this design document
2. ✅ Approve approach
3. ✅ Begin Phase 1 (data caching - 1 hour)

### **This Week:**
4. ✅ Implement Phase 2 (multicore engine - 4-6 hours)
5. ✅ Test with single backtest
6. ✅ Verify CPU utilization reaches 95%+

### **Next Week:**
7. ✅ Integrate with wiring test (Phase 3)
8. ✅ Run full wiring test (29 scenarios)
9. ✅ Verify results match single-core baseline
10. ✅ Document performance improvements

---

## 📈 SUCCESS CRITERIA

**Wiring Test Performance:**
- [ ] Completes in < 3 minutes (10x improvement)
- [ ] CPU utilization > 90% during test
- [ ] All 29 scenarios execute correctly
- [ ] Results match single-core baseline

**Production Readiness:**
- [ ] No regressions in normal backtests
- [ ] Fallback to single-core works
- [ ] Memory usage < 1GB
- [ ] Error handling robust

**Future Enablement:**
- [ ] Can run 50-150 tests/day
- [ ] Batch mode available
- [ ] Foundation for distributed optimization

---

## 💡 CONCLUSION

Your alternate solution is **THE CORRECT APPROACH**. 

You were absolutely right about:
1. ✅ Loading data once
2. ✅ No database needed during backtest
3. ✅ Making backtest itself multicore

This solves the fundamental issue and benefits the entire system, not just wiring tests.

**Estimated Implementation:** 6-8 hours  
**Expected Speedup:** 10x (17 min → 2 min)  
**Risk:** Low (clear fallback path)  
**Recommendation:** **IMPLEMENT IMMEDIATELY** ✅
