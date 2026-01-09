# Strategy Builder - Phase 1 Build Plan

**Phase:** Foundation (Week 1)  
**Date:** 2026-01-09  
**Status:** Ready to Implement  
**Estimated Time:** 5-7 days  

---

## 🎯 Phase 1 Goals

Build the foundational layer that all other components depend on:

1. **Registry Bridge** - Clean interface to BlockRegistry
2. **Data Models** - Type-safe configuration models
3. **Basic Validator** - Validation logic for strategies
4. **Strategy Registry** - Track all created strategies

**Success Criteria:** Can programmatically create a strategy configuration, validate it, and save metadata (no UI yet).

---

## 📋 Task Breakdown

### Task 1.1: Setup Directory Structure (30 min)

**Goal:** Create all necessary directories and __init__.py files

**Steps:**
```bash
# Create directories
mkdir -p src/utils/Strategy_Builder/ui
mkdir -p tests/Strategy_Builder
mkdir -p data/logs/Strategy_Builder
mkdir -p docs/v3/Strategy_Builder/examples

# Create __init__.py files
touch src/utils/Strategy_Builder/__init__.py
touch src/utils/Strategy_Builder/ui/__init__.py
touch tests/Strategy_Builder/__init__.py
```

**Checklist:**
- [ ] All directories created
- [ ] All __init__.py files created
- [ ] Git add all new files

---

### Task 1.2: Data Models Implementation (3 hours)

**File:** `src/utils/Strategy_Builder/models.py`

**Goal:** Create all data models using Pydantic for validation

**Implementation:**

```python
"""
Strategy Builder Data Models

Type-safe models for strategy configuration.
Uses Pydantic for automatic validation and clear errors.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class SignalRole(str, Enum):
    """Signal role in strategy logic"""
    FILTER = "FILTER"      # Must be true for entry
    SIGNAL = "SIGNAL"      # Primary entry trigger
    BOOSTER = "BOOSTER"    # Increases confluence
    TEST_ALL = "TEST_ALL"  # Test all permutations


class BlockType(str, Enum):
    """Block type from registry"""
    EVENT = "EVENT"
    SIGNAL = "SIGNAL"
    CONTEXT = "CONTEXT"
    HYBRID = "HYBRID"


class StrategyCategory(str, Enum):
    """Strategy category"""
    REVERSAL = "REVERSAL"
    CONTINUATION = "CONTINUATION"
    SCALPING = "SCALPING"
    RANGE_TRADING = "RANGE_TRADING"
    BREAKOUT = "BREAKOUT"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"


class SignalConfiguration(BaseModel):
    """Configuration for a single signal"""
    signal_name: str
    signal_display_name: str
    role: SignalRole
    required: bool = True
    min_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    
    class Config:
        use_enum_values = True


class BlockSelection(BaseModel):
    """A selected building block with its configuration"""
    block_name: str
    block_display_name: str
    block_category: str
    block_type: BlockType
    weight: int = Field(ge=0, le=100)
    weight_range: tuple[int, int]
    enabled: bool = True
    signals: List[SignalConfiguration] = Field(default_factory=list)
    is_main_signal: bool = False
    
    @validator('weight')
    def weight_in_range(cls, v, values):
        """Ensure weight is within range"""
        if 'weight_range' in values:
            min_w, max_w = values['weight_range']
            if not (min_w <= v <= max_w):
                raise ValueError(
                    f"Weight {v} not in range ({min_w}, {max_w})"
                )
        return v
    
    class Config:
        use_enum_values = True


class StrategyConfiguration(BaseModel):
    """Complete strategy configuration"""
    strategy_name: str
    strategy_number: int = Field(ge=1)
    strategy_category: StrategyCategory
    description: str = ""
    
    # Blocks
    main_signal_block: str
    blocks: List[BlockSelection] = Field(default_factory=list)
    
    # Parameters
    min_confluence: int = Field(default=70, ge=0, le=200)
    risk_reward_ratio: str = "1:3"
    max_bars_held: int = Field(default=1000, ge=100)
    
    # Risk Management
    risk_per_trade_pct: float = Field(default=1.0, ge=0.1, le=5.0)
    max_leverage: float = Field(default=2.0, ge=1.0, le=10.0)
    
    # Optimization
    optimization_enabled: bool = True
    test_days: int = Field(default=180, ge=30)
    optimization_configs: int = Field(default=48, ge=4)
    
    # Test permutations (for TEST_ALL signals)
    test_permutations: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('blocks')
    def has_main_signal(cls, v, values):
        """Ensure main signal block is in blocks"""
        if 'main_signal_block' in values:
            main = values['main_signal_block']
            if not any(b.block_name == main for b in v):
                raise ValueError(
                    f"Main signal block '{main}' not in blocks list"
                )
        return v
    
    @validator('strategy_name')
    def valid_strategy_name(cls, v, values):
        """Ensure strategy name follows convention"""
        if 'strategy_number' in values:
            expected_prefix = f"strategy_{values['strategy_number']:02d}_"
            if not v.startswith(expected_prefix):
                # Auto-fix
                # Remove any existing prefix
                name_part = v.split('_', 2)[-1] if '_' in v else v
                return f"{expected_prefix}{name_part}"
        return v
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    def add_error(self, message: str):
        """Add an error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning"""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion"""
        self.suggestions.append(message)


class BlockInfo(BaseModel):
    """Information about a block from registry"""
    name: str
    display_name: str
    category: str
    block_type: BlockType
    weight_range: tuple[int, int]
    default_weight: int
    signals: List[str]
    description: str = ""
    
    class Config:
        use_enum_values = True


class SignalInfo(BaseModel):
    """Information about a signal"""
    name: str
    display_name: str
    description: str = ""
    tier_type: str = ""  # 'fixed', 'scaled', 'quality_thresholds'
    max_points: int = 0


class StrategyMetadata(BaseModel):
    """Metadata for a registered strategy"""
    number: int
    name: str
    category: StrategyCategory
    created_date: str
    modified_date: str
    file_path: str
    config_path: str
    version: int = 1
    status: str = "DRAFT"  # DRAFT, VALIDATED, OPTIMIZED, LIVE
    
    class Config:
        use_enum_values = True
```

**Checklist:**
- [ ] All models implemented
- [ ] Pydantic validators working
- [ ] Enums defined
- [ ] Documentation added
- [ ] Test file created (test_models.py)

---

### Task 1.3: Registry Bridge Implementation (4 hours)

**File:** `src/utils/Strategy_Builder/registry_bridge.py`

**Goal:** Create clean interface to BlockRegistry for UI consumption

**Implementation:** (See next section for full code)

**Key Features:**
- Query blocks by category
- Get signal options for blocks
- Validate block+signal combinations
- Provide metadata for UI display
- Cache registry data for performance

**Checklist:**
- [ ] RegistryBridge class implemented
- [ ] All query methods working
- [ ] Signal validation working
- [ ] Caching implemented
- [ ] Test file created
- [ ] Error handling complete

---

### Task 1.4: Basic Validator Implementation (3 hours)

**File:** `src/utils/Strategy_Builder/validator.py`

**Goal:** Validate strategy configurations before save/generation

**Features:**
1. Validate all blocks exist in registry
2. Validate all signals exist for their blocks
3. Validate weight ranges
4. Validate no conflicting signal roles
5. Validate min_confluence makes sense
6. Validate main signal block is configured

**Checklist:**
- [ ] StrategyValidator class implemented
- [ ] All validation rules implemented
- [ ] Clear error messages
- [ ] Warnings for suboptimal configs
- [ ] Suggestions for improvements
- [ ] Test file with edge cases

---

### Task 1.5: Strategy Registry Implementation (3 hours)

**File:** `src/utils/Strategy_Builder/strategy_registry.py`

**Goal:** Track all created strategies, auto-increment numbers

**File:** `data/strategy_registry.yaml` (persisted registry)

**Features:**
1. Auto-increment strategy numbers
2. Save/load strategy metadata
3. Validate unique names
4. List all strategies
5. Search strategies
6. Version management

**Checklist:**
- [ ] StrategyRegistry class implemented
- [ ] YAML persistence working
- [ ] Auto-increment working
- [ ] Unique name validation
- [ ] Test file created
- [ ] Migration from existing strategies (if any)

---

### Task 1.6: Unit Tests (2 hours)

**Goal:** Comprehensive test coverage for all Phase 1 components

**Tests to Create:**

1. **test_models.py**
   - Test all Pydantic validations
   - Test edge cases
   - Test invalid configurations

2. **test_registry_bridge.py**
   - Test block queries
   - Test signal queries
   - Test validation methods
   - Test error handling

3. **test_validator.py**
   - Test all validation rules
   - Test error messages
   - Test warnings
   - Test suggestions

4. **test_strategy_registry.py**
   - Test auto-increment
   - Test save/load
   - Test unique names
   - Test search

**Target:** >90% code coverage

**Checklist:**
- [ ] All test files created
- [ ] All tests passing
- [ ] Coverage >90%
- [ ] Edge cases covered

---

### Task 1.7: Integration Test (1 hour)

**File:** `tests/Strategy_Builder/test_integration_phase1.py`

**Goal:** Test full workflow without UI

**Test Scenario:**
```python
def test_create_strategy_programmatically():
    """
    Test creating a strategy from scratch programmatically
    
    This simulates what the UI will do.
    """
    # 1. Query registry for blocks
    bridge = RegistryBridge()
    patterns = bridge.get_blocks_by_category()['PATTERNS']
    
    # 2. Create configuration
    config = StrategyConfiguration(
        strategy_name="test_m_pattern",
        strategy_number=99,
        strategy_category=StrategyCategory.REVERSAL,
        main_signal_block="double_top",
        blocks=[
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=30,
                weight_range=(20, 35),
                is_main_signal=True,
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_BREAKDOWN",
                        signal_display_name="Bearish Breakdown",
                        role=SignalRole.SIGNAL
                    )
                ]
            ),
            # ... more blocks
        ]
    )
    
    # 3. Validate
    validator = StrategyValidator()
    result = validator.validate(config)
    assert result.is_valid
    
    # 4. Register
    registry = StrategyRegistry()
    registry.register_strategy(config)
    
    # 5. Verify saved
    loaded = registry.load_strategy(99)
    assert loaded.strategy_name == config.strategy_name
```

**Checklist:**
- [ ] Integration test written
- [ ] Test passes
- [ ] Covers full workflow
- [ ] Tests error paths

---

### Task 1.8: Documentation (1 hour)

**Files to Create:**

1. **docs/v3/Strategy_Builder/API_REFERENCE.md**
   - Document all classes
   - Document all methods
   - Include examples

2. **docs/v3/Strategy_Builder/EXAMPLES.md**
   - Example: Create strategy programmatically
   - Example: Validate strategy
   - Example: Load strategy

3. **README.md** in src/utils/Strategy_Builder/
   - Quick start guide
   - Architecture overview
   - Development guide

**Checklist:**
- [ ] API reference complete
- [ ] Examples created
- [ ] README written
- [ ] All code documented

---

## ⏱️ Time Estimates

| Task | Estimated Time | Priority |
|------|----------------|----------|
| 1.1 Directory Setup | 30 min | P0 |
| 1.2 Data Models | 3 hours | P0 |
| 1.3 Registry Bridge | 4 hours | P0 |
| 1.4 Validator | 3 hours | P0 |
| 1.5 Strategy Registry | 3 hours | P0 |
| 1.6 Unit Tests | 2 hours | P0 |
| 1.7 Integration Test | 1 hour | P0 |
| 1.8 Documentation | 1 hour | P1 |

**Total:** ~18 hours (~2-3 days of focused work)

---

## 📊 Success Criteria

At the end of Phase 1, we should be able to:

✅ **Programmatically create a strategy configuration**
```python
config = StrategyConfiguration(
    strategy_name="test_strategy",
    strategy_number=1,
    strategy_category=StrategyCategory.REVERSAL,
    main_signal_block="double_top",
    blocks=[...]
)
```

✅ **Validate the configuration**
```python
validator = StrategyValidator()
result = validator.validate(config)
assert result.is_valid
```

✅ **Register and persist the strategy**
```python
registry = StrategyRegistry()
registry.register_strategy(config)
```

✅ **Load it back**
```python
loaded = registry.load_strategy(1)
assert loaded == config
```

✅ **All tests passing with >90% coverage**

---

## 🚀 Next Steps After Phase 1

Once Phase 1 is complete, we'll have a solid foundation to build on:

**Phase 2:** Code Generation (strategy file templates)  
**Phase 3:** Basic UI (Tkinter MVP)  
**Phase 4:** Professional UI (PyQt6)  
**Phase 5:** Integration (Optimizer, Backtest)  
**Phase 6:** Polish (Error handling, Documentation)  

---

## 🐛 Known Challenges & Solutions

### Challenge 1: Registry Performance
**Problem:** Querying registry on every UI update could be slow  
**Solution:** Implement caching in RegistryBridge

### Challenge 2: Pydantic Validation Errors
**Problem:** Pydantic errors can be cryptic  
**Solution:** Wrap in custom ValidationResult with friendly messages

### Challenge 3:** Strategy Number Conflicts
**Problem:** Multiple users creating strategies simultaneously  
**Solution:** File locking on registry YAML + retry logic

---

**Ready to Begin Implementation!**

Start with Task 1.1 (Directory Setup) and work through sequentially.
Each task builds on the previous one.

All code should follow institutional-grade standards:
- Type hints everywhere
- Comprehensive docstrings
- Error handling
- Logging
- Tests