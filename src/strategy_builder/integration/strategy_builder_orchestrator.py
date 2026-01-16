"""
Strategy Builder Orchestrator
Integration layer connecting all 5 core components
Provides high-level workflow orchestration
Reference: docs/v3/UI-UX/20_INTEGRATION_LAYER.md
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from dataclasses import dataclass, field

from src.strategy_builder.core.registry_interface import RegistryInterface
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfigEngine,
    StrategyConfig,
    TimingConstraint
)
from src.strategy_builder.core.signal_dependency_resolver import SignalDependencyResolver
from src.strategy_builder.core.nautilus_code_generator import (
    NautilusCodeGenerator,
    GeneratedCode
)
from src.strategy_builder.testing.walkforward_test_engine import (
    WalkforwardTestEngine,
    WalkforwardConfig,
    WalkforwardMode,
    WalkforwardResult
)


class MockRegistry:
    """
    Mock registry for testing/standalone operation
    Provides basic registry interface without actual block data
    """
    
    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """Return mock blocks"""
        return [
            {
                'name': 'Double_Top',
                'category': 'PATTERN',
                'type': 'SIGNAL',
                'weight': 10,
                'description': 'Double top pattern detector',
                'signals': [
                    {
                        'name': 'BEARISH_BREAKDOWN',
                        'count': 100,
                        'percentage': 50.0,
                        'description': 'Bearish breakdown signal'
                    }
                ]
            },
            {
                'name': 'RSI',
                'category': 'INDICATOR',
                'type': 'SIGNAL',
                'weight': 5,
                'description': 'RSI indicator',
                'signals': [
                    {
                        'name': 'OVERBOUGHT',
                        'count': 50,
                        'percentage': 25.0,
                        'description': 'Overbought condition'
                    }
                ]
            }
        ]
        
    def get_block(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific block"""
        blocks = self.get_all_blocks()
        for block in blocks:
            if block['name'] == name:
                return block
        return None


class WorkflowStep(Enum):
    """Workflow step enumeration"""
    CREATE_STRATEGY = "create_strategy"
    ADD_BLOCK = "add_block"
    ADD_SIGNAL = "add_signal"
    VALIDATE = "validate"
    VALIDATE_DEPENDENCIES = "validate_dependencies"
    GENERATE_CODE = "generate_code"
    RUN_BACKTEST = "run_backtest"
    SEARCH_BLOCKS = "search_blocks"
    GET_SIGNALS = "get_signals"


@dataclass
class WorkflowResult:
    """Result from a workflow operation"""
    success: bool
    step: WorkflowStep
    message: str = ""
    errors: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    strategy_config: Optional[StrategyConfig] = None
    generated_code: Optional[GeneratedCode] = None
    test_result: Optional[WalkforwardResult] = None
    data: Optional[Any] = None


class StrategyBuilderOrchestrator:
    """
    High-level orchestrator connecting all strategy builder components
    Provides simplified workflow API for strategy creation and testing
    """
    
    def __init__(self, registry=None):
        """
        Initialize orchestrator with all components
        
        Args:
            registry: Optional BlockRegistry instance (uses mock if not provided)
        """
        # Initialize all 5 core components
        # Use mock registry if none provided
        if registry is None:
            registry = MockRegistry()
        
        # Share registry across components that need it
        self.registry = registry
        self.registry_interface = RegistryInterface(registry)
        self.config_engine = StrategyConfigEngine(registry)
        self.dependency_resolver = SignalDependencyResolver()
        self.code_generator = NautilusCodeGenerator()
        self.test_engine = WalkforwardTestEngine()
        
    def create_strategy(
        self,
        name: str,
        description: str = ""
    ) -> WorkflowResult:
        """
        Create a new strategy
        
        Args:
            name: Strategy name
            description: Strategy description
            
        Returns:
            WorkflowResult with strategy config
        """
        try:
            # Create new config through engine
            self.config_engine = StrategyConfigEngine(self.registry)
            self.config_engine.config.name = name
            self.config_engine.config.description = description or f"Strategy: {name}"
            
            return WorkflowResult(
                success=True,
                step=WorkflowStep.CREATE_STRATEGY,
                message=f"Strategy '{name}' created successfully",
                strategy_config=self.config_engine.config
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.CREATE_STRATEGY,
                message="Failed to create strategy",
                errors=[str(e)]
            )
            
    def add_block(
        self,
        block_name: str,
        logic: str = "AND"
    ) -> WorkflowResult:
        """
        Add a building block to the strategy
        
        Args:
            block_name: Name of the building block
            logic: Block logic ("AND" or "OR")
            
        Returns:
            WorkflowResult
        """
        try:
            # Check if strategy exists
            if not self.config_engine.config.name:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.ADD_BLOCK,
                    message="No strategy created. Create a strategy first.",
                    errors=["Strategy not initialized"]
                )
                
            # Add block through engine
            self.config_engine.add_block(block_name, logic)
            
            return WorkflowResult(
                success=True,
                step=WorkflowStep.ADD_BLOCK,
                message=f"Block '{block_name}' added with logic '{logic}'",
                strategy_config=self.config_engine.config
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.ADD_BLOCK,
                message=f"Failed to add block '{block_name}'",
                errors=[str(e)]
            )
            
    def add_signal(
        self,
        block_name: str,
        signal_name: str,
        logic: str = "AND",
        within_candles: Optional[int] = None,
        reference_signal: Optional[str] = None
    ) -> WorkflowResult:
        """
        Add a signal to a block
        
        Args:
            block_name: Name of the block
            signal_name: Name of the signal
            logic: Signal logic ("AND" or "OR")
            within_candles: Optional timing constraint (candles)
            reference_signal: Optional reference signal for timing
            
        Returns:
            WorkflowResult
        """
        try:
            # Check if strategy exists
            if not self.config_engine.config.name:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.ADD_SIGNAL,
                    message="No strategy created",
                    errors=["Strategy not initialized"]
                )
                
            # Create timing constraint if specified
            timing_constraint = None
            if within_candles and reference_signal:
                timing_constraint = TimingConstraint(
                    max_candles=within_candles,
                    reference=reference_signal
                )
                
            # Add signal through engine
            self.config_engine.add_signal(
                block_name=block_name,
                signal_name=signal_name,
                logic=logic,
                constraint=timing_constraint
            )
            
            return WorkflowResult(
                success=True,
                step=WorkflowStep.ADD_SIGNAL,
                message=f"Signal '{signal_name}' added to block '{block_name}'",
                strategy_config=self.config_engine.config
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.ADD_SIGNAL,
                message=f"Failed to add signal '{signal_name}'",
                errors=[str(e)]
            )
    
    def add_block_with_signals(
        self,
        block_name: str,
        signal_names: List[str],
        block_logic: str = "AND",
        signal_logic: str = "AND"
    ) -> WorkflowResult:
        """
        NEW: Add block with signals - handles both new blocks and adding signals to existing blocks
        
        This is the institutional-grade method that intelligently:
        1. Creates block if it doesn't exist
        2. Adds all specified signals to the block
        3. Handles both initial addition and subsequent signal additions
        
        Args:
            block_name: Name of the building block
            signal_names: List of signal names to add
            block_logic: Logic for the block itself ("AND" or "OR")
            signal_logic: Logic for the signals ("AND" or "OR")
            
        Returns:
            WorkflowResult
        """
        try:
            # Check if strategy exists
            if not self.config_engine.config.name:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.ADD_BLOCK,
                    message="No strategy created. Create a strategy first.",
                    errors=["Strategy not initialized"]
                )
            
            # Check if block already exists in config
            block_exists = any(
                block.name == block_name 
                for block in self.config_engine.config.blocks
            )
            
            # If block doesn't exist, add it first
            if not block_exists:
                add_block_result = self.add_block(block_name, block_logic)
                if not add_block_result.success:
                    return add_block_result
            
            # Add all signals to the block
            signals_added = []
            errors = []
            
            for signal_name in signal_names:
                result = self.add_signal(
                    block_name=block_name,
                    signal_name=signal_name,
                    logic=signal_logic
                )
                
                if result.success:
                    signals_added.append(signal_name)
                else:
                    errors.extend(result.errors)
            
            # Determine overall success
            success = len(signals_added) > 0
            
            if success:
                message = f"Added {len(signals_added)} signal(s) to block '{block_name}'"
                if errors:
                    message += f" (with {len(errors)} error(s))"
            else:
                message = f"Failed to add signals to block '{block_name}'"
            
            return WorkflowResult(
                success=success,
                step=WorkflowStep.ADD_SIGNAL,
                message=message,
                errors=errors,
                strategy_config=self.config_engine.config,
                data={
                    'block_name': block_name,
                    'signals_added': signals_added,
                    'block_existed': block_exists
                }
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.ADD_BLOCK,
                message=f"Failed to add block with signals '{block_name}'",
                errors=[str(e)]
            )
            
    def validate_strategy(self) -> WorkflowResult:
        """
        Validate the current strategy configuration
        
        Returns:
            WorkflowResult with validation errors
        """
        try:
            # Validate through engine
            validation_result = self.config_engine.validate()
            
            return WorkflowResult(
                success=validation_result.valid,
                step=WorkflowStep.VALIDATE,
                message="Strategy validated" if validation_result.valid else "Validation failed",
                validation_errors=validation_result.errors,
                strategy_config=self.config_engine.config
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.VALIDATE,
                message="Validation error",
                errors=[str(e)]
            )
            
    def validate_dependencies(self) -> WorkflowResult:
        """
        Validate signal dependencies
        
        Returns:
            WorkflowResult with dependency validation
        """
        try:
            # Build dependency graph
            graph = self.dependency_resolver.build_graph(self.config_engine.config)
            
            # Check for circular dependencies
            has_circular = graph.has_circular_dependency()
            
            if has_circular:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.VALIDATE_DEPENDENCIES,
                    message="Circular dependencies detected",
                    validation_errors=["Circular dependency in signal constraints"]
                )
                
            return WorkflowResult(
                success=True,
                step=WorkflowStep.VALIDATE_DEPENDENCIES,
                message="Dependencies validated successfully"
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.VALIDATE_DEPENDENCIES,
                message="Dependency validation error",
                errors=[str(e)]
            )
            
    def generate_code(self) -> WorkflowResult:
        """
        Generate NautilusTrader code for the strategy
        
        Returns:
            WorkflowResult with generated code
        """
        try:
            # Validate first
            validation = self.validate_strategy()
            if not validation.success:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.GENERATE_CODE,
                    message="Cannot generate code - validation failed",
                    validation_errors=validation.validation_errors
                )
                
            # Generate code
            generated_code = self.code_generator.generate(self.config_engine.config)
            
            return WorkflowResult(
                success=True,
                step=WorkflowStep.GENERATE_CODE,
                message="Code generated successfully",
                generated_code=generated_code
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.GENERATE_CODE,
                message="Code generation error",
                errors=[str(e)]
            )
            
    def run_backtest(
        self,
        lookback_days: int = 180,
        training_window_days: int = 0,
        mode: WalkforwardMode = WalkforwardMode.MODE_1
    ) -> WorkflowResult:
        """
        Run walkforward backtest on the strategy
        
        Args:
            lookback_days: Days to look back for testing
            training_window_days: Optional training window
            mode: Test mode (MODE_1 or MODE_2)
            
        Returns:
            WorkflowResult with test results
        """
        try:
            # Validate first
            validation = self.validate_strategy()
            if not validation.success:
                return WorkflowResult(
                    success=False,
                    step=WorkflowStep.RUN_BACKTEST,
                    message="Cannot run backtest - validation failed",
                    validation_errors=validation.validation_errors
                )
                
            # Configure test engine
            test_config = WalkforwardConfig(
                mode=mode,
                lookback_days=lookback_days,
                training_window_days=training_window_days
            )
            self.test_engine = WalkforwardTestEngine(test_config)
            
            # Run backtest
            test_result = self.test_engine.run(self.config_engine.config)
            
            return WorkflowResult(
                success=True,
                step=WorkflowStep.RUN_BACKTEST,
                message="Backtest completed successfully",
                test_result=test_result
            )
        except Exception as e:
            return WorkflowResult(
                success=False,
                step=WorkflowStep.RUN_BACKTEST,
                message="Backtest error",
                errors=[str(e)]
            )
            
    def search_blocks(self, query: str = "", **filters) -> List[Any]:
        """
        Search for building blocks
        
        Args:
            query: Search query
            **filters: Additional filters
            
        Returns:
            List of search results
        """
        try:
            results = self.registry_interface.search_blocks(query, **filters)
            return results
        except Exception:
            return []
            
    def get_block_signals(self, block_name: str) -> List[Any]:
        """
        Get signals for a specific block
        
        Args:
            block_name: Block name
            
        Returns:
            List of signals
        """
        try:
            block_info = self.registry_interface.get_block(block_name)
            if block_info:
                return block_info.signals
            return []
        except Exception:
            return []
            
    def get_current_config(self) -> StrategyConfig:
        """
        Get current strategy configuration
        
        Returns:
            Current StrategyConfig
        """
        return self.config_engine.config
        
    def reset(self):
        """Reset orchestrator state"""
        self.config_engine = StrategyConfigEngine(self.registry)
        self.dependency_resolver = SignalDependencyResolver()
        self.test_engine = WalkforwardTestEngine()
