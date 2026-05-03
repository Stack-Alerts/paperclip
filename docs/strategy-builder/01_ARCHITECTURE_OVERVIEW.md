# Architecture Overview - Strategy Builder Redesign
**Document**: 01_ARCHITECTURE_OVERVIEW.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical  
**Last Updated**: 2026-01-16

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Context](#system-context)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [Integration Points](#integration-points)
7. [Technology Stack](#technology-stack)
8. [Design Principles](#design-principles)

---

## Executive Summary

The Strategy Builder redesign creates a flexible, registry-powered system for building complex multi-block, multi-signal trading strategies. The architecture leverages the new Building Block Registry as a single source of truth and introduces sophisticated AND/OR logic with timing constraints for institutional-grade strategy development.

### Key Architectural Goals
1. **Registry-Driven**: All building blocks sourced from central registry
2. **Flexible Configuration**: Support any combination of blocks, signals, and logic
3. **Real-time Feedback**: Live backtest previews and parameter updates
4. **Production-Grade Code**: Generate NautilusTrader-compliant strategy code
5. **Walkforward Testing**: Two-mode testing system (historical + live continuation)

---

## System Context

### Current State (Before Redesign)
```
┌─────────────────────────────────────────────────────────┐
│         OLD STRATEGY BUILDER (Pre-Registry)             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  • Static building block definitions                    │
│  • Limited signal combinations                          │
│  • No AND/OR logic support                             │
│  • No timing constraints                               │
│  • Manual signal validation                            │
│  • Signal name mismatches common                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### New State (After Redesign)
```
┌──────────────────────────────────────────────────────────────────┐
│            NEW STRATEGY BUILDER (Registry-Powered)               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Building Block Registry (Single Source of Truth)            │
│  ✅ Dual Signal Architecture (Granular + Simple)                │
│  ✅ Multi-block, Multi-signal Support                           │
│  ✅ AND/OR Logic (Mandatory vs. Optional blocks)                │
│  ✅ Timing Constraints ("Within X candles")                     │
│  ✅ Auto Signal Validation (Registry-backed)                    │
│  ✅ Dependency Resolution (Signal → Signal → Signal)            │
│  ✅ Real-time Preview & Live Testing                            │
│  ✅ NautilusTrader Code Generation                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## High-Level Architecture

### System Overview
```
┌────────────────────────────────────────────────────────────────────────┐
│                        STRATEGY BUILDER SYSTEM                         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────┐          ┌──────────────────┐        ┌─────────────────┐
│   UI LAYER   │◄────────►│  BUSINESS LOGIC  │◄──────►│  DATA SOURCES   │
│              │          │      LAYER       │        │                 │
│  - Builder   │          │                  │        │  - Registry     │
│  - Preview   │          │  - Config Engine │        │  - Market Data  │
│  - Testing   │          │  - Validation    │        │  - Backtest     │
│              │          │  - Code Gen      │        │  - Live Feed    │
└──────────────┘          └──────────────────┘        └─────────────────┘
        │                           │                           │
        │                           ▼                           │
        │                  ┌──────────────────┐                │
        │                  │  TESTING ENGINE  │                │
        │                  │                  │                │
        │                  │  - Mode 1: Hist  │                │
        │                  │  - Mode 2: Live  │                │
        │                  │  - Walkforward   │                │
        │                  └──────────────────┘                │
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                          ┌──────────────────┐
                          │  NAUTILUS TRADER │
                          │   INTEGRATION    │
                          │                  │
                          │  - Strategy Base │
                          │  - DataEngine    │
                          │  - ExecEngine    │
                          │  - Portfolio     │
                          └──────────────────┘
```

---

## Component Architecture

### 1. UI Layer Components

#### 1.1 Strategy Builder Interface
```
┌─────────────────────────────────────────────────────────────────┐
│                    STRATEGY BUILDER UI                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Strategy Information Panel                             │   │
│  │  - Name, Description (auto-generated)                   │   │
│  │  - Bullish/Bearish indicator                           │   │
│  │  - Required signals count (auto-calculated)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Block Search & Selection                               │   │
│  │  - Search by name, signal, description                  │   │
│  │  - Filter by category, type, tags                       │   │
│  │  - Show signal statistics (count, %)                    │   │
│  │  - Exclude already-added blocks                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Strategy Configuration (Drag & Drop)                   │   │
│  │                                                         │   │
│  │  [Block 1] ▲▼                                          │   │
│  │    ├─ Signal 1                      [AND/OR] [X candles]│   │
│  │    ├─ Signal 2                      [AND/OR] [X candles]│   │
│  │    └─ Signal 3                      [AND/OR]           │   │
│  │                                                         │   │
│  │  [Block 2] ▲▼ (AND) ◄─ Indent controls               │   │
│  │    ├─ Signal 1                      [OR]               │   │
│  │    └─ Signal 2                      [AND] [X candles]  │   │
│  │                                                         │   │
│  │  [Block 3] ▲▼ (OR) ◄─ Optional/Booster                │   │
│  │    └─ Signal 1                                         │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Adaptive SL/TP Configuration                           │   │
│  │  - Stop Loss v2.0 settings (existing)                   │   │
│  │  - Dynamic TP Mode (Fibonacci/Hybrid/Static)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Testing Controls                                       │   │
│  │  - Mode 1: Historical Walkforward                       │   │
│  │  - Mode 2: Live Continuation                            │   │
│  │  - Training Window (days)                               │   │
│  │  - Testing Window (days)                                │   │
│  │  - [Run Test] [Stop Test] [Results]                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Real-time Preview Panel                                │   │
│  │  - Live backtest results                                │   │
│  │  - Signal trigger visualization                         │   │
│  │  - Performance metrics                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Business Logic Layer Components

#### 2.1 Strategy Configuration Engine
```python
class StrategyConfigEngine:
    """
    Manages strategy configuration state and validation
    
    Responsibilities:
    - Maintain strategy configuration (blocks, signals, logic)
    - Validate block/signal combinations
    - Calculate required signal counts
    - Generate strategy descriptions
    - Resolve signal dependencies
    """
    
    def __init__(self, registry: BlockRegistry):
        self.registry = registry
        self.config = StrategyConfig()
        
    def add_block(self, block_name: str, logic: str = 'AND') -> bool:
        """Add building block to strategy"""
        
    def add_signal(self, block_name: str, signal_name: str, 
                   constraint: Optional[TimingConstraint] = None) -> bool:
        """Add signal to block"""
        
    def set_logic(self, block_name: str, logic: str) -> bool:
        """Set AND/OR logic for block"""
        
    def calculate_required_signals(self) -> int:
        """Calculate total required signals (AND blocks only)"""
        
    def generate_description(self) -> str:
        """Auto-generate strategy description"""
        
    def validate(self) -> ValidationResult:
        """Validate entire configuration"""
```

#### 2.2 Signal Dependency Resolver
```python
class SignalDependencyResolver:
    """
    Resolves signal-to-signal dependencies and timing constraints
    
    Handles:
    - "Signal 2 within X candles of Signal 1"
    - "Signal 3 only if Signal 2 triggered"
    - Cascade failures (reset entire strategy if timing fails)
    - OR block booster calculations
    """
    
    def resolve_dependencies(self, config: StrategyConfig) -> DependencyGraph:
        """Build dependency graph"""
        
    def validate_timing_constraint(self, signal_history: List, 
                                   constraint: TimingConstraint) -> bool:
        """Check if timing constraint is met"""
        
    def should_reset_strategy(self, signal_state: SignalState) -> bool:
        """Determine if strategy should reset"""
```

#### 2.3 Code Generation Engine
```python
class NautilusCodeGenerator:
    """
    Generates production-grade NautilusTrader strategy code
    
    Output:
    - Complete Strategy class
    - Proper type usage (Quantity, Price, Money)
    - Enum usage (OrderSide.BUY, not "BUY")
    - Error handling
    - Signal tracking
    - Position management
    """
    
    def generate_strategy(self, config: StrategyConfig) -> str:
        """Generate complete strategy Python code"""
        
    def generate_signal_detection(self, blocks: List[BlockConfig]) -> str:
        """Generate signal detection logic"""
        
    def generate_entry_logic(self, config: StrategyConfig) -> str:
        """Generate entry conditions with AND/OR logic"""
        
    def generate_exit_logic(self, sl_config, tp_config) -> str:
        """Generate stop loss and take profit logic"""
```

### 3. Data Layer Components

#### 3.1 Building Block Registry Interface
```python
class RegistryInterface:
    """
    Interface to Building Block Registry
    
    Provides:
    - Block metadata queries
    - Signal validation
    - Statistics retrieval
    - Block instantiation
    """
    
    def get_all_blocks(self) -> Dict[str, BlockMetadata]:
        """Get all registered blocks with metadata"""
        
    def search_blocks(self, query: str, filters: Dict) -> List[BlockMetadata]:
        """Search blocks by name, signal, description"""
        
    def get_signal_statistics(self, block_name: str) -> Dict[str, SignalStats]:
        """Get historical signal occurrences and percentages"""
        
    def validate_signal(self, block_name: str, signal_name: str) -> bool:
        """Validate signal exists for block"""
```

#### 3.2 Market Data Provider
```python
class MarketDataProvider:
    """
    Provides market data for backtesting and live testing
    
    Modes:
    - Historical: Load historical candle data
    - Live: Stream real-time candle data
    """
    
    def load_historical(self, start_date, end_date, timeframe) -> DataFrame:
        """Load historical OHLCV data"""
        
    def stream_live(self, callback: Callable) -> None:
        """Stream live candle data"""
```

### 4. Testing Engine Components

#### 4.1 Walkforward Test Engine
```python
class WalkforwardTestEngine:
    """
    Executes walkforward tests in two modes
    
    Mode 1: Historical Walkforward
    - Start X days back
    - Expand window candle-by-candle
    - Stop at current candle
    
    Mode 2: Live Continuation Walkforward
    - Start X days back
    - Expand to current
    - Continue with live candles until stopped
    """
    
    def run_mode1(self, config: StrategyConfig, days: int) -> TestResults:
        """Run historical walkforward"""
        
    def run_mode2(self, config: StrategyConfig, days: int, 
                  on_update: Callable) -> TestHandle:
        """Run live continuation walkforward"""
        
    def calculate_metrics(self, trades: List[Trade]) -> Metrics:
        """Calculate performance metrics"""
```

#### 4.2 Real-time Preview Engine
```python
class RealtimePreviewEngine:
    """
    Provides real-time backtest preview as user modifies strategy
    
    Features:
    - Incremental updates on config changes
    - Quick preview mode (limited data)
    - Signal visualization on chart
    """
    
    def start_preview(self, config: StrategyConfig, 
                     on_update: Callable) -> None:
        """Start real-time preview"""
        
    def update_config(self, config: StrategyConfig) -> None:
        """Update preview with new config"""
        
    def stop_preview(self) -> None:
        """Stop preview"""
```

---

## Data Flow

### Strategy Creation Flow
```
User Action: Add Building Block
        │
        ▼
┌──────────────────────┐
│  1. Query Registry   │ ──► BlockRegistry.get_block(name)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  2. Validate Block   │ ──► Check if already added
└──────────────────────┘     Check compatibility
        │
        ▼
┌──────────────────────┐
│  3. Add to Config    │ ──► StrategyConfig.add_block()
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  4. Update UI        │ ──► Show block in builder
└──────────────────────┘     Remove from search
        │
        ▼
┌──────────────────────┐
│  5. Trigger Preview  │ ──► RealtimePreviewEngine.update()
└──────────────────────┘
```

### Signal Configuration Flow
```
User Action: Add Signal to Block
        │
        ▼
┌──────────────────────┐
│  1. Validate Signal  │ ──► Registry.validate_signal()
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  2. Configure Logic  │ ──► Set AND/OR
└──────────────────────┘     Set timing constraint
        │
        ▼
┌──────────────────────┐
│  3. Update Config    │ ──► BlockConfig.add_signal()
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  4. Recalculate      │ ──► Calculate required signals
└──────────────────────┘     Resolve dependencies
        │
        ▼
┌──────────────────────┐
│  5. Update Preview   │ ──► RealtimePreviewEngine.update()
└──────────────────────┘
```

### Testing Flow (Mode 1: Historical)
```
User Action: Run Test (Mode 1)
        │
        ▼
┌──────────────────────┐
│  1. Load Data        │ ──► MarketDataProvider.load_historical()
└──────────────────────┘     Days = training + testing
        │
        ▼
┌──────────────────────┐
│  2. Generate Code    │ ──► NautilusCodeGenerator.generate()
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  3. Setup Engine     │ ──► NautilusTrader BacktestEngine
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  4. Run Walkforward  │ ──► Candle-by-candle expansion
└──────────────────────┘     From (days ago) → current
        │
        ▼
┌──────────────────────┐
│  5. Collect Results  │ ──► Trades, metrics, adjustments
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  6. Display Report   │ ──► Show comprehensive results
└──────────────────────┘
```

### Testing Flow (Mode 2: Live Continuation)
```
User Action: Run Test (Mode 2)
        │
        ▼
┌──────────────────────┐
│  1. Historical Phase │ ──► Same as Mode 1
└──────────────────────┘     Days ago → current
        │
        ▼
┌──────────────────────┐
│  2. Switch to Live   │ ──► MarketDataProvider.stream_live()
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  3. Process Live     │ ──► Each new candle triggers update
└──────────────────────┘     Continue until user stops
        │
        ▼
┌──────────────────────┐
│  4. Continuous       │ ──► Real-time metrics
└──────────────────────┘     Live signal detection
        │                    Position tracking
        ▼
┌──────────────────────┐
│  5. User Stops       │ ──► Final report
└──────────────────────┘     Total days = historical + live
```

---

## Integration Points

### 1. Building Block Registry Integration
```python
# Registry provides single source of truth
from src.detectors.building_blocks.registry import BlockRegistry

# Strategy Builder queries registry
blocks = BlockRegistry.get_all_blocks()
metadata = BlockRegistry.get_block('double_top')
signals = BlockRegistry.get_valid_signals('double_top')

# Instantiate blocks for testing
detector = BlockRegistry.instantiate('double_top', timeframe='15min')
result = detector.analyze(df)
```

### 2. NautilusTrader Integration
```python
# Generated strategy inherits from NautilusTrader
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.types import Quantity, Price

class GeneratedStrategy(Strategy):
    """Auto-generated from Strategy Builder"""
    
    def on_start(self):
        # Subscribe to required data
        self.subscribe_bars(self.bar_type)
    
    def on_bar(self, bar: Bar):
        # Detect signals using building blocks
        # Execute entry/exit logic with AND/OR
        # Manage positions with adaptive SL/TP
        pass
```

### 3. Adaptive SL/TP Integration
```python
# Existing Adaptive SL v2.0 configuration
from src.strategies.universal_optimizer.modules.adaptive_sl_v2 import AdaptiveSLv2

# Strategy Builder passes config to generated strategy
sl_config = {
    'mode': 'fibonacci',
    'aggressive_factor': 1.2,
    'fibonacci_level': 0.618
}

# Generated strategy uses existing SL/TP systems
self.adaptive_sl = AdaptiveSLv2(self.config['sl_config'])
```

### 4. Market Data Integration
```python
# Historical data from LakeAPI
from src.data_manager.lake_api import LakeAPI

# Live data from exchange
from exchange_connectors import BinanceConnector

# Unified interface in testing engine
class MarketDataProvider:
    def get_data(self, mode: str, **kwargs):
        if mode == 'historical':
            return LakeAPI.load_ohlcv(...)
        elif mode == 'live':
            return BinanceConnector.stream_candles(...)
```

---

## Technology Stack

### Frontend (UI Layer)
```
Primary: PyQt6 or PySide6
- Rich widget library
- Drag-and-drop support
- Cross-platform
- Professional appearance

Chart Visualization: Plotly or Matplotlib
- Real-time chart updates
- Signal markers
- Interactive zooming
```

### Backend (Business Logic)
```
Python 3.10+
- Type hints throughout
- Dataclasses for configs
- Async support for live testing

Key Libraries:
- NautilusTrader: Strategy framework
- Pandas/NumPy: Data manipulation
- Pydantic: Configuration validation
```

### Data Layer
```
Building Block Registry: Existing implementation
Market Data: LakeAPI (historical) + Live connectors
Storage: JSON for configurations, Parquet for test results
```

### Testing
```
pytest: Unit tests
Integration tests: Full walkforward simulations
Performance tests: Large strategy benchmarks
```

---

## Design Principles

### 1. Single Source of Truth
**Principle**: All building blocks, signals, and metadata come from the registry  
**Benefit**: No signal mismatches, automatic validation, scalability  
**Implementation**: RegistryInterface wraps BlockRegistry access

### 2. Composition Over Inheritance
**Principle**: Strategies are composed of blocks and signals, not hardcoded classes  
**Benefit**: Infinite flexibility, user-driven configuration  
**Implementation**: StrategyConfig is a data structure, not a class hierarchy

### 3. Fail-Fast Validation
**Principle**: Validate early and provide immediate feedback  
**Benefit**: Prevent invalid configurations, guide users to correct usage  
**Implementation**: Validation at every step (add block, add signal, generate code)

### 4. Real-time Feedback
**Principle**: Show results as user builds strategy  
**Benefit**: Immediate understanding of strategy behavior  
**Implementation**: RealtimePreviewEngine with incremental updates

### 5. Separation of Concerns
**Principle**: UI, business logic, data access are separate layers  
**Benefit**: Testability, maintainability, reusability  
**Implementation**: Layered architecture with clear interfaces

### 6. Production-Grade Code Generation
**Principle**: Generated code must meet institutional standards  
**Benefit**: Strategies are immediately deployable to live trading  
**Implementation**: NautilusCodeGenerator follows .clinerules precisely

### 7. User Experience First
**Principle**: Design for the user's mental model, not the system's  
**Benefit**: Intuitive interface, reduced learning curve  
**Implementation**: Button-based controls, visual feedback, tooltips everywhere

### 8. Extensibility
**Principle**: System can grow without major refactoring  
**Benefit**: Add new block types, logic operators, testing modes easily  
**Implementation**: Plugin architecture for blocks, strategy pattern for logic

---

## Related Documents

- [02_USER_FLOWS.md](02_USER_FLOWS.md) - Detailed user interaction flows
- [03_COMPONENT_SPECS.md](03_COMPONENT_SPECS.md) - Component specifications
- [04_BLOCK_MANAGEMENT.md](04_BLOCK_MANAGEMENT.md) - Block management system
- [30_NAUTILUS_COMPATIBILITY.md](30_NAUTILUS_COMPATIBILITY.md) - NautilusTrader integration
- [40_IMPLEMENTATION_ROADMAP.md](40_IMPLEMENTATION_ROADMAP.md) - Implementation plan

---

**Document Status**: 🟢 Complete  
**Review Status**: 🔴 Pending Review  
**Approved By**: N/A  
**Version**: 1.0.0
