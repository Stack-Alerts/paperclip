"""
Unit tests for Exit Condition Orchestrator Methods
Tests add/remove/configure exit condition workflow methods
Sprint 1.8 Task 1.8.33
"""

import pytest
from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator,
    WorkflowStep
)


class TestExitConditionOrchestrator:
    """Test orchestrator exit condition CRUD methods"""
    
    def test_add_strategy_level_exit_condition(self):
        """Test adding strategy-level exit condition"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy
        orchestrator.create_strategy("Test Strategy")
        
        # Add exit condition
        result = orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=0.3,
            binding_level="STRATEGY",
            exit_mode="ABSOLUTE"
        )
        
        assert result.success == True
        assert "strategy-level" in result.message.lower()
        
        # Verify exit condition added
        config = orchestrator.get_current_config()
        assert len(config.exit_conditions) == 1
        assert config.exit_conditions[0].signal_name == "BEARISH"
        assert config.exit_conditions[0].percentage == 0.3
        assert config.exit_conditions[0].exit_mode == "ABSOLUTE"
    
    def test_add_block_level_exit_condition(self):
        """Test adding block-level exit condition"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy and add block
        orchestrator.create_strategy("Test Strategy")
        orchestrator.add_block("hod", "AND")
        
        # Add exit condition
        result = orchestrator.add_exit_condition(
            signal_name="HOD_REJECTION",
            percentage=0.4,
            binding_level="BLOCK",
            block_name="hod",
            exit_mode="FLEXIBLE"
        )
        
        assert result.success == True
        assert "block-level" in result.message.lower()
        
        # Verify exit condition added
        config = orchestrator.get_current_config()
        assert len(config.blocks[0].exit_conditions) == 1
        assert config.blocks[0].exit_conditions[0].signal_name == "HOD_REJECTION"
        assert config.blocks[0].exit_conditions[0].percentage == 0.4
        assert config.blocks[0].exit_conditions[0].exit_mode == "FLEXIBLE"
    
    def test_add_signal_level_exit_condition(self):
        """Test adding signal-level exit condition"""
        orchestrator = StrategyBuilderOrchestrator()
        
        # Create strategy, add block and signal
        orchestrator.create_strategy("Test Strategy")
        orchestrator.add_block("hod", "AND")
        orchestrator.add_signal("hod", "AT_HOD", "AND")
        
        # Add exit condition
        result = orchestrator.add_exit_condition(
            signal_name="BELOW_HOD",
            percentage=0.2,
            binding_level="SIGNAL",
            block_name="hod",
            parent_signal_name="AT_HOD"
        )
        
        assert result.success == True
        assert "signal-level" in result.message.lower()
        
        # Verify exit condition added
        config = orchestrator.get_current_config()
        signal = config.blocks[0].signals[0]
        assert len(signal.exit_conditions) == 1
        assert signal.exit_conditions[0].signal_name == "BELOW_HOD"
        assert signal.exit_conditions[0].percentage == 0.2
    
    def test_add_exit_condition_validation(self):
        """Test exit condition input validation"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Invalid percentage (too low)
        result = orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=0.0
        )
        assert result.success == False
        assert "percentage" in result.message.lower()
        
        # Invalid percentage (too high)
        result = orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=1.5
        )
        assert result.success == False
        
        # Invalid exit mode
        result = orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=0.5,
            exit_mode="INVALID"
        )
        assert result.success == False
        assert "exit mode" in result.message.lower()
        
        # Invalid binding level
        result = orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=0.5,
            binding_level="INVALID"
        )
        assert result.success == False
        assert "binding level" in result.message.lower()
    
    def test_remove_strategy_level_exit_condition(self):
        """Test removing strategy-level exit condition"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Add then remove
        orchestrator.add_exit_condition(signal_name="BEARISH", percentage=0.3)
        
        result = orchestrator.remove_exit_condition(
            signal_name="BEARISH",
            binding_level="STRATEGY"
        )
        
        assert result.success == True
        assert "removed" in result.message.lower()
        
        # Verify removed
        config = orchestrator.get_current_config()
        assert len(config.exit_conditions) == 0
    
    def test_remove_block_level_exit_condition(self):
        """Test removing block-level exit condition"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        orchestrator.add_block("hod", "AND")
        
        # Add then remove
        orchestrator.add_exit_condition(
            signal_name="HOD_REJECTION",
            percentage=0.4,
            binding_level="BLOCK",
            block_name="hod"
        )
        
        result = orchestrator.remove_exit_condition(
            signal_name="HOD_REJECTION",
            binding_level="BLOCK",
            block_name="hod"
        )
        
        assert result.success == True
        
        # Verify removed
        config = orchestrator.get_current_config()
        assert len(config.blocks[0].exit_conditions) == 0
    
    def test_configure_exit_condition(self):
        """Test configuring exit condition settings"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Add exit condition
        orchestrator.add_exit_condition(
            signal_name="BEARISH",
            percentage=0.3,
            exit_mode="ABSOLUTE"
        )
        
        # Configure (update percentage and mode)
        result = orchestrator.configure_exit_condition(
            signal_name="BEARISH",
            binding_level="STRATEGY",
            percentage=0.5,
            exit_mode="FLEXIBLE",
            tp_proximity_threshold=3.0
        )
        
        assert result.success == True
        assert "updated" in result.message.lower()
        
        # Verify updates
        config = orchestrator.get_current_config()
        ec = config.exit_conditions[0]
        assert ec.percentage == 0.5
        assert ec.exit_mode == "FLEXIBLE"
        assert ec.tp_proximity_threshold == 3.0
    
    def test_remove_nonexistent_exit_condition(self):
        """Test removing exit condition that doesn't exist"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Try to remove nonexistent
        result = orchestrator.remove_exit_condition(
            signal_name="NONEXISTENT",
            binding_level="STRATEGY"
        )
        
        assert result.success == False
        assert "not found" in result.message.lower()
    
    def test_configure_nonexistent_exit_condition(self):
        """Test configuring exit condition that doesn't exist"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Try to configure nonexistent
        result = orchestrator.configure_exit_condition(
            signal_name="NONEXISTENT",
            binding_level="STRATEGY",
            percentage=0.5
        )
        
        assert result.success == False
        assert "not found" in result.message.lower()
    
    def test_add_multiple_exit_conditions(self):
        """Test adding multiple exit conditions at same level"""
        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.create_strategy("Test Strategy")
        
        # Add multiple
        orchestrator.add_exit_condition(signal_name="BEARISH", percentage=0.3)
        orchestrator.add_exit_condition(signal_name="HOD_REJECTION", percentage=0.25)
        orchestrator.add_exit_condition(signal_name="BELOW_HOD", percentage=0.15)
        
        # Verify all added
        config = orchestrator.get_current_config()
        assert len(config.exit_conditions) == 3
        assert config.exit_conditions[0].signal_name == "BEARISH"
        assert config.exit_conditions[1].signal_name == "HOD_REJECTION"
        assert config.exit_conditions[2].signal_name == "BELOW_HOD"
