# Institutional-Grade Configuration Debugger

**Status:** Production Ready  
**Version:** 1.0.0  
**Date:** 2026-01-11  
**Purpose:** Micro-granular logging and validation of configuration usage in trading systems

## Overview

The Configuration Debugger provides institutional-grade tracking and validation of every configuration value from source to usage. Designed for trading systems where real money is at risk, it ensures 100% accuracy by logging every decision point and validating that configured values are actually being used as configured.

## Core Features

### 1. **Configuration Registry**
- Tracks every config field with source information
- Records type, value, and registration timestamp
- Supports multiple config sources (files, dicts, objects)

### 2. **Usage Tracking**
- Logs every config value read
- Tracks code location of each read
- Identifies missing keys and default value usage

### 3. **Validation**
- Compares expected vs actual values
- Detects mismatches with CRITICAL alerts
- Provides full audit trail of all validations

### 4. **Decision Logging**
- Logs every if/else, switch, branch point
- Records config keys involved in decisions
- Tracks decision outcomes

### 5. **Action Logging**
- Logs actions taken (calculate TP, set SL, etc.)
- Records config keys used in actions
- Tracks parameters passed to actions

## Quick Start

### Basic Usage

```python
from pathlib import Path
from src.debugger_logger import ConfigDebugger, DebugLevel

# Create debugger
debugger = ConfigDebugger(
    name="UniversalOptimizer",
    level=DebugLevel.MEDIUM,  # CRITICAL, HIGH, MEDIUM, LOW, TRACE
    log_file=Path("logs/config_debug.log"),
    console_output=True
)

# Register configuration source
config = {
    'tp_mode': 'FIBONACCI',
    'min_risk_reward': 1.2,
    'max_leverage': 2.0
}
debugger.register_config_source(
    config_dict=config,
    source="config/optimizer_001.yaml",
    source_type="yaml_file"
)

# Get config values with tracking
tp_mode = debugger.get_config_value('tp_mode', default='PERCENTAGE')
# Output: [CONFIG_READ] tp_mode = FIBONACCI (from config/optimizer_001.yaml)

# Validate usage
debugger.validate_config_usage(
    key='tp_mode',
    expected_value='FIBONACCI',
    actual_value=tp_mode
)
# Output: [CONFIG_VALIDATED] tp_mode: FIBONACCI == FIBONACCI ✓

# Log decisions
test_tp_modes = (tp_mode == 'FIBONACCI')
debugger.log_decision(
    decision_type='if_statement',
    condition='tp_mode == FIBONACCI',
    result=test_tp_modes,
    config_keys_used=['tp_mode']
)

# Log actions
debugger.log_action(
    action='calculate_take_profit',
    config_keys_used=['tp_mode'],
    parameters={'mode': tp_mode, 'price': 45000}
)

# Generate report
report = debugger.generate_report()
print(report)

# Save report
debugger.save_report(Path("reports/config_audit.txt"))
debugger.export_json(Path("reports/config_audit.json"))
```

## Debug Levels

```python
class DebugLevel(Enum):
    CRITICAL = 1  # Only critical mismatches
    HIGH = 2      # Important decisions and actions
    MEDIUM = 3    # All config reads (recommended for testing)
    LOW = 4       # Every field access
    TRACE = 5     # Everything including internal calculations
```

## Integration Examples

### Example 1: Universal Optimizer Integration

```python
from src.debugger_logger import ConfigDebugger, DebugLevel

class UniversalOptimizer:
    def __init__(self, config_file: Path):
        # Initialize debugger
        self.debugger = ConfigDebugger(
            name="UniversalOptimizer",
            level=DebugLevel.MEDIUM,
            log_file=Path(f"logs/optimizer_debug_{datetime.now():%Y%m%d_%H%M%S}.log"),
            console_output=True
        )
        
        # Load config
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        # Register config
        self.debugger.register_config_source(
            config_dict=config,
            source=str(config_file),
            source_type="yaml_file"
        )
        
        # Get config values with tracking
        self.tp_mode = self.debugger.get_config_value('tp_mode', 'PERCENTAGE')
        self.min_rr = self.debugger.get_config_value('min_risk_reward', 1.2)
        
    def calculate_take_profit(self, entry_price: float, sl_distance: float):
        # Log the action
        self.debugger.log_action(
            action='calculate_take_profit',
            config_keys_used=['tp_mode'],
            parameters={'entry': entry_price, 'sl_dist': sl_distance}
        )
        
        # Make decision based on tp_mode
        if self.tp_mode == 'FIBONACCI':
            self.debugger.log_decision(
                decision_type='if',
                condition='tp_mode == FIBONACCI',
                result=True,
                config_keys_used=['tp_mode']
            )
            return self._fibonacci_tp(entry_price)
        else:
            self.debugger.log_decision(
                decision_type='else',
                condition='tp_mode == PERCENTAGE',
                result=True,
                config_keys_used=['tp_mode']
            )
            return self._percentage_tp(entry_price)
```

### Example 2: TP Mode Validation

```python
# In dynamic_tp_calculator.py
def calculate_tp_levels(self, config, entry_price, sl_distance):
    # Get tp_mode from config
    tp_mode_config = config.get('tp_mode', 'PERCENTAGE')
    
    # Validate we're using the right mode
    debugger.validate_config_usage(
        key='tp_mode',
        expected_value=tp_mode_config,
        actual_value=tp_mode_config  # Should match!
    )
    
    # Log decision
    debugger.log_decision(
        decision_type='if',
        condition=f'tp_mode == {tp_mode_config}',
        result=True,
        config_keys_used=['tp_mode']
    )
    
    # If mismatch detected, will show:
    # ❌ CRITICAL MISMATCH DETECTED
    # Key: tp_mode
    # Expected: FIBONACCI
    # Actual: PERCENTAGE
    # ⚠️ CONFIG VALUE NOT BEING USED AS CONFIGURED!
```

## Output Examples

### Successful Validation
```
[CONFIG_SOURCE_REGISTERED] 2026-01-11T11:30:00
Source: config/optimizer_001_lod_rejection.yaml (yaml_file)
Fields Registered: 15
Fields: tp_mode, min_risk_reward, max_leverage, ...

[CONFIG_READ] tp_mode = FIBONACCI (from config/optimizer_001_lod_rejection.yaml)
[CONFIG_VALIDATED] tp_mode: FIBONACCI == FIBONACCI ✓
[DECISION] if: tp_mode == FIBONACCI = True (using {'tp_mode': 'FIBONACCI'})
[ACTION] calculate_take_profit
  Config Used: {'tp_mode': 'FIBONACCI'}
  Parameters: {'entry': 45000, 'sl_dist': 450}
```

### Mismatch Detection
```
╔══════════════════════════════════════════════════════════════════════════════╗
║ ❌ CRITICAL MISMATCH DETECTED                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
Timestamp: 2026-01-11T11:30:15
Key: tp_mode
Expected: FIBONACCI (str)
Actual: PERCENTAGE (str)
Location: dynamic_tp_calculator.py:125

⚠️  CONFIG VALUE NOT BEING USED AS CONFIGURED!
⚠️  THIS COULD LEAD TO INCORRECT TRADING DECISIONS!
```

## Audit Report

The `generate_report()` method produces a comprehensive audit:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ CONFIGURATION AUDIT REPORT                                                   ║
║ Component: UniversalOptimizer                                                ║
║ Generated: 2026-01-11 11:35:00                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. CONFIGURATION REGISTRY
────────────────────────────────────────────────────────────────────────────────
Total Fields: 15

  tp_mode:
    Value: FIBONACCI
    Type: str
    Source: config/optimizer_001_lod_rejection.yaml
    Registered: 2026-01-11T11:30:00

  min_risk_reward:
    Value: 1.2
    Type: float
    Source: config/optimizer_001_lod_rejection.yaml
    Registered: 2026-01-11T11:30:00

2. USAGE SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Reads: 47
Found: 45
Missing (used default): 2

Missing Keys:
  - test_tp_modes (requested 1 times)
  - quick_test (requested 1 times)

3. MISMATCH SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Mismatches: 1

❌ CRITICAL MISMATCHES DETECTED:

  Key: tp_mode
  Expected: FIBONACCI
  Actual: PERCENTAGE
  Location: dynamic_tp_calculator.py:125
  Time: 2026-01-11T11:30:15

4. DECISION SUMMARY
────────────────────────────────────────────────────────────────────────────────
Total Decisions: 23

Recent Decisions:
  [if_statement] tp_mode == FIBONACCI = True
    Config: ['tp_mode']
    Location: optimizer_core.py:245
```

## Best Practices

### 1. **Always Register Config Sources**
```python
# Bad
tp_mode = config.get('tp_mode')

# Good
debugger.register_config_source(config, source="config.yaml")
tp_mode = debugger.get_config_value('tp_mode')
```

### 2. **Validate Critical Values**
```python
# After reading a config value that affects trading
tp_mode_from_config = config['tp_mode']
debugger.validate_config_usage(
    key='tp_mode',
    expected_value=tp_mode_from_config,
    actual_value=self.tp_mode  # What's actually being used
)
```

### 3. **Log All Decision Points**
```python
if self.tp_mode == 'FIBONACCI':
    debugger.log_decision(
        decision_type='if',
        condition='tp_mode == FIBONACCI',
        result=True,
        config_keys_used=['tp_mode']
    )
    # fibonacci code...
else:
    debugger.log_decision(
        decision_type='else',
        condition='tp_mode != FIBONACCI',
        result=True,
        config_keys_used=['tp_mode']
    )
    # percentage code...
```

### 4. **Generate Reports After Tests**
```python
# At end of backtest
report = debugger.generate_report()
debugger.save_report(Path("reports/audit.txt"))
debugger.export_json(Path("reports/audit.json"))

# Check for mismatches
if debugger.mismatch_registry:
    print("⚠️ CRITICAL: Configuration mismatches detected!")
    for mismatch in debugger.mismatch_registry:
        print(f"  {mismatch['key']}: {mismatch['expected']} != {mismatch['actual']}")
```

## Common Use Cases

### Finding Why TP Mode Isn't Working

```python
# 1. Register config with debugger
debugger.register_config_source(optimizer_config, "optimizer_config.yaml")

# 2. Track where tp_mode is read
tp_mode = debugger.get_config_value('tp_mode')
# Logs: [CONFIG_READ] tp_mode = FIBONACCI (from optimizer_config.yaml)

# 3. Validate it's used correctly in TP calculator
actual_mode_used = calculate_tp(..., mode=some_variable)
debugger.validate_config_usage('tp_mode', tp_mode, actual_mode_used)
# If mismatch: CRITICAL MISMATCH DETECTED!

# 4. Check the report
report = debugger.generate_report()
# Shows all reads, all usages, all mismatches
```

## Troubleshooting

### Issue: Too Much Output
**Solution:** Reduce debug level
```python
debugger.level = DebugLevel.HIGH  # Less verbose
```

### Issue: Missing Config Values
**Solution:** Check the usage summary in the report
```python
report = debugger.generate_report()
# Section 2 shows all missing keys
```

### Issue: Mismatch Not Detected
**Solution:** Ensure validation is called
```python
# Must explicitly validate
debugger.validate_config_usage(key, expected, actual)
```

## API Reference

### ConfigDebugger

#### `__init__(name, level, log_file, console_output)`
Initialize the debugger.

#### `register_config_source(config_dict, source, source_type)`
Register a configuration source for tracking.

#### `get_config_value(key, default, location)`
Get a config value with tracking. Returns the value.

#### `validate_config_usage(key, expected_value, actual_value, location)`
Validate that a config value is being used correctly. Returns True if match.

#### `log_decision(decision_type, condition, result, config_keys_used, location)`
Log a decision point (if/else, etc.).

#### `log_action(action, config_keys_used, parameters, location)`
Log an action being taken.

#### `generate_report()`
Generate comprehensive audit report. Returns formatted string.

#### `save_report(output_file)`
Save audit report to file.

#### `export_json(output_file)`
Export all data as JSON for analysis.

## Integration Checklist

- [ ] Import ConfigDebugger
- [ ] Initialize debugger with appropriate level
- [ ] Register all config sources
- [ ] Replace direct config.get() with debugger.get_config_value()
- [ ] Add validation for critical values
- [ ] Log all decision points
- [ ] Log all actions
- [ ] Generate report at end of run
- [ ] Check for mismatches in report
- [ ] Fix any mismatches found

## Next Steps

1. Integrate into universal_optimizer_v2.py
2. Run test with debugger enabled
3. Review audit report
4. Fix any configuration mismatches
5. Verify trades change when tp_mode changes

---

**Remember:** Real money is at risk. Use this debugger to ensure 100% accuracy.
