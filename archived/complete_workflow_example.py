"""
Complete Workflow Example
Demonstrates all 9 strategy builder components working together
Shows real-world usage of the entire system
Reference: docs/v3/UI-UX/24_COMPLETE_EXAMPLE.md
"""

import tempfile
from pathlib import Path
from typing import Dict, Any

from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfigEngine,
    TimingConstraint
)
from src.strategy_builder.core.signal_dependency_resolver import SignalDependencyResolver
from src.strategy_builder.core.registry_interface import RegistryInterface
from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
from src.strategy_builder.testing.walkforward_test_engine import (
    WalkforwardTestEngine,
    WalkforwardConfig,
    WalkforwardMode
)
from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.execution.block_state_manager import BlockStateManager
from src.strategy_builder.validation.strategy_validator import (
    StrategyValidator,
    ValidationLevel
)
from src.strategy_builder.persistence.strategy_persistence import (
    StrategyPersistence,
    PersistenceFormat
)


class CompleteWorkflowExample:
    """
    Comprehensive example showing all components in action
    Demonstrates complete strategy lifecycle from creation to execution
    """
    
    def __init__(self):
        """Initialize example with all components"""
        self.orchestrator = StrategyBuilderOrchestrator()
        self.validator = StrategyValidator()
        self.persistence = StrategyPersistence()
        
    def run_complete_workflow(self) -> Dict[str, Any]:
        """
        Execute complete workflow demonstrating all components
        
        Returns:
            Dictionary with results from each step
        """
        results = {}
        
        # Step 1: Create Strategy (StrategyConfigEngine via Orchestrator)
        print("=== Step 1: Creating Strategy ===")
        create_result = self.orchestrator.create_strategy(
            name="Example_MA_Crossover",
            description="Moving Average crossover strategy with momentum confirmation"
        )
        results['create'] = create_result.success
        print(f"Strategy created: {create_result.success}")
        
        # Step 2: Add Blocks and Signals
        print("\n=== Step 2: Adding Blocks and Signals ===")
        
        # Add first block
        self.orchestrator.add_block("MA_Crossover", "AND")
        self.orchestrator.add_signal("MA_Crossover", "GOLDEN_CROSS", "AND")
        self.orchestrator.add_signal(
            "MA_Crossover",
            "VOLUME_CONFIRMATION",
            "AND",
            within_candles=5,
            reference_signal="GOLDEN_CROSS"
        )
        
        # Add second block
        self.orchestrator.add_block("Momentum", "OR")
        self.orchestrator.add_signal("Momentum", "RSI_OVERSOLD", "OR")
        self.orchestrator.add_signal("Momentum", "MACD_BULLISH", "OR")
        
        print("Blocks and signals added")
        results['blocks_added'] = True
        
        # Step 3: Validate Strategy (StrategyValidator)
        print("\n=== Step 3: Validating Strategy ===")
        config = self.orchestrator.get_current_config()
        validation_result = self.validator.validate(config, ValidationLevel.STRICT)
        results['validation'] = validation_result.is_valid
        print(f"Validation passed: {validation_result.is_valid}")
        
        if not validation_result.is_valid:
            print(f"Errors: {validation_result.errors}")
            return results
            
        # Step 4: Check Dependencies (SignalDependencyResolver via Orchestrator)
        print("\n=== Step 4: Checking Dependencies ===")
        dep_result = self.orchestrator.validate_dependencies()
        results['dependencies'] = dep_result.success
        print(f"Dependencies valid: {dep_result.success}")
        
        # Step 5: Generate Code (NautilusCodeGenerator via Orchestrator)
        print("\n=== Step 5: Generating NautilusTrader Code ===")
        code_result = self.orchestrator.generate_code()
        results['code_generation'] = code_result.success
        if code_result.success:
            print(f"Code generated: {len(code_result.generated_code.strategy_code)} characters")
        
        # Step 6: Save Strategy (StrategyPersistence)
        print("\n=== Step 6: Saving Strategy ===")
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "example_strategy.json"
            save_result = self.persistence.save(config, save_path)
            results['save'] = save_result.success
            print(f"Strategy saved: {save_result.success}")
            
            # Step 7: Load Strategy (StrategyPersistence)
            print("\n=== Step 7: Loading Strategy ===")
            load_result = self.persistence.load(save_path)
            results['load'] = load_result.success
            print(f"Strategy loaded: {load_result.success}")
            
            if load_result.success:
                loaded_config = load_result.config
                print(f"Loaded strategy: {loaded_config.name}")
                print(f"Blocks: {len(loaded_config.blocks)}")
        
        # Step 8: Initialize Execution State (BlockStateManager)
        print("\n=== Step 8: Initializing Execution State ===")
        state_manager = BlockStateManager(config)
        results['state_manager'] = True
        print("State manager initialized")
        
        # Simulate signal firing
        state_manager.on_candle(100)
        state_manager.signal_fired("MA_Crossover", "GOLDEN_CROSS", 100)
        state_manager.signal_fired("MA_Crossover", "VOLUME_CONFIRMATION", 103)
        
        is_complete = state_manager.is_strategy_complete()
        print(f"Strategy requirements met: {is_complete}")
        results['execution_state'] = is_complete
        
        # Step 9: Get Execution State
        print("\n=== Step 9: Getting Execution State ===")
        execution_state = state_manager.get_execution_state()
        print(f"Current candle: {execution_state.current_candle}")
        print(f"Complete: {execution_state.complete}")
        results['execution_snapshot'] = True
        
        # Summary
        print("\n=== WORKFLOW COMPLETE ===")
        print(f"Total steps: {len(results)}")
        print(f"Successful steps: {sum(1 for v in results.values() if v)}")
        
        return results
        
    def demonstrate_registry_search(self):
        """Demonstrate RegistryInterface functionality"""
        print("\n=== Demonstrating Registry Search ===")
        
        # Search for blocks
        results = self.orchestrator.search_blocks("RSI")
        print(f"Found {len(results)} blocks matching 'RSI'")
        
        return len(results) >= 0
        
    def demonstrate_backtest(self):
        """Demonstrate WalkforwardTestEngine functionality"""
        print("\n=== Demonstrating Backtest ===")
        
        config = self.orchestrator.get_current_config()
        
        # Run backtest (would need actual data in real scenario)
        backtest_result = self.orchestrator.run_backtest(
            lookback_days=30,
            mode=WalkforwardMode.MODE_1
        )
        
        print(f"Backtest completed: {backtest_result.success}")
        
        return backtest_result.success


def run_example():
    """
    Main entry point for complete workflow example
    Demonstrates all 9 components in action
    """
    print("="*60)
    print("COMPLETE STRATEGY BUILDER WORKFLOW EXAMPLE")
    print("Demonstrating all 9 components")
    print("="*60)
    
    example = CompleteWorkflowExample()
    
    # Run complete workflow
    results = example.run_complete_workflow()
    
    # Additional demonstrations
    example.demonstrate_registry_search()
    example.demonstrate_backtest()
    
    print("\n" + "="*60)
    print("EXAMPLE COMPLETE")
    print("="*60)
    
    return results


if __name__ == "__main__":
    run_example()
