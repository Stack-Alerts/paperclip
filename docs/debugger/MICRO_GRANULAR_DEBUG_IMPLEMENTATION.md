# Micro-Granular Debug Implementation Plan
## Full Integration - Option A (Complete)

**Objective:** Integrate ConfigDebugger throughout entire optimization pipeline to log every config read, every decision, every calculation with full validation.

**Date:** 2026-01-11  
**Status:** IN PROGRESS

---

## Implementation Phases

### Phase 1: Entry Point Integration ✅
**File:** `scripts/universal_optimizer_v2.py`

**Changes:**
- Add `--enable-debugger` flag
- Create ConfigDebugger instance when flag is set
- Pass debugger to optimizer_core

**Log Points:**
1. Debugger initialization
2. Strategy module loading
3. Configuration loading from file

---

### Phase 2: Core Optimization Integration ⏳
**File:** `src/strategies/universal_optimizer/modules/optimizer_core.py`

**Changes:**
- Accept `debugger` parameter (Optional[ConfigDebugger])
- Register full configuration dictionary
- Pass debugger to simulator
- Log configuration optimization grid building
- Log each optimization iteration

**Log Points:**
1. Full config registration (all fields)
2. TP/SL grid generation
3. Each optimization configuration created
4. Configuration selection logic
5. Best configuration selection
6. Configuration application to file

---

### Phase 3: Simulation Engine Integration ⏳
**File:** `src/strategies/universal_optimizer/modules/ultra_hybrid_simulator.py`

**Changes:**
- Accept debugger in `test_single_config()`
- Log every config value read
- Log every decision point (if/else)
- Validate values used match config
- Log every trade entry/exit

**Log Points:**
1. Config snapshot registration
2. Risk parameter reads (risk_per_trade_pct, max_leverage)
3. TP/SL mode selection decisions
4. Entry signal generation
5. TP calculation calls
6. SL calculation calls
7. Exit logic decisions
8. Every trade execution
9. Position size calculations
10. Validation: value used == value configured

**Critical Validations:**
- `tp_mode` read matches `tp_mode` used
- `min_risk_reward` read matches value in calculation
- `risk_per_trade_pct` read matches position sizing
- All conditional branches logged with config keys involved

---

### Phase 4: TP Calculator Integration ⏳
**File:** `src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py`

**Changes:**
- Accept debugger in all calculation methods
- Log TP mode selection
- Log every calculation step
- Log Fibonacci level selection
- Validate all parameters used

**Log Points:**
1. TP mode decision (PERCENTAGE vs FIBONACCI vs ATR)
2. Fibonacci level selection and calculation  
3. ATR-based TP calculation
4. Percentage-based TP calculation
5. Min R:R validation
6. Final TP value selection
7. Validation: config values match calculation inputs

**Example Log Output:**
```
[CONFIG_READ] tp_mode = 'FIBONACCI' (from config) at dynamic_tp_calculator.py:45
[DECISION] if: tp_mode == 'FIBONACCI' = True (using {'tp_mode': 'FIBONACCI'})
[CONFIG_READ] fib_level = 1.618 (from config)
[ACTION] Calculate Fibonacci TP
  Config Used: {'fib_level': 1.618, 'min_risk_reward': 1.2}
  Parameters: {'entry': 45000.00, 'sl': 44500.00, 'side': 'LONG'}
  Calculation: distance = 45000.00 - 44500.00 = 500.00
  Calculation: tp_distance = 500.00 * 1.618 = 809.00
  Calculation: tp = 45000.00 + 809.00 = 45809.00
  Calculation: rr = 809.00 / 500.00 = 1.618
[VALIDATION] ✓ fib_level used (1.618) == config value (1.618) MATCH
[VALIDATION] ✓ rr (1.618) >= min_risk_reward (1.2) SUCCESS
```

---

### Phase 5: SL Calculator Integration ⏳
**File:** `src/strategies/universal_optimizer/modules/dynamic_sl_calculator.py`

**Changes:**
- Accept debugger in all calculation methods
- Log SL mode selection
- Log delayed SL logic
- Log volatility calculations
- Log structure-based SL
- Validate all parameters

**Log Points:**
1. Delayed SL decision (use_delayed_sl)
2. Bar delay period
3. Emergency SL percentage
4. Volatility lookback and calculation
5. Volatility multiplier application
6. Min/max SL bounds
7. Structure-based SL detection
8. Final SL value selection
9. Validation: all config values match

**Example Log Output:**
```
[CONFIG_READ] use_delayed_sl = True (from config)
[DECISION] if: use_delayed_sl = True (using {'use_delayed_sl': True})
[CONFIG_READ] delay_bars = 2 (from config)
[DECISION] if: current_bar < entry_bar + delay_bars = True
[ACTION] Using emergency SL (delayed period active)
  Config Used: {'emergency_sl_pct': 2.5, 'absolute_min_sl_pct': 0.7}
  Parameters: {'entry': 45000.00, 'side': 'LONG'}
  Calculation: sl_distance = 45000.00 * 0.025 = 1125.00
  Calculation: sl = 45000.00 - 1125.00 = 43875.00
[VALIDATION] ✓ emergency_sl_pct used (2.5) == config value (2.5) MATCH
```

---

### Phase 6: Additional Integration Points ⏳

**Files to integrate:**
- `src/strategies/universal_optimizer/modules/confluence_calculator.py` - Log confluence calculations
- `src/strategies/universal_optimizer/modules/file_operations.py` - Log config file reads/writes
- Any building blocks that read config - Log config access

---

## Data Flow with Debugger

```
universal_optimizer_v2.py (--enable-debugger)
    |
    |--> Create ConfigDebugger("UniversalOptimizer", log_file="logs/optimizer_debug.log")
    |
    +--> optimizer_core.optimize_strategy_v2(debugger=debugger)
         |
         |--> debugger.register_config_source(full_config, source="config.yaml")
         |
         +--> test_single_config(config, debugger=debugger)
              |
              |--> debugger.get_config_value('tp_mode')
              |--> debugger.log_decision('if', 'tp_mode == FIBONACCI', True, ['tp_mode'])
              |
              +--> calculate_tp(..., debugger=debugger)
              |    |
              |    |--> debugger.get_config_value('fib_level')
              |    |--> debugger.log_action('Calculate Fibonacci TP', ['fib_level'], {...})
              |    +--> debugger.validate_config_usage('fib_level', 1.618, actual_value)
              |
              +--> calculate_sl(..., debugger=debugger)
                   |
                   |--> debugger.get_config_value('use_delayed_sl')
                   |--> debugger.log_decision('if', 'use_delayed_sl', True, ['use_delayed_sl'])
                   +--> debugger.log_action('Calculate delayed SL', [...], {...})
```

---

## Integration Checklist

### universal_optimizer_v2.py
- [ ] Add --enable-debugger argument
- [ ] Create ConfigDebugger instance
- [ ] Pass to optimizer_core

### optimizer_core.py
- [ ] Accept debugger parameter
- [ ] Register full configuration
- [ ] Pass to ultra_hybrid_simulator
- [ ] Log optimization grid building
- [ ] Log configuration selection

### ultra_hybrid_simulator.py
- [ ] Accept debugger parameter
- [ ] Register config snapshot per test
- [ ] Log all config reads
- [ ] Log all decision points
- [ ] Log all trade executions
- [ ] Validate config usage

### dynamic_tp_calculator.py
- [ ] Accept debugger in all methods
- [ ] Log TP mode selection
- [ ] Log all calculations
- [ ] Validate parameters

### dynamic_sl_calculator.py
- [ ] Accept debugger in all methods
- [ ] Log SL mode selection
- [ ] Log all calculations
- [ ] Validate parameters

---

## Expected Log Output Format

### Ideal Micro-Granular Log
```
╔══════════════════════════════════════════════════════════════════════════════╗
║ INSTITUTIONAL-GRADE CONFIGURATION DEBUGGER                                ║
║ Component: UniversalOptimizer                                              ║
║ Level: MEDIUM                                                              ║
║ Started: 2026-01-11 12:00:00                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

[CONFIG_SOURCE_REGISTERED] 2026-01-11T12:00:01
Source: config/strategy_001.yaml (config_file)
Fields Registered: 25
Fields: tp_mode, min_risk_reward, risk_per_trade_pct, max_leverage, use_delayed_sl, delay_bars, emergency_sl_pct, volatility_lookback, volatility_multiplier, absolute_min_sl_pct, absolute_max_sl_pct, use_structure_sl, min_confluence, max_bars_held, ...

[CONFIG_READ] tp_mode = 'FIBONACCI' (from config/strategy_001.yaml) at ultra_hybrid_simulator.py:234
[CONFIG_READ] min_risk_reward = 1.2 (from config/strategy_001.yaml) at ultra_hybrid_simulator.py:235
[CONFIG_READ] risk_per_trade_pct = 1.0 (from config/strategy_001.yaml) at ultra_hybrid_simulator.py:236

[DECISION] if: tp_mode == 'FIBONACCI' = True
  Config keys: ['tp_mode']
  Location: ultra_hybrid_simulator.py:240

[ACTION] Calculate Fibonacci TP
  Config Used: {'tp_mode': 'FIBONACCI', 'fib_level': 1.618, 'min_risk_reward': 1.2}
  Parameters: {'entry': 45000.00, 'sl': 44500.00, 'side': 'LONG'}
  Location: dynamic_tp_calculator.py:56

[CONFIG_READ] fib_level = 1.618 (from config/strategy_001.yaml) at dynamic_tp_calculator.py:58
[VALIDATION] ✓ fib_level: 1.618 == 1.618 MATCH at dynamic_tp_calculator.py:59

[ACTION] Entry Trade
  Config Used: {'risk_per_trade_pct': 1.0, 'max_leverage': 2.0}
  Parameters: {'price': 45000.00, 'side': 'LONG', 'tp': 45809.00, 'sl': 44500.00}
  Position Size: 0.0445 BTC
  Location: ultra_hybrid_simulator.py:345

[CONFIG_READ] use_delayed_sl = True (from config/strategy_001.yaml) at ultra_hybrid_simulator.py:412
[DECISION] if: use_delayed_sl = True
  Config keys: ['use_delayed_sl']
  Location: ultra_hybrid_simulator.py:413

[CONFIG_READ] delay_bars = 2 (from config/strategy_001.yaml) at ultra_hybrid_simulator.py:415
[DECISION] if: bars_since_entry < delay_bars = True (1 < 2)
  Config keys: ['delay_bars']
  Location: ultra_hybrid_simulator.py:416

[ACTION] Using delayed SL (emergency SL active)
  Config Used: {'emergency_sl_pct': 2.5}
  Parameters: {'entry': 45000.00}
  Emergency SL: 43875.00
  Location: dynamic_sl_calculator.py:123

... (thousands more log entries for complete audit trail)

═══ SUMMARY ═══
Total Config Reads: 3,456
Total Decisions: 1,234
Total Actions: 789
Total Validations: 3,456
Mismatches: 0 ✓
```

---

## Testing

After implementation, test with:
```bash
python scripts/universal_optimizer_v2.py strategy_001_hod_rejection --enable-debugger --quick-test
```

Expected: Multi-thousand line log with every config read, decision, action logged

---

## Success Criteria

1. ✅ Every config value read is logged
2. ✅ Every if/else decision is logged with config keys
3. ✅ Every calculation is logged with inputs and outputs
4. ✅ Every validation confirms value used == value configured
5. ✅ Any mismatch triggers CRITICAL alert
6. ✅ Log file provides complete audit trail
7. ✅ Can trace any calculation back to config source

---

## Implementation Notes

- Use `debugger.get_config_value()` instead of direct dict access
- Use `debugger.log_decision()` for every if/else
- Use `debugger.log_action()` for every calculation
- Use `debugger.validate_config_usage()` after using values
- Keep debugger parameter `Optional[ConfigDebugger] = None` for backward compatibility
- Only log when `debugger is not None`

---

**Next Steps:**
1. Start with universal_optimizer_v2.py (Phase 1)
2. Move to optimizer_core.py (Phase 2)
3. Integrate ultra_hybrid_simulator.py (Phase 3)
4. Continue systematically through all phases
