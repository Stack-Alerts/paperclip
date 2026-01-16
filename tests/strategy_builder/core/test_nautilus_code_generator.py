"""
Unit Tests for NautilusCodeGenerator
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/31_NAUTILUS_CODE_GENERATION.md
"""

import pytest
from src.strategy_builder.core.nautilus_code_generator import (
    NautilusCodeGenerator,
    GeneratedCode,
    CodeValidationResult
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint
)


class TestNautilusCodeGenerator:
    """Test suite for NautilusCodeGenerator"""
    
    def test_generator_initialization(self):
        """Test generator initializes correctly"""
        generator = NautilusCodeGenerator()
        assert generator is not None
        
    def test_generate_simple_strategy(self):
        """Test generating code for simple strategy"""
        generator = NautilusCodeGenerator()
        
        # Create simple config
        config = StrategyConfig()
        config.name = "SimpleStrategy"
        config.description = "Test strategy"
        
        block = BlockConfig(name="Double_Top", logic="AND", signals=[])
        signal = SignalConfig(name="BEARISH_BREAKDOWN", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        # Generate code
        result = generator.generate(config)
        assert result is not None
        assert isinstance(result, GeneratedCode)
        assert len(result.strategy_code) > 0
        
    def test_generated_code_has_imports(self):
        """Test generated code includes proper imports"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        # Check for required imports
        assert "from nautilus_trader.trading.strategy import Strategy" in code
        assert "from nautilus_trader.model" in code
        assert "from nautilus_trader.core" in code
        
    def test_generated_code_has_class_definition(self):
        """Test generated code has proper class definition"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config("MyStrategy")
        
        result = generator.generate(config)
        code = result.strategy_code
        
        assert "class MyStrategy(Strategy):" in code
        
    def test_generated_code_has_init_method(self):
        """Test generated code has __init__ method"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        assert "def __init__(self" in code
        assert "super().__init__" in code
        
    def test_generated_code_has_on_start(self):
        """Test generated code has on_start method"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        assert "def on_start(self)" in code
        
    def test_generated_code_has_on_bar(self):
        """Test generated code has on_bar method"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        assert "def on_bar(self, bar: Bar)" in code
        
    def test_generated_code_uses_proper_types(self):
        """Test generated code uses NautilusTrader types"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        # Should use proper types, not float
        assert "Quantity(" in code or "quantity" in code.lower()
        assert "Price(" in code or "price" in code.lower()
        
    def test_generated_code_uses_enums(self):
        """Test generated code uses enums, not strings"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        code = result.strategy_code
        
        # Should use OrderSide.BUY not "BUY"
        assert "OrderSide." in code or "order_side=" in code
        
    def test_validate_generated_code_syntax(self):
        """Test that generated code has valid Python syntax"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        validation = generator.validate_syntax(result.strategy_code)
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0
        
    def test_generate_with_multiple_blocks(self):
        """Test generating code with multiple building blocks"""
        generator = NautilusCodeGenerator()
        
        config = StrategyConfig()
        config.name = "MultiBlockStrategy"
        
        # Block 1
        block1 = BlockConfig(name="Double_Top", logic="AND", signals=[])
        block1.signals.append(SignalConfig(name="BEARISH_BREAKDOWN", logic="AND"))
        config.blocks.append(block1)
        
        # Block 2
        block2 = BlockConfig(name="Volume_Spike", logic="AND", signals=[])
        block2.signals.append(SignalConfig(name="HIGH_VOLUME", logic="AND"))
        config.blocks.append(block2)
        
        result = generator.generate(config)
        assert len(result.strategy_code) > 0
        
    def test_generate_with_timing_constraints(self):
        """Test generating code with timing constraints"""
        generator = NautilusCodeGenerator()
        
        config = StrategyConfig()
        config.name = "TimingStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        block.signals.append(signal1)
        
        constraint = TimingConstraint(max_candles=20, reference="SIGNAL1")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND", timing_constraint=constraint)
        block.signals.append(signal2)
        
        config.blocks.append(block)
        
        result = generator.generate(config)
        code = result.strategy_code
        
        # Should have timing validation logic
        assert "candle" in code.lower() or "bar" in code.lower()
        
    def test_generate_config_dict(self):
        """Test generating strategy config dictionary"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        
        result = generator.generate(config)
        config_dict = result.config_dict
        
        assert config_dict is not None
        assert "strategy_name" in config_dict or "instrument_id" in config_dict
        
    def test_generate_includes_docstrings(self):
        """Test generated code includes docstrings"""
        generator = NautilusCodeGenerator()
        config = self._create_test_config()
        config.description = "This is a test strategy"
        
        result = generator.generate(config)
        code = result.strategy_code
        
        assert '"""' in code or "'''" in code
        assert config.description in code
        
    # Helper method
    def _create_test_config(self, name="TestStrategy"):
        """Create a test configuration"""
        config = StrategyConfig()
        config.name = name
        config.description = "Test strategy for code generation"
        
        block = BlockConfig(name="Double_Top", logic="AND", signals=[])
        signal = SignalConfig(name="BEARISH_BREAKDOWN", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        return config


class TestGeneratedCode:
    """Test GeneratedCode data class"""
    
    def test_generated_code_creation(self):
        """Test creating GeneratedCode"""
        code = GeneratedCode(
            strategy_code="class MyStrategy(Strategy): pass",
            config_dict={"name": "MyStrategy"},
            file_name="my_strategy.py"
        )
        assert code.strategy_code is not None
        assert code.config_dict is not None
        assert code.file_name == "my_strategy.py"


class TestCodeValidationResult:
    """Test CodeValidationResult data class"""
    
    def test_validation_result_valid(self):
        """Test creating valid validation result"""
        result = CodeValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        assert result.is_valid is True
        assert len(result.errors) == 0
        
    def test_validation_result_with_errors(self):
        """Test creating validation result with errors"""
        result = CodeValidationResult(
            is_valid=False,
            errors=["Syntax error on line 10"],
            warnings=["Unused import"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestNautilusCodeGeneratorIntegration:
    """Integration tests for complete code generation"""
    
    def test_complete_strategy_generation_workflow(self):
        """Test complete workflow of generating strategy"""
        generator = NautilusCodeGenerator()
        
        # Create complex config
        config = StrategyConfig()
        config.name = "CompleteStrategy"
        config.description = "Complete test strategy with multiple features"
        
        # Add AND block
        block1 = BlockConfig(name="Double_Top", logic="AND", signals=[])
        block1.signals.append(SignalConfig(name="BEARISH_BREAKDOWN", logic="AND"))
        config.blocks.append(block1)
        
        # Add OR block (booster)
        block2 = BlockConfig(name="RSI", logic="OR", signals=[])
        block2.signals.append(SignalConfig(name="OVERBOUGHT", logic="OR"))
        config.blocks.append(block2)
        
        # Generate
        result = generator.generate(config)
        
        # Validate
        validation = generator.validate_syntax(result.strategy_code)
        assert validation.is_valid is True
        
        # Check structure
        assert "class CompleteStrategy(Strategy):" in result.strategy_code
        assert "def on_bar" in result.strategy_code
        assert len(result.config_dict) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
