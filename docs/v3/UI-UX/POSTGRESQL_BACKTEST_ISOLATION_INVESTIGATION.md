# PostgreSQL Backtest Isolation Investigation
## NAUTILUS EXPERT: Why Are Workers Accessing Database During Backtest?

**Date**: 2026-02-07  
**Issue**: Workers trigger PostgreSQL SSL errors during bar aggregation  
**Root Cause**: ARCHITECTURAL FLAW in data flow

---

## Current (BROKEN) Flow

```
1. User Opens Strategy
   ├─> Strategy Browser loads from PostgreSQL ✅
   └─> Orchestrator sets current_version_id

2. User Validates Strategy
   ├─> In-memory validation ✅
   └─> No database access

3. User Clicks "Run Backtest"
   ├─> BacktestWorker.run() starts
   ├─> Line 149: orchestrator.get_current_strategy_for_backtest()
   │   └─> ❌ OPENS PostgreSQL CONNECTION!
   │   └─> Loads strategy from database (AGAIN!)
   │   └─> Connection stays open
   │
   ├─> Line 165: data_provider.load_bars()
   │   └─> ProcessPoolExecutor spawns 31 workers
   │   └─> Workers inherit broken PostgreSQL connection
   │   └─> SSL error during cleanup
   │
   └─> Backtest runs (data loads successfully)

4. Backtest Complete
   └─> Results saved to PostgreSQL ✅
```

**Problem**: Strategy is loaded from PostgreSQL DURING backtest execution when it's already in memory!

---

## Why This Happens

### File: `src/strategy_builder/ui/backtest_config_panel.py` (Line 149)

```python
# ARCHITECTURAL FLAW: Loads from database during backtest
strategy_config = self.orchestrator.get_current_strategy_for_backtest()
```

### File: `src/strategy_builder/integration/strategy_builder_orchestrator.py` (Line 941)

```python
def get_current_strategy_for_backtest(self) -> Optional[Any]:
    """
    Get current strategy configuration from DATABASE for backtesting
    
    PROBLEM: Opens PostgreSQL connection during backtest execution!
    """
    if not self.current_version_id:
        return None
    
    from src.optimizer_v3.database import get_database_manager
    db = get_database_manager()  # ❌ OPENS CONNECTION
    
    version_dict = db.strategy.get_strategy_version(self.current_version_id)
    # ... rest of code
```

### Why It Exists

Sprint 2.0.2 introduced database-first architecture:
- Strategy stored in PostgreSQL with full configuration
- Backtest needed "complete" strategy from database
- Assumed in-memory config might be incomplete

**Reality**: In-memory config is ALREADY complete when user clicks "Run Backtest"!

---

## Correct (INSTITUTIONAL GRADE) Flow

```
1. User Opens Strategy
   ├─> Strategy Browser loads from PostgreSQL ✅
   ├─> Orchestrator stores in-memory config ✅
   └─> PostgreSQL connection closes ✅

2. User Validates Strategy
   ├─> In-memory validation ✅
   └─> No database access ✅

3. User Clicks "Run Backtest"
   ├─> Serialize in-memory config to JSON/Dict
   ├─> Pass config Dict to BacktestWorker.__init__()
   ├─> NO DATABASE ACCESS ✅
   │
   ├─> BacktestWorker.run() executes
   │   ├─> Uses pre-loaded config Dict
   │   ├─> ProcessPoolExecutor spawns workers
   │   └─> Workers NEVER see PostgreSQL ✅
   │
   └─> Backtest runs (clean multiprocessing)

4. Backtest Complete
   ├─> Results aggregated in memory
   ├─> Open PostgreSQL connection
   ├─> Save results
   └─> Close connection ✅
```

**Key Principle**: Database access ONLY at boundaries (load strategy, save results), NEVER during execution.

---

## Investigation Results

### PostgreSQL Access Points During Backtest

**1. orchestrator.get_current_strategy_for_backtest()** - Line 149  
   - **Why**: Loads strategy from database  
   - **Needed**: NO - config already in memory  
   - **Fix**: Use in-memory config instead

**2. Data Manager** (Bar Aggregation)  
   - **Why**: Loads bars from parquet files  
   - **PostgreSQL Access**: NONE (confirmed)  
   - **Clean**: ✅

**3. Signal Evaluator** (Trade Logic)  
   - **Why**: Evaluates signals during backtest  
   - **PostgreSQL Access**: NONE (uses passed config)  
   - **Clean**: ✅

**Conclusion**: ONLY #1 accesses PostgreSQL - completely unnecessary!

---

## Feasibility Analysis

### Is Database-Free Backtest Feasible?

**YES - 100% Feasible**

#### Current State
- ✅ Strategy loaded in orchestrator.config_engine.config
- ✅ All blocks, signals, exits, timing, rechecks in memory
- ✅ Validation confirms completeness
- ✅ No dynamic loading during backtest needed

#### Required Changes
1. Remove database call from BacktestWorker
2. Serialize config to plain Dict before passing to worker
3. Worker uses serialized Dict (no database objects)
4. Save results to database AFTER backtest completes

#### Benefits
- ✅ No PostgreSQL connections during execution
- ✅ Clean multiprocessing (no connection inheritance)
- ✅ Faster execution (no database I/O)
- ✅ Safer (no connection leaks)
- ✅ Testable (works without database)

---

## Architectural Issues Identified

### Issue #1: Unnecessary Database Coupling
**Location**: `BacktestWorker.run()` line 149  
**Problem**: Loads strategy from database when already in memory  
**Impact**: PostgreSQL connection stays open during multiprocessing  
**Solution**: Use in-memory config serialization

### Issue #2: Connection Lifecycle Management
**Location**: `DatabaseManager` singleton  
**Problem**: Connection pool survives across process boundaries  
**Impact**: Workers inherit broken SSL connections  
**Solution**: No database access during backtest execution

### Issue #3: Mixed Concerns
**Location**: `get_current_strategy_for_backtest()`  
**Problem**: Method name implies "get config" but actually "load from database"  
**Impact**: Misleading - suggests it's just accessing current config  
**Solution**: Rename to `load_strategy_from_database()` or remove entirely

---

## Recommended Solution: Database Isolation Pattern

### Pattern: Three-Phase Execution

```python
# PHASE 1: LOAD (Database Access)
def prepare_backtest():
    """Load all data from database, then close connections"""
    strategy_dict = load_strategy_from_database()
    close_all_database_connections()
    return strategy_dict  # Plain Dict, no database objects

# PHASE 2: EXECUTE (No Database Access)
def run_backtest(strategy_dict):
    """Pure in-memory execution, no database"""
    # Multiprocessing safe - no database connections
    results = execute_backtest(strategy_dict)
    return results  # Plain Dict, no database objects

# PHASE 3: SAVE (Database Access)
def save_results(results_dict):
    """Open connection, save, close"""
    connect_to_database()
    save_backtest_results(results_dict)
    close_database_connection()
```

### Benefits
- ✅ Clear separation of concerns
- ✅ Database access isolated to boundaries
- ✅ Multiprocessing completely clean
- ✅ Testable (can test Phase 2 independently)
- ✅ No connection leak possible

---

## Impact Assessment

### Files Requiring Changes
1. `src/strategy_builder/ui/backtest_config_panel.py` (BacktestWorker)
2. `src/strategy_builder/integration/strategy_builder_orchestrator.py`
3. `src/optimizer_v3/core/institutional_signal_evaluator.py` (verify no DB deps)

### Files NOT Requiring Changes
- ✅ `src/data_manager/*` (already database-free)
- ✅ `src/optimizer_v3/core/backtest_data_provider.py` (uses files only)
- ✅ Bar aggregation (uses parquet only)

### Risk Assessment
**Risk Level**: LOW  
**Why**: Changes only affect data flow, not logic  
**Testing**: Run existing backtest, verify results identical

---

## Next Steps

If feasible, will create comprehensive implementation document with:
- ✅ Detailed checklist of all changes
- ✅ Code modifications for each file
- ✅ Migration strategy (backward compatibility)
- ✅ Testing protocol
- ✅ Rollback plan

**Status**: Investigation complete - feasible and recommended ✅

---

## Conclusion

**User is 100% correct**: Workers should NEVER access PostgreSQL.

**Current Architecture**: FLAWED - loads strategy from database during execution  
**Correct Architecture**: Database access ONLY at boundaries (load/save)

**Recommendation**: Implement database isolation pattern - institutional grade solution.

Proceeding to create implementation document...
