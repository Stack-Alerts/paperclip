"""
Test Strategy Builder Data Models

Tests all Pydantic models for correctness.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest
from pydantic import ValidationError

from src.utils.Strategy_Builder.models import (
    SignalRole,
    BlockType,
    StrategyCategory,
    TestType,
    SignalConfiguration,
    BlockSelection,
    StrategyConfiguration,
    ValidationResult,
    BlockInfo,
    SignalInfo,
    StrategyMetadata,
    QuickTestResult
)


class TestEnums:
    """Test enum definitions"""
    
    def test_signal_role_enum(self):
        """Test SignalRole enum"""
        assert SignalRole.FILTER == "FILTER"
        assert SignalRole.SIGNAL == "SIGNAL"
        assert SignalRole.BOOSTER == "BOOSTER"
        assert SignalRole.TEST_ALL == "TEST_ALL"
    
    def test_block_type_enum(self):
        """Test BlockType enum"""
        assert BlockType.EVENT == "EVENT"
        assert BlockType.SIGNAL == "SIGNAL"
        assert BlockType.CONTEXT == "CONTEXT"
        assert BlockType.HYBRID == "HYBRID"
    
    def test_strategy_category_enum(self):
        """Test StrategyCategory enum"""
        assert StrategyCategory.REVERSAL == "REVERSAL"
        assert StrategyCategory.CONTINUATION == "CONTINUATION"


class TestSignalConfiguration:
    """Test SignalConfiguration model"""
    
    def test_valid_signal_config(self):
        """Test creating valid signal configuration"""
        config = SignalConfiguration(
            signal_name="BEARISH_BREAKDOWN",
            signal_display_name="Bearish Breakdown",
            role=SignalRole.SIGNAL
        )
        assert config.signal_name == "BEARISH_BREAKDOWN"
        assert config.role == "SIGNAL"
        assert config.required is True
        assert config.min_confidence == 0.0
    
    def test_signal_config_with_confidence(self):
        """Test signal config with custom confidence"""
        config = SignalConfiguration(
            signal_name="HOD_REJECTION",
            signal_display_name="HOD Rejection",
            role=SignalRole.BOOSTER,
            min_confidence=75.0
        )
        assert config.min_confidence == 75.0
    
    def test_invalid_confidence(self):
        """Test invalid confidence value"""
        with pytest.raises(ValidationError):
            SignalConfiguration(
                signal_name="TEST",
                signal_display_name="Test",
                role=SignalRole.SIGNAL,
                min_confidence=150.0  # Invalid: >100
            )


class TestBlockSelection:
    """Test BlockSelection model"""
    
    def test_valid_block_selection(self):
        """Test creating valid block selection"""
        block = BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=30,
            weight_range=(20, 35)
        )
        assert block.block_name == "double_top"
        assert block.weight == 30
        assert block.enabled is True
    
    def test_weight_validation(self):
        """Test weight range validation"""
        with pytest.raises(ValidationError):
            BlockSelection(
                block_name="test",
                block_display_name="Test",
                block_category="TEST",
                block_type=BlockType.EVENT,
                weight=50,  # Out of range
                weight_range=(20, 35)
            )
    
    def test_invalid_weight_range(self):
        """Test invalid weight range"""
        with pytest.raises(ValidationError):
            BlockSelection(
                block_name="test",
                block_display_name="Test",
                block_category="TEST",
                block_type=BlockType.EVENT,
                weight=30,
                weight_range=(35, 20)  # Invalid: min > max
            )


class TestStrategyConfiguration:
    """Test StrategyConfiguration model"""
    
    def test_valid_strategy_config(self):
        """Test creating valid strategy configuration"""
        config = StrategyConfiguration(
            strategy_name="test_strategy",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="double_top",
            blocks=[
                BlockSelection(
                    block_name="double_top",
                    block_display_name="Double Top",
                    block_category="PATTERNS",
                    block_type=BlockType.EVENT,
                    weight=30,
                    weight_range=(20, 35),
                    is_main_signal=True
                )
            ]
        )
        assert config.strategy_number == 1
        assert config.strategy_name == "strategy_01_test_strategy"  # Auto-fixed
        assert config.main_signal_block == "double_top"
        assert len(config.blocks) == 1
        assert config.created_date is not None
        assert config.modified_date is not None
    
    def test_strategy_name_auto_fix(self):
        """Test strategy name auto-fixing"""
        config = StrategyConfiguration(
            strategy_name="my_strategy",
            strategy_number=5,
            strategy_category=StrategyCategory.SCALPING,
            main_signal_block="test",
            blocks=[
                BlockSelection(
                    block_name="test",
                    block_display_name="Test",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(15, 25),
                    is_main_signal=True
                )
            ]
        )
        assert config.strategy_name == "strategy_05_my_strategy"
    
    def test_main_signal_validation(self):
        """Test main signal block validation"""
        with pytest.raises(ValidationError):
            StrategyConfiguration(
                strategy_name="test",
                strategy_number=1,
                strategy_category=StrategyCategory.REVERSAL,
                main_signal_block="missing_block",  # Not in blocks list
                blocks=[
                    BlockSelection(
                        block_name="other_block",
                        block_display_name="Other",
                        block_category="TEST",
                        block_type=BlockType.EVENT,
                        weight=20,
                        weight_range=(15, 25)
                    )
                ]
            )
    
    def test_risk_reward_validation(self):
        """Test risk:reward ratio validation"""
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="test",
            risk_reward_ratio="1:3",
            blocks=[
                BlockSelection(
                    block_name="test",
                    block_display_name="Test",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(15, 25),
                    is_main_signal=True
                )
            ]
        )
        assert config.risk_reward_ratio == "1:3"
        
        # Test invalid format
        with pytest.raises(ValidationError):
            StrategyConfiguration(
                strategy_name="test",
                strategy_number=1,
                strategy_category=StrategyCategory.REVERSAL,
                main_signal_block="test",
                risk_reward_ratio="invalid",  # Invalid format
                blocks=[
                    BlockSelection(
                        block_name="test",
                        block_display_name="Test",
                        block_category="TEST",
                        block_type=BlockType.EVENT,
                        weight=20,
                        weight_range=(15, 25),
                        is_main_signal=True
                    )
                ]
            )


class TestValidationResult:
    """Test ValidationResult model"""
    
    def test_valid_result(self):
        """Test valid validation result"""
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert "✅" in result.get_summary()
    
    def test_add_error(self):
        """Test adding errors"""
        result = ValidationResult()
        result.add_error("Test error")
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "❌" in result.get_summary()
    
    def test_add_warning(self):
        """Test adding warnings"""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "warning(s)" in result.get_summary()
    
    def test_add_suggestion(self):
        """Test adding suggestions"""
        result = ValidationResult()
        result.add_suggestion("Test suggestion")
        assert len(result.suggestions) == 1


class TestQuickTestResult:
    """Test QuickTestResult model"""
    
    def test_promising_result(self):
        """Test promising test result"""
        result = QuickTestResult(
            test_passed=True,
            test_type=TestType.LIGHT,
            test_days=30,
            total_trades=25,
            win_rate=68.0,
            net_pnl_pct=12.5,
            recommendation="PROMISING"
        )
        assert result.recommendation == "PROMISING"
        assert "✅" in result.get_summary()
        assert "promise" in result.get_summary()
    
    def test_needs_work_result(self):
        """Test needs work result"""
        result = QuickTestResult(
            test_passed=False,
            test_type=TestType.SINGLE,
            test_days=30,
            total_trades=8,
            win_rate=40.0,
            recommendation="NEEDS_WORK",
            issues=["Low trade count", "Poor win rate"]
        )
        assert result.recommendation == "NEEDS_WORK"
        assert "⚠️" in result.get_summary()
    
    def test_failed_result(self):
        """Test failed result"""
        result = QuickTestResult(
            test_passed=False,
            test_type=TestType.SINGLE,
            test_days=30,
            total_trades=2,
            win_rate=0.0,
            recommendation="FAILED",
            issues=["No profitable trades"]
        )
        assert result.recommendation == "FAILED"
        assert "❌" in result.get_summary()
    
    def test_invalid_recommendation(self):
        """Test invalid recommendation"""
        with pytest.raises(ValidationError):
            QuickTestResult(
                test_passed=True,
                test_type=TestType.SINGLE,
                test_days=30,
                recommendation="INVALID"  # Not in allowed values
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])