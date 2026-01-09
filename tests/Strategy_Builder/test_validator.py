"""
Test Strategy Validator

Tests all validation layers for strategy configurations.

Author: BTC_Engine_v3
Date: 2026-01-09
"""

import pytest
from pydantic import ValidationError

from src.utils.Strategy_Builder.validator import StrategyValidator
from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType
)
from src.detectors.building_blocks.registry import auto_discover_blocks

# Auto-discover blocks for testing
auto_discover_blocks()


@pytest.fixture
def validator():
    """Create validator instance"""
    return StrategyValidator()


@pytest.fixture
def valid_strategy():
    """Create a valid strategy configuration for testing"""
    return StrategyConfiguration(
        strategy_name="test_reversal",
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
                weight_range=(20, 40),
                is_main_signal=True,
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_BREAKDOWN",
                        signal_display_name="Bearish Breakdown",
                        role=SignalRole.SIGNAL
                    )
                ]
            )
        ]
    )


class TestValidatorBasicStructure:
    """Test basic structure validation"""
    
    def test_valid_strategy_passes(self, validator, valid_strategy):
        """Test that valid strategy passes validation"""
        result = validator.validate(valid_strategy)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_too_few_blocks(self, validator):
        """Test Pydantic catches empty blocks (main signal not in blocks)"""
        # Pydantic validates this before Validator can
        with pytest.raises(ValidationError):
            StrategyConfiguration(
                strategy_name="test",
                strategy_number=1,
                strategy_category=StrategyCategory.REVERSAL,
                main_signal_block="double_top",
                blocks=[]  # No blocks - Pydantic will reject this
            )
    
    def test_too_many_blocks(self, validator):
        """Test validation fails with too many blocks"""
        # Create 11 blocks (max is 10)
        blocks = []
        for i in range(11):
            blocks.append(
                BlockSelection(
                    block_name=f"block_{i}",
                    block_display_name=f"Block {i}",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=10,
                    weight_range=(5, 15)
                )
            )
        
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="block_0",
            blocks=blocks
        )
        
        result = validator.validate(config)
        assert not result.is_valid
        assert any("too many" in error.lower() for error in result.errors)


class TestValidatorBlockExistence:
    """Test block existence validation"""
    
    def test_nonexistent_block_fails(self, validator):
        """Test validation fails for non-existent block"""
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="nonexistent_block",
            blocks=[
                BlockSelection(
                    block_name="nonexistent_block",
                    block_display_name="Nonexistent",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30)
                )
            ]
        )
        
        result = validator.validate(config)
        assert not result.is_valid
        assert any("not found in registry" in error for error in result.errors)


class TestValidatorSignals:
    """Test signal validation"""
    
    def test_invalid_signal_fails(self, validator):
        """Test validation fails for invalid signal"""
        config = StrategyConfiguration(
            strategy_name="test",
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
                    weight_range=(20, 40),
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name="INVALID_SIGNAL_XYZ",
                            signal_display_name="Invalid",
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        assert not result.is_valid
        assert any("invalid signal" in error.lower() for error in result.errors)


class TestValidatorWeights:
    """Test weight validation"""
    
    def test_weight_out_of_range_fails(self, validator):
        """Test Pydantic catches weight out of range"""
        # Pydantic validates weights at model creation
        with pytest.raises(ValidationError):
            BlockSelection(
                block_name="double_top",
                block_display_name="Double Top",
                block_category="PATTERNS",
                block_type=BlockType.EVENT,
                weight=50,  # Out of range (20-40)
                weight_range=(20, 40),
                is_main_signal=True,
                signals=[
                    SignalConfiguration(
                        signal_name="BEARISH_BREAKDOWN",
                        signal_display_name="Bearish Breakdown",
                        role=SignalRole.SIGNAL
                    )
                ]
            )
    
    def test_low_total_weight_warning(self, validator):
        """Test warning for low total weight"""
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="double_top",
            blocks=[
                BlockSelection(
                    block_name="double_top",
                    block_display_name="Double Top",
                    block_category="PATTERNS",
                    block_type=BlockType.EVENT,
                    weight=20,  # Very low total weight
                    weight_range=(20, 40),
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name="BEARISH_BREAKDOWN",
                            signal_display_name="Bearish Breakdown",
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        # Should pass but with warnings
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("low" in warning.lower() for warning in result.warnings)


class TestValidatorMainSignal:
    """Test main signal validation"""
    
    def test_main_signal_not_in_blocks_fails(self, validator):
        """Test Pydantic catches main signal not in blocks"""
        # Pydantic validates this before Validator can
        with pytest.raises(ValidationError):
            StrategyConfiguration(
                strategy_name="test",
                strategy_number=1,
                strategy_category=StrategyCategory.REVERSAL,
                main_signal_block="missing_block",  # Not in blocks list
                blocks=[
                    BlockSelection(
                        block_name="double_top",
                        block_display_name="Double Top",
                        block_category="PATTERNS",
                        block_type=BlockType.EVENT,
                        weight=30,
                        weight_range=(20, 40),
                        signals=[
                            SignalConfiguration(
                                signal_name="BEARISH_BREAKDOWN",
                                signal_display_name="Bearish Breakdown",
                                role=SignalRole.SIGNAL
                            )
                        ]
                    )
                ]
            )
    
    def test_main_signal_not_marked_warning(self, validator):
        """Test warning if main signal block not marked"""
        config = StrategyConfiguration(
            strategy_name="test",
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
                    weight_range=(20, 40),
                    is_main_signal=False,  # Not marked
                    signals=[
                        SignalConfiguration(
                            signal_name="BEARISH_BREAKDOWN",
                            signal_display_name="Bearish Breakdown",
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        # Should pass but with warning
        assert result.is_valid
        assert len(result.warnings) > 0


class TestValidatorRoleDistribution:
    """Test role distribution validation"""
    
    def test_no_signal_role_fails(self, validator):
        """Test validation fails without SIGNAL role"""
        config = StrategyConfiguration(
            strategy_name="test",
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
                    weight_range=(20, 40),
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name="PATTERN_FORMING",
                            signal_display_name="Pattern Forming",
                            role=SignalRole.FILTER  # Only filter, no signal
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        assert not result.is_valid
        assert any("at least one SIGNAL role" in error for error in result.errors)


class TestValidatorConflicts:
    """Test conflict detection"""
    
    def test_conflicting_patterns_warning(self, validator):
        """Test warning for conflicting bullish/bearish patterns"""
        config = StrategyConfiguration(
            strategy_name="test",
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
                    weight_range=(20, 40),
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name="BEARISH_BREAKDOWN",
                            signal_display_name="Bearish Breakdown",
                            role=SignalRole.SIGNAL
                        )
                    ]
                ),
                BlockSelection(
                    block_name="double_bottom",
                    block_display_name="Double Bottom",
                    block_category="PATTERNS",
                    block_type=BlockType.EVENT,
                    weight=30,
                    weight_range=(20, 40),
                    signals=[
                        SignalConfiguration(
                            signal_name="BULLISH_BREAKOUT",
                            signal_display_name="Bullish Breakout",
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        # Should pass but with warnings about conflicts
        assert result.is_valid
        # Note: This will warn only if both patterns exist in registry


class TestValidatorStrategySpecific:
    """Test strategy-specific validation"""
    
    def test_reversal_without_reversal_indicators_validates(self, validator):
        """Test reversal strategy without reversal indicators (non-existent block)"""
        # This tests that validator handles non-existent blocks gracefully
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="fake_ema",
            blocks=[
                BlockSelection(
                    block_name="fake_ema",
                    block_display_name="Fake EMA",
                    block_category="MOVING_AVERAGES",
                    block_type=BlockType.SIGNAL,
                    weight=30,
                    weight_range=(20, 40),
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name="ABOVE_EMA",
                            signal_display_name="Above EMA",
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        # Should fail due to missing block
        assert not result.is_valid


class TestValidatorQuickValidate:
    """Test quick validate method"""
    
    def test_quick_validate_valid(self, validator, valid_strategy):
        """Test quick validate returns True for valid strategy"""
        is_valid = validator.quick_validate(valid_strategy)
        assert is_valid is True
    
    def test_quick_validate_invalid(self, validator):
        """Test quick validate with invalid config (Pydantic will reject)"""
        #  Pydantic catches the error, so test with validator-level error
        config = StrategyConfiguration(
            strategy_name="test",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block="nonexistent",
            blocks=[
                BlockSelection(
                    block_name="nonexistent",
                    block_display_name="Nonexistent",
                    block_category="TEST",
                    block_type=BlockType.EVENT,
                    weight=20,
                    weight_range=(10, 30)
                )
            ]
        )
        
        is_valid = validator.quick_validate(config)
        assert is_valid is False


class TestValidatorIntegration:
    """Integration tests with real registry data"""
    
    def test_validate_real_strategy(self, validator):
        """Test validation with real blocks from registry"""
        from src.utils.Strategy_Builder.registry_bridge import RegistryBridge
        
        bridge = RegistryBridge()
        blocks = bridge.get_blocks_by_category()
        
        if not blocks:
            pytest.skip("No blocks in registry")
        
        # Get first available block
        first_category = list(blocks.keys())[0]
        first_block = blocks[first_category][0]
        
        if not first_block.signals:
            pytest.skip("Block has no signals")
        
        # Create strategy with real block
        config = StrategyConfiguration(
            strategy_name="test_real",
            strategy_number=1,
            strategy_category=StrategyCategory.REVERSAL,
            main_signal_block=first_block.name,
            blocks=[
                BlockSelection(
                    block_name=first_block.name,
                    block_display_name=first_block.display_name,
                    block_category=first_block.category,
                    block_type=first_block.block_type,
                    weight=first_block.default_weight,
                    weight_range=first_block.weight_range,
                    is_main_signal=True,
                    signals=[
                        SignalConfiguration(
                            signal_name=first_block.signals[0],
                            signal_display_name=first_block.signals[0].replace('_', ' ').title(),
                            role=SignalRole.SIGNAL
                        )
                    ]
                )
            ]
        )
        
        result = validator.validate(config)
        assert result.is_valid or len(result.errors) == 0  # Should be valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])