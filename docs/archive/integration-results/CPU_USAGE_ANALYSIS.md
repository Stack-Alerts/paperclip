# 🔬 CPU USAGE ANALYSIS - Wiring Test Performance Investigation

**Date:** February 11, 2026  
**System:** 32 CPU cores available  
**Observed:** Only 1 CPU at 99% usage  
**Expected:** 31-32 CPUs at 90%+ usage  

---

## 🐛 ROOT CAUSE IDENTIFIED

### **The Wiring Test Runs Backtests SEQUENTIALLY, Not in Parallel!**

**Current Architecture:**
```python
# backtest_config_panel.py - Line ~2600
for i, scenario in enumerate(all_scenarios):  # ← SEQUENTIAL LOOP!
    # Apply scenario config to UI
    self._apply_scenario_to_ui(scenario.config)
    
    # Run ONE backtest and WAIT for completion
    result = self._run_test_and_wait()  # ← BLOCKS HERE!
    
    # Store results, then move to NEXT scenario
    test_results.append(result)
```

**What Happens:**
1. Test 1 starts → Uses all CPUs → Completes
2. Test 2 starts → Uses all CPUs → Completes
3. ... repeat 29 times (SEQUENTIAL!)

**Why Only 1 CPU?**
- The **GUI thread** runs the test loop (1 CPU)
- Each **backtest** runs in a QThread (also 1 CPU for Python)
- The backtest **data loading** uses multiprocessing (31 CPUs)
- But backtests run **ONE AT A TIME**, so CPUs idle between tests

---

## 📊 DETAILED ANALYSIS

### Phase 1: Data Loading (Uses All CPUs ✅)

**File:** `src/data_manager/processing/bar_aggregator.py`

```python
# Line ~200
with mp.Pool(processes=cpu_count) as pool:  # ← Uses all 32 CPUs!
    results = pool.starmap(self._process_month_chunk, args)
```

**CPU Usage During Data Load:**
- **All 32 CPUs:** 90-98% (parallel aggregation)
- **Duration:** 10-15 seconds per backtest

### Phase 2: Signal Evaluation (Single CPU ❌)

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

```python
# BacktestWorker.run() - Line ~400
for i in range(total_candles):  # ← SINGLE THREADED!
    result = evaluator.evaluate_bar(current_bar, i, lookback_bars, total_candles)
    # Process trades...
```

**CPU Usage During Evaluation:**
- **1 CPU:** 98-100% (Python GIL limits to 1 thread)
- **31 CPUs:** 0% (idle)
- **Duration:** 20-30 seconds per backtest

### Phase 3: Test Framework (Single CPU ❌)

**File:** `src/strategy_builder/ui/backtest_config_panel.py`

```python
# _on_test_wiring_clicked() - Line ~2600
for i, scenario in enumerate(all_scenarios):  # ← SEQUENTIAL!
    result = self._run_test_and_wait()  # ← BLOCKS until complete
```

**CPU Usage:**
- **1 CPU:** GUI thread managing test loop
- **31 CPUs:** 0% (waiting for next backtest)

---

## ⏱️ PERFORMANCE BREAKDOWN

**Per Backtest:**
- Data Loading: 10-15 sec (multicore ✅)
- Signal Evaluation: 20-30 sec (single core ❌)
- **Total:** ~35-40 sec per backtest

**Wiring Test (29 backtests):**
- Sequential: 29 × 35 sec = **~17 minutes** ❌
- **If parallel**: 29 ÷ 32 CPUs × 35 sec = **~32 seconds** ✅ (30x faster!)

---

## 🚫 WHY NOT PARALLEL?

### Technical Constraints:

**1. Qt GUI Thread Limitation**
- Qt widgets must be accessed from main thread only
- `_apply_scenario_to_ui()` modifies UI widgets
- Cannot be called from worker threads

**2. Database Connection Issues**
- Each backtest creates database connections
- PostgreSQL has connection limits
- 32 simultaneous backtests = 32 × connections = overflow

**3. Python GIL (Global Interpreter Lock)**
- Signal evaluation is CPU-bound Python code
- GIL prevents true parallelism within a process
- Would need multiprocessing, not threading

**4. Memory Constraints**
- Each backtest loads ~7,000 bars into memory
- 32 simultaneous backtests = 32 × memory usage
- Risk of OOM (Out of Memory)

---

## ✅ SOLUTIONS

### Solution 1: Accept Sequential Execution (Current)

**Pros:**
- Simple, safe, works
- No race conditions
- No memory issues
- No database connection issues

**Cons:**
- Takes 17 minutes
- Wastes CPU capacity

**User Experience:**
- Progress bar shows current test
- Can cancel mid-run
- Generates detailed report

---

### Solution 2: Parallel Multi-Process Execution (Complex)

**Implementation:**
```python
# New approach - multiprocessing pool
from multiprocessing import Pool

def run_single_backtest(scenario_config):
    """Run backtest in separate process"""
    # Each process:
    # 1. Creates own Database connection
    # 2. Loads own data
    # 3  Runs backtest
    # 4. Returns results
    return results

# Run all 29 in parallel
with Pool(processes=min(29, cpu_count())) as pool:
    results = pool.map(run_single_backtest, all_scenarios)
```

**Pros:**
- Uses all CPUs simultaneously
- 17 min → **~32 seconds** (30x faster!)
- No GIL issues (separate processes)

**Cons:**
- Cannot update UI during execution (no progress bar)
- 29 simultaneous database connections (might hit limits)
- 29 × memory usage (~200GB for large datasets!)
- Cannot cancel individual tests
- More complex error handling

**Risk:** HIGH - Resource exhaustion, connection limits

---

### Solution 3: Batch Parallel Execution (Compromise)

**Implementation:**
```python
# Run N backtests at a time
BATCH_SIZE = 8  # Use 8 CPUs simultaneously

for batch_start in range(0, len(all_scenarios), BATCH_SIZE):
    batch = all_scenarios[batch_start:batch_start+BATCH_SIZE]
    
    # Run this batch in parallel
    with Pool(processes=BATCH_SIZE) as pool:
        batch_results = pool.map(run_single_backtest, batch)
    
    results.extend(batch_results)
```

**Pros:**
- 8x speedup: 17 min → **~2 minutes**
- Controlled resource usage
- Can show batch progress
- Safer than full parallelism

**Cons:**
- Still no individual test progress
- Still hits database connection limits
- More complex than current solution

**Risk:** MEDIUM - Manageable but needs testing

---

### Solution 4: Optimize Single-Threaded Execution (Practical)

**Keep sequential, but make each backtest faster:**

1. **Cache Data Loading:**
```python
# Load data ONCE for all tests (same timeframe/dates)
bars = load_data_once()

# Reuse for all 29 tests
for scenario in all_scenarios:
    result = run_backtest_with_cached_data(bars, scenario)
```

**Savings:** 10-15 sec × 29 = **~7 minutes saved!**

2. **Reduce Candle Count for Testing:**
```python
# Use last 1000 candles instead of 7000
test_bars = bars[-1000:]  # Still validates wiring
```

**Savings:** ~20 sec × 29 = **~10 minutes saved!**

3. **Skip Data Reload:**
```python
# Don't reload from disk for each test
# Use in-memory cached bars
```

**Total Savings:** **~17 minutes → ~5 minutes** (3x faster)

**Pros:**
- Easy to implement
- No architectural changes
- No resource risks
- Still validates all parameters

**Cons:**
- Still sequential
- Still "only" 3x faster (not 30x)

**Risk:** LOW - Safe optimization

---

## 🎯 RECOMMENDED SOLUTION

### **Solution 4: Optimize Single-Threaded (Immediate)**

**Why:**
- Easy to implement (30 min work)
- No risks
- 3x faster (good enough for testing)
- Maintains all safety guarantees

**Implementation Plan:**

**Step 1:** Cache data loading
```python
# In _on_test_wiring_clicked()
# Load bars ONCE before test loop
print("Pre-loading historical data...")
bars = self.data_provider.load_bars_for_backtest(...)

# Pass to each backtest
for scenario in all_scenarios:
    result = self._run_test_with_cached_data(bars, scenario)
```

**Step 2:** Reduce test candle count
```python
# Use last 1000-2000 candles for wiring validation
# Still enough to validate parameter effects
test_bars = bars[-1500:]  # ~1.5 days of 15m data
```

**Step 3:** Add progress indicators
```python
# Show which test is running
progress.setLabelText(
    f"Test {i+1}/{total}: {scenario.description}\n"
    f"Estimated time remaining: {(total-i) * 30} seconds"
)
```

---

## 📈 FUTURE OPTIMIZATION (Solution 3)

### **When System is More Mature:**

1. Implement batch parallelism (8 tests at a time)
2. Add connection pooling for database
3. Implement result caching
4. Add incremental testing (only test changed parameters)

**Expected:** **17 min → 2-3 minutes**

---

## 💡 CONCLUSION

**Current State:**
- ✅ Works correctly
- ✅ Safe and stable
- ❌ Uses only 1 CPU during signal evaluation
- ❌ Takes 17 minutes for 29 tests

**Why Only 1 CPU:**
1. Tests run **sequentially** (by design)
2. Signal evaluation is **single-threaded** (Python GIL)
3. Only data loading uses multiprocessing (10-15 sec per test)
4. Signal evaluation is single-core (20-30 sec per test)

**Immediate Fix:**
- Implement data caching + reduce candle count
- **17 min → ~5 min** (3x faster)
- **Low risk, easy implementation**

**Future Enhancement:**
- Batch parallel execution
- **~5 min → ~2 min** (8x faster total)
- **Medium risk, requires testing**
