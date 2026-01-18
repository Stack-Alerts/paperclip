"""
Unit Tests for StrategyBuilderOrchestrator
Integration layer connecting all 5 core components
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/20_INTEGRATION_LAYER.md
"""

import pytest
from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator,
    WorkflowResult,
    WorkflowStep
)


class TestStrategyBuilderOrchestrator:
    """Test suite for StrategyBuilderOrchestrator"""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initializes with all components"""
        orchestrator = StrategyBuilderOrchestrator()
        
        assert orchestrator is not None
        assert orchestrator.registry_interface is not None
        assert orchestrator.config_engine is not None
        assert orchestrator.dependency_resolver is not None
        assert orchestrator.code_generator is not None
        assert orchestrator.test_engine is not None
        
    def test_create_new_strategy(self):
        """Test creating a new strategy from scratch"""
        orchestrator = StrategyBuilderOrchestrator()
        
        result = orchestrator.create_strategy(
            name="TestStrategy",
            description="Test strategy for integration"
        )
        
        assert result is not None
        assert result.success is True
        assert result.strategy_config is not None
        
    def test_add_block_to_strategy(self):
        """Test adding a building block to strategy"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy
        result = orchestrator.create_strategy("TestStrategy")
        
        # Add block
        result = orchestrator.add_block(
            block_name="Double_Top",
            logic="AND"
        )
        
        assert result.success is True
        assert len(orchestrator.config_engine.config.blocks) == 1
        
    def test_add_signal_to_block(self):
        """Test adding signal to a block"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("TestStrategy")
        orchestrator.add_block("Double_Top", "AND")
        
        # Add signal
        result = orchestrator.add_signal(
            block_name="Double_Top",
            signal_name="BEARISH_BREAKDOWN",
            logic="AND"
        )
        
        assert result.success is True
        
    def test_validate_strategy(self):
        """Test strategy validation through orchestrator"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("TestStrategy")
        orchestrator.add_block("Double_Top", "AND")
        orchestrator.add_signal("Double_Top", "BEARISH_BREAKDOWN", "AND")
        
        # Validate
        result = orchestrator.validate_strategy()
        
        assert result.success is True
        assert result.validation_errors == []
        
    def test_generate_code_workflow(self):
        """Test complete code generation workflow"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("TestStrategy")
        orchestrator.add_block("Double_Top", "AND")
        orchestrator.add_signal("Double_Top", "BEARISH_BREAKDOWN", "AND")
        
        # Generate code
        result = orchestrator.generate_code()
        
        assert result.success is True
        assert result.generated_code is not None
        assert len(result.generated_code.strategy_code) > 0
        
    def test_run_backtest_workflow(self):
        """Test complete backtest workflow"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("TestStrategy")
        orchestrator.add_block("Double_Top", "AND")
        orchestrator.add_signal("Double_Top", "BEARISH_BREAKDOWN", "AND")
        
        # Run backtest
        result = orchestrator.run_backtest(lookback_days=30)
        
        assert result.success is True
        assert result.test_result is not None
        
    def test_complete_workflow(self):
        """Test complete end-to-end workflow"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Step 1: Create strategy
        result = orchestrator.create_strategy("CompleteStrategy")
        assert result.success is True
        
        # Step 2: Add blocks
        result = orchestrator.add_block("Double_Top", "AND")
        assert result.success is True
        
        # Step 3: Add signals
        result = orchestrator.add_signal("Double_Top", "BEARISH_BREAKDOWN", "AND")
        assert result.success is True
        
        # Step 4: Validate
        result = orchestrator.validate_strategy()
        assert result.success is True
        
        # Step 5: Generate code
        result = orchestrator.generate_code()
        assert result.success is True
        
        # Step 6: Run backtest
        result = orchestrator.run_backtest(lookback_days=10)
        assert result.success is True
        
    def test_search_blocks(self):
        """Test searching blocks through orchestrator"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Search for blocks
        results = orchestrator.search_blocks(query="pattern")
        
        assert results is not None
        assert isinstance(results, list)
        
    def test_get_block_signals(self):
        """Test getting signals for a block"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Get signals for a block
        signals = orchestrator.get_block_signals("Double_Top")
        
        assert signals is not None
        assert isinstance(signals, list)
        
    def test_workflow_with_dependencies(self):
        """Test workflow with signal dependencies"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("DependencyStrategy")
        orchestrator.add_block("Block1", "AND")
        orchestrator.add_signal("Block1", "SIGNAL1", "AND")
        
        # Add signal with timing constraint
        result = orchestrator.add_signal(
            block_name="Block1",
            signal_name="SIGNAL2",
            logic="AND",
            within_candles=20,
            reference_signal="SIGNAL1"
        )
        
        assert result.success is True
        
        # Validate dependencies
        result = orchestrator.validate_dependencies()
        assert result.success is True
        
    def test_workflow_error_handling(self):
        """Test workflow error handling"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Try to add signal without strategy
        result = orchestrator.add_signal("Block1", "SIGNAL1", "AND")
        
        assert result.success is False
        assert len(result.errors) > 0


class TestWorkflowResult:
    """Test WorkflowResult data class"""
    
    def test_result_creation(self):
        """Test creating workflow result"""
        result = WorkflowResult(
            success=True,
            step=WorkflowStep.CREATE_STRATEGY,
            message="Strategy created successfully"
        )
        
        assert result.success is True
        assert result.step == WorkflowStep.CREATE_STRATEGY
        assert result.message == "Strategy created successfully"


class TestWorkflowStep:
    """Test WorkflowStep enum"""
    
    def test_workflow_steps(self):
        """Test workflow step enum values"""
        assert WorkflowStep.CREATE_STRATEGY is not None
        assert WorkflowStep.ADD_BLOCK is not None
        assert WorkflowStep.ADD_SIGNAL is not None
        assert WorkflowStep.VALIDATE is not None
        assert WorkflowStep.GENERATE_CODE is not None
        assert WorkflowStep.RUN_BACKTEST is not None


class TestStrategyBuilderIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_strategy_lifecycle(self):
        """Test complete strategy lifecycle"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Create
        orchestrator.create_strategy("LifecycleStrategy")
        
        # Build
        orchestrator.add_block("Double_Top", "AND")
        orchestrator.add_signal("Double_Top", "BEARISH_BREAKDOWN", "AND")
        
        orchestrator.add_block("RSI", "OR")
        orchestrator.add_signal("RSI", "OVERBOUGHT", "OR")
        
        # Validate
        validation = orchestrator.validate_strategy()
        assert validation.success is True
        
        # Generate
        code_result = orchestrator.generate_code()
        assert code_result.success is True
        assert code_result.generated_code is not None
        
        # Test
        test_result = orchestrator.run_backtest(lookback_days=30)
        assert test_result.success is True
        assert test_result.test_result.total_positions >= 0
        
    def test_multi_block_strategy(self):
        """Test strategy with multiple blocks"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("MultiBlockStrategy")
        
        # Add multiple blocks
        for i in range(3):
            orchestrator.add_block(f"Block{i}", "AND")
            orchestrator.add_signal(f"Block{i}", f"SIGNAL{i}", "AND")
            
        # Validate
        result = orchestrator.validate_strategy()
        assert result.success is True
        
        # Check configuration
        config = orchestrator.get_current_config()
        assert len(config.blocks) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
