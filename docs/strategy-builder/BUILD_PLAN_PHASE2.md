# Strategy Builder - Phase 2 Build Plan

**Phase:** Code Generation  
**Status:** Starting  
**Estimated Time:** 2-3 days  
**Dependencies:** Phase 1 Complete ✅

---

## Overview

Phase 2 adds code generation capabilities to transform validated `StrategyConfiguration` objects into:
1. NautilusTrader-compatible strategy Python files
2. pytest test files
3. Optimizer configuration files

---

## Tasks

### Task 2.1: Jinja2 Template System (4 hours)

**Deliverables:**
- Strategy template (`strategy_template.py.j2`)
- Test template (`test_template.py.j2`)
- Optimizer config template (`optimizer_config.yaml.j2`)

**Strategy Template Requirements:**
- Import necessary NautilusTrader modules
- Import selected building blocks
- Class definition with proper inheritance
- `on_start()` - Initialize blocks with configs
- `on_bar()` - Process bar data through blocks
- `calculate_confluence()` - Weight-based scoring
- `should_enter_trade()` - Entry logic
- `place_order()` - Order execution
- Proper error handling and logging

**Test Template Requirements:**
- Import strategy class
- Setup fixtures
- Test initialization
- Test block processing
- Test confluence calculation
- Test entry/exit logic
- Test risk management

**Optimizer Config Requirements:**
- Parameter ranges from weight_range
- Signal permutations for TEST_ALL roles
- Optimization targets
- Walk-forward settings

### Task 2.2: Code Generator Module (4 hours)

**File:** `src/utils/Strategy_Builder/generator.py`

**Class:** `StrategyGenerator`

**Methods:**
```python
class StrategyGenerator:
    def __init__(self):
        """Initialize with Jinja2 environment"""
        
    def generate_strategy_file(
        self,
        config: StrategyConfiguration,
        output_dir: Path = None
    ) -> Path:
        """Generate strategy .py file"""
        
    def generate_test_file(
        self,
        config: StrategyConfiguration,
        output_dir: Path = None
    ) -> Path:
        """Generate test file"""
        
    def generate_optimizer_config(
        self,
        config: StrategyConfiguration,
        output_dir: Path = None
    ) -> Path:
        """Generate optimizer YAML"""
        
    def generate_all(
        self,
        config: StrategyConfiguration,
        strategy_dir: Path = None,
        test_dir: Path = None,
        config_dir: Path = None
    ) -> Dict[str, Path]:
        """Generate all files at once"""
        
    def validate_generated_code(self, filepath: Path) -> bool:
        """Validate Python syntax"""
```

**Features:**
- Jinja2 template rendering
- Automatic import generation
- Proper indentation
- Syntax validation
- File overwrite protection
- Dry-run mode

### Task 2.3: Template Data Preparation (2 hours)

**Helper Functions:**
```python
def prepare_template_context(
    config: StrategyConfiguration
) -> Dict[str, Any]:
    """Prepare all data needed by templates"""
    
    return {
        'strategy_name': config.strategy_name,
        'strategy_number': config.strategy_number,
        'category': config.strategy_category,
        'blocks': prepare_blocks_data(config.blocks),
        'signals': prepare_signals_data(config.blocks),
        'weights': prepare_weights_data(config.blocks),
        'imports': generate_imports(config.blocks),
        'parameters': config.model_dump(),
        'timestamp': datetime.now().isoformat(),
    }
```

### Task 2.4: Testing (4 hours)

**Test File:** `tests/Strategy_Builder/test_generator.py`

**Test Coverage:**
- Template loading
- Context preparation
- Strategy file generation
- Test file generation
- Optimizer config generation
- Syntax validation
- Import validation
- Generated code execution
- Integration with Phase 1 components

**Minimum:** 20 tests

### Task 2.5: Integration (2 hours)

**Updates:**
- Update `__init__.py` to export `StrategyGenerator`
- Add convenience method to `StrategyRegistry`:
  ```python
  def generate_strategy_files(
      self,
      strategy_number: int,
      generate_tests: bool = True,
      generate_optimizer: bool = True
  ) -> Dict[str, Path]:
      """Load config and generate all files"""
  ```

### Task 2.6: Documentation (2 hours)

**Updates:**
- Add Code Generation section to USER_GUIDE.md
- Create TEMPLATES.md (template documentation)
- Update CHANGELOG.md
- Add examples to docs

---

## File Structure (After Phase 2)

```
src/utils/Strategy_Builder/
├── __init__.py
├── models.py
├── registry_bridge.py
├── validator.py
├── strategy_registry.py
├── generator.py              ⭐ NEW
└── templates/                ⭐ NEW
    ├── strategy_template.py.j2
    ├── test_template.py.j2
    └── optimizer_config.yaml.j2

tests/Strategy_Builder/
├── test_models.py
├── test_registry_bridge.py
├── test_validator.py
├── test_strategy_registry.py
├── test_integration.py
└── test_generator.py         ⭐ NEW

docs/v3/Strategy_Builder/
├── ARCHITECTURE_V1.0.md
├── BUILD_PLAN_PHASE1.md
├── BUILD_PLAN_PHASE2.md      ⭐ NEW
├── USER_GUIDE.md
├── TEMPLATES.md              ⭐ NEW
├── CHANGELOG.md
└── README.md
```

---

## Success Criteria

### Functional Requirements
- ✅ Generate syntactically correct Python
- ✅ Generated strategies import correctly
- ✅ Generated strategies run in backtest
- ✅ Generated tests pass
- ✅ Optimizer configs are valid YAML
- ✅ All imports resolve
- ✅ Proper error handling

### Quality Requirements
- ✅ Generated code follows PEP 8
- ✅ Institutional-grade code quality
- ✅ Comprehensive logging
- ✅ Type hints in generated code
- ✅ Docstrings in generated code

### Testing Requirements
- ✅ 20+ tests for generator
- ✅ 100% test coverage
- ✅ All tests passing
- ✅ Integration tests with Phase 1

---

## Example Usage

```python
from src.utils.Strategy_Builder import (
    StrategyConfiguration,
    StrategyGenerator,
    StrategyRegistry
)

# Load strategy config
registry = StrategyRegistry()
config = registry.load_strategy(1)

# Generate files
generator = StrategyGenerator()
files = generator.generate_all(config)

print(f"Strategy: {files['strategy']}")
print(f"Test: {files['test']}")
print(f"Optimizer: {files['optimizer']}")

# Output:
# Strategy: src/strategies/strategy_001_reversal_m.py
# Test: tests/strategies/test_001_reversal_m.py
# Optimizer: config/optimizer_001_reversal_m.yaml
```

---

## Timeline

| Task | Hours | Days |
|------|-------|------|
| 2.1 Templates | 4 | 0.5 |
| 2.2 Generator | 4 | 0.5 |
| 2.3 Data Prep | 2 | 0.25 |
| 2.4 Testing | 4 | 0.5 |
| 2.5 Integration | 2 | 0.25 |
| 2.6 Documentation | 2 | 0.25 |
| **Total** | **18** | **2.25** |

**Estimated:** 2-3 days

---

## Dependencies

### Required
- ✅ Phase 1 Complete
- ✅ Jinja2 installed
- ✅ NautilusTrader understanding

### Optional
- PyYAML for optimizer configs
- Black for code formatting
- Pylint for code quality

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Template complexity | Start simple, iterate |
| Import resolution | Test with actual blocks |
| Generated code errors | Syntax validation |
| Nautilus compatibility | Reference existing strategies |

---

## Next: Task 2.1

Start with template creation. Templates are the foundation of code generation.

**Status:** Ready to begin ✅  
**First Task:** Create Jinja2 templates  
**Estimated Time:** 4 hours