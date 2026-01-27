"""
Unit tests for Exit Condition Validation
Tests ExitConditionValidator class
Sprint 1.8 Task 1.8.36
"""

import pytest
from src.strategy_builder.validation.strategy_validator import (
    ExitConditionValidator,
    StrategyValidator
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    ExitCondition
)


class TestExitConditionValidator:
    """Test exit condition validation rules"""
    
    def test_valid_exit_conditions(self):
        """Test validation passes for valid exit conditions"""
        # Create valid config with exit conditions
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[
                BlockConfig(
                    name="test_block",
                    logic="AND",
                    signals=[SignalConfig(name="SIGNAL1", logic="AND")]
                )
            ]
        )
        
        # Add valid exit condition
        config.exit_conditions = [
            ExitCondition(
                signal_name="EXIT_SIGNAL",
                percentage=0.5,
                exit_mode="ABSOLUTE",
                binding_level="STRATEGY"
            )
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) == 0
    
    def test_percentage_too_low(self):
        """Test validation fails for percentage <= 0"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=0.0, exit_mode="ABSOLUTE")
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("invalid percentage" in e.lower() for e in errors)
    
    def test_percentage_too_high(self):
        """Test validation fails for percentage > 1.0"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=1.5, exit_mode="ABSOLUTE")
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("invalid percentage" in e.lower() for e in errors)
    
    def test_total_percentage_exceeds_100(self):
        """Test validation fails when total percentage > 100%"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        # Add multiple exit conditions totaling > 100%
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=0.6, exit_mode="ABSOLUTE"),
            ExitCondition(signal_name="EXIT2", percentage=0.5, exit_mode="ABSOLUTE")
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("total" in e.lower() and "110" in e for e in errors)
    
    def test_invalid_exit_mode(self):
        """Test validation fails for invalid exit mode"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=0.5, exit_mode="INVALID_MODE")
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("exit_mode" in e.lower() for e in errors)
    
    def test_invalid_binding_level(self):
        """Test validation fails for invalid binding level"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        exit_cond = ExitCondition(signal_name="EXIT1", percentage=0.5, exit_mode="ABSOLUTE")
        exit_cond.binding_level = "INVALID_LEVEL"
        config.exit_conditions = [exit_cond]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("binding_level" in e.lower() for e in errors)
    
    def test_flexible_mode_invalid_threshold(self):
        """Test validation fails for FLEXIBLE mode with invalid threshold"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        config.exit_conditions = [
            ExitCondition(
                signal_name="EXIT1",
                percentage=0.5,
                exit_mode="FLEXIBLE",
                tp_proximity_threshold=-1.0  # Invalid
            )
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("tp_proximity_threshold" in e.lower() for e in errors)
    
    def test_flexible_mode_invalid_reversal(self):
        """Test validation fails for FLEXIBLE mode with invalid reversal trigger"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        config.exit_conditions = [
            ExitCondition(
                signal_name="EXIT1",
                percentage=0.5,
                exit_mode="FLEXIBLE",
                reversal_trigger=0.0  # Invalid
            )
        ]
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("reversal_trigger" in e.lower() for e in errors)
    
    def test_block_level_exit_validation(self):
        """Test validation of block-level exit conditions"""
        block = BlockConfig(
            name="test_block",
            logic="AND",
            signals=[SignalConfig(name="S1", logic="AND")]
        )
        
        # Add exit conditions exceeding 100%
        block.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=0.7, exit_mode="ABSOLUTE"),
            ExitCondition(signal_name="EXIT2", percentage=0.4, exit_mode="ABSOLUTE")
        ]
        
        config = StrategyConfig(name="Test", blocks=[block])
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("test_block" in e and "110" in e for e in errors)
    
    def test_signal_level_exit_validation(self):
        """Test validation of signal-level exit conditions"""
        signal = SignalConfig(name="S1", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=0.6, exit_mode="ABSOLUTE"),
            ExitCondition(signal_name="EXIT2", percentage=0.5, exit_mode="ABSOLUTE")
        ]
        
        block = BlockConfig(name="test_block", logic="AND", signals=[signal])
        config = StrategyConfig(name="Test", blocks=[block])
        
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("S1" in e and "110" in e for e in errors)
    
    def test_integration_with_strategy_validator(self):
        """Test exit condition validation integrates with main validator"""
        validator = StrategyValidator()
        
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[BlockConfig(name="test", logic="AND", signals=[SignalConfig(name="S1", logic="AND")])]
        )
        
        # Add invalid exit condition
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT1", percentage=1.5, exit_mode="ABSOLUTE")
        ]
        
        result = validator.validate(config)
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert any("exit" in e.lower() for e in result.errors)
    
    def test_multiple_levels_validation(self):
        """Test validation across multiple binding levels"""
        signal = SignalConfig(name="S1", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="EXIT_S", percentage=0.3, exit_mode="ABSOLUTE")
        ]
        
        block = BlockConfig(name="test_block", logic="AND", signals=[signal])
        block.exit_conditions = [
            ExitCondition(signal_name="EXIT_B", percentage=0.4, exit_mode="ABSOLUTE")
        ]
        
        config = StrategyConfig(name="Test", blocks=[block])
        config.exit_conditions = [
            ExitCondition(signal_name="EXIT_ST", percentage=0.5, exit_mode="ABSOLUTE")
        ]
        
        # All percentages valid individually
        errors = ExitConditionValidator.validate_exit_conditions(config)
        assert len(errors) == 0
