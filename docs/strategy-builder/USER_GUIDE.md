# Strategy Builder - User Guide

**Version:** 1.0  
**Status:** Phase 1 Complete  
**Date:** 2026-01-09

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Creating Strategies](#creating-strategies)
4. [Validation](#validation)
5. [Managing Strategies](#managing-strategies)
6. [API Reference](#api-reference)
7. [Examples](#examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

The Strategy Builder is already integrated into BTC_Engine_v3. No additional installation required.

### Basic Usage

```python
from src.utils.Strategy_Builder import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType,
    RegistryBridge,
    StrategyValidator,
    StrategyRegistry
)

# 1. Explore available blocks
bridge = RegistryBridge()
blocks = bridge.get_blocks_by_category()

# 2. Create strategy
config = StrategyConfiguration(
    strategy_name="my_reversal_strategy",
    strategy_number=1,
    strategy_category=StrategyCategory.REVERSAL,
    main_signal_block="double_top",
    blocks=[
        BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=30,
            weight_range=(20, 40),
            is_main_signal=True,
            signals=[
                SignalConfiguration(
                    signal_name="BEARISH_BREAKDOWN",
                    signal_display_name="Bearish Breakdown",
                    role=SignalRole.SIGNAL
                )
            ]
        )
    ]
)

# 3. Validate
validator = StrategyValidator()
result = validator.validate(config)

if result.is_valid:
    print("✅ Strategy is valid!")
else:
    print("❌ Validation failed:")
    for error in result.errors:
        print(f"  - {error}")

# 4. Save
registry = StrategyRegistry()
filepath = registry.save_strategy(config)
print(f"Strategy saved to: {filepath}")
```

---

## Core Concepts

### Strategy Structure

A strategy consists of:

1. **Building Blocks**: Modular components (patterns, indicators, etc.)
2. **Signals**: Specific outputs from blocks (e.g., BEARISH_BREAKDOWN)
3. **Weights**: Importance of each block (contributes to confluence score)
4. **Roles**: How signals are used (FILTER, SIGNAL, BOOSTER)

### Strategy Categories

- **REVERSAL**: Trades reversals (M, W patterns, etc.)
- **CONTINUATION**: Trades trend continuations
- **SCALPING**: Quick in-and-out trades
- **RANGE_TRADING**: Trades within ranges
- **BREAKOUT**: Trades breakouts
- **MOMENTUM**: Follows strong momentum
- **MEAN_REVERSION**: Trades mean reversion

### Signal Roles

- **FILTER**: Must be true for entry (eliminates trades)
- **SIGNAL**: Primary entry trigger (generates trades)
- **BOOSTER**: Increases confluence (improves quality)
- **TEST_ALL**: Test all permutations in optimizer

### Block Types

- **EVENT**: One-time events (pattern formation)
- **SIGNAL**: Continuous signals (above MA, etc.)
- **CONTEXT**: Market context (trend, volatility)
- **HYBRID**: Combination of above

---

## Creating Strategies

### Step 1: Explore Available Blocks

```python
bridge = RegistryBridge()

# Get all blocks by category
blocks = bridge.get_blocks_by_category()

for category, category_blocks in blocks.items():
    print(f"\n{category}:")
    for block in category_blocks:
        print(f"  - {block.display_name}")
        print(f"    Signals: {', '.join(block.signals)}")
        print(f"    Weight Range: {block.weight_range}")
```

### Step 2: Select Blocks

Choose blocks that align with your strategy:

```python
# Example: Reversal strategy with double top
selected_blocks = [
    {
        'name': 'double_top',
        'display_name': 'Double Top',
        'category': 'PATTERNS',
        'type': BlockType.EVENT,
        'weight': 30,
        'weight_range': (20, 40),
        'signals': ['BEARISH_BREAKDOWN']
    }
]
```

### Step 3: Create Configuration

```python
config = StrategyConfiguration(
    strategy_name="reversal_double_top",
    strategy_number=1,
    strategy_category=StrategyCategory.REVERSAL,
    description="Reversal strategy using double top pattern",
    main_signal_block="double_top",
    blocks=[
        BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=30,
            weight_range=(20, 40),
            is_main_signal=True,
            signals=[
                SignalConfiguration(
                    signal_name="BEARISH_BREAKDOWN",
                    signal_display_name="Bearish Breakdown",
                    role=SignalRole.SIGNAL
                )
            ]
        )
    ],
    min_confluence=70,
    risk_reward_ratio="1:3"
)
```

### Step 4: Validate

```python
validator = StrategyValidator()
result = validator.validate(config)

print(result.get_summary())

if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")

for warning in result.warnings:
    print(f"Warning: {warning}")
```

### Step 5: Save

```python
registry = StrategyRegistry()

# Save with validation
filepath = registry.save_strategy(config, validate=True)

# Or save without validation (for testing)
filepath = registry.save_strategy(config, validate=False)
```

---

## Validation

The validator performs 8 layers of validation:

### 1. Basic Structure
- Strategy has 1-10 blocks
- Naming convention is correct
- Required fields are present

### 2. Block Existence
- All blocks exist in registry
- Blocks have valid metadata

### 3. Signal Validity
- All signals exist for their blocks
- Signal names match block's available signals

### 4. Weight Constraints
- Individual weights within specified ranges
- Total weight is reasonable (warning if < 50)

### 5. Main Signal Logic
- Main signal block is in blocks list
- Main signal block is marked correctly

### 6. Role Distribution
- At least one SIGNAL role exists
- Balanced distribution recommended

### 7. Conflict Detection
- No conflicting bullish/bearish patterns
- Compatible block combinations

### 8. Strategy-Specific
- Category-appropriate blocks
- Logical combinations

### Validation Results

```python
result = validator.validate(config)

# Check validity
if result.is_valid:
    print("✅ Valid")
else:
    print("❌ Invalid")

# Get errors
for error in result.errors:
    print(f"Error: {error}")

# Get warnings
for warning in result.warnings:
    print(f"Warning: {warning}")

# Get suggestions
for suggestion in result.suggestions:
    print(f"Suggestion: {suggestion}")

# Quick validate (boolean only)
is_valid = validator.quick_validate(config)
```

---

## Managing Strategies

### List All Strategies

```python
registry = StrategyRegistry()

# List all
strategies = registry.list_strategies()

for s in strategies:
    print(f"{s.number}: {s.name} ({s.category})")
```

### Filter by Category

```python
# Get only reversal strategies
reversal_strategies = registry.list_strategies(
    category=StrategyCategory.REVERSAL
)
```

### Search Strategies

```python
# Search by name (case-insensitive)
results = registry.search_strategies('double_top')

for s in results:
    print(f"Found: {s.name}")
```

### Load Strategy

```python
# Load by number
config = registry.load_strategy(1)

if config:
    print(f"Loaded: {config.strategy_name}")
else:
    print("Strategy not found")
```

### Delete Strategy

```python
# Delete strategy
success = registry.delete_strategy(1)

if success:
    print("Strategy deleted")
else:
    print("Strategy not found")
```

### Get Statistics

```python
# Total count
total = registry.get_strategy_count()
print(f"Total strategies: {total}")

# Count by category
counts = registry.get_category_counts()
for category, count in counts.items():
    print(f"{category}: {count}")
```

### Export/Import

```python
# Export
success = registry.export_strategy(
    strategy_number=1,
    output_path=Path("exported_strategy.json")
)

# Import
imported = registry.import_strategy(
    filepath=Path("exported_strategy.json"),
    strategy_number=None,  # Auto-assign
    validate=True
)
```

---

## API Reference

### StrategyConfiguration

Main strategy configuration model.

**Fields:**
- `strategy_name` (str): Strategy name
- `strategy_number` (int): Unique number (1-150)
- `strategy_category` (StrategyCategory): Category
- `description` (str): Optional description
- `main_signal_block` (str): Main signal block name
- `blocks` (List[BlockSelection]): Selected blocks
- `min_confluence` (int): Minimum confluence score (default: 70)
- `risk_reward_ratio` (str): Risk:reward ratio (default: "1:3")
- `max_bars_held` (int): Max bars to hold position (default: 1000)
- `risk_per_trade_pct` (float): Risk per trade % (default: 1.0)
- `max_leverage` (float): Max leverage (default: 2.0)

### BlockSelection

Block selection within a strategy.

**Fields:**
- `block_name` (str): Block identifier
- `block_display_name` (str): Human-readable name
- `block_category` (str): Category
- `block_type` (BlockType): Type
- `weight` (int): Weight (must be in  weight_range)
- `weight_range` (Tuple[int, int]): Valid weight range
- `enabled` (bool): Whether block is enabled (default: True)
- `signals` (List[SignalConfiguration]): Selected signals
- `is_main_signal` (bool): Is this the main signal? (default: False)

### SignalConfiguration

Signal configuration within a block.

**Fields:**
- `signal_name` (str): Signal identifier
- `signal_display_name` (str): Human-readable name
- `role` (SignalRole): Signal role (FILTER/SIGNAL/BOOSTER/TEST_ALL)
- `required` (bool): Is signal required? (default: True)
- `min_confidence` (float): Minimum confidence (0-100, default: 0)

### RegistryBridge

Bridge to building blocks registry.

**Methods:**
- `get_blocks_by_category() -> Dict[str, List[BlockInfo]]`
  Get all blocks organized by category

### StrategyValidator

Validates strategy configurations.

**Methods:**
- `validate(config: StrategyConfiguration) -> ValidationResult`
  Full validation with detailed results
  
- `quick_validate(config: StrategyConfiguration) -> bool`
  Quick boolean validation

### StrategyRegistry

Manages strategy persistence.

**Methods:**
- `get_next_strategy_number() -> int`
  Get next available strategy number
  
- `save_strategy(config, validate=True, overwrite=False) -> Path`
  Save strategy to JSON
  
- `load_strategy(strategy_number: int) -> Optional[StrategyConfiguration]`
  Load strategy by number
  
- `list_strategies(category=None) -> List[StrategyMetadata]`
  List all or filtered strategies
  
- `search_strategies(query: str) -> List[StrategyMetadata]`
  Search strategies by name
  
- `delete_strategy(strategy_number: int) -> bool`
  Delete strategy
  
- `get_strategy_count() -> int`
  Get total count
  
- `get_category_counts() -> Dict[str, int]`
  Get count by category
  
- `export_strategy(strategy_number, output_path) -> bool`
  Export strategy
  
- `import_strategy(filepath, strategy_number, validate) -> Optional[StrategyConfiguration]`
  Import strategy

---

## Examples

### Example 1: Simple Reversal Strategy

```python
from src.utils.Strategy_Builder import *

# Create simple reversal strategy
config = StrategyConfiguration(
    strategy_name="simple_reversal",
    strategy_number=1,
    strategy_category=StrategyCategory.REVERSAL,
    main_signal_block="double_top",
    blocks=[
        BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=30,
            weight_range=(20, 40),
            is_main_signal=True,
            signals=[
                SignalConfiguration(
                    signal_name="BEARISH_BREAKDOWN",
                    role=SignalRole.SIGNAL
                )
            ]
        )
    ]
)

# Validate and save
validator = StrategyValidator()
if validator.quick_validate(config):
    registry = StrategyRegistry()
    registry.save_strategy(config)
```

### Example 2: Multi-Block Strategy

```python
# Create strategy with multiple blocks
config = StrategyConfiguration(
    strategy_name="multi_block_reversal",
    strategy_number=2,
    strategy_category=StrategyCategory.REVERSAL,
    main_signal_block="double_top",
    blocks=[
        # Main signal
        BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=35,
            weight_range=(30, 40),
            is_main_signal=True,
            signals=[
                SignalConfiguration(
                    signal_name="BEARISH_BREAKDOWN",
                    role=SignalRole.SIGNAL
                )
            ]
        ),
        # Filter
        BlockSelection(
            block_name="ema_200",
            block_display_name="EMA 200",
            block_category="MOVING_AVERAGES",
            block_type=BlockType.SIGNAL,
            weight=15,
            weight_range=(10, 20),
            signals=[
                SignalConfiguration(
                    signal_name="BELOW_EMA",
                    role=SignalRole.FILTER
                )
            ]
        ),
        # Booster
        BlockSelection(
            block_name="rsi",
            block_display_name="RSI",
            block_category="OSCILLATORS",
            block_type=BlockType.SIGNAL,
            weight=20,
            weight_range=(15, 25),
            signals=[
                SignalConfiguration(
                    signal_name="OVERBOUGHT",
                    role=SignalRole.BOOSTER
                )
            ]
        )
    ],
    min_confluence=75
)
```

### Example 3: Batch Operations

```python
# Create multiple strategies
registry = StrategyRegistry()

strategies = [
    ("reversal_m", StrategyCategory.REVERSAL),
    ("reversal_w", StrategyCategory.REVERSAL),
    ("continuation_trend", StrategyCategory.CONTINUATION),
]

for name, category in strategies:
    num = registry.get_next_strategy_number()
    
    config = StrategyConfiguration(
        strategy_name=name,
        strategy_number=num,
        strategy_category=category,
        main_signal_block="test",
        blocks=[...]  # Add blocks
    )
    
    registry.save_strategy(config, validate=False)

# List all
for s in registry.list_strategies():
    print(f"{s.number}: {s.name}")
```

---

## Best Practices

### 1. Always Validate

```python
# ✅ Good
result = validator.validate(config)
if result.is_valid:
    registry.save_strategy(config, validate=False)

# ❌ Bad
registry.save_strategy(config, validate=False)  # No validation
```

### 2. Use Descriptive Names

```python
# ✅ Good
strategy_name = "reversal_double_top_rsi_filter"

# ❌ Bad
strategy_name = "strat1"
```

### 3. Keep Blocks Focused

```python
# ✅ Good - 3-5 blocks with clear roles
blocks = [main_signal, filter, booster]

# ❌ Bad - Too many blocks
blocks = [block1, block2, ..., block10]  # Too complex
```

### 4. Balance Weights

```python
# ✅ Good - Total ~70-100
main_signal: 35
filter: 20
booster: 20
# Total: 75

# ❌ Bad - Too low total
main_signal: 10
filter: 5
# Total: 15 (too low)
```

### 5. Use Appropriate Roles

```python
# ✅ Good
main_pattern = SignalRole.SIGNAL  # Primary entry
ma_filter = SignalRole.FILTER     # Must be true
rsi_boost = SignalRole.BOOSTER    # Adds confluence

# ❌ Bad
everything = SignalRole.SIGNAL  # Confusing
```

---

## Troubleshooting

### Common Errors

**Error: "Main signal block not in blocks list"**
```python
# Make sure main_signal_block matches a block name
main_signal_block = "double_top"  # ✅
blocks = [BlockSelection(block_name="double_top", ...)]  # ✅
```

**Error: "Block not found in registry"**
```python
# Use RegistryBridge to find valid block names
bridge = RegistryBridge()
blocks = bridge.get_blocks_by_category()
# Use actual block names from registry
```

**Error: "Weight not in range"**
```python
# Ensure weight is within weight_range
weight = 25  # ✅
weight_range = (20, 30)  # ✅
```

**Error: "Invalid signal for block"**
```python
# Check available signals for block
bridge = RegistryBridge()
block_info = bridge.get_block_info("double_top")
print(block_info.signals)  # Use one of these
```

### Validation Warnings

**Warning: "Low total weight"**
- Increase individual block weights
- Add more blocks
- Target total weight: 70-100

**Warning: "No FILTER roles"**
- Consider adding a filter block
- Filters improve strategy quality

**Warning: "Conflicting patterns"**
- Remove conflicting blocks
- Choose either bullish OR bearish patterns

---

## Code Generation (Phase 2)

The Strategy Builder now includes automatic code generation! Turn your strategy configurations into production-ready NautilusTrader strategies, test files, and optimizer configs.

### Quick Start

```python
from src.utils.Strategy_Builder import StrategyGenerator, StrategyRegistry

# Load saved strategy
registry = StrategyRegistry()
config = registry.load_strategy(1)

# Generate all files
generator = StrategyGenerator()
files = generator.generate_all(config)

print(f"Strategy: {files['strategy']}")
print(f"Test: {files['test']}")
print(f"Optimizer: {files['optimizer']}")
```

### One-Line Generation

```python
# Even easier - one call!
registry = StrategyRegistry()
files = registry.generate_strategy_files(1)

# All files generated:
# src/strategies/strategy_001_name.py
# tests/strategies/test_001_name.py
# config/optimizer_001_name.yaml
```

### What Gets Generated?

1. **NautilusTrader Strategy File**
   - Complete strategy implementation
   - All building blocks initialized
   - Confluence calculation
   - Entry/exit logic
   - Risk management
   - Performance tracking

2. **Comprehensive Test Suite**
   - Strategy initialization tests
   - Block processing tests
   - Confluence calculation tests
   - Entry/exit logic tests
   - Risk management tests
   - Edge case tests

3. **Optimizer Configuration**
   - Parameter optimization ranges
   - Walk-forward test settings
   - Backtest configuration
   - Validation settings

### Generated Code Features

- ✅ Syntactically valid Python
- ✅ All imports resolved
- ✅ Type hints included
- ✅ Comprehensive logging
- ✅ Error handling
- ✅ PEP 8 compliant

### Example: Complete Workflow

```python
# 1. Create strategy configuration
config = StrategyConfiguration(
    strategy_name="my_strategy",
    strategy_number=1,
    strategy_category=StrategyCategory.REVERSAL,
    main_signal_block="double_top",
    blocks=[...list of blocks...]
)

# 2. Validate
validator = StrategyValidator()
result = validator.validate(config)

if result.is_valid:
    # 3. Save configuration
    registry = StrategyRegistry()
    registry.save_strategy(config)
    
    # 4. Generate all files
    files = registry.generate_strategy_files(1)
    
    print("✅ Strategy ready for testing!")
    print(f"Strategy: {files['strategy']}")
    print(f"Test: {files['test']}")
    print(f"Config: {files['optimizer']}")
```

### Advanced Usage

```python
# Custom output directories
generator = StrategyGenerator()
files = generator.generate_all(
    config,
    strategy_dir=Path("custom/strategies"),
    test_dir=Path("custom/tests"),
    config_dir=Path("custom/configs")
)

# Dry run (preview without saving)
previews = generator.dry_run(config)
print("Strategy preview:")
print(previews['strategy'][:500])  # First 500 chars

# Validate generated code
is_valid = generator.validate_python_syntax(files['strategy'])
print(f"Generated code valid: {is_valid}")
```

---

## Support

For issues or questions:
1. Check this guide
2. Review test files for examples
3. Check API reference
4. Review source code documentation

---

**Version:** 2.0 (Code Generation Complete!)  
**Last Updated:** 2026-01-09  
**Status:** Production Ready ✅
