"""
Unit tests for Exit Condition data structures
Tests ExitCondition, DeferredExit, and validation
Sprint 1.8 Task 1.8.7
"""

import pytest
from src.strategy_builder.core.strategy_config_engine import (
    ExitCondition,
    DeferredExit,
    RecheckConfig,
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    ConfigValidators
)


class TestExitConditionDataclass:
    """Test ExitCondition dataclass creation and attributes"""
    
    def test_exit_condition_creation_minimal(self):
        """Test ExitCondition with minimal required parameters"""
        exit_cond = ExitCondition(signal_name="HOD_REJECTION")
        
        assert exit_cond.signal_name == "HOD_REJECTION"
        assert exit_cond.percentage == 0.5
        assert exit_cond.exit_mode == "ABSOLUTE"
        assert exit_cond.tp_proximity_threshold == 2.0
        assert exit_cond.reversal_trigger == 0.5
        assert exit_cond.recheck_config is None
        assert exit_cond.recheck_chain == []
        assert exit_cond.parent_signal is None
        assert exit_cond.binding_level == "STRATEGY"
    
    def test_exit_condition_creation_full(self):
        """Test ExitCondition with all parameters"""
        recheck = RecheckConfig(
            enabled=True,
            bar_delay=10,
            parent_signal="AT_HOD",
            validation_mode="SIGNAL"
        )
        
        exit_cond = ExitCondition(
            signal_name="BEARISH_BREAKDOWN",
            percentage=0.35,
            exit_mode="FLEXIBLE",
            tp_proximity_threshold=3.0,
            reversal_trigger=0.8,
            recheck_config=recheck,
            recheck_chain=[recheck],
            parent_signal="PATTERN_FORMING",
            binding_level="BLOCK"
        )
        
        assert exit_cond.signal_name == "BEARISH_BREAKDOWN"
        assert exit_cond.percentage == 0.35
        assert exit_cond.exit_mode == "FLEXIBLE"
        assert exit_cond.tp_proximity_threshold == 3.0
        assert exit_cond.reversal_trigger == 0.8
        assert exit_cond.recheck_config == recheck
        assert len(exit_cond.recheck_chain) == 1
        assert exit_cond.parent_signal == "PATTERN_FORMING"
        assert exit_cond.binding_level == "BLOCK"
    
    def test_exit_condition_with_nested_recheck(self):
        """Test ExitCondition with nested RECHECK chain"""
        recheck1 = RecheckConfig(enabled=True, bar_delay=5, validation_mode="SIGNAL")
        recheck2 = RecheckConfig(enabled=True, bar_delay=3, validation_mode="RECHECK")
        
        exit_cond = ExitCondition(
            signal_name="BELOW_HOD",
            percentage=0.25,
            recheck_chain=[recheck1, recheck2]
        )
        
        assert len(exit_cond.recheck_chain) == 2
        assert exit_cond.recheck_chain[0].bar_delay == 5
        assert exit_cond.recheck_chain[1].bar_delay == 3


class TestDeferredExitDataclass:
    """Test DeferredExit dataclass for FLEXIBLE mode tracking"""
    
    def test_deferred_exit_creation(self):
        """Test DeferredExit with position tracking data"""
        exit_cond = ExitCondition(
            signal_name="BEARISH",
            percentage=0.4,
            exit_mode="FLEXIBLE"
        )
        
        deferred = DeferredExit(
            exit_condition=exit_cond,
            position_id="pos_12345",
            trigger_bar=25,
            trigger_price=45250.0,
            nearest_tp=45500.0,
            nearest_tp_name="TP1",
            peak_price_toward_tp=45300.0
        )
        
        assert deferred.exit_condition == exit_cond
        assert deferred.position_id == "pos_12345"
        assert deferred.trigger_bar == 25
        assert deferred.trigger_price == 45250.0
        assert deferred.nearest_tp == 45500.0
        assert deferred.nearest_tp_name == "TP1"
        assert deferred.peak_price_toward_tp == 45300.0


class TestExitConditionValidation:
    """Test exit condition validation rules"""
    
    def test_validate_exit_conditions_empty_strategy(self):
        """Test validation with no exit conditions"""
        config = StrategyConfig()
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) == 0
    
    def test_validate_strategy_level_percentage_within_limit(self):
        """Test strategy-level exit conditions under 100%"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.3),
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.25)
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) == 0
    
    def test_validate_strategy_level_percentage_exceeds_limit(self):
        """Test strategy-level exit conditions exceeding 100%"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.6),
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.5)
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("exceeds 100%" in error for error in errors)
    
    def test_validate_block_level_percentage_exceeds_limit(self):
        """Test block-level exit conditions exceeding 100%"""
        config = StrategyConfig()
        block = BlockConfig(name="hod", logic="AND")
        block.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.7),
            ExitCondition(signal_name="BELOW_HOD", percentage=0.4)
        ]
        config.blocks = [block]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("hod" in error and "exceeds 100%" in error for error in errors)
    
    def test_validate_signal_level_percentage_exceeds_limit(self):
        """Test signal-level exit conditions exceeding 100%"""
        config = StrategyConfig()
        signal = SignalConfig(name="AT_HOD", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="BELOW_HOD", percentage=0.8),
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.3)
        ]
        block = BlockConfig(name="hod", logic="AND", signals=[signal])
        config.blocks = [block]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("AT_HOD" in error and "exceeds 100%" in error for error in errors)
    
    def test_validate_invalid_percentage_zero(self):
        """Test exit condition with 0% (invalid)"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.0)
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("invalid percentage" in error for error in errors)
    
    def test_validate_invalid_percentage_negative(self):
        """Test exit condition with negative percentage (invalid)"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=-0.1)
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("invalid percentage" in error for error in errors)
    
    def test_validate_invalid_percentage_over_100(self):
        """Test exit condition with percentage > 100% (invalid)"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=1.5)
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("invalid percentage" in error for error in errors)
    
    def test_validate_invalid_exit_mode(self):
        """Test exit condition with invalid exit_mode"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", exit_mode="INVALID_MODE")
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("invalid exit_mode" in error for error in errors)
    
    def test_validate_invalid_binding_level(self):
        """Test exit condition with invalid binding_level"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", binding_level="INVALID_LEVEL")
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        assert len(errors) > 0
        assert any("invalid binding_level" in error for error in errors)
    
    def test_validate_valid_exit_modes(self):
        """Test both valid exit modes: ABSOLUTE and FLEXIBLE"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.3, exit_mode="ABSOLUTE"),
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.2, exit_mode="FLEXIBLE")
        ]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        # Should have no errors related to exit_mode
        mode_errors = [e for e in errors if "exit_mode" in e]
        assert len(mode_errors) == 0
    
    def test_validate_valid_binding_levels(self):
        """Test all three valid binding levels"""
        config = StrategyConfig()
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.2, binding_level="STRATEGY")
        ]
        
        signal = SignalConfig(name="AT_HOD", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="BELOW_HOD", percentage=0.15, binding_level="SIGNAL")
        ]
        
        block = BlockConfig(name="hod", logic="AND", signals=[signal])
        block.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.25, binding_level="BLOCK")
        ]
        
        config.blocks = [block]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        # Should have no errors related to binding_level
        binding_errors = [e for e in errors if "binding_level" in e]
        assert len(binding_errors) == 0
    
    def test_validate_complex_multi_level_exits(self):
        """Test complex scenario with exits at all three levels"""
        config = StrategyConfig()
        
        # Strategy-level exits: 30% + 20% = 50% ✓
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.3),
            ExitCondition(signal_name="BEARISH_BREAKDOWN", percentage=0.2)
        ]
        
        # Block-level exits: 40% ✓
        signal1 = SignalConfig(name="AT_HOD", logic="AND")
        signal1.exit_conditions = [
            ExitCondition(signal_name="BELOW_HOD", percentage=0.2, binding_level="SIGNAL")
        ]
        
        signal2 = SignalConfig(name="ABOVE_HOD", logic="OR")
        signal2.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.15, binding_level="SIGNAL")
        ]
        
        block1 = BlockConfig(name="hod", logic="AND", signals=[signal1, signal2])
        block1.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.4, binding_level="BLOCK")
        ]
        
        block2 = BlockConfig(name="double_top", logic="OR")
        block2.exit_conditions = [
            ExitCondition(signal_name="BEARISH_BREAKDOWN", percentage=0.5, binding_level="BLOCK")
        ]
        
        config.blocks = [block1, block2]
        
        errors = ConfigValidators.validate_exit_conditions(config)
        
        # All percentages are within limits at each level
        if errors:
            # Print for debugging
            for error in errors:
                print(f"Validation error: {error}")
        
        assert len(errors) == 0


class TestExitConditionIntegration:
    """Integration tests for exit conditions in strategy config"""
    
    def test_strategy_config_with_exit_conditions(self):
        """Test StrategyConfig with exit_conditions field"""
        config = StrategyConfig()
        
        assert hasattr(config, 'exit_conditions')
        assert config.exit_conditions == []
        
        # Add exit conditions
        config.exit_conditions.append(
            ExitCondition(signal_name="BEARISH", percentage=0.5)
        )
        
        assert len(config.exit_conditions) == 1
        assert config.exit_conditions[0].signal_name == "BEARISH"
    
    def test_block_config_with_exit_conditions(self):
        """Test BlockConfig with exit_conditions field"""
        block = BlockConfig(name="hod", logic="AND")
        
        assert hasattr(block, 'exit_conditions')
        assert block.exit_conditions == []
        
        # Add exit conditions
        block.exit_conditions.append(
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.3)
        )
        
        assert len(block.exit_conditions) == 1
        assert block.exit_conditions[0].signal_name == "HOD_REJECTION"
    
    def test_signal_config_with_exit_conditions(self):
        """Test SignalConfig with exit_conditions field"""
        signal = SignalConfig(name="AT_HOD", logic="AND")
        
        assert hasattr(signal, 'exit_conditions')
        assert signal.exit_conditions == []
        
        # Add exit conditions
        signal.exit_conditions.append(
            ExitCondition(signal_name="BELOW_HOD", percentage=0.25)
        )
        
        assert len(signal.exit_conditions) == 1
        assert signal.exit_conditions[0].signal_name == "BELOW_HOD"
