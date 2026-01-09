# Strategy Builder - Registry-Powered Strategy Development

**Status:** Architecture Complete, Ready for Implementation  
**Version:** 1.0  
**Date:** 2026-01-09  

---

## 🎯 Overview

The Strategy Builder is a **registry-powered** system for creating, validating, and managing trading strategies without writing code. It provides an intuitive UI that reads directly from the BlockRegistry, ensuring **100% consistency** and eliminating ad-hoc code bugs.

### Key Principle: SINGLE SOURCE OF TRUTH

```
BlockRegistry → Strategy Builder → Generated Strategies
     ↓                 ↓                    ↓
  (Blocks)         (UI Wizard)          (Python Files)
  (Signals)        (Validation)         (Tests)
  (Metadata)       (Templates)          (Configs)
```

**Everything references the registry. Zero hardcoded values. Zero drift.**

---

## 📚 Documentation

1. **[ARCHITECTURE_V1.0.md](ARCHITECTURE_V1.0.md)** - Complete system architecture
   - Vision and principles
   - Component design
   - UI framework selection (PyQt6 recommended)
   - User workflows
   - Technology stack

2. **[BUILD_PLAN_PHASE1.md](BUILD_PLAN_PHASE1.md)** - Detailed implementation plan
   - Phase 1 task breakdown (Foundation)
   - Time estimates (~18 hours)
   - Success criteria
   - Testing strategy
   - Known challenges and solutions

3. **API_REFERENCE.md** (To be created in Phase 1)
4. **EXAMPLES.md** (To be created in Phase 1)
5. **USER_GUIDE.md** (To be created in Phase 3)

---

## 🏗️ Components

### Core Components (Phase 1 - Foundation)

1. **Registry Bridge** (`src/utils/Strategy_Builder/registry_bridge.py`)
   - Clean interface to BlockRegistry
   - Query blocks by category
   - Get signal options
   - Validate block+signal combinations

2. **Data Models** (`src/utils/Strategy_Builder/models.py`)
   - `StrategyConfiguration` - Complete strategy config
   - `BlockSelection` - Selected blocks with signals
   - `SignalConfiguration` - Signal roles and settings
   - `ValidationResult` - Validation feedback

3. **Validator** (`src/utils/Strategy_Builder/validator.py`)
   - Validate block existence
   - Validate signal compatibility
   - Validate weight ranges
   - Validate strategy logic
   - Clear error messages with suggestions

4. **Strategy Registry** (`src/utils/Strategy_Builder/strategy_registry.py`)
   - Track all created strategies
   - Auto-increment strategy numbers (01_, 02_, ...)
   - Save/load strategy metadata
   - Version management

### UI Components (Phases 3-4)

5. **UI Framework** (`src/utils/Strategy_Builder/ui/`)
   - Main window with drag-drop canvas
   - Block selection panel (categorized)
   - Signal configuration dialogs
   - Validation feedback
   - Optimizer integration

### Code Generation (Phase 2)

6. **Strategy Generator** (`src/utils/Strategy_Builder/generator.py`)
   - Generate NautilusTrader-compatible strategies
   - Generate test files
   - Generate optimizer configurations
   - Jinja2 templates for consistency

---

## 🚀 User Workflow

### Create New Strategy (5 minutes)

```
1. Launch Builder
   → Click "New Strategy"
   → Auto-generates name: strategy_01_custom_reversal

2. Select Main Signal
   → Drag "Double Top" to Main Signal zone
   → Configure: BEARISH_BREAKDOWN → SIGNAL

3. Add Supporting Blocks
   → Drag "HOD" to Filters zone
   → Configure signals:
      ☑ BEARISH → FILTER
      ☑ HOD_REJECTION → BOOSTER
      ☑ BELOW_HOD → TEST_ALL (optimizer will test)

4. Set Parameters
   → Min Confluence: 70
   → Risk:Reward: 1:3
   → Enable Optimization: ☑

5. Validate & Save
   → Click "Validate" (✅ All checks pass)
   → Click "Save"
   → Generates:
      - src/strategies/strategy_01_custom_reversal.py
      - tests/strategies/test_01_custom_reversal.py

6. Run Optimizer (Optional)
   → Click "Run Optimizer"
   → Tests 48 configurations
   → Auto-applies best weights
```

### Edit Existing Strategy

```
1. Click "Open Strategy"
   → Shows list of all strategies
   → Select strategy to edit

2. Make Changes
   → Add/remove blocks
   → Modify signal roles
   → Adjust parameters

3. Save
   → Version increment: strategy_01_custom_reversal_v2.py
   → Or overwrite (with confirmation)
```

---

## 🎯 Benefits

### Before (Manual Coding)
❌ Copy-paste strategy templates  
❌ Hardcoded block lists  
❌ Manual signal configuration  
❌ Easy to introduce bugs  
❌ No validation until runtime  
❌ Inconsistent naming  

### After (Strategy Builder)
✅ Guided wizard workflow  
✅ Registry-powered (no hardcode)  
✅ Automatic signal validation  
✅ Impossible to create invalid strategies  
✅ Validation before save  
✅ Automatic naming convention  
✅ Generated tests included  
✅ Optimizer integration  

---

## 📊 Current Status

### ✅ Complete
- Architecture design
- Component definitions
- User workflows
- Technology stack selection
- Phase 1 implementation plan

### 🚧 In Progress
- Nothing yet (architecture phase complete)

### 📅 Upcoming
- **Phase 1:** Foundation (Data models, Registry bridge, Validator) - 2-3 days
- **Phase 2:** Code Generation (Templates, Generator) - 2-3 days  
- **Phase 3:** Basic UI (Tkinter MVP) - 3-4 days
- **Phase 4:** Professional UI (PyQt6) - 5-7 days
- **Phase 5:** Integration (Optimizer, Backtest) - 3-4 days
- **Phase 6:** Polish (Error handling, Docs) - 1-2 days

**Total Estimated Time:** 3-4 weeks

---

## 🛠️ Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| UI Framework | PyQt6 | Professional, native, drag-drop |
| Data Models | Pydantic v2 | Type-safe, validation |
| Code Generation | Jinja2 | Flexible templates |
| Testing | pytest | Industry standard |
| Logging | Rich | Beautiful output |
| Config Storage | YAML | Human-readable |

---

## 🔐 Validation & Safety

The Strategy Builder prevents invalid strategies through multiple validation layers:

1. **Registry Validation** - Block must exist in registry
2. **Signal Validation** - Signal must be valid for block
3. **Weight Validation** - Weight must be in allowed range
4. **Logic Validation** - Signal roles must not conflict
5. **Code Validation** - Generated Python must be syntactically correct
6. **Import Validation** - All imports must resolve

**Result:** Impossible to create a strategy that won't run.

---

## 📚 Related Documentation

- [Registry Architecture](../building_blocks/REGISTRY_ARCHITECTURE.md)
- [Registry No Fallbacks](../building_blocks/REGISTRY_NO_FALLBACKS_COMPLETE.md)
- [Universal Optimizer Guide](../Strategies/UNIVERSAL_OPTIMIZER_GUIDE.md)
- [Strategy Developer Guide](../data_manager/STRATEGY_DEVELOPER_GUIDE.md)

---

## 🚀 Getting Started (After Implementation)

```bash
# Install dependencies
pip install PyQt6 pydantic jinja2 pyyaml rich

# Launch Strategy Builder
python scripts/strategy_builder.py

# Or programmatically (for testing)
from src.utils.Strategy_Builder import StrategyBuilder

builder = StrategyBuilder()
builder.launch_ui()
```

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| Strategy Creation Time | <5 minutes |
| Error Rate | <1% |
| User Satisfaction | >90% |
| Registry Coverage | 100% |
| Code Quality | Pylint >9.0 |
| Test Coverage | >90% |

---

## 🤝 Contributing

When implementing:

1. Follow Phase 1 build plan sequentially
2. Write tests for all components
3. Document all public APIs
4. Use type hints everywhere
5. Handle all error cases
6. Log important events
7. Keep code institutional-grade

---

**Ready for Implementation!**

See [BUILD_PLAN_PHASE1.md](BUILD_PLAN_PHASE1.md) for detailed tasks.

**Author:** BTC_Engine_v3 Expert Mode  
**Status:** Architecture Complete  
**Next:** Begin Phase 1 Implementation