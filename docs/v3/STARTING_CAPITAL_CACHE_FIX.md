# Starting Capital Python Cache Fix

**Date:** 2026-01-10  
**Issue:** Test runs showed $10,000 capital despite YAML config having $25,000  
**Root Cause:** Python bytecode cache (.pyc files) cached old OptimizationConfig dataclass  
**Solution:** Clear all Python cache files and restart processes

---

## Problem Timeline

### 1. Initial Implementation
- Added `starting_capital` field to UI (`strategy_creator.py`)
- Added field to `StrategyConfiguration` model (`models.py`)
- Updated YAML template to use `{{ config.starting_capital }}`
- Added field to `OptimizationConfig` dataclass (`data_classes.py`)
- Updated `optimizer_core.py` to read from YAML and pass to configs

### 2. Test Results
User ran test and saw:
```
📊 Loaded risk params from optimizer_001_hod_rejection.yaml:
   - Starting Capital: $25,000.00  ← CORRECT IN YAML

TEST PARAMETERS:
├─ Starting Capital: $10,000.00 USDT  ← WRONG IN SIMULATOR
├─ Risk per trade: 25% of capital = $2,500 margin  ← Proves using $10k
```

### 3. Investigation
- YAML file: ✅ Correct (`starting_capital: 25000.0`)
- Optimizer loading: ✅ Correct (log shows $25,000)
- Config building: ✅ Correct (passes value to OptimizationConfig)
- Simulator execution: ❌ Wrong (uses $10,000)

### 4. Root Cause Analysis

The issue was in `ultra_hybrid_simulator.py` line 395-397:
```python
leverage = getattr(config, 'max_leverage', 10.0)
starting_capital = getattr(config, 'starting_capital', 10000.0)  # ← Returns default!
risk_per_trade_pct = getattr(config, 'risk_per_trade_pct', 1.0)
```

When `starting_capital` was first added to `OptimizationConfig` dataclass:
1. Python compiled the dataclass into bytecode (.pyc)
2. This bytecode was cached in `__pycache__/` directories
3. Even though the source code now had `starting_capital` field
4. The cached bytecode still used the OLD definition WITHOUT this field
5. So `getattr(config, 'starting_capital', 10000.0)` found no attribute
6. And returned the fallback default of `10000.0`

**Classic Python cache invalidation issue!**

---

## Solution

### Clear All Python Cache Files

```bash
# Remove all __pycache__ directories
find /home/sirrus/projects/BTC_Engine_v3 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove all .pyc files
find /home/sirrus/projects/BTC_Engine_v3 -type f -name "*.pyc" -delete 2>/dev/null || true
```

### Verification Steps

After clearing cache:

1. **Restart Visual Strategy Creator GUI**
   ```bash
   python scripts/strategy_builder_qt.py
   ```

2. **Run Test Again**
   ```bash
   python scripts/universal_optimizer_v2.py strategy_001_hod_rejection --quick-test
   ```

3. **Verify Output**
   Should now show:
   ```
   📊 Loaded risk params from optimizer_001_hod_rejection.yaml:
      - Starting Capital: $25,000.00
   
   TEST PARAMETERS:
   ├─ Starting Capital: $25,000.00 USDT  ← NOW CORRECT!
   ├─ Risk per trade: 25% of capital = $6,250 margin  ← Uses $25k
   ```

---

## Data Flow (Complete End-to-End)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Visual Strategy Creator GUI                              │
│    - User sets Starting Capital: $25,000                    │
│    - Saves to StrategyConfiguration model                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Strategy Configuration File (YAML)                       │
│    src/utils/Strategy_Builder/templates/                    │
│    optimizer_config.yaml.j2                                 │
│                                                              │
│    backtest:                                                │
│      initial_capital: {{ config.starting_capital }}         │
│                                                              │
│    Generated: config/optimizer_001_hod_rejection.yaml       │
│    backtest:                                                │
│      initial_capital: 25000.0  ← CORRECT                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Optimizer Core (optimizer_core.py)                       │
│    load_risk_params_from_yaml()                             │
│    - Reads backtest.initial_capital from YAML               │
│    - Returns: {'starting_capital': 25000.0}  ← CORRECT      │
│                                                              │
│    build_optimization_configs()                             │
│    - Creates OptimizationConfig with:                       │
│      starting_capital=risk_params['starting_capital']       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Optimization Config Dataclass (data_classes.py)          │
│    @dataclass                                               │
│    class OptimizationConfig:                                │
│        starting_capital: float = 10000.0                    │
│                                                              │
│    ⚠️  CACHE ISSUE: .pyc had OLD version without field!     │
│    ✅  AFTER FIX: Fresh compilation includes field          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Ultra Hybrid Simulator (ultra_hybrid_simulator.py)       │
│    test_single_config()                                     │
│                                                              │
│    BEFORE FIX:                                              │
│    starting_capital = getattr(config, 'starting_capital',   │
│                               10000.0)                       │
│    → Returns 10000.0 (field not in cached dataclass!)       │
│                                                              │
│    AFTER FIX:                                               │
│    starting_capital = getattr(config, 'starting_capital',   │
│                               10000.0)                       │
│    → Returns 25000.0 (field exists in fresh dataclass!)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Prevention (Best Practices)

### 1. Always Clear Cache After Dataclass Changes
```bash
# Add to development workflow
find . -type d -name "__pycache__" -delete
find . -type f -name "*.pyc" -delete
```

### 2. Use Direct Attribute Access (Not getattr)
**Bad (hides cache issues):**
```python
starting_capital = getattr(config, 'starting_capital', 10000.0)
```

**Good (fails fast if attribute missing):**
```python
starting_capital = config.starting_capital  # Will raise AttributeError if missing
```

### 3. Restart Processes After Model Changes
- Close and restart GUI after changing `models.py`
- Restart any long-running Python processes
- Clear cache in CI/CD pipelines

### 4. Add Cache Clearing to Makefile
```makefile
.PHONY: clean-cache
clean-cache:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Python cache cleared"
```

---

## Files Modified During Fix

1. **src/utils/Strategy_Builder/models.py**
   - Added `starting_capital` field to `StrategyConfiguration`

2. **src/utils/Strategy_Builder/qt_gui/strategy_creator.py**
   - Added UI widget for starting capital
   - Added to load/save logic

3. **src/utils/Strategy_Builder/templates/optimizer_config.yaml.j2**
   - Changed `initial_capital: 10000.0` → `initial_capital: {{ config.starting_capital }}`

4. **src/strategies/universal_optimizer/modules/data_classes.py**
   - Added `starting_capital` field to `OptimizationConfig` dataclass

5. **src/strategies/universal_optimizer/modules/optimizer_core.py**
   - Added `load_risk_params_from_yaml()` function
   - Updated `build_optimization_configs()` to use YAML values

6. **src/strategies/universal_optimizer/modules/ultra_hybrid_simulator.py**
   - Already using `getattr()` (correct!)
   - No changes needed, just cache clear

---

## Lessons Learned

1. **Python bytecode cache is persistent across runs**
   - Doesn't automatically invalidate when source changes
   - Especially tricky with dataclasses

2. **Dataclass changes require cache clearing**
   - Adding fields to existing dataclass
   - Changing field types or defaults
   - Modifying `__post_init__` logic

3. **Always verify end-to-end data flow**
   - Check YAML file ✅
   - Check loading logic ✅
   - Check dataclass definition ✅
   - Check actual usage ✅
   - **Check Python cache!** ⚠️

4. **getattr() with defaults can hide issues**
   - Use for backward compatibility
   - But makes debugging harder
   - Consider using direct attribute access during development

---

## Success Criteria

After fix, test should show:

✅ YAML config: `starting_capital: 25000.0`  
✅ Optimizer loading: `Starting Capital: $25,000.00`  
✅ Test execution: `Starting Capital: $25,000.00 USDT`  
✅ Position sizing: `Risk per trade: 25% of capital = $6,250 margin`  

**All values consistent end-to-end!**
