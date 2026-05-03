# Backtest Configuration Coverage Testing

**Institutional-Grade Automated Testing of Backtest Configuration Permutations**

## 📋 Overview

This test suite provides comprehensive coverage of all backtest configuration combinations to verify:

- ✅ All TP/SL modes (Fibonacci/Hybrid/Fixed)
- ✅ Adaptive SL v2.0 functionality
- ✅ Emergency SL → Adaptive SL transition
- ✅ Partial exits (TP1/TP2/TP3)
- ✅ Stop loss exits
- ✅ Time limit exits (max_bars_held)
- ✅ No stuck trades
- ✅ Risk/Reward configurations

**Approach**: Uses orthogonal array testing (pairwise coverage) to achieve complete coverage with minimal test count (~20-30 tests instead of 1,152 exhaustive combinations).

**Execution**: Runs REAL backtests (not mocked) against actual data to find real bugs.

---

## 🚀 Quick Start

### Installation

```bash
# Install pairwise testing library (optional - fallback to manual if not available)
pip install allpairspy

# Ensure pandas is installed (for reporting)
pip install pandas
```

### Run Tests

```bash
# Run full coverage test suite
pytest tests/integration/test_backtest_configuration_coverage.py -v -s

# Run only critical scenarios (faster - ~5-10 min)
pytest tests/integration/test_backtest_configuration_coverage.py -v -s -k "CRITICAL"

# Run only edge case scenarios
pytest tests/integration/test_backtest_configuration_coverage.py -v -s -k "EDGE"

# Run standalone (without pytest)
python tests/integration/test_backtest_configuration_coverage.py
```

---

## 📊 Test Scenarios

### Critical Path Scenarios (8 tests)

**Purpose**: Test most important production configurations

| ID | Description | TP/SL | SL Adj | Preset | Expected |
|----|-------------|-------|--------|--------|----------|
| CRITICAL_001 | Default Production | Fibonacci | Adaptive | Balanced | TP/SL exits, SL adjustments |
| CRITICAL_002 | Hybrid Adaptive | Hybrid | Adaptive | Balanced | TP/SL exits, SL adjustments |
| CRITICAL_003 | Fixed Adaptive | Fixed | Adaptive | Balanced | TP/SL exits, SL adjustments |
| CRITICAL_004 | Static SL | Fibonacci | Static | - | TP/SL exits, no SL adj |
| CRITICAL_005 | Conservative | Fibonacci | Adaptive | Conservative | Wider SLs |
| CRITICAL_006 | Aggressive | Fibonacci | Adaptive | Aggressive | Tighter SLs, more SL hits |
| CRITICAL_007 | Hybrid Static | Hybrid | Static | - | Lower risk profile |
| CRITICAL_008 | Simplest Config | Fixed | Static | - | Minimal configuration |

### Edge Case Scenarios (5 tests)

**Purpose**: Test boundary conditions and unusual configurations

| ID | Description | Config | Expected |
|----|-------------|--------|----------|
| EDGE_001 | Time Limit Hit | max_bars=5 | Trades exit at time limit |
| EDGE_002 | Minimal Delay | delay=1, Aggressive | SL activates fast, more SL hits |
| EDGE_003 | Maximum Delay | delay=3, Conservative | Widest protection |
| EDGE_004 | Low Risk Profile | risk=5%, leverage=5x | Conservative trading |
| EDGE_005 | High Risk Profile | risk=10%, leverage=10x | Aggressive trading |

### Pairwise Scenarios (~10-20 tests)

**Purpose**: Ensure every parameter combination tested at least once

Generated dynamically using pairwise coverage algorithm to test:
- TP/SL modes: Fibonacci × Hybrid × Fixed
- SL adjustment: Adaptive × Static
- Risk %: 5% × 10%
- Leverage: 5x × 10x
- Max bars: 50 × 200

---

## 📁 File Structure

```
tests/integration/
├── README_COVERAGE_TESTING.md          # This file
├── test_backtest_configuration_coverage.py  # Main test framework
├── test_scenarios.py                   # Scenario definitions
├── __init__.py                         # Package init
├── results/                            # Test results (auto-generated)
│   └── coverage_test_YYYY-MM-DD_HH-MM-SS.csv
└── fixtures/                           # Test fixtures (future)
```

---

## 🔍 Test Configuration

### Standard Test Settings

All tests use consistent settings:

```python
{
    'lookback_days': 90,      # Fast execution
    'training_window': 60,    # 60 days training
    'testing_window': 30,     # 30 days testing
    'timeframe': '15m',       # 15-minute bars
    'mode': 1,                # Historical (faster)
    'starting_capital': 10000,
    'min_risk_reward': 1.2,
    'confluence_threshold': 20,
}
```

### Test Strategy

Uses "50% Asia Rejection Simple (v2)" - a proven 2-signal strategy:

```python
{
    'blocks': [
        'Signal 1: AT_ASIA_50',
        'Signal 2: BELOW_ASIA_50 (within 5 candles of Signal 1)'
    ],
    'strategy_type': 'Bearish',
}
```

**Why this strategy?**
- ✅ Already tested and working
- ✅ Simple (2 signals = fast execution)
- ✅ Good signal generation rate (~20-30 trades per 30 days)
- ✅ Tests timing constraints

---

## ✅ Validation Criteria

Each scenario validates:

### 1. Minimum Trade Count
```python
if results['trades'] < expected['min_trades']:
    FAIL("Too few trades executed")
```

### 2. TP Exits Working
```python
if expected['tp_exits']:
    tp_count = TP1 + TP2 + TP3
    if tp_count == 0:
        FAIL("No TP exits found")
```

### 3. SL Exits Working
```python
if expected['sl_exits']:
    if SL count == 0:
        FAIL("No SL exits found")
```

### 4. No Stuck Trades
```python
if backtest_completes:
    # Implicit check - all trades must close
    PASS
```

### 5. SL Adjustments (Adaptive only)
```python
if sl_adjustment == 'Adaptive v2.0':
    if SL_adjustment_count == 0:
        FAIL("Adaptive SL not updating")
```

### 6. Time Limit Exits
```python
if max_bars_held == 5:  # Very short
    if no time_limit_exits:
        FAIL("Expected time limit exits")
```

---

## 📈 Expected Output

### Success Case

```
================================================================================
BACKTEST CONFIGURATION COVERAGE TEST
Total Scenarios: 23
Strategy: 50% Asia Rejection Simple (v2)
Lookback: 90 days (60 train, 30 test)
================================================================================

[1/23] CRITICAL_001: Fibonacci + Adaptive Balanced (Default Production Config)
  ✅ PASS - Trades: 78 (TP1:27, TP2:18, TP3:12, SL:21)

[2/23] CRITICAL_002: Hybrid + Adaptive Balanced
  ✅ PASS - Trades: 72 (TP1:24, TP2:16, TP3:11, SL:21)

[3/23] CRITICAL_003: Fixed % + Adaptive Balanced
  ✅ PASS - Trades: 65 (TP1:22, TP2:15, TP3:9, SL:19)

...

[23/23] PAIRWISE_006: Fixed/Static/5%/10x/50bars
  ✅ PASS - Trades: 38 (TP1:12, TP2:8, TP3:5, SL:13)

================================================================================
TEST SUMMARY
================================================================================
Total Scenarios: 23
Passed: 23
Failed: 0
Pass Rate: 100.0%

Results saved to: tests/integration/results/coverage_test_2026-02-10_09-30-00.csv
================================================================================
```

### Failure Case

```
[5/23] CRITICAL_005: Fibonacci + Adaptive Conservative (Wider SLs)
  ❌ FAIL - Trades: 65 (TP1:20, TP2:12, TP3:7, SL:0)
    ⚠️  No SL exits found - expected at least one
    ⚠️  Expected SL adjustments but found none (Adaptive SL not working?)

================================================================================
TEST SUMMARY
================================================================================
Total Scenarios: 23
Passed: 22
Failed: 1
Pass Rate: 95.7%

❌ FAILURES (1):

  CRITICAL_005:
    - No SL exits found - expected at least one
    - Expected SL adjustments but found none (Adaptive SL not working?)
================================================================================
```

---

## 📊 Results Analysis

### CSV Report

Generated at: `tests/integration/results/coverage_test_YYYY-MM-DD_HH-MM-SS.csv`

**Columns**:
- `scenario_id`: Unique test ID
- `description`: Test description
- `passed`: True/False
- `trades`: Total trades executed
- `tp1/tp2/tp3`: TP exit counts
- `sl`: SL exit count
- `failures`: Failure messages (if failed)
- `config`: Full JSON config used

**Example**:
```csv
scenario_id,description,passed,trades,tp1,tp2,tp3,sl,failures,config
CRITICAL_001,Fibonacci + Adaptive Balanced,True,78,27,18,12,21,"","{...}"
CRITICAL_005,Conservative,False,65,20,12,7,0,"No SL exits; No SL adjustments","{...}"
```

### Analysis Queries

```python
import pandas as pd

# Load results
df = pd.read_csv('tests/integration/results/coverage_test_YYYY-MM-DD.csv')

# Pass rate by TP/SL mode
df.groupby(df['config'].str.contains('Fibonacci'))[['passed']].mean()

# Average trades by config
df.groupby('scenario_id')['trades'].mean()

# SL hits by preset
df[df['config'].str.contains('Adaptive')]['sl'].describe()
```

---

## 🔧 Customization

### Add New Scenarios

Edit `tests/integration/test_scenarios.py`:

```python
CRITICAL_SCENARIOS.append(
    BacktestScenario(
        id="CRITICAL_009",
        description="My Custom Test",
        config={
            'tpsl_mode': 'Fibonacci',
            'sl_adjustment': 'Adaptive v2.0',
            'adaptive_preset': 'Balanced',
            'risk_pct': 15,  # Custom risk
            'leverage': 10,
            'max_bars_held': 100,  # Custom time limit
            'sl_delay': 2,
            'emergency_sl': 2,
        },
        expected_behavior={
            'min_trades': 10,
            'tp_exits': True,
            'sl_exits': True,
        }
    )
)
```

### Change Test Strategy

Edit `_load_test_strategy()` in `test_backtest_configuration_coverage.py`:

```python
def _load_test_strategy(self):
    return {
        'name': 'My Custom Strategy',
        'strategy_type': 'Bullish',
        'blocks': [
            # Your strategy blocks
        ],
    }
```

### Change Test Duration

Edit `_build_config()`:

```python
config.update({
    'lookback_days': 180,  # Longer test
    'training_window': 120,
    'testing_window': 60,
})
```

---

## ⚡ Performance

### Expected Runtime

| Scenario Count | Bars per Test | Time per Test | Total Time |
|----------------|---------------|---------------|------------|
| 23 scenarios | ~8,000 bars | 10-15 sec | ~5-10 min |
| 50 scenarios | ~8,000 bars | 10-15 sec | ~10-12 min |
| 100 scenarios | ~8,000 bars | 10-15 sec | ~20-25 min |

### Optimization Tips

1. **Reduce lookback**: 90 → 60 days (faster, less coverage)
2. **Run critical only**: `-k "CRITICAL"` (5-10 scenarios)
3. **Parallel execution**: Use `pytest-xdist` (future enhancement)
4. **Cache data**: Reuse loaded bars across tests (future enhancement)

---

## 🐛 Troubleshooting

### Test Fails to Import

```bash
# Error: ModuleNotFoundError: No module named 'test_scenarios'
# Solution: Add __init__.py to tests/integration/
touch tests/integration/__init__.py
```

### allpairspy not found

```bash
# Warning: allpairspy not installed. Using manual pairwise scenarios.
# Solution: Install it (optional)
pip install allpairspy

# Or: Use manual pairwise (6 scenarios instead of ~15)
# No action needed - fallback works automatically
```

### Backtest Worker hangs

```python
# Issue: Worker.run() blocks forever
# Solution: Check signal connections in worker

# Ensure worker emits backtest_finished signal
worker.backtest_finished.emit(True, results)
```

### No trades generated

```python
# Issue: All scenarios show 0 trades
# Solutions:
# 1. Check strategy configuration valid
# 2. Check data availability for date range
# 3. Lower min_trades threshold in expected_behavior
# 4. Check signal detection is working
```

---

## 📚 References

- **Orthogonal Array Testing**: https://en.wikipedia.org/wiki/Orthogonal_array_testing
- **Pairwise Testing**: https://www.pairwise.org/
- **allpairspy Library**: https://github.com/thombashi/allpairspy

---

## ✅ Checklist for Running Tests

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] allpairspy installed (optional: `pip install allpairspy`)
- [ ] Data available for past 90 days
- [ ] Database accessible (optimizer_v3.db)
- [ ] No other backtests running
- [ ] Run command: `pytest tests/integration/test_backtest_configuration_coverage.py -v -s`
- [ ] Review results CSV after completion
- [ ] Investigate any failures
- [ ] Fix bugs found
- [ ] Re-run tests until 100% pass

---

## 🎯 Success Criteria

**Test suite is successful when**:

- ✅ 100% pass rate (all scenarios pass)
- ✅ All TP/SL modes tested
- ✅ All Adaptive presets tested
- ✅ Static vs Adaptive differentiated
- ✅ Partial exits working (TP1/TP2/TP3)
- ✅ Time limits working
- ✅ No stuck trades
- ✅ No unexplained failures

**Ready for production when**:

- ✅ Coverage tests pass 100%
- ✅ Exit flow verified working
- ✅ SL adjustments verified
- ✅ All bugs fixed
- ✅ CSV reports clean

---

**Last Updated**: February 10, 2026  
**Author**: BTC_Engine_v3 Team  
**Version**: 1.0
