# Strategy Builder Architecture v1.0 - Registry-Powered

**Date:** 2026-01-09  
**Status:** Architecture Design  
**Author:** BTC_Engine_v3 Expert Mode  

---

## 🎯 Vision

**SINGLE SOURCE OF TRUTH ARCHITECTURE**

Create a registry-powered strategy builder that eliminates ad-hoc code, prevents bugs through strict validation, and provides an intuitive UI for building institutional-grade trading strategies.

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE SOURCE OF TRUTH                    │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐     ┌─────────────┐ │
│  │   REGISTRY   │─────▶│   BUILDER    │────▶│  STRATEGIES │ │
│  │              │      │              │     │             │ │
│  │ • Blocks     │      │ • UI Wizard  │     │ • Generated │ │
│  │ • Signals    │      │ • Validation │     │ • Validated │ │
│  │ • Metadata   │      │ • Templates  │     │ • Numbered  │ │
│  └──────────────┘      └──────────────┘     └─────────────┘ │
│         │                      │                    │        │
│         └──────────────────────┴────────────────────┘        │
│                     All Reference Registry                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Core Principles

### 1. Registry as Single Source of Truth
- **Building Blocks** define themselves in registry via `@register_block`
- **Strategy Builder** reads from registry (never hardcoded)
- **Confluence Calculator** scores via registry
- **Optimizer** validates via registry
- **Trade Manager** (future) will use registry

### 2. Zero Ad-Hoc Code
- No hardcoded block lists
- No manual signal definitions
- No copy-paste strategy templates
- All generated from registry metadata

### 3. Fail-Fast Validation
- Validate block existence before selection
- Validate signal compatibility before save
- Validate strategy before optimizer run
- Clear error messages with fixes

### 4. Intuitive UX
- Wizard-based workflow
- Intelligent suggestions
- Auto-naming with increment
- Load/edit existing strategies

---

## 🏗️ Architecture Components

### Component 1: Registry Integration Layer

**Purpose:** Bridge between BlockRegistry and Strategy Builder

```python
class RegistryBridge:
    """
    Provides clean interface to BlockRegistry for UI
    
    Responsibilities:
    - Query blocks by category
    - Get signal options for blocks
    - Validate block+signal combinations
    - Provide metadata for UI display
    """
    
    @classmethod
    def get_blocks_by_category(cls) -> Dict[str, List[BlockInfo]]:
        """
        Returns:
        {
            'PATTERNS': [
                BlockInfo(name='double_top', display_name='Double Top', 
                          signals=['BEARISH_BREAKDOWN', 'PATTERN_FORMING'],
                          weight_range=(20, 35), type='EVENT'),
                ...
            ],
            'PRICE_LEVELS': [...],
            ...
        }
        """
    
    @classmethod
    def get_signal_options(cls, block_name: str) -> List[SignalInfo]:
        """
        Returns available signals for a block with metadata
        """
    
    @classmethod
    def validate_block_signal(cls, block_name: str, signal: str) -> ValidationResult:
        """
        Validates if signal is valid for block
        Returns: (is_valid, error_message, suggestions)
        """
```

### Component 2: Strategy Configuration Model

**Purpose:** In-memory representation of strategy being built

```python
@dataclass
class BlockSelection:
    """Represents a selected block with its signals"""
    block_name: str
    block_display_name: str
    block_category: str
    block_type: str  # 'EVENT', 'SIGNAL', 'CONTEXT'
    weight: int
    enabled: bool
    signals: List[SignalConfiguration]
    
@dataclass
class SignalConfiguration:
    """Represents a signal's role in the strategy"""
    signal_name: str
    signal_display_name: str
    role: str  # 'FILTER', 'SIGNAL', 'BOOSTER', 'TEST_ALL'
    required: bool
    min_confidence: float
    
@dataclass
class StrategyConfiguration:
    """Complete strategy configuration"""
    strategy_name: str
    strategy_number: int
    strategy_category: str  # 'REVERSAL', 'CONTINUATION', etc.
    main_signal_block: str
    blocks: List[BlockSelection]
    min_confluence: int
    risk_reward_ratio: float
    optimization_enabled: bool
    test_permutations: List[Dict]  # For TEST_ALL signals
    
    def validate(self) -> ValidationResult:
        """Validates entire configuration"""
    
    def to_strategy_file(self) -> str:
        """Generates Python strategy file"""
    
    def to_optimizer_config(self) -> Dict:
        """Generates optimizer configuration"""
```

### Component 3: UI Framework Selection

**Research: Best Python UI for Ubuntu 2025**

#### Option A: **PyQt6** (RECOMMENDED)
**Pros:**
- Native-looking UI on Ubuntu
- Drag-drop support built-in
- Excellent documentation
- Professional appearance
- Most popular for trading GUIs

**Cons:**
- GPL license (commercial requires license)
- Steeper learning curve

#### Option B: **Tkinter**
**Pros:**
- Built into Python (no install)
- Simple for basic UIs
- Good for quick prototypes

**Cons:**
- Less modern appearance
- Limited drag-drop
- Harder to make professional UI

#### Option C: **Streamlit**
**Pros:**
- Very easy to build
- Good for data apps
- Auto-reloading

**Cons:**
- Web-based (not native)
- Limited customization
- Not ideal for complex workflows

#### Option D: **Dear PyGui**
**Pros:**
- Fast rendering
- Modern look
- Good for trading tools

**Cons:**
- Less mature
- Smaller community

**RECOMMENDATION:** **PyQt6** for production-grade UI with fallback to **Tkinter** for quick MVP.

### Component 4: UI Application Structure

```
Strategy Builder UI
│
├── Main Window
│   ├── Menu Bar
│   │   ├── File → New Strategy, Open, Save, Save As
│   │   ├── View → Toggle Advanced Options
│   │   └── Help → Documentation, Examples
│   │
│   ├── Strategy Info Panel (Top)
│   │   ├── Strategy Name [Auto-generated, Editable]
│   │   ├── Strategy Number [Auto: 01_, 02_, ...]
│   │   └── Strategy Category [Dropdown: REVERSAL, CONTINUATION, ...]
│   │
│   ├── Block Selection Panel (Left - 30%)
│   │   ├── Category Filter [Tabs]
│   │   │   ├── ALL
│   │   │   ├── PATTERNS
│   │   │   ├── PRICE_LEVELS
│   │   │   ├── OSCILLATORS
│   │   │   ├── SESSIONS
│   │   │   └── ...
│   │   │
│   │   └── Block List (Searchable)
│   │       ├── [Icon] Double Top (EVENT) ⭐ Main Signal
│   │       ├── [Icon] HOD (CONTEXT)
│   │       ├── [Icon] RSI Divergence (EVENT)
│   │       └── ... (Drag to Strategy Panel)
│   │
│   ├── Strategy Canvas (Center - 50%)
│   │   ├── Drop Zones
│   │   │   ├── [Main Signal] ← Drop PRIMARY block here
│   │   │   ├── [Filters] ← Drop FILTER blocks here
│   │   │   ├── [Boosters] ← Drop BOOSTER blocks here
│   │   │   └── [Context] ← Drop CONTEXT blocks here
│   │   │
│   │   └── Block Configuration Cards
│   │       ├── ╔═══════════════════════════════╗
│   │       │   ║ 🎯 MAIN SIGNAL: Double Top   ║
│   │       │   ╠═══════════════════════════════╣
│   │       │   ║ Weight: [30] (20-35)          ║
│   │       │   ║ Signals:                      ║
│   │       │   ║ ☑ BEARISH_BREAKDOWN [SIGNAL] ║
│   │       │   ║ ☐ PATTERN_FORMING [FILTER]   ║
│   │       │   ║ [Add Signal] [Remove Block]  ║
│   │       │   ╚═══════════════════════════════╝
│   │       │
│   │       ├── ╔═══════════════════════════════╗
│   │       │   ║ 🎚️ FILTER: HOD                ║
│   │       │   ╠═══════════════════════════════╣
│   │       │   ║ Weight: [20] (15-25)          ║
│   │       │   ║ Signals:                      ║
│   │       │   ║ ☑ BEARISH [FILTER]            ║
│   │       │   ║ ☑ HOD_REJECTION [BOOSTER]    ║
│   │       │   ║ ☑ BELOW_HOD [TEST_ALL] 🧪    ║
│   │       │   ║ [Configure] [Remove]          ║
│   │       │   ╚═══════════════════════════════╝
│   │       └── ...
│   │
│   └── Configuration Panel (Right - 20%)
│       ├── Strategy Parameters
│       │   ├── Min Confluence: [70] (50-100)
│       │   ├── Risk:Reward: [1:3] dropdown
│       │   └── Max Bars Held: [1000]
│       │
│       ├── Optimization Settings
│       │   ├── ☑ Enable Optimization
│       │   ├── Test Days: [180]
│       │   └── Configs to Test: [48]
│       │
│       └── Action Buttons
│           ├── [💾 Save Strategy]
│           ├── [✅ Validate]
│           ├── [🚀 Run Optimizer]
│           └── [📊 View Backtest]
│
└── Footer Status Bar
    ├── ✅ Strategy Valid | 4 Blocks Selected | 9 Signals Configured
    └── Ready to Save
```

### Component 5: Strategy Template Generator

**Purpose:** Generate Python strategy files from configuration

```python
class StrategyGenerator:
    """
    Generates institutional-grade strategy files
    
    Templates:
    - NautilusTrader-compatible strategy class
    - All imports from registry
    - Proper block initialization
    - Confluence calculation
    - Entry/exit logic
    - Risk management
    - Performance tracking
    """
    
    def __init__(self, config: StrategyConfiguration):
        self.config = config
        self.registry_bridge = RegistryBridge()
    
    def generate(self) -> Tuple[str, Path]:
        """
        Returns: (strategy_code, file_path)
        
        Generated file includes:
        - Docstring with strategy description
        - Import statements (from registry)
        - Strategy class with all methods
        - Block initialization
        - Signal analysis
        - Entry/exit logic
        - Comments explaining each part
        """
    
    def validate_generated_code(self, code: str) -> ValidationResult:
        """
        Validates generated code:
        - Python syntax check
        - Import validation
        - Block name validation
        - Signal name validation
        """
```

### Component 6: Strategy Registry (NEW!)

**Purpose:** Register and track all created strategies

```python
class StrategyRegistry:
    """
    Central registry for all strategies
    
    Features:
    - Auto-increment strategy numbers
    - Track strategy metadata
    - Validate uniqueness
    - Load/save strategies
    - Version control
    """
    
    _strategies: Dict[int, StrategyMetadata] = {}
    
    @classmethod
    def get_next_number(cls) -> int:
        """Auto-increment: 01, 02, 03, ..."""
    
    @classmethod
    def register_strategy(cls, config: StrategyConfiguration):
        """Register new strategy"""
    
    @classmethod
    def load_strategy(cls, number: int) -> StrategyConfiguration:
        """Load existing strategy for editing"""
    
    @classmethod
    def list_strategies(cls) -> List[StrategyMetadata]:
        """List all registered strategies"""
    
    @classmethod
    def validate_name(cls, name: str) -> bool:
        """Ensure unique strategy names"""
```

---

## 🔄 User Workflow

### Workflow 1: Create New Strategy

```
1. Launch Builder
   │
   ├─▶ Click "New Strategy"
   │   │
   │   ├─▶ Auto-generates name: "strategy_01_custom_reversal"
   │   └─▶ Selects category: [REVERSAL / CONTINUATION / SCALPING / ...]
   │
2. Select Main Signal Block
   │
   ├─▶ Browse PATTERNS category
   ├─▶ Drag "Double Top" to "Main Signal" zone
   ├─▶ Configure signals:
   │   ├─ ☑ BEARISH_BREAKDOWN → Role: SIGNAL
   │   └─ ☑ PATTERN_FORMING → Role: FILTER
   │
3. Add Supporting Blocks
   │
   ├─▶ Search "HOD" (auto-suggests from registry)
   ├─▶ Drag to "Filters" zone
   ├─▶ Configure signals:
   │   ├─ ☑ BEARISH → Role: FILTER
   │   ├─ ☑ HOD_REJECTION → Role: BOOSTER
   │   └─ ☑ BELOW_HOD → Role: TEST_ALL 🧪
   │       (Marks for optimizer permutation testing)
   │
4. Configure Strategy Parameters
   │
   ├─▶ Min Confluence: 70
   ├─▶ Risk:Reward: 1:3
   └─▶ Enable optimization: ☑
   │
5. Validate & Save
   │
   ├─▶ Click "Validate"
   │   ├─ ✅ All blocks exist in registry
   │   ├─ ✅ All signals valid
   │   ├─ ✅ No conflicts
   │   └─ ✅ Ready to save
   │
   ├─▶ Click "Save Strategy"
   │   ├─ Generates: src/strategies/strategy_01_custom_reversal.py
   │   ├─ Generates: tests/strategies/test_01_custom_reversal.py
   │   ├─ Updates strategy registry
   │   └─ Shows: "✅ Strategy saved successfully!"
   │
6. Run Optimization (Optional)
   │
   └─▶ Click "Run Optimizer"
       ├─ Launches universal_optimizer_v2
       ├─ Tests all TEST_ALL permutations
       ├─ Finds optimal weights
       └─ Updates strategy file with results
```

### Workflow 2: Edit Existing Strategy

```
1. Click "Open Strategy"
   │
   ├─▶ Shows list of strategies:
   │   ├─ 01_custom_reversal (M-Pattern)
   │   ├─ 02_ema_trend (Trend Following)  
   │   └─ 03_scalping (Quick Scalps)
   │
2. Select strategy to edit
   │
   ├─▶ Loads all configuration
   ├─▶ Displays blocks in canvas
   └─▶ Shows current signals
   │
3. Make changes
   │
   ├─▶ Add/remove blocks
   ├─▶ Modify signal roles
   └─▶ Adjust parameters
   │
4. Validate & Save
   │
   ├─▶ Increments version: strategy_01_custom_reversal_v2.py
   └─▶ Or overwrites original (with confirmation)
```

---

## 📁 Directory Structure

```
BTC_Engine_v3/
│
├── docs/v3/Strategy_Builder/
│   ├── ARCHITECTURE_V1.0.md (this file)
│   ├── USER_GUIDE.md
│   ├── API_REFERENCE.md
│   ├── EXAMPLES.md
│   └── TROUBLESHOOTING.md
│
├── src/utils/Strategy_Builder/
│   ├── __init__.py
│   ├── registry_bridge.py          # Registry integration
│   ├── models.py                    # Data models
│   ├── generator.py                 # Strategy file generator
│   ├── validator.py                 # Validation logic
│   ├── strategy_registry.py         # Strategy tracking
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py           # Main UI window
│       ├── block_selector.py        # Block selection panel
│       ├── strategy_canvas.py       # Drag-drop canvas
│       ├── signal_configurator.py   # Signal configuration
│       ├── widgets.py                # Custom widgets
│       └── styles.py                 # UI styling
│
├── src/strategies/
│   ├── strategy_01_*.py              # Generated strategies
│   ├── strategy_02_*.py
│   └── ...
│
├── tests/Strategy_Builder/
│   ├── test_registry_bridge.py
│   ├── test_generator.py
│   ├── test_validator.py
│   └── test_ui_logic.py
│
├── tests/strategies/
│   ├── test_01_*.py                  # Generated tests
│   ├── test_02_*.py
│   └── ...
│
├── data/logs/Strategy_Builder/
│   ├── builder_2026-01-09.log
│   ├── validation_errors.log
│   └── generation_history.log
│
└── scripts/
    └── strategy_builder.py           # Launch script
```

---

## 🛠️ Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| **UI Framework** | PyQt6 | Professional, native, drag-drop support |
| **Data Models** | Python Dataclasses | Type-safe, clean |
| **Validation** | Pydantic v2 | Powerful validation, great errors |
| **Code Generation** | Jinja2 Templates | Flexible, maintainable templates |
| **Testing** | pytest | Industry standard |
| **Logging** | Python logging + Rich | Beautiful console + file logs |
| **Config Storage** | YAML | Human-readable, version-control friendly |

---

## 🧪 Testing Strategy

### Unit Tests
- Registry bridge functions
- Validation logic
- Code generation
- Signal role assignment

### Integration Tests  
- Full workflow: build → validate → generate → save
- Load existing strategy
- Optimizer integration

### UI Tests
- Block drag-drop
- Signal configuration
- Validation feedback
- Error handling

### End-to-End Tests
- Create strategy → optimize → backtest
- Edit strategy → re-optimize
- Multiple strategies workflow

---

## 🚧 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Registry bridge implementation
- [ ] Data models (StrategyConfiguration, BlockSelection, etc.)
- [ ] Basic validator
- [ ] Strategy registry

### Phase 2: Code Generation (Week 1-2)
- [ ] Jinja2 templates for strategies
- [ ] Generator with full NautilusTrader compatibility
- [ ] Test file generation
- [ ] Validation of generated code

### Phase 3: Basic UI (Week 2-3)
- [ ] Tkinter MVP (rapid prototype)
- [ ] Block list display
- [ ] Simple selection (no drag-drop yet)
- [ ] Save/load functionality

### Phase 4: Professional UI (Week 3-4)
- [ ] PyQt6 implementation
- [ ] Drag-drop canvas
- [ ] Signal configurator dialog
- [ ] Visual feedback & validation

### Phase 5: Integration (Week 4-5)
- [ ] Optimizer integration
- [ ] Strategy registry persistence
- [ ] Load/edit workflows
- [ ] Documentation

### Phase 6: Polish (Week 5-6)
- [ ] Error handling & logging
- [ ] User guide & examples
- [ ] Testing complete
- [ ] Production ready

---

## 📊 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Creation Time** | <5 min | Time from start to saved strategy |
| **Error Rate** | <1% | Invalid generated strategies |
| **User Satisfaction** | >90% | Ease of use rating |
| **Registry Coverage** | 100% | All registry blocks accessible |
| **Code Quality** | A+ | Pylint score >9.0 |
| **Test Coverage** | >90% | pytest coverage |

---

## 🔐 Security & Safety

### Validation Checkpoints
1. **Block Exists** - Verify in registry before adding
2. **Signal Valid** - Check signal exists for block
3. **No Conflicts** - Ensure signal roles don't conflict
4. **Code Syntax** - Validate generated Python
5. **Import Check** - Verify all imports resolve
6. **Test Generation** - Ensure tests pass

### Error Prevention
- Impossible to select invalid blocks (not in UI)
- Impossible to configure invalid signals (filtered)
- Impossible to save invalid strategies (validation required)
- Impossible to run optimizer on invalid config (checked)

---

## 📚 Related Documentation

- [Registry Architecture](../building_blocks/REGISTRY_ARCHITECTURE.md)
- [Registry No Fallbacks](../building_blocks/REGISTRY_NO_FALLBACKS_COMPLETE.md)
- [Universal Optimizer Guide](../Strategies/UNIVERSAL_OPTIMIZER_GUIDE.md)
- [Strategy Developer Guide](../data_manager/STRATEGY_DEVELOPER_GUIDE.md)

---

## 🎯 Next Steps

1. Review architecture with team
2. Approve technology stack
3. Create Phase 1 implementation plan
4. Begin development

---

**Author:** Cline AI - Expert Mode  
**Version:** 1.0  
**Status:** Ready for Review