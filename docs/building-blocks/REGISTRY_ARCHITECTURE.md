# Building Block Registry Architecture
**Version:** 2.0  
**Date:** 2026-01-09  
**Purpose:** Centralized, self-maintaining building block management system

---

## Problem Statement

**Current Issues:**
1. 80+ building blocks scattered across directories
2. Each block returns different signal formats
3. ConfluenceCalculator has hardcoded assumptions about signals
4. No single source of truth
5. Adding new blocks requires manual updates in 5+ places
6. Signal name mismatches cause silent failures (0 points)
7. Obscene development time wasted on preventable bugs

**Impact:**
- 6+ hours debugging signal mismatches
- 0 trades due to name mismatches
- Every new block = manual updates everywhere
- High complexity, low maintainability

---

## Solution: Building Block Registry Pattern

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   BUILDING BLOCK REGISTRY                   │
│                  (Single Source of Truth)                   │
├─────────────────────────────────────────────────────────────┤
│ • Auto-discovery of all blocks                             │
│ • Signal schema validation                                 │
│ • Metadata storage                                         │
│ • Dynamic loading                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
         ┌────────┼────────┬────────────┐
         │        │        │            │
         ▼        ▼        ▼            ▼
    Strategies  Optimizer  Confluence  New Tools
                           Calculator  (auto-work)
```

### Core Components

#### 1. Registry Core (`src/detectors/building_blocks/registry.py`)

**Responsibilities:**
- Auto-discover all building blocks
- Store metadata for each block
- Provide query interface
- Validate signal schemas
- Dynamic instantiation

**API:**
```python
from src.detectors.building_blocks.registry import BlockRegistry

# Get all blocks
blocks = BlockRegistry.get_all_blocks()

# Get specific block
block_meta = BlockRegistry.get_block('double_top')

# Get blocks by category
patterns = BlockRegistry.get_blocks_by_category('PATTERNS')

# Instantiate block
detector = BlockRegistry.instantiate('double_top', timeframe='15min')

# Get valid signals for block
signals = BlockRegistry.get_valid_signals('double_top')
# Returns: ['BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN']

# Get recommended weight
weight = BlockRegistry.get_default_weight('double_top')
# Returns: 30
```

#### 2. Block Metadata Standard

Every building block MUST declare its metadata:

```python
# In each detector file (e.g., double_top.py)

from src.detectors.building_blocks.registry import register_block

@register_block(
    name='double_top',
    category='PATTERNS',
    class_name='DoubleTopPattern',
    default_weight=30,
    valid_signals=[
        'BEARISH_BREAKDOWN',
        'PATTERN_FORMING',
        'NO_PATTERN',
        'INSUFFICIENT_DATA',
        'ERROR'
    ],
    signal_tiers={
        'BEARISH_BREAKDOWN': {
            'base_points': 30,
            'formula': 'quality_thresholds',
            'thresholds': [(90, 30), (80, 25), (70, 20), (0, 15)]
        },
        'PATTERN_FORMING': {
            'max_points': 15,
            'formula': 'scaled'
        },
        'NO_PATTERN': {
            'points': 0
        }
    },
    description='Double top bearish reversal pattern',
    tags=['reversal', 'bearish', 'swing-trading']
)
class DoubleTopPattern:
    def __init__(self, timeframe='15min'):
        # Implementation...
    
    def analyze(self, df):
        # Must return signal from valid_signals list
        return {
            'signal': 'BEARISH_BREAKDOWN',  # MUST be in valid_signals
            'confidence': 95,
            # ... other fields
        }
```

**Benefits:**
- Block self-describes its capabilities
- Registry validates at import time
- ConfluenceCalculator auto-adapts
- No manual updates needed

#### 3. Auto-Registration Mechanism

**How it works:**

```python
# registry.py

class BlockRegistry:
    _blocks = {}
    
    @classmethod
    def register(cls, metadata):
        """Register a building block with metadata"""
        name = metadata['name']
        
        # Validate metadata
        cls._validate_metadata(metadata)
        
        # Store
        cls._blocks[name] = metadata
        
        # Auto-generate ConfluenceCalculator tier
        cls._update_confluence_tiers(name, metadata)
        
        return lambda block_class: block_class
    
    @classmethod
    def _validate_metadata(cls, metadata):
        """Ensure metadata is complete and valid"""
        required = ['name', 'category', 'class_name', 'valid_signals']
        for field in required:
            if field not in metadata:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate signals are defined in signal_tiers
        signals = set(metadata['valid_signals'])
        tiers = set(metadata.get('signal_tiers', {}).keys())
        
        undefined = signals - tiers - {'ERROR', 'INSUFFICIENT_DATA'}
        if undefined:
            raise ValueError(f"Signals {undefined} not defined in signal_tiers")
    
    @classmethod
    def _update_confluence_tiers(cls, name, metadata):
        """Auto-update ConfluenceCalculator with this block's tiers"""
        ConfluenceCalculator.SIGNAL_TIERS[name] = {
            'max_points': metadata['default_weight'],
            'tiers': metadata['signal_tiers']
        }


# Decorator for convenience
def register_block(**metadata):
    """Decorator to register a building block"""
    return BlockRegistry.register(metadata)
```

#### 4. Dynamic ConfluenceCalculator

**NEW VERSION - No hardcoded signals!**

```python
class ConfluenceCalculator:
    # Signal tiers auto-populated by registry
    SIGNAL_TIERS = {}  # Starts empty, registry fills it
    
    @classmethod
    def calculate_points(cls, block_name, signal, confidence, weight=None):
        """Calculate points - queries registry if needed"""
        
        # Get tier from registry if not in cache
        if block_name not in cls.SIGNAL_TIERS:
            metadata = BlockRegistry.get_block(block_name)
            if metadata:
                cls.SIGNAL_TIERS[block_name] = {
                    'max_points': metadata['default_weight'],
                    'tiers': metadata['signal_tiers']
                }
        
        # Rest of calculation logic (unchanged)
        # ...
```

#### 5. Validation & Testing

**Auto-Validation Script:**

```python
# scripts/validate_registry.py

def validate_all_blocks():
    """Validate every registered block actually works"""
    
    for block_name, metadata in BlockRegistry.get_all_blocks().items():
        print(f"Validating {block_name}...")
        
        # 1. Can we instantiate it?
        try:
            detector = BlockRegistry.instantiate(block_name)
        except Exception as e:
            raise ValueError(f"{block_name}: Failed to instantiate - {e}")
        
        # 2. Does it have analyze() method?
        if not hasattr(detector, 'analyze'):
            raise ValueError(f"{block_name}: Missing analyze() method")
        
        # 3. Does it return valid signals?
        test_df = create_test_data()
        result = detector.analyze(test_df)
        
        signal = result.get('signal', '')
        valid_signals = metadata['valid_signals']
        
        if signal not in valid_signals:
            raise ValueError(
                f"{block_name}: Returned invalid signal '{signal}'\n"
                f"Valid signals: {valid_signals}"
            )
        
        # 4. Is signal defined in ConfluenceCalculator?
        if block_name in ConfluenceCalculator.SIGNAL_TIERS:
            tiers = ConfluenceCalculator.SIGNAL_TIERS[block_name]['tiers']
            if signal not in tiers and signal not in ['ERROR', 'INSUFFICIENT_DATA']:
                raise ValueError(
                    f"{block_name}: Signal '{signal}' not in ConfluenceCalculator tiers"
                )
        
        print(f"  ✅ {block_name} validated")
    
    print("\n✅ All blocks validated successfully!")
```

**Run this in CI/CD:**
```bash
# Pre-commit hook
python scripts/validate_registry.py || exit 1

# GitHub Actions
- name: Validate Building Blocks
  run: python scripts/validate_registry.py
```

---

## Implementation Plan

### Phase 1: Create Registry Infrastructure (Day 1)

1. Create `src/detectors/building_blocks/registry.py`
2. Implement `BlockRegistry` class
3. Implement `@register_block` decorator
4. Create validation tools

### Phase 2: Migrate Existing Blocks (Day 2-3)

1. Add `@register_block()` to all 80 blocks
2. Define signal schemas for each
3. Validate each block works

### Phase 3: Update ConfluenceCalculator (Day 3)

1. Make SIGNAL_TIERS dynamic
2. Query registry instead of hardcoded lists
3. Remove all assumptions

### Phase 4: Update Strategy Templates (Day 4)

1. Strategies query registry for available blocks
2. Auto-suggest compatible blocks
3. Validate block configurations

### Phase 5: Testing & Documentation (Day 5)

1. Comprehensive testing
2. Update all documentation
3. Create migration guide

---

## Usage Examples

### Adding a New Building Block

**OLD WAY (Manual, Error-Prone):**
```
1. Create detector file
2. Manually add to ConfluenceCalculator.SIGNAL_TIERS
3. Manually add to strategy imports
4. Manually add to file_operations.py mappings
5. Manually add to catalog
6. Hope you didn't misspell anything
7. Debug signal mismatches for 3 hours
```

**NEW WAY (Automatic):**
```python
# 1. Create detector with decorator (ONE FILE!)

from src.detectors.building_blocks.registry import register_block

@register_block(
    name='new_indicator',
    category='OSCILLATORS',
    class_name='NewIndicator',
    default_weight=20,
    valid_signals=['BULLISH', 'BEARISH', 'NEUTRAL'],
    signal_tiers={
        'BULLISH': {'base_points': 20, 'formula': 'scaled'},
        'BEARISH': {'base_points': 20, 'formula': 'scaled'},
        'NEUTRAL': {'points': 0}
    }
)
class NewIndicator:
    def analyze(self, df):
        return {'signal': 'BULLISH', 'confidence': 85}

# 2. Done! Block is automatically:
#    - Available in all strategies ✅
#    - Registered in ConfluenceCalculator ✅
#    - Validated on import ✅
#    - Listed in registry ✅
#    - Queryable by tools ✅
```

### Using in Strategies

**AUTO-DISCOVERY:**
```python
from src.detectors.building_blocks.registry import BlockRegistry

class MyStrategy:
    def _initialize_blocks(self):
        # Get all pattern blocks
        pattern_blocks = BlockRegistry.get_blocks_by_category('PATTERNS')
        
        for block_name, metadata in pattern_blocks.items():
            # Auto-instantiate
            self.detectors[block_name] = BlockRegistry.instantiate(
                block_name, 
                timeframe=self.timeframe
            )
            
            # Auto-configure with recommended weight
            self.blocks[block_name] = {
                'weight': metadata['default_weight'],
                'enabled': True
            }
```

### ConfluenceCalculator Auto-Adapts

**NO MORE MANUAL UPDATES:**
```python
# Calculate confluence - works for ANY block!
confluence, signals = ConfluenceCalculator.calculate_confluence(
    block_results,  # Whatever blocks you used
    block_configs   # Whatever weights you set
)

# Calculator queries registry for signal definitions
# If block not in SIGNAL_TIERS cache, loads from registry
# If signal not in registry, raises clear error
```

---

## Benefits

### For Developers

✅ **Add blocks in ONE place** (the detector file itself)
✅ **Zero manual updates** to ConfluenceCalculator
✅ **Automatic validation** catches errors at import time
✅ **Self-documenting** code (metadata is documentation)
✅ **Auto-complete support** in IDEs

### For System

✅ **Single source of truth** (registry)
✅ **NO signal mismatches** (validated at import)
✅ **Scalable** to 1000+ blocks
✅ **Maintainable** (changes in one place)
✅ **Testable** (automated validation)

### For Users

✅ **Fewer bugs** (caught at import, not runtime)
✅ **Faster development** (no manual coordination)
✅ **Better errors** (clear, specific messages)
✅ **Confidence** (validation guarantees correctness)

---

## Migration Strategy

### Migrating Existing Blocks

```bash
# 1. Run migration script
python scripts/migrate_to_registry.py

# This script:
# - Scans all building block files
# - Extracts current signal types
# - Generates @register_block() decorators
# - Updates files automatically
# - Validates each migration

# 2. Review changes
git diff src/detectors/building_blocks/

# 3. Run validation
python scripts/validate_registry.py

# 4. Commit
git commit -m "migrate: Convert all blocks to registry pattern"
```

### Backward Compatibility

**OLD code still works:**
```python
# Old way (still works during transition)
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern

# New way (preferred)
from src.detectors.building_blocks.registry import BlockRegistry
detector = BlockRegistry.instantiate('double_top')
```

---

## Anti-Patterns & Gotchas

### ❌ DON'T: Return undeclared signals

```python
@register_block(
    valid_signals=['BULLISH', 'BEARISH']
)
class BadBlock:
    def analyze(self, df):
        return {'signal': 'SIDEWAYS'}  # ❌ NOT in valid_signals!
        # Raises ValueError at runtime
```

### ✅ DO: Declare all possible signals

```python
@register_block(
    valid_signals=['BULLISH', 'BEARISH', 'SIDEWAYS', 'NEUTRAL']
)
class GoodBlock:
    def analyze(self, df):
        return {'signal': 'SIDEWAYS'}  # ✅ Declared!
```

### ❌ DON'T: Hardcode signal tiers

```python
# In ConfluenceCalculator
SIGNAL_TIERS = {
    'double_top': {  # ❌ Hardcoded!
        'tiers': {...}
    }
}
```

### ✅ DO: Let registry populate it

```python
# ConfluenceCalculator queries registry automatically
# No manual updates needed!
```

---

## Future Enhancements

### Phase 6: ML Block Integration

```python
@register_block(
    name='lstm_predictor',
    category='ML_MODELS',
    model_path='models/lstm_btc_15min.pth',
    valid_signals=['LONG', 'SHORT', 'FLAT'],
    # ... metadata
)
class LSTMPredictor:
    # Registry handles model loading
    pass
```

### Phase 7: Block Discovery UI

```
$ python -m registry.cli search --category PATTERNS --tag reversal

Results:
  - double_top (PATTERNS, bearish)
  - triple_top (PATTERNS, bearish)
  - head_and_shoulders (PATTERNS, bearish)
  
$ python -m registry.cli info double_top

Block: double_top
Category: PATTERNS
Weight: 30
Signals: BEARISH_BREAKDOWN, PATTERN_FORMING, NO_PATTERN
Description: Double top bearish reversal pattern
Used by: 12 strategies
```

### Phase 8: Auto-Generated Documentation

```python
# Registry can generate complete docs
BlockRegistry.generate_docs('docs/building_blocks/')

# Creates:
# - Signal reference
# - Usage examples
# - Compatibility matrix
# - Performance stats
```

---

## Success Metrics

### Before Registry (Current State)

- ❌ 6 hours debugging signal mismatches
- ❌ 0 trades due to naming errors
- ❌ Manual updates in 5+ places per block
- ❌ No validation until runtime
- ❌ Silent failures (0 points)

### After Registry (Target State)

- ✅ 0 hours debugging (validated at import)
- ✅ Guaranteed signal matches
- ✅ ONE place to update (the block itself)
- ✅ Import-time validation
- ✅ Clear errors with fixes

---

## Conclusion

The Building Block Registry Pattern solves the root cause of signal mismatches:

**No single source of truth → Registry IS the single source of truth**

Every component (ConfluenceCalculator, Strategies, Optimizer) queries the registry instead of making assumptions. New blocks register themselves. Validation is automatic. The system is self-maintaining.

**Investment:** 1 week implementation  
**Payoff:** Eliminates entire category of bugs forever  
**ROI:** 100x (saves 6+ hrs per bug × future bugs avoided)

---

**Next Step:** Implement Phase 1 (Registry Core)  
**Timeline:** Start immediately, complete in 1 week  
**Priority:** CRITICAL (prevents all future signal mismatch bugs)