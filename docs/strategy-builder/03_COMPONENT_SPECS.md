# Component Specifications - Strategy Builder Redesign
**Document**: 03_COMPONENT_SPECS.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical  
**Last Updated**: 2026-01-16

---

## UI Components

### StrategyBuilderWindow
Main application window containing all panels.

**Properties**:
- `strategy_config`: Current strategy configuration
- `registry_interface`: Connection to Building Block Registry
- `preview_engine`: Real-time preview system
- `test_engine`: Walkforward test engine

**Methods**:
- `initialize_ui()`: Setup all panels and layouts
- `load_strategy(path)`: Load saved strategy
- `save_strategy(path)`: Save current strategy
- `validate_strategy()`: Validate complete configuration

---

### StrategyInformationPanel
Display and edit strategy metadata.

**UI Elements**:
- Name field (text input, required)
- Description field (auto-generated, editable)
- Type indicator (Bullish/Bearish badge)
- Required signals count (auto-calculated label)

**Methods**:
- `update_description()`: Auto-generate from blocks/signals
- `calculate_required_signals()`: Sum AND block signals
- `set_strategy_type()`: Detect from block selections

---

### BlockSearchPanel
Search and filter building blocks.

**UI Elements**:
- Search input field
- Category filter dropdown
- Type filter (EVENT/SIGNAL/CONTEXT/HYBRID)
- Tag multi-select
- Results list with:
  - Block name
  - Category badge
  - Type badge
  - Default weight
  - Description
  - Signal statistics expandable

**Methods**:
- `search_blocks(query, filters)`: Filter registry
- `display_signal_stats(block_name)`: Show occurrence data
- `add_block_to_strategy(block_name, logic)`: Add with AND/OR
- `refresh_available_blocks()`: Exclude already-added

---

### StrategyConfigurationPanel
Visual strategy builder with drag-and-drop.

**UI Elements**:
- Block list (scrollable, drag-and-drop enabled)
- Each block displays:
  - Block header (name, AND/OR badge, controls)
  - Signal list (expandable)
  - Move up/down buttons (▲▼)
  - Indent/unindent buttons (→←)
  - Remove button (×)

**Methods**:
- `add_block(block_config)`: Add to list
- `remove_block(block_id)`: Remove and update
- `reorder_block(from_index, to_index)`: Drag-and-drop
- `indent_block(block_id)`: Create dependency
- `render_block_hierarchy()`: Visual indentation

---

### SignalConfigurationWidget
Configure signals within a block.

**UI Elements**:
- Signal selector dropdown
- AND/OR toggle buttons
- "Within X Candles" checkbox
- Candle count spinner (when enabled)
- Reference signal dropdown
- Dependency indicator
- Add/Remove signal buttons

**Methods**:
- `add_signal(signal_name)`: Add to block
- `configure_logic(signal_id, logic)`: Set AND/OR
- `set_timing_constraint(signal_id, candles, ref)`: Add constraint
- `validate_constraint()`: Check validity

---

### AdaptiveSLTPPanel
Configure stop loss and take profit (existing integration).

**UI Elements**:
- SL Mode: Dropdown (Fibonacci/Aggressive/Conservative)
- Fibonacci Level: Slider (0.236-0.618)
- TP Mode: Dropdown (Fibonacci/Hybrid/Static)
- TP1/TP2/TP3: Percentage inputs

**Methods**:
- `load_sl_config()`: Load from existing system
- `save_sl_config()`: Save to strategy
- `validate_sl_tp()`: Ensure valid values

---

### TestingControlsPanel
Configure and run walkforward tests.

**UI Elements**:
- Mode selector: Radio buttons (Mode 1/Mode 2)
- Testing window: Spinner (days)
- Training window: Spinner (days, optional)
- Timeframe: Dropdown (1min, 5min, 15min, 1h, 4h, 1d)
- Run Test button
- Stop Test button (enabled during test)
- Progress bar
- Live metrics display

**Methods**:
- `start_test(mode, config)`: Launch test
- `stop_test()`: Terminate live test
- `update_progress(metrics)`: Real-time updates
- `show_results(test_results)`: Display report

---

### RealtimePreviewPanel
Live backtest preview during strategy building.

**UI Elements**:
- Chart canvas (Plotly/Matplotlib)
- Signal markers on chart
- Quick metrics panel:
  - Signals triggered
  - Potential trades
  - Win rate estimate
  - P&L preview
- Pause/Resume button
- Expand button

**Methods**:
- `start_preview(config)`: Start background test
- `update_preview(new_config)`: Refresh on changes
- `render_chart(data, signals)`: Draw chart with markers
- `stop_preview()`: Pause updates

---

## Business Logic Components

### StrategyConfigEngine
Core configuration management system.

```python
class StrategyConfigEngine:
    """Manages strategy configuration state and validation"""
    
    def __init__(self, registry: BlockRegistry):
        self.registry = registry
        self.config = StrategyConfig()
        self.validators = ConfigValidators()
        
    def add_block(self, block_name: str, logic: str = 'AND') -> bool:
        """Add building block with AND/OR logic"""
        metadata = self.registry.get_block(block_name)
        if not metadata:
            raise ValueError(f"Block {block_name} not found")
        
        block_config = BlockConfig(
            name=block_name,
            logic=logic,
            signals=[],
            metadata=metadata
        )
        
        self.config.blocks.append(block_config)
        self.recalculate_requirements()
        return True
        
    def add_signal(self, block_name: str, signal_name: str,
                   logic: str = 'AND',
                   constraint:Optional[TimingConstraint] = None) -> bool:
        """Add signal to block with configuration"""
        block = self.config.get_block(block_name)
        if not block:
            raise ValueError(f"Block {block_name} not in strategy")
        
        # Validate signal exists
        if not self.registry.validate_signal(block_name, signal_name):
            raise ValueError(f"Invalid signal {signal_name}")
        
        signal_config = SignalConfig(
            name=signal_name,
            logic=logic,
            timing_constraint=constraint
        )
        
        block.signals.append(signal_config)
        self.recalculate_requirements()
        return True
        
    def recalculate_requirements(self):
        """Calculate total required signals (AND blocks only)"""
        total = 0
        for block in self.config.blocks:
            if block.logic == 'AND':
                # Count AND signals in this block
                and_signals = [s for s in block.signals if s.logic == 'AND']
                total += max(len(and_signals), 1)  # At least 1
        
        self.config.required_signals = total
        
    def generate_description(self) -> str:
        """Auto-generate strategy description"""
        parts = []
        
        for block in self.config.blocks:
            logic_str = "REQUIRED" if block.logic == 'AND' else "OPTIONAL"
            signal_names = [s.name for s in block.signals[:2]]
            parts.append(f"{block.name} ({logic_str}): {', '.join(signal_names)}")
        
        return " + ".join(parts)
        
    def validate(self) -> ValidationResult:
        """Comprehensive validation"""
        errors = []
        warnings = []
        
        # Must have at least one block
        if len(self.config.blocks) == 0:
            errors.append("Strategy must have at least one building block")
        
        # Each block must have at least one signal
        for block in self.config.blocks:
            if len(block.signals) == 0:
                errors.append(f"Block {block.name} must have at least one signal")
        
        # Check timing constraints
        for block in self.config.blocks:
            for signal in block.signals:
                if signal.timing_constraint:
                    if not self.validators.validate_timing(signal, block):
                        errors.append(f"Invalid timing constraint on {signal.name}")
        
        # Check circular dependencies
        if self.validators.has_circular_dependencies(self.config):
            errors.append("Circular dependencies detected")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

### SignalDependencyResolver
Resolves signal dependencies and timing constraints.

```python
class SignalDependencyResolver:
    """Handles signal-to-signal dependencies and timing"""
    
    def __init__(self):
        self.dependency_graph = {}
        
    def build_graph(self, config: StrategyConfig) -> DependencyGraph:
        """Build dependency graph from configuration"""
        graph = DependencyGraph()
        
        for block_idx, block in enumerate(config.blocks):
            for signal_idx, signal in enumerate(block.signals):
                node_id = f"{block.name}.{signal.name}"
                
                # Add node
                graph.add_node(node_id, signal)
                
                # Add timing dependencies
                if signal.timing_constraint:
                    ref_id = self._resolve_reference(
                        signal.timing_constraint.reference,
                        block_idx,
                        signal_idx,
                        config
                    )
                    graph.add_edge(ref_id, node_id, 
                                 weight=signal.timing_constraint.candles)
        
        return graph
        
    def validate_timing(self, signal_history: List[SignalEvent],
                       constraint: TimingConstraint) -> bool:
        """Check if timing constraint is satisfied"""
        if len(signal_history) < 2:
            return False
        
        latest_signal = signal_history[-1]
        reference_signal = self._find_reference(
            signal_history,
            constraint.reference
        )
        
        if not reference_signal:
            return False
        
        candles_elapsed = latest_signal.candle_index - reference_signal.candle_index
        return candles_elapsed <= constraint.candles
        
    def should_reset_strategy(self, signal_state: SignalState,
                             config: StrategyConfig) -> bool:
        """Determine if strategy should reset due to failed timing"""
        # Check all AND blocks with timing constraints
        for block in config.blocks:
            if block.logic != 'AND':
                continue
                
            for signal in block.signals:
                if not signal.timing_constraint:
                    continue
                    
                # If AND signal with timing failed, reset entire strategy
                if not self.validate_timing(
                    signal_state.history,
                    signal.timing_constraint
                ):
                    return True
        
        return False
```

---

### NautilusCodeGenerator
Generates production-grade NautilusTrader strategy code.

```python
class NautilusCodeGenerator:
    """Generate institutional-grade strategy code"""
    
    def __init__(self, registry: BlockRegistry):
        self.registry = registry
        self.templates = CodeTemplates()
        
    def generate_strategy(self, config: StrategyConfig) -> str:
        """Generate complete strategy file"""
        code_parts = []
        
        # Imports
        code_parts.append(self._generate_imports(config))
        
        # Strategy class
        code_parts.append(self._generate_class_definition(config))
        
        # Initialization
        code_parts.append(self._generate_init(config))
        
        # on_start
        code_parts.append(self._generate_on_start(config))
        
        # on_bar (main logic)
        code_parts.append(self._generate_on_bar(config))
        
        # Signal detection
        code_parts.append(self._generate_signal_detection(config))
        
        # Entry logic
        code_parts.append(self._generate_entry_logic(config))
        
        # Exit logic
        code_parts.append(self._generate_exit_logic(config))
        
        # Helper methods
        code_parts.append(self._generate_helpers(config))
        
        return "\n\n".join(code_parts)
        
    def _generate_imports(self, config: StrategyConfig) -> str:
        """Generate all required imports"""
        imports = [
            "from nautilus_trader.trading.strategy import Strategy",
            "from nautilus_trader.model.enums import OrderSide, TimeInForce",
            "from nautilus_trader.model.types import Quantity, Price, Money",
            "from nautilus_trader.model.orders import MarketOrder",
            "from nautilus_trader.core.data import Bar",
            "from typing import Dict, List, Optional",
            "from decimal import Decimal"
        ]
        
        # Add building block imports
        for block in config.blocks:
            module_path = self.registry.get_block(block.name).module_path
            imports.append(f"from {module_path} import {block.metadata.class_name}")
        
        return "\n".join(imports)
        
    def _generate_entry_logic(self, config: StrategyConfig) -> str:
        """Generate entry conditions with AND/OR logic"""
        code = """
    def check_entry_conditions(self) -> bool:
        \"\"\"Check if all entry conditions are met\"\"\"
        required_count = 0
        bonus_count = 0
        
"""
        
        # AND blocks (required)
        for block in config.blocks:
            if block.logic == 'AND':
                code += f"        # {block.name} (REQUIRED)\n"
                code += f"        if self.detect_{block.name}_signals():\n"
                code += f"            required_count += 1\n\n"
        
        # OR blocks (optional boosters)
        for block in config.blocks:
            if block.logic == 'OR':
                code += f"        # {block.name} (OPTIONAL BOOSTER)\n"
                code += f"        if self.detect_{block.name}_signals():\n"
                code += f"            bonus_count += 1\n\n"
        
        code += f"        # Required: {config.required_signals} signals\n"
        code += f"        entry_valid = required_count >= {config.required_signals}\n"
        code += f"        \n"
        code += f"        # Boost position size if bonuses triggered\n"
        code += f"        if bonus_count > 0:\n"
        code += f"            self.position_multiplier = 1.0 + (bonus_count * 0.1)\n"
        code += f"        \n"
        code += f"        return entry_valid\n"
        
        return code
```

---

## Data Components

### RegistryInterface
Interface to Building Block Registry.

```python
class RegistryInterface:
    """Clean interface to BuildingBlockRegistry"""
    
    def __init__(self):
        self.registry = BlockRegistry
        
    def get_all_blocks(self) -> Dict[str, BlockMetadata]:
        """Get all registered blocks"""
        return self.registry.get_all_blocks()
        
    def search_blocks(self, query: str, 
                     filters: Optional[Dict] = None) -> List[BlockMetadata]:
        """Search blocks with filters"""
        blocks = self.registry.get_all_blocks()
        results = []
        
        for name, metadata in blocks.items():
            # Text search
            if query:
                if (query.lower() not in name.lower() and
                    query.lower() not in metadata.description.lower()):
                    continue
            
            # Apply filters
            if filters:
                if 'category' in filters and metadata.category != filters['category']:
                    continue
                if 'tags' in filters:
                    if not any(tag in metadata.tags for tag in filters['tags']):
                        continue
            
            results.append(metadata)
        
        return results
        
    def get_signal_statistics(self, block_name: str) -> Dict[str, SignalStats]:
        """Get occurrence statistics for block signals"""
        # This would query historical data analysis
        # Placeholder for now
        metadata = self.registry.get_block(block_name)
        stats = {}
        
        for signal in metadata.valid_signals:
            stats[signal] = SignalStats(
                signal_name=signal,
                total_occurrences=0,  # From historical analysis
                percentage=0.0,
                description=metadata.signal_tiers.get(signal, {}).get('description', '')
            )
        
        return stats
```

---

### MarketDataProvider
Provides historical and live market data.

```python
class MarketDataProvider:
    """Unified interface for market data"""
    
    def __init__(self):
        self.lake_api = LakeAPI()  # Historical
        self.live_connector = None  # Live feed
        
    def load_historical(self, symbol: str, timeframe: str,
                       start_days_ago: int, end_days_ago: int = 0) -> pd.DataFrame:
        """Load historical OHLCV data"""
        end_date = datetime.now() - timedelta(days=end_days_ago)
        start_date = end_date - timedelta(days=start_days_ago)
        
        df = self.lake_api.load_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Validate data
        self._validate_ohlcv(df)
        
        return df
        
    def stream_live(self, symbol: str, timeframe: str,
                   callback: Callable) -> None:
        """Stream live candle data"""
        if not self.live_connector:
            self.live_connector = BinanceConnector()
        
        self.live_connector.subscribe_candles(
            symbol=symbol,
            timeframe=timeframe,
            on_candle=callback
        )
        
    def _validate_ohlcv(self, df: pd.DataFrame):
        """Validate OHLCV data integrity"""
        assert not df.isnull().any().any(), "NaN values found"
        assert (df['high'] >= df['low']).all(), "High < Low error"
        assert (df['volume'] > 0).all(), "Zero volume found"
```

---

## Testing Components

### WalkforwardTestEngine
Executes walkforward tests in two modes.

```python
class WalkforwardTestEngine:
    """Walkforward testing with Mode 1 (historical) and Mode 2 (live)"""
    
    def __init__(self, data_provider: MarketDataProvider,
                 code_generator: NautilusCodeGenerator):
        self.data_provider = data_provider
        self.code_generator = code_generator
        self.test_handle = None
        
    def run_mode1(self, config: StrategyConfig,
                  testing_days: int,
                  training_days: int = 0) -> TestResults:
        """Mode 1: Historical walkforward"""
        # Load data
        total_days = testing_days + training_days
        df = self.data_provider.load_historical(
            symbol='BTC/USDT',
            timeframe=config.timeframe,
            start_days_ago=total_days
        )
        
        # Generate strategy code
        strategy_code = self.code_generator.generate_strategy(config)
        
        # Setup Nautilus BacktestEngine
        engine = self._setup_backtest_engine(strategy_code, df)
        
        # Run walkforward (expanding window)
        results = self._run_walkforward_historical(
            engine,
            start_index=training_days * self._candles_per_day(config.timeframe),
            end_index=len(df)
        )
        
        return results
        
    def run_mode2(self, config: StrategyConfig,
                  testing_days: int,
                  training_days: int = 0,
                  on_update: Callable = None) -> TestHandle:
        """Mode 2: Historical + Live continuation"""
        # Run historical phase first
        historical_results = self.run_mode1(config, testing_days, training_days)
        
        # Switch to live mode
        def on_live_candle(candle):
            # Process new candle
            result = self.test_handle.process_candle(candle)
            
            # Update callback
            if on_update:
                on_update(result)
        
        # Start live stream
        self.data_provider.stream_live(
            symbol='BTC/USDT',
            timeframe=config.timeframe,
            callback=on_live_candle
        )
        
        self.test_handle = TestHandle(
            historical_results=historical_results,
            live_mode=True
        )
        
        return self.test_handle
        
    def stop_test(self):
        """Stop live test Mode 2"""
        if self.test_handle and self.test_handle.live_mode:
            self.test_handle.stop()
            self.data_provider.live_connector.disconnect()
```

---

### RealtimePreviewEngine
Provides real-time backtest preview.

```python
class RealtimePreviewEngine:
    """Live preview as user builds strategy"""
    
    def __init__(self, data_provider: MarketDataProvider,
                 code_generator: NautilusCodeGenerator):
        self.data_provider = data_provider
        self.code_generator = code_generator
        self.preview_thread = None
        self.current_results = None
        
    def start_preview(self, config: StrategyConfig,
                     on_update: Callable):
        """Start background preview"""
        if self.preview_thread:
            self.stop_preview()
        
        # Load last 30 days for quick preview
        df = self.data_provider.load_historical(
            symbol='BTC/USDT',
            timeframe=config.timeframe,
            start_days_ago=30
        )
        
        # Run preview in background thread
        self.preview_thread = threading.Thread(
            target=self._run_preview,
            args=(config, df, on_update)
        )
        self.preview_thread.start()
        
    def update_config(self, config: StrategyConfig):
        """Update preview with new configuration"""
        # Will restart preview with new config
        if self.preview_thread:
            self.start_preview(config, self.on_update_callback)
        
    def _run_preview(self, config, df, callback):
        """Run quick backtest for preview"""
        try:
            # Generate code
            code = self.code_generator.generate_strategy(config)
            
            # Quick backtest
            engine = self._setup_quick_engine(code, df)
            results = engine.run()
            
            # Extract signals for visualization
            signals = self._extract_signals(results)
            
            # Callback with results
            callback(PreviewResults(
                signals=signals,
                quick_metrics=self._calculate_quick_metrics(results)
            ))
        except Exception as e:
            callback(PreviewError(str(e)))
```

---

**Document Status**: 🟢 Complete  
**Review Status**: 🔴 Pending  
**Version**: 1.0.0
