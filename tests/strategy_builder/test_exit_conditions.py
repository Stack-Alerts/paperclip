"""
Unit Tests for Exit Conditions
Sprint 1.8 - Tasks 1.8.87-1.8.88

Tests ExitCondition dataclass creation and validation.
"""

import pytest
from decimal import Decimal
from src.strategy_builder.core.strategy_config_engine import (
    ExitCondition,
    DeferredExit,
    RecheckConfig,
    StrategyConfig,
    BlockConfig,
    SignalConfig
)
from src.strategy_builder.validation.strategy_validator import ExitConditionValidator


class TestExitConditionCreation:
    """Test ExitCondition dataclass creation - Task 1.8.87"""
    
    def test_exit_condition_defaults(self):
        """Test ExitCondition with default values"""
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
    
    def test_exit_condition_absolute_mode(self):
        """Test ExitCondition in ABSOLUTE mode"""
        exit_cond = ExitCondition(
            signal_name="BEARISH_BREAKDOWN",
            percentage=0.3,
            exit_mode="ABSOLUTE",
            binding_level="BLOCK"
        )
        
        assert exit_cond.signal_name == "BEARISH_BREAKDOWN"
        assert exit_cond.percentage == 0.3
        assert exit_cond.exit_mode == "ABSOLUTE"
        assert exit_cond.binding_level == "BLOCK"
    
    def test_exit_condition_flexible_mode(self):
        """Test ExitCondition in FLEXIBLE mode with custom thresholds"""
        exit_cond = ExitCondition(
            signal_name="HOD_REJECTION",
            percentage=0.4,
            exit_mode="FLEXIBLE",
            tp_proximity_threshold=1.5,
            reversal_trigger=0.3,
            binding_level="SIGNAL",
            parent_signal="ABOVE_HOD"
        )
        
        assert exit_cond.signal_name == "HOD_REJECTION"
        assert exit_cond.percentage == 0.4
        assert exit_cond.exit_mode == "FLEXIBLE"
        assert exit_cond.tp_proximity_threshold == 1.5
        assert exit_cond.reversal_trigger == 0.3
        assert exit_cond.binding_level == "SIGNAL"
        assert exit_cond.parent_signal == "ABOVE_HOD"
    
    def test_exit_condition_with_recheck(self):
        """Test ExitCondition with RECHECK configuration"""
        recheck = RecheckConfig(
            bar_delay=10,
            must_still_be_true=True,
            signal_name="BEARISH_BREAKDOWN"
        )
        
        exit_cond = ExitCondition(
            signal_name="PATTERN_FORMING",
            percentage=0.25,
            recheck_config=recheck
        )
        
        assert exit_cond.recheck_config is not None
        assert exit_cond.recheck_config.bar_delay == 10
        assert exit_cond.recheck_config.must_still_be_true is True
        assert exit_cond.recheck_config.signal_name == "BEARISH_BREAKDOWN"
    
    def test_exit_condition_with_recheck_chain(self):
        """Test ExitCondition with nested RECHECK chain"""
        recheck1 = RecheckConfig(bar_delay=5, must_still_be_true=True, signal_name="HOD_REJECTION")
        recheck2 = RecheckConfig(bar_delay=3, must_still_be_true=True, signal_name="BELOW_HOD")
        
        exit_cond = ExitCondition(
            signal_name="BEARISH_BREAKDOWN",
            percentage=0.35,
            recheck_chain=[recheck1, recheck2]
        )
        
        assert len(exit_cond.recheck_chain) == 2
        assert exit_cond.recheck_chain[0].signal_name == "HOD_REJECTION"
        assert exit_cond.recheck_chain[1].signal_name == "BELOW_HOD"
    
    def test_deferred_exit_creation(self):
        """Test DeferredExit dataclass creation"""
        exit_cond = ExitCondition(signal_name="BELOW_HOD", percentage=0.3, exit_mode="FLEXIBLE")
        
        deferred = DeferredExit(
            exit_condition=exit_cond,
            position_id="pos_123",
            trigger_bar=20,
            trigger_price=45300.0,
            nearest_tp=45500.0,
            nearest_tp_name="TP1",
            peak_price_toward_tp=45450.0
        )
        
        assert deferred.exit_condition.signal_name == "BELOW_HOD"
        assert deferred.position_id == "pos_123"
        assert deferred.trigger_bar == 20
        assert deferred.trigger_price == 45300.0
        assert deferred.nearest_tp == 45500.0
        assert deferred.nearest_tp_name == "TP1"
        assert deferred.peak_price_toward_tp == 45450.0


class TestExitConditionValidation:
    """Test ExitCondition percentage validation - Task 1.8.88"""
    
    def test_valid_percentage_range(self):
        """Test valid percentage values (0 < pct <= 1.0)"""
        valid_percentages = [0.01, 0.25, 0.5, 0.75, 1.0]
        
        for pct in valid_percentages:
            exit_cond = ExitCondition(signal_name="HOD_REJECTION", percentage=pct)
            assert 0 < exit_cond.percentage <= 1.0
    
    def test_strategy_level_percentage_limit(self):
        """Test strategy-level exits cannot exceed 100%"""
        validator = ExitConditionValidator()
        
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.6, binding_level="STRATEGY"),
                ExitCondition(signal_name="BEARISH_BREAKDOWN", percentage=0.5, binding_level="STRATEGY")
            ]
        )
        
        errors = validator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("110.0%" in err or "exceed" in err.lower() for err in errors)
    
    def test_block_level_percentage_limit(self):
        """Test block-level exits cannot exceed 100%"""
        validator = ExitConditionValidator()
        
        block = BlockConfig(
            name="hod_block",
            signals=[],
            logic_type="AND",
            exit_conditions=[
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.7, binding_level="BLOCK"),
                ExitCondition(signal_name="BELOW_HOD", percentage=0.4, binding_level="BLOCK")
            ]
        )
        
        config = StrategyConfig(name="Test", blocks=[block])
        
        errors = validator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("110.0%" in err or "exceed" in err.lower() for err in errors)
    
    def test_signal_level_percentage_limit(self):
        """Test signal-level exits cannot exceed 100%"""
        validator = ExitConditionValidator()
        
        signal = SignalConfig(
            name="AT_HOD",
            exit_conditions=[
                ExitCondition(signal_name="BELOW_HOD", percentage=0.6, binding_level="SIGNAL", parent_signal="AT_HOD"),
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.5, binding_level="SIGNAL", parent_signal="AT_HOD")
            ]
        )
        
        block = BlockConfig(name="hod", signals=[signal], logic_type="AND")
        config = StrategyConfig(name="Test", blocks=[block])
        
        errors = validator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("110.0%" in err or "exceed" in err.lower() for err in errors)
    
    def test_valid_percentage_limits(self):
        """Test valid percentage configurations at all levels"""
        validator = ExitConditionValidator()
        
        signal = SignalConfig(
            name="AT_HOD",
            exit_conditions=[
                ExitCondition(signal_name="BELOW_HOD", percentage=0.2, binding_level="SIGNAL", parent_signal="AT_HOD")
            ]
        )
        
        block = BlockConfig(
            name="hod",
            signals=[signal],
            logic_type="AND",
            exit_conditions=[
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.4, binding_level="BLOCK")
            ]
        )
        
        config = StrategyConfig(
            name="Test",
            blocks=[block],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.3, binding_level="STRATEGY")
            ]
        )
        
        errors = validator.validate_exit_conditions(config)
        # Should have no percentage limit errors (20% + 40% + 30% < 100% at each level)
        assert not any("exceed" in err.lower() for err in errors)
    
    def test_zero_percentage_invalid(self):
        """Test that 0% is invalid"""
        validator = ExitConditionValidator()
        
        config = StrategyConfig(
            name="Test",
            blocks=[],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.0)
            ]
        )
        
        errors = validator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("percentage" in err.lower() and "0" in err for err in errors)
    
    def test_percentage_above_100_invalid(self):
        """Test that >100% is invalid for individual exit"""
        validator = ExitConditionValidator()
        
        config = StrategyConfig(
            name="Test",
            blocks=[],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=1.5)  # 150%
            ]
        )
        
        errors = validator.validate_exit_conditions(config)
        assert len(errors) > 0
        assert any("percentage" in err.lower() or "150" in err for err in errors)
    
    def test_multiple_binding_levels_independent(self):
        """Test that percentage limits are independent per binding level"""
        validator = ExitConditionValidator()
        
        # Each level at 90% (valid independently)
        signal = SignalConfig(
            name="AT_HOD",
            exit_conditions=[
                ExitCondition(signal_name="BELOW_HOD", percentage=0.9, binding_level="SIGNAL", parent_signal="AT_HOD")
            ]
        )
        
        block = BlockConfig(
            name="hod",
            signals=[signal],
            logic_type="AND",
            exit_conditions=[
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.9, binding_level="BLOCK")
            ]
        )
        
        config = StrategyConfig(
            name="Test",
            blocks=[block],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.9, binding_level="STRATEGY")
            ]
        )
        
        errors = validator.validate_exit_conditions(config)
        # Should be valid - each level is independent (90% at each is OK)
        assert not any("exceed" in err.lower() for err in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
