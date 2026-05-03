# PostgreSQL Backtest Isolation - Implementation Plan
## NAUTILUS EXPERT: Institutional-Grade Database Isolation Pattern

**Date**: 2026-02-07  
**Priority**: HIGH - Fixes PostgreSQL SSL errors + Improves architecture  
**Effort**: 2-3 hours  
**Risk**: LOW - Changes data flow only, not business logic

---

## Executive Summary

### Problem
Backtest execution currently loads strategy from PostgreSQL **during** execution, causing:
- PostgreSQL connections inherited by multiprocessing workers
- SSL errors during worker cleanup
- Unnecessary database I/O during performance-critical execution

### Solution
Implement Three-Phase Database Isolation Pattern:
1. **LOAD** - Get data from database, then close connections
2. **EXECUTE** - Pure in-memory execution (no database)
3. **SAVE** - Save results, then close connections

### Benefits
- ✅ Eliminates PostgreSQL multiprocessing errors
- ✅ Faster execution (no database I/O)
- ✅ Safer (no connection leaks)
- ✅ Cleaner architecture (separation of concerns)
- ✅ More testable (execute phase independent)

---

## Implementation Checklist

### Phase 1: Preparation (30 min)
- [ ] 1.1 Read investigation report: `POSTGRESQL_BACKTEST_ISOLATION_INVESTIGATION.md`
- [ ] 1.2 Commit all current work to `feature/phase-2-sprint-work` branch
- [ ] 1.3 Create fix branch FROM current branch: `git checkout -b fix/postgresql-backtest-isolation`
- [ ] 1.4 Run existing backtest to capture baseline behavior
- [ ] 1.5 Verify all tabs populate correctly (Trades, Metrics, AI Recommendations, Training)

### Phase 2: Code Modifications (90 min)
- [ ] 2.1 Modify orchestrator: Add config serialization method
- [ ] 2.2 Modify BacktestWorker: Use serialized config instead of database
- [ ] 2.3 Add connection cleanup helpers
- [ ] 2.4 Update DictWrapper (if needed)
- [ ] 2.5 Remove unnecessary connection disposal code

### Phase 3: Testing (45 min)
- [ ] 3.1 Unit test: Config serialization/deserialization
- [ ] 3.2 Integration test: Full backtest execution
- [ ] 3.3 Verify: No PostgreSQL SSL errors
- [ ] 3.4 Verify: Results identical to baseline
- [ ] 3.5 Performance test: Measure execution time improvement

### Phase 4: Cleanup & Documentation (15 min)
- [ ] 4.1 Remove deprecated code (get_current_strategy_for_backtest)
- [ ] 4.2 Update docstrings
- [ ] 4.3 Git commit with detailed message
- [ ] 4.4 Merge back to `feature/phase-2-sprint-work`: `git checkout feature/phase-2-sprint-work && git merge fix/postgresql-backtest-isolation`
- [ ] 4.5 Update this document with test results
- [ ] 4.6 Delete fix branch: `git branch -d fix/postgresql-backtest-isolation`

---

## Pre-Implementation: Commit Current Work

### Current Branch Status
**Branch**: `feature/phase-2-sprint-work`  
**Modified Files**: 8 files  
**Untracked Files**: 8 files (including investigation docs)

### Commit Workflow
```bash
# Stage all changes
git add -A

# Commit current sprint work
git commit -m "Sprint 2.0.2: Database-first backtest + PostgreSQL isolation investigation

- Added institutional signal evaluator integration
- Implemented DictWrapper for Dict→Object attribute access
- Created database-first backtest architecture
- Added comprehensive investigation docs for PostgreSQL isolation fix
- Modified orchestrator to support database strategy loading
- Updated BacktestWorker for real-time trade streaming

Investigation shows PostgreSQL should NOT be accessed during backtest execution.
Next step: Implement database isolation pattern per POSTGRESQL_BACKTEST_ISOLATION_IMPLEMENTATION.md"

# Create fix branch FROM current sprint branch
git checkout -b fix/postgresql-backtest-isolation

# After implementation and testing, merge back:
git checkout feature/phase-2-sprint-work
git merge fix/postgresql-backtest-isolation
git branch -d fix/postgresql-backtest-isolation
```

---

## Post-Backtest Results Saving (CRITICAL)

### Phase 3: SAVE Results to Database

After backtest completes, results must be saved for ALL tabs:

#### 1. Trades Tab
**Already Handled**: Trades streamed in real-time via `trade_data_emit` signal
- OPEN trades added to table during execution
- CLOSED trades updated when position exits
- No additional saving needed - trades already in UI

**Database Save** (if needed for persistence):
```python
# After backtest complete
trades_list = self.trades_panel.get_all_trades()
# Save to PostgreSQL for historical analysis
db.test_results.save_trades(strategy_id, version_id, trades_list)
```

#### 2. Metrics Tab
**Location**: `_populate_tabs_with_results()` in backtest_config_panel.py

**Current Implementation** (Line ~1149):
```python
# Generate metrics
metrics_data = {
    'total_pnl': Decimal(str(total_pnl)),
    'win_rate': Decimal(str(winning_trades / trade_count * 100)),
    # ... all metrics
}

# Update metrics panel
self.metrics_panel.update_metrics(metrics_data, backtest_complete=True, backtest_results=full_results)
```

**Database Save** (add after metrics calculation):
```python
# Save metrics to database for historical tracking
try:
    from src.optimizer_v3.database import get_database_manager
    db = get_database_manager()
    
    test_result_id = db.test_results.create_test_result({
        'strategy_id': self.orchestrator.current_version_id,
        'strategy_version_id': self.orchestrator.current_version_id,
        'test_type': 'backtest',
        'start_date': backtest_config['start_date'],
        'end_date': backtest_config['end_date'],
        'total_pnl': float(metrics_data['total_pnl']),
        'win_rate': float(metrics_data['win_rate']),
        'sharpe_ratio': float(metrics_data['sharpe_ratio']),
        # ... all metrics
    })
    
    db.close()
    print(f"✅ Saved backtest metrics to database (ID: {test_result_id})")
except Exception as e:
    print(f"⚠️ Failed to save metrics: {e}")
```

#### 3. AI Recommendations Tab
**Already Handled**: Automatically triggered when metrics update with `backtest_complete=True`

**Flow**:
```python
# Line 1172 in backtest_config_panel.py
self.metrics_panel.update_metrics(metrics_data, backtest_complete=True, backtest_results=full_results)
  ↓
metrics_panel._on_ai_request_approved() triggered
  ↓
AI analyzes results and generates recommendations
  ↓
recommendations_generated signal emitted
  ↓
AI Recommendations panel displays results
```

**Database Save** (already implemented in ai_recommendations_panel.py):
```python
# Recommendations automatically saved when generated
db.ai_recommendations.create_recommendation({
    'strategy_id': strategy_id,
    'recommendation_type': 'performance',
    'title': 'Optimize entry conditions',
    # ... recommendation details
})
```

#### 4. Training Tab
**Status**: Training tab is separate system (Sprint 2.1)

**Backtest Results NOT Saved to Training**:
- Training uses historical multi-backtest data
- Single backtest results go to Metrics/Trades tabs only
- Training panel shows training session results, not individual backtests

**No Action Needed**: Training tab independent of backtest results

---

## Detailed Code Modifications

### Modification 1: Orchestrator - Add Config Serialization

**File**: `src/strategy_builder/integration/strategy_builder_orchestrator.py`

**Location**: After `get_current_config()` method (line ~935)

**Add New Method**:
```python
def serialize_config_for_backtest(self) -> dict:
    """
    Serialize in-memory strategy config to plain Dict for backtest execution
    
    INSTITUTIONAL PATTERN: Database Isolation
    - No database access during backtest
    - Config serialized from validated in-memory state
    - Pure Dict (no ORM objects, no database connections)
    
    Returns:
        dict: Serialized strategy configuration with:
            - name: Strategy name
            - blocks: List of building blocks with signals
            - exit_conditions: Exit configuration
            - timing_constraints: Timing rules
            - recheck_config: RECHECK validation settings
            - strategy_type: Bullish/Bearish/Neutral
            - all other validated parameters
    
    Raises:
        ValueError: If strategy not configured or validation failed
    """
    config = self.config_engine.config
    
    # Validate config exists
    if not config or not config.name:
        raise ValueError("No strategy configured - load or create strategy first")
    
    # Validate strategy has blocks
    if not config.blocks:
        raise ValueError("Strategy has no blocks - add building blocks first")
    
    # Serialize to plain dict (no ORM objects)
    config_dict = {
        'name': config.name,
        'description': config.description if hasattr(config, 'description') else '',
        'strategy_type': getattr(config, 'strategy_type', 'Bearish'),
        'blocks': [],
        'exit_conditions': [],
        'parameters': {},
    }
    
    # Serialize blocks
    for block in config.blocks:
        block_dict = {
            'name': block.name,
            'logic': block.logic,
            'signals': [],
            'exit_conditions': []
        }
        
        # Serialize signals
        for signal in block.signals:
            signal_dict = {
                'name': signal.name,
                'logic': signal.logic,
                'timing_constraint': None,
                'exit_conditions': []
            }
            
            # Serialize timing constraint if exists
            if hasattr(signal, 'timing_constraint') and signal.timing_constraint:
                signal_dict['timing_constraint'] = {
                    'max_candles': signal.timing_constraint.max_candles,
                    'reference': signal.timing_constraint.reference
                }
            
            # Serialize signal-level exit conditions
            if hasattr(signal, 'exit_conditions'):
                for exit_cond in signal.exit_conditions:
                    signal_dict['exit_conditions'].append({
                        'signal_name': exit_cond.signal_name,
                        'percentage': float(exit_cond.percentage),
                        'exit_mode': exit_cond.exit_mode if hasattr(exit_cond, 'exit_mode') else 'ABSOLUTE',
                        'tp_proximity_threshold': float(getattr(exit_cond, 'tp_proximity_threshold', 2.0)),
                        'reversal_trigger': float(getattr(exit_cond, 'reversal_trigger', 0.5)),
                        'binding_level': 'SIGNAL',
                        'recheck_config': {
                            'enabled': exit_cond.recheck_config.enabled if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else False,
                            'bar_delay': exit_cond.recheck_config.bar_delay if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else None
                        } if hasattr(exit_cond, 'recheck_config') else None
                    })
            
            block_dict['signals'].append(signal_dict)
        
        # Serialize block-level exit conditions
        if hasattr(block, 'exit_conditions'):
            for exit_cond in block.exit_conditions:
                block_dict['exit_conditions'].append({
                    'signal_name': exit_cond.signal_name,
                    'percentage': float(exit_cond.percentage),
                    'exit_mode': exit_cond.exit_mode if hasattr(exit_cond, 'exit_mode') else 'ABSOLUTE',
                    'tp_proximity_threshold': float(getattr(exit_cond, 'tp_proximity_threshold', 2.0)),
                    'reversal_trigger': float(getattr(exit_cond, 'reversal_trigger', 0.5)),
                    'binding_level': 'BLOCK',
                    'recheck_config': {
                        'enabled': exit_cond.recheck_config.enabled if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else False,
                        'bar_delay': exit_cond.recheck_config.bar_delay if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else None
                    } if hasattr(exit_cond, 'recheck_config') else None
                })
        
        config_dict['blocks'].append(block_dict)
    
    # Serialize strategy-level exit conditions
    if hasattr(config, 'exit_conditions'):
        for exit_cond in config.exit_conditions:
            config_dict['exit_conditions'].append({
                'signal_name': exit_cond.signal_name,
                'percentage': float(exit_cond.percentage),
                'exit_mode': exit_cond.exit_mode if hasattr(exit_cond, 'exit_mode') else 'ABSOLUTE',
                'tp_proximity_threshold': float(getattr(exit_cond, 'tp_proximity_threshold', 2.0)),
                'reversal_trigger': float(getattr(exit_cond, 'reversal_trigger', 0.5)),
                'binding_level': 'STRATEGY',
                'recheck_config': {
                    'enabled': exit_cond.recheck_config.enabled if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else False,
                    'bar_delay': exit_cond.recheck_config.bar_delay if hasattr(exit_cond, 'recheck_config') and exit_cond.recheck_config else None
                } if hasattr(exit_cond, 'recheck_config') else None
            })
    
    # Serialize additional parameters
    config_dict['parameters'] = {
        'stop_loss': float(getattr(config, 'stop_loss', 0.02)),
        'take_profit': float(getattr(config, 'take_profit', 0.03)),
        'position_size': float(getattr(config, 'position_size', 0.1)),
        'risk_per_trade': float(getattr(config, 'risk_per_trade', 0.01)),
    }
    
    print(f"✅ Serialized strategy config: {config_dict['name']}")
    print(f"   Blocks: {len(config_dict['blocks'])}")
    print(f"   Total signals: {sum(len(b['signals']) for b in config_dict['blocks'])}")
    print(f"   Exit conditions: {len(config_dict['exit_conditions'])}")
    
    return config_dict
```

**Testing**:
```python
# Test serialization
config_dict = orchestrator.serialize_config_for_backtest()
assert config_dict['name'] == 'My Strategy'
assert len(config_dict['blocks']) > 0
assert all(isinstance(b, dict) for b in config_dict['blocks'])
```

---

### Modification 2: BacktestWorker - Use Serialized Config

**File**: `src/strategy_builder/ui/backtest_config_panel.py`

**Location 1**: `BacktestWorker.__init__()` (line ~119)

**BEFORE**:
```python
def __init__(self, orchestrator, config: dict, output_panel=None):
    super().__init__()
    self.orchestrator = orchestrator
```

**AFTER**:
```python
def __init__(self, strategy_config_dict: dict, backtest_config: dict, output_panel=None):
    """
    Initialize backtest worker with PRE-SERIALIZED config
    
    INSTITUTIONAL PATTERN: Database Isolation
    - No orchestrator reference (prevents database access)
    - Strategy config is plain Dict (no ORM objects)
    - All data pre-loaded before worker creation
    
    Args:
        strategy_config_dict: Serialized strategy configuration (from orchestrator)
        backtest_config: Backtest parameters (lookback, mode, etc.)
        output_panel: Optional reference to live output panel
    """
    super().__init__()
    self.strategy_config = strategy_config_dict  # Plain Dict, no database
    self.backtest_config = backtest_config
```

**Location 2**: `BacktestWorker.run()` (line ~149)

**BEFORE**:
```python
# CRITICAL FIX: Close ALL database connections before multiprocessing
try:
    from src.optimizer_v3.database import get_database_manager
    db = get_database_manager()
    if hasattr(db, 'engine') and db.engine is not None:
        db.engine.dispose()
        print("✅ Pre-fork cleanup: Closed PostgreSQL connections")
except Exception as e:
    print(f"⚠️ Could not close database connections: {e}")

# Sprint 2.0.2: Initialize institutional signal evaluator
self.live_message.emit("Initializing institutional signal evaluator...", "INFO", "SYSTEM")

# CRITICAL FIX: Load strategy from DATABASE with eager loading
strategy_config = self.orchestrator.get_current_strategy_for_backtest()

if not strategy_config:
    raise ValueError("No validated strategy found")
```

**AFTER**:
```python
# Sprint 2.0.2: Initialize institutional signal evaluator
self.live_message.emit("Initializing institutional signal evaluator...", "INFO", "SYSTEM")

# INSTITUTIONAL PATTERN: Use pre-loaded config (NO DATABASE ACCESS!)
strategy_config = self.strategy_config
if not strategy_config:
    raise ValueError("No strategy config provided - internal error")
```

**Location 3**: `BacktestWorker.run()` - Remove Connection Disposal

**REMOVE THESE LINES** (no longer needed):
```python
# CRITICAL FIX: Close PostgreSQL connections BEFORE returning
if hasattr(db, 'engine') and db.engine is not None:
    db.engine.dispose()
    print("✅ Closed PostgreSQL connections before multiprocessing")
```

**Location 4**: `_on_run_clicked()` - Pass Serialized Config (line ~1094)

**BEFORE**:
```python
def _on_run_clicked(self):
    """Handle run button click"""
    # ... validation ...
    
    config = self.get_config()
    self.trades_panel.clear_trades()
    
    # Create worker
    self.worker = BacktestWorker(self.orchestrator, config, self.output_panel)
```

**AFTER**:
```python
def _on_run_clicked(self):
    """Handle run button click"""
    # Validate strategy
    validation = self.orchestrator.validate_strategy()
    if not validation.success:
        self.results_text.setText(f"❌ Strategy validation failed:\n{validation.message}")
        return
    
    # INSTITUTIONAL PATTERN: Serialize config BEFORE creating worker
    try:
        strategy_config_dict = self.orchestrator.serialize_config_for_backtest()
    except ValueError as e:
        self.results_text.setText(f"❌ Failed to prepare strategy:\n{str(e)}")
        return
    
    backtest_config = self.get_config()
    self.trades_panel.clear_trades()
    
    # Create worker with serialized config (no database access possible)
    self.worker = BacktestWorker(
        strategy_config_dict=strategy_config_dict,
        backtest_config=backtest_config,
        output_panel=self.output_panel
    )
```

**Testing**:
```python
# Test worker creation
worker = BacktestWorker(
    strategy_config_dict={'name': 'Test', 'blocks': []},
    backtest_config={'lookback_days': 180},
    output_panel=None
)
assert worker.strategy_config['name'] == 'Test'
assert not hasattr(worker, 'orchestrator')  # No database reference!
```

---

### Modification 3: Cleanup - Remove Orchestrator Database Method

**File**: `src/strategy_builder/integration/strategy_builder_orchestrator.py`

**Location**: `get_current_strategy_for_backtest()` method (line ~941)

**BEFORE** (keeping for backward compatibility):
```python
def get_current_strategy_for_backtest(self) -> Optional[Any]:
    """Load strategy from database for backtesting"""
    # ... 50 lines of database code ...
```

**AFTER** (deprecate with warning):
```python
def get_current_strategy_for_backtest(self) -> Optional[Any]:
    """
    DEPRECATED: Use serialize_config_for_backtest() instead
    
    This method loads from database during backtest execution,
    causing PostgreSQL multiprocessing errors. Use the new
    database isolation pattern instead.
    
    Will be removed in future version.
    """
    import warnings
    warnings.warn(
        "get_current_strategy_for_backtest() is deprecated - "
        "use serialize_config_for_backtest() instead",
        DeprecationWarning,
        stacklevel=2
    )
    
    # For backward compatibility, serialize from in-memory config
    return self.serialize_config_for_backtest()
```

---

## Testing Protocol

### Test 1: Unit Test - Config Serialization

**File**: `tests/strategy_builder/test_backtest_isolation.py` (create new)

```python
"""
Test backtest database isolation pattern
"""

def test_config_serialization():
    """Test strategy config serializes to plain Dict"""
    from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator
    
    orchestrator = StrategyBuilderOrchestrator()
    orchestrator.create_strategy("Test Strategy")
    orchestrator.add_block_with_signals("liquidity_sweep", ["BEARISH_SWEEP"])
    
    # Serialize config
    config_dict = orchestrator.serialize_config_for_backtest()
    
    # Verify plain Dict (no ORM objects)
    assert isinstance(config_dict, dict)
    assert config_dict['name'] == 'Test Strategy'
    assert len(config_dict['blocks']) == 1
    assert config_dict['blocks'][0]['name'] == 'liquidity_sweep'
    assert len(config_dict['blocks'][0]['signals']) == 1

def test_worker_no_database_access():
    """Test worker NEVER accesses database"""
    from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
    import sys
    
    config_dict = {
        'name': 'Test',
        'blocks': [{'name': 'test_block', 'signals': []}],
        'exit_conditions': []
    }
    
    backtest_config = {'lookback_days': 180, 'mode': 1, 'timeframe': '15m'}
    
    worker = BacktestWorker(config_dict, backtest_config)
    
    # Verify no database module loaded
    assert 'src.optimizer_v3.database' not in sys.modules or \
           not hasattr(worker, 'orchestrator')
```

---

### Test 2: Integration Test - Full Backtest

**Instructions**:
1. Load strategy from Strategy Browser
2. Click "Run Backtest"
3. Monitor terminal for PostgreSQL errors
4. Verify backtest completes successfully
5. Compare results with baseline (should be identical)

**Expected Output**:
```
✅ Serialized strategy config: 50 EMA Bull Break Strategy
   Blocks: 4
   Total signals: 6
   Exit conditions: 2
✅ Loaded 15,168 bars for backtest
✅ Backtest completed successfully! 127 trades executed
```

**NO PostgreSQL SSL errors should appear**

---

### Test 3: Performance Test

**Measure**:
- Baseline (current): Time from click to completion
- Optimized (new): Time from click to completion

**Expected Improvement**: 5-10% faster (no database I/O)

---

## Rollback Plan

If issues arise:

1. **Revert Files**:
   ```bash
   git checkout HEAD -- src/strategy_builder/integration/strategy_builder_orchestrator.py
   git checkout HEAD -- src/strategy_builder/ui/backtest_config_panel.py
   ```

2. **Restore Baseline**:
   - Orchestrator keeps `get_current_strategy_for_backtest()`
   - BacktestWorker uses orchestrator reference
   - Database loads during execution (with SSL errors)

3. **Document Issues**: Add to rollback section below

---

## Migration Strategy

### Backward Compatibility

**Keep deprecated method** for 1-2 releases:
- `get_current_strategy_for_backtest()` issues warning
- Falls back to `serialize_config_for_backtest()`
- Allows gradual migration

### Communication

**Release Notes**:
```
v3.x.x - Database Isolation Pattern

FIXED: PostgreSQL SSL errors during backtest execution
IMPROVED: Backtest performance (5-10% faster)
CHANGED: Internal backtest data flow (no breaking changes)
DEPRECATED: StrategyBuilderOrchestrator.get_current_strategy_for_backtest()
            Use serialize_config_for_backtest() instead
```

---

## Success Criteria

- [ ] ✅ No PostgreSQL SSL errors during backtest
- [ ] ✅ Backtest results identical to baseline
- [ ] ✅ Performance improvement measurable
- [ ] ✅ All tests pass
- [ ] ✅ Clean multiprocessing (no connection errors)
- [ ] ✅ Code cleaner (separation of concerns)

---

## Timeline

**Total Effort**: 2-3 hours

| Phase | Duration | Tasks |
|-------|----------|-------|
| Preparation | 30 min | Baseline, backup, branch |
| Implementation | 90 min | Code changes (3 modifications) |
| Testing | 45 min | Unit + integration + performance |
| Cleanup | 15 min | Documentation, commit |

---

## Notes & Observations

### Post-Implementation Notes
(To be filled after implementation)

**PostgreSQL Errors**: 
- Before: [count]
- After: [count]

**Performance**:
- Before: [time] seconds
- After: [time] seconds
- Improvement: [%]

**Issues Encountered**:
- [List any issues]

**Rollback Needed**:
- [ ] Yes (see reason below)
- [ ] No (implementation successful)

---

## Conclusion

This implementation provides **institutional-grade database isolation** for backtest execution:

✅ **Clean Architecture**: Database access only at boundaries  
✅ **Safe Multiprocessing**: Workers never touch database  
✅ **Better Performance**: No database I/O during execution  
✅ **More Testable**: Execute phase independent of database  
✅ **Maintainable**: Clear separation of concerns  

**Status**: Ready for implementation ✅

---

**Author**: NAUTILUS EXPERT (Cline)  
**Date**: 2026-02-07  
**Version**: 1.0
