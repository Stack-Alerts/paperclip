# Strategy Builder UI - Session Handoff Document

**Date:** January 16, 2026  
**Branch:** strategy_development  
**Current Status:** Backend 100% Complete, UI Ready to Build  

---

## 📋 EXACT REQUEST FOR NEXT SESSION

Copy and paste this to start the next session:

```
Build the Strategy Builder UI (Phase 1) using PyQt5.

CONTEXT:
- Project: BTC_Engine_v3 trading bot strategy builder
- Location: ~/projects/BTC_Engine_v3
- Branch: strategy_development
- Backend: 100% complete (10 components, 186 tests passing)
- Design specs: Complete in docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md

TASK - UI PHASE 1 (2 weeks):
Implement the first 3 UI components using PyQt5:

1. Strategy Information Panel
   - Name input field
   - Description text area (auto-populated from blocks)
   - Strategy type radio buttons (Bullish/Bearish)
   - Required signals counter (auto-calculated)
   - Reference: docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md section "Strategy Information Panel"

2. Block Search and Selection
   - Search bar with filtering
   - Block list with:
     * Block name, category, type
     * Signal counts from historical data
     * Expandable signal lists
     * "Add to Strategy" buttons
   - Filter by: Block name, Category, Type
   - Reference: docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md section "Block Search and Selection"

3. Basic Strategy Blocks Configuration
   - Display added blocks in list
   - Show signals for each block
   - Up/Down reordering buttons
   - Delete block buttons
   - AND/OR logic selectors
   - Reference: docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md section "Strategy Blocks Configuration"

BACKEND API (Already Complete):
Use StrategyBuilderOrchestrator from:
src/strategy_builder/integration/strategy_builder_orchestrator.py

Example usage:
```python
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator

orchestrator = StrategyBuilderOrchestrator()

# Create strategy
orchestrator.create_strategy("My Strategy", "Description")

# Add blocks
orchestrator.add_block("BlockName", "AND")
orchestrator.add_signal("BlockName", "SIGNAL_NAME", "AND")

# Search blocks
results = orchestrator.search_blocks("RSI")

# Validate
validation = orchestrator.validate_strategy()

# Save
config = orchestrator.get_current_config()
from src.strategy_builder.persistence.strategy_persistence import StrategyPersistence
StrategyPersistence().save(config, Path("strategy.json"))
```

REQUIREMENTS:
- Use PyQt5 (pip install PyQt5 PyQt5-tools)
- Follow TDD approach (write tests for UI components)
- Match design specs exactly (see docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md)
- Connect to existing backend (all APIs ready)
- Maintain institutional-grade quality

REFERENCE DOCUMENTS:
1. Design Specs: docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md
2. Backend Example: src/strategy_builder/examples/complete_workflow_example.py
3. API Documentation: All docstrings in src/strategy_builder/
4. This Handoff: docs/v3/UI-UX/NEXT_SESSION_HANDOFF.md

TESTING:
- Backend tests pass: python -m pytest tests/strategy_builder/ -v (186 tests)
- UI should have unit tests for each component
- Integration tests connecting UI to backend

DELIVERABLES:
1. Strategy Information Panel (working PyQt5 widget)
2. Block Search and Selection (working PyQt5 widget)
3. Basic Strategy Blocks Configuration (working PyQt5 widget)
4. Tests for all 3 components
5. Main window that integrates all 3 components
6. Documentation of UI code

START BY:
1. Reading docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md completely
2. Running src/strategy_builder/examples/complete_workflow_example.py to see backend
3. Verifying backend tests pass: python -m pytest tests/strategy_builder/ -v
4. Creating src/strategy_builder/ui/ directory
5. Building Strategy Information Panel first (simplest component)

SUCCESS CRITERIA:
- All 3 UI components working
- Connected to backend APIs
- Tests passing
- Matches design specifications
- Ready for Phase 2 (advanced features)
```

---

## 📁 Key File Locations

### Documentation
- **Design Specs:** `docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md`
- **This Handoff:** `docs/v3/UI-UX/NEXT_SESSION_HANDOFF.md`
- **Implementation Tracker:** `docs/v3/UI-UX/IMPLEMENTATION_TASK_TRACKER.md`

### Backend Code (All Complete)
- **Main API:** `src/strategy_builder/integration/strategy_builder_orchestrator.py`
- **Config Engine:** `src/strategy_builder/core/strategy_config_engine.py`
- **Registry:** `src/strategy_builder/core/registry_interface.py`
- **Validator:** `src/strategy_builder/validation/strategy_validator.py`
- **Persistence:** `src/strategy_builder/persistence/strategy_persistence.py`
- **Code Gen:** `src/strategy_builder/core/nautilus_code_generator.py`
- **Testing:** `src/strategy_builder/testing/walkforward_test_engine.py`
- **Example:** `src/strategy_builder/examples/complete_workflow_example.py`

### Tests (All Passing)
- **All Tests:** `tests/strategy_builder/` (186 tests, 100% passing)
- **Run Command:** `python -m pytest tests/strategy_builder/ -v`

### Where UI Will Go
- **UI Code:** `src/strategy_builder/ui/` (to be created)
- **UI Tests:** `tests/strategy_builder/ui/` (to be created)
- **Main Window:** `src/strategy_builder/ui/main_window.py` (to be created)

---

## 🎯 Backend Status (Complete)

### All 10 Components Built ✅
1. StrategyConfigEngine - Configuration management (24 tests)
2. SignalDependencyResolver - Dependency tracking (19 tests)
3. RegistryInterface - Building block abstraction (17 tests)
4. NautilusCodeGenerator - Code generation (18 tests)
5. WalkforwardTestEngine - Backtesting framework (16 tests)
6. StrategyBuilderOrchestrator - Integration layer (16 tests)
7. BlockStateManager - Execution state (18 tests)
8. StrategyValidator - Multi-level validation (23 tests)
9. StrategyPersistence - JSON/YAML save/load (19 tests)
10. CompleteWorkflowExample - End-to-end demo (16 tests)

**Total:** 186/186 tests passing in 0.11s

### Git Commits (12 on strategy_development)
```
e2fefd8 - Design Analysis Documentation
eb351e3 - CompleteWorkflowExample (100% completion!)
80f1cfb - StrategyPersistence
e50926f - StrategyValidator
2dc5702 - BlockStateManager
68ae760 - StrategyBuilderOrchestrator
9aa2ea8 - Fix pytest warnings
5d8e439 - WalkforwardTestEngine
585df93 - NautilusCodeGenerator
c1900d5 - RegistryInterface
db8efbd - SignalDependencyResolver
997c89a - StrategyConfigEngine
```

---

## 📚 Quick Start for Next Session

### 1. Verify Backend Works
```bash
cd ~/projects/BTC_Engine_v3
source venv/bin/activate
python -m pytest tests/strategy_builder/ -v  # Should show 186 passed
python -m src.strategy_builder.examples.complete_workflow_example  # Demo
```

### 2. Install PyQt5
```bash
pip install PyQt5 PyQt5-tools
```

### 3. Read Design Specs
```bash
cat docs/v3/UI-UX/STRATEGY_BUILDER_DESIGN_ANALYSIS.md
# Focus on Component Specifications section
```

### 4. Create UI Structure
```bash
mkdir -p src/strategy_builder/ui
mkdir -p tests/strategy_builder/ui
touch src/strategy_builder/ui/__init__.py
touch tests/strategy_builder/ui/__init__.py
```

### 5. Start with Strategy Information Panel
Create: `src/strategy_builder/ui/strategy_info_panel.py`

```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit, QRadioButton
from src.strategy_builder.integration.strategy_builder_orchestrator import StrategyBuilderOrchestrator

class StrategyInfoPanel(QWidget):
    def __init__(self, orchestrator: StrategyBuilderOrchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        # Add fields: name, description, type radio buttons
        # Connect to orchestrator.create_strategy()
        self.setLayout(layout)
```

---

## 🔍 Important Backend APIs

### StrategyBuilderOrchestrator Methods
```python
# Strategy Management
create_strategy(name: str, description: str) -> WorkflowResult
get_current_config() -> StrategyConfig

# Block Management
add_block(name: str, logic: str) -> WorkflowResult
search_blocks(query: str) -> List[str]
get_block_signals(block_name: str) -> List[str]

# Signal Management
add_signal(block_name: str, signal_name: str, logic: str, 
          within_candles: int = None, reference_signal: str = None) -> WorkflowResult

# Validation & Generation
validate_strategy() -> WorkflowResult
validate_dependencies() -> WorkflowResult
generate_code() -> WorkflowResult

# Testing
run_backtest(lookback_days: int, mode: WalkforwardMode) -> WorkflowResult

# Workflow Steps
WorkflowStep enum: CREATE_STRATEGY, ADD_BLOCK, ADD_SIGNAL, VALIDATE, 
                   GENERATE_CODE, RUN_BACKTEST, SAVE, LOAD
```

### StrategyPersistence
```python
save(config: StrategyConfig, filepath: Path, format: PersistenceFormat = None) -> PersistenceResult
load(filepath: Path) -> PersistenceResult

# Formats: PersistenceFormat.JSON, PersistenceFormat.YAML
```

### StrategyValidator
```python
validate(config: StrategyConfig, level: ValidationLevel = STANDARD) -> ValidationResult
validate_nautilus_compatibility(config: StrategyConfig) -> ValidationResult

# Levels: ValidationLevel.BASIC, STANDARD, STRICT
```

---

## ✅ Phase 1 Success Criteria

### Strategy Information Panel ✅
- [ ] Name input field working
- [ ] Description text area working
- [ ] Auto-population of description from blocks
- [ ] Bullish/Bearish radio buttons
- [ ] Required signals counter (auto-calculated)
- [ ] Connected to orchestrator.create_strategy()
- [ ] Unit tests passing

### Block Search and Selection ✅
- [ ] Search bar implemented
- [ ] Block list populated from registry
- [ ] Signal counts displayed (from historical data)
- [ ] Expandable signal details
- [ ] Multi-criteria filtering working
- [ ] "Add to Strategy" button functional
- [ ] Blocks removed from list after adding
- [ ] Connected to orchestrator.search_blocks()
- [ ] Unit tests passing

### Basic Strategy Blocks Configuration ✅
- [ ] Display added blocks in order
- [ ] Show signals for each block
- [ ] Up/Down reordering working
- [ ] Delete block button working
- [ ] AND/OR logic selectors
- [ ] Visual hierarchy clear
- [ ] Connected to orchestrator.add_block/add_signal()
- [ ] Unit tests passing

### Integration ✅
- [ ] All 3 components in main window
- [ ] Components communicate properly
- [ ] Data flows correctly to backend
- [ ] Validation feedback displayed
- [ ] Error handling implemented
- [ ] Integration tests passing

---

## 📊 Timeline Estimate

**Phase 1 Breakdown:**
- Strategy Info Panel: 2 days
- Block Search & Selection: 4 days
- Basic Blocks Configuration: 6 days
- Integration & Testing: 2 days
- **Total:** ~2 weeks

**After Phase 1:**
- Phase 2: Advanced Features (2 weeks)  
- Phase 3: Polish & Testing (1 week)
- **Total Project:** ~5 weeks

---

## 🎯 Next Session Goals

**Week 1:**
- Strategy Information Panel complete
- Block Search and Selection started
- Initial main window structure

**Week 2:**
- Block Search and Selection complete
- Basic Strategy Blocks Configuration complete
- All integration working
- Tests passing
- Ready for Phase 2

---

## 💡 Tips for Success

1. **Start Simple** - Strategy Info Panel is easiest, build confidence
2. **Follow TDD** - Write tests first, maintain quality standards
3. **Use Backend Example** - `complete_workflow_example.py` shows everything
4. **Reference Design** - Match mockups in `STRATEGY_BUILDER_DESIGN_ANALYSIS.md`
5. **Test Often** - Run backend tests to ensure nothing breaks
6. **Ask Questions** - Backend is complex but well-documented
7. **Git Commits** - Clean commits like backend (feat/fix/docs pattern)

---

## 🚀 Ready to Start

Everything is prepared:
- ✅ Backend complete and tested
- ✅ Design specifications ready
- ✅ APIs documented
- ✅ Examples provided
- ✅ Framework chosen (PyQt5)
- ✅ Timeline estimated
- ✅ Success criteria defined

**Just copy the request above and start the next session!**

Good luck building the UI! The foundation is rock-solid. 🎉

---

**Document Version:** 1.0  
**Last Updated:** January 16, 2026  
**Author:** Cline (AI Assistant)  
**Status:** Ready for Next Session
