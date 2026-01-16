"""
Unit Tests for StrategyValidator
Advanced validation with NautilusTrader compatibility checks
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/22_STRATEGY_VALIDATOR.md
"""

import pytest

from src.strategy_builder.validation.strategy_validator import (
    StrategyValidator,
    ValidationResult,
    ValidationLevel,
    ValidationRule
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint
)


class TestStrategyValidator:
    """Test suite for StrategyValidator"""
    
    def test_validator_initialization(self):
        """Test validator initializes correctly"""
        validator = StrategyValidator()
        
        assert validator is not None
        assert len(validator.rules) > 0
        
    def test_validate_empty_strategy(self):
        """Test validation of empty strategy fails"""
        config = StrategyConfig()
        validator = StrategyValidator()
        
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        
    def test_validate_strategy_without_name(self):
        """Test strategy without name fails"""
        config = StrategyConfig()
        config.name = ""
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("name" in error.lower() for error in result.errors)
        
    def test_validate_strategy_without_blocks(self):
        """Test strategy without blocks fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        config.blocks = []
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("block" in error.lower() for error in result.errors)
        
    def test_validate_block_without_signals(self):
        """Test block without signals fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("signal" in error.lower() for error in result.errors)
        
    def test_validate_valid_strategy(self):
        """Test valid strategy passes"""
        config = self._create_valid_strategy()
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        
    def test_validate_invalid_block_logic(self):
        """Test invalid block logic fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="INVALID", signals=[])
        signal = SignalConfig(name="SIGNAL1", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("logic" in error.lower() for error in result.errors)
        
    def test_validate_invalid_signal_logic(self):
        """Test invalid signal logic fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal = SignalConfig(name="SIGNAL1", logic="INVALID")
        block.signals.append(signal)
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("logic" in error.lower() for error in result.errors)
        
    def test_validate_timing_constraint_without_reference(self):
        """Test timing constraint without reference fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal = SignalConfig(
            name="SIGNAL1",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="")
        )
        block.signals.append(signal)
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("reference" in error.lower() for error in result.errors)
        
    def test_validate_timing_constraint_invalid_max_candles(self):
        """Test timing constraint with invalid max_candles fails"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=0, reference="SIGNAL1")
        )
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("candle" in error.lower() for error in result.errors)
        
    def test_validate_nautilus_compatibility(self):
        """Test NautilusTrader compatibility validation"""
        config = self._create_valid_strategy()
        
        validator = StrategyValidator()
        result = validator.validate_nautilus_compatibility(config)
        
        assert result.is_valid is True
        
    def test_validate_warnings(self):
        """Test validator can produce warnings"""
        config = self._create_strategy_with_warnings()
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        # Strategy may be valid but have warnings
        assert len(result.warnings) > 0
        
    def test_validation_levels(self):
        """Test different validation levels"""
        config = self._create_valid_strategy()
        validator = StrategyValidator()
        
        # Basic validation
        result_basic = validator.validate(config, level=ValidationLevel.BASIC)
        assert result_basic.is_valid is True
        
        # Strict validation
        result_strict = validator.validate(config, level=ValidationLevel.STRICT)
        assert result_strict.is_valid is True
        
    def test_validate_circular_dependencies(self):
        """Test detection of circular dependencies"""
        config = self._create_strategy_with_circular_dependency()
        
        validator = StrategyValidator()
        result = validator.validate(config, level=ValidationLevel.STRICT)
        
        assert result.is_valid is False
        assert any("circular" in error.lower() for error in result.errors)
        
    def test_validate_duplicate_block_names(self):
        """Test detection of duplicate block names"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        block1.signals.append(SignalConfig(name="SIGNAL1", logic="AND"))
        
        block2 = BlockConfig(name="Block1", logic="AND", signals=[])  # Duplicate name
        block2.signals.append(SignalConfig(name="SIGNAL2", logic="AND"))
        
        config.blocks.extend([block1, block2])
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("duplicate" in error.lower() for error in result.errors)
        
    def test_validate_duplicate_signal_names(self):
        """Test detection of duplicate signal names in block"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(name="SIGNAL1", logic="AND")  # Duplicate name
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is False
        assert any("duplicate" in error.lower() for error in result.errors)
        
    # Helper methods
    def _create_valid_strategy(self):
        """Create a valid strategy for testing"""
        config = StrategyConfig()
        config.name = "ValidStrategy"
        config.description = "A valid test strategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND")
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        return config
        
    def _create_strategy_with_warnings(self):
        """Create strategy that generates warnings"""
        config = StrategyConfig()
        config.name = "WarningStrategy"
        
        # Create strategy with many blocks (performance warning)
        for i in range(20):
            block = BlockConfig(name=f"Block{i}", logic="AND", signals=[])
            signal = SignalConfig(name=f"SIGNAL{i}", logic="AND")
            block.signals.append(signal)
            config.blocks.append(block)
            
        return config
        
    def _create_strategy_with_circular_dependency(self):
        """Create strategy with circular timing dependencies"""
        config = StrategyConfig()
        config.name = "CircularStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        
        # Signal2 depends on Signal1
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="SIGNAL1")
        )
        # This would create circular if Signal1 also depended on Signal2
        # For now, just invalid reference
        signal1.timing_constraint = TimingConstraint(max_candles=20, reference="SIGNAL2")
        
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        return config


class TestValidationResult:
    """Test ValidationResult data class"""
    
    def test_validation_result_valid(self):
        """Test creating valid result"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        
    def test_validation_result_with_errors(self):
        """Test creating result with errors"""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=[]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        
    def test_validation_result_with_warnings(self):
        """Test creating result with warnings"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning 1"]
        )
        
        assert result.is_valid is True
        assert len(result.warnings) == 1


class TestValidationLevel:
    """Test ValidationLevel enum"""
    
    def test_validation_levels_exist(self):
        """Test validation level enums exist"""
        assert ValidationLevel.BASIC is not None
        assert ValidationLevel.STANDARD is not None
        assert ValidationLevel.STRICT is not None


class TestValidationRule:
    """Test ValidationRule data class"""
    
    def test_validation_rule_creation(self):
        """Test creating validation rule"""
        rule = ValidationRule(
            name="test_rule",
            description="Test rule description",
            level=ValidationLevel.STANDARD
        )
        
        assert rule.name == "test_rule"
        assert rule.description == "Test rule description"
        assert rule.level == ValidationLevel.STANDARD


class TestStrategyValidatorIntegration:
    """Integration tests for complete validation workflows"""
    
    def test_complete_validation_workflow(self):
        """Test complete validation from config to result"""
        # Create strategy
        config = StrategyConfig()
        config.name = "CompleteStrategy"
        config.description = "Complete validation test"
        
        # Add blocks
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="SIGNAL1")
        )
        block1.signals.extend([signal1, signal2])
        
        block2 = BlockConfig(name="Block2", logic="OR", signals=[])
        signal3 = SignalConfig(name="SIGNAL3", logic="OR")
        signal4 = SignalConfig(name="SIGNAL4", logic="OR")
        block2.signals.extend([signal3, signal4])
        
        config.blocks.extend([block1, block2])
        
        # Validate
        validator = StrategyValidator()
        result = validator.validate(config)
        
        assert result.is_valid is True
        assert isinstance(result, ValidationResult)
        
    def test_validation_with_all_rule_types(self):
        """Test validation exercising all rule types"""
        config = StrategyConfig()
        config.name = "AllRulesStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal = SignalConfig(name="SIGNAL1", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        validator = StrategyValidator()
        
        # Test all levels
        result_basic = validator.validate(config, ValidationLevel.BASIC)
        result_standard = validator.validate(config, ValidationLevel.STANDARD)
        result_strict = validator.validate(config, ValidationLevel.STRICT)
        
        assert result_basic.is_valid is True
        assert result_standard.is_valid is True
        assert result_strict.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
