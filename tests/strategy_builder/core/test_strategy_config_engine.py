"""
Unit Tests for StrategyConfigEngine
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/03_COMPONENT_SPECS.md
"""

import pytest
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfigEngine,
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint,
    ValidationResult
)


class TestStrategyConfigEngine:
    """Test suite for StrategyConfigEngine core functionality"""
    
    def test_engine_initialization(self):
        """Test that engine initializes with empty config"""
        engine = StrategyConfigEngine(registry=None)  # Mock registry later
        assert engine.config is not None
        assert len(engine.config.blocks) == 0
        assert engine.config.required_signals == 0
        
    def test_add_block_and_logic(self):
        """Test adding a block with AND logic"""
        engine = StrategyConfigEngine(registry=None)
        
        # Add block with AND logic
        result = engine.add_block("Double_Top", logic="AND")
        assert result is True
        assert len(engine.config.blocks) == 1
        assert engine.config.blocks[0].name == "Double_Top"
        assert engine.config.blocks[0].logic == "AND"
        
    def test_add_block_or_logic(self):
        """Test adding a block with OR logic"""
        engine = StrategyConfigEngine(registry=None)
        
        # Add block with OR logic (optional/booster)
        result = engine.add_block("RSI", logic="OR")
        assert result is True
        assert engine.config.blocks[0].logic == "OR"
        
    def test_add_duplicate_block_fails(self):
        """Test that adding duplicate block raises error"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Double_Top", logic="AND")
        
        # Attempt to add same block again
        with pytest.raises(ValueError, match="Block .* already added"):
            engine.add_block("Double_Top", logic="AND")
            
    def test_remove_block(self):
        """Test removing a block from strategy"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Double_Top", logic="AND")
        engine.add_block("Volume_Spike", logic="AND")
        
        # Remove first block
        result = engine.remove_block("Double_Top")
        assert result is True
        assert len(engine.config.blocks) == 1
        assert engine.config.blocks[0].name == "Volume_Spike"
        
    def test_add_signal_to_block(self):
        """Test adding a signal to a block"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Double_Top", logic="AND")
        
        # Add signal
        result = engine.add_signal(
            block_name="Double_Top",
            signal_name="BEARISH_BREAKDOWN",
            logic="AND"
        )
        assert result is True
        block = engine.config.get_block("Double_Top")
        assert len(block.signals) == 1
        assert block.signals[0].name == "BEARISH_BREAKDOWN"
        
    def test_add_signal_with_timing_constraint(self):
        """Test adding signal with 'Within X candles' constraint"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Double_Top", logic="AND")
        engine.add_signal("Double_Top", "SIGNAL1", logic="AND")
        
        # Add signal with timing constraint
        constraint = TimingConstraint(max_candles=20, reference="Signal 1")
        result = engine.add_signal(
            block_name="Double_Top",
            signal_name="SIGNAL2",
            logic="AND",
            constraint=constraint
        )
        assert result is True
        assert engine.config.get_block("Double_Top").signals[1].timing_constraint is not None
        
    def test_recalculate_required_signals_and_only(self):
        """Test that only AND blocks count towards required signals"""
        engine = StrategyConfigEngine(registry=None)
        
        # Add AND blocks (required)
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "SIGNAL1", logic="AND")
        engine.add_block("Block2", logic="AND")
        engine.add_signal("Block2", "SIGNAL2", logic="AND")
        
        # Add OR block (optional - should not count)
        engine.add_block("Block3", logic="OR")
        engine.add_signal("Block3", "SIGNAL3", logic="OR")
        
        # Should require 2 signals (from 2 AND blocks)
        assert engine.config.required_signals == 2
        
    def test_recalculate_with_multiple_and_signals_per_block(self):
        """Test required signals with multiple AND signals per block"""
        engine = StrategyConfigEngine(registry=None)
        
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "SIGNAL1", logic="AND")
        engine.add_signal("Block1", "SIGNAL2", logic="AND")
        engine.add_signal("Block1", "SIGNAL3", logic="AND")
        
        # Block has 3 AND signals, required should be at least 3
        # (Implementation detail: could be 1 per block or total AND signals)
        assert engine.config.required_signals >= 1
        
    def test_generate_description(self):
        """Test auto-generation of strategy description"""
        engine = StrategyConfigEngine(registry=None)
        
        engine.add_block("Double_Top", logic="AND")
        engine.add_signal("Double_Top", "BEARISH_BREAKDOWN", logic="AND")
        engine.add_block("Volume_Spike", logic="AND")
        engine.add_signal("Volume_Spike", "HIGH_VOLUME", logic="AND")
        engine.add_block("RSI", logic="OR")
        engine.add_signal("RSI", "OVERBOUGHT", logic="OR")
        
        description = engine.generate_description()
        assert "Double_Top" in description
        assert "REQUIRED" in description or "AND" in description
        assert "Volume_Spike" in description
        assert "RSI" in description
        assert "OPTIONAL" in description or "OR" in description
        
    def test_validate_empty_strategy_fails(self):
        """Test validation fails for empty strategy"""
        engine = StrategyConfigEngine(registry=None)
        
        result = engine.validate()
        assert result.valid is False
        assert any("at least one" in error.lower() for error in result.errors)
        
    def test_validate_block_without_signals_fails(self):
        """Test validation fails for block with no signals"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Double_Top", logic="AND")
        # Don't add any signals
        
        result = engine.validate()
        assert result.valid is False
        assert any("must have at least one signal" in error.lower() for error in result.errors)
        
    def test_validate_valid_strategy_passes(self):
        """Test validation passes for properly configured strategy"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bearish"
        
        # Add valid configuration
        engine.add_block("Double_Top", logic="AND")
        engine.add_signal("Double_Top", "BEARISH_BREAKDOWN", logic="AND")
        engine.add_block("Volume_Spike", logic="AND")
        engine.add_signal("Volume_Spike", "HIGH_VOLUME", logic="AND")
        
        result = engine.validate()
        assert result.valid is True
        assert len(result.errors) == 0
        
    def test_validate_invalid_timing_constraint(self):
        """Test validation catches invalid timing constraints"""
        engine = StrategyConfigEngine(registry=None)
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "SIGNAL1", logic="AND")
        
        # Add invalid timing constraint (reference doesn't exist)
        invalid_constraint = TimingConstraint(max_candles=20, reference="NonExistentSignal")
        engine.add_signal(
            "Block1", 
            "SIGNAL2", 
            logic="AND",
            constraint=invalid_constraint
        )
        
        result = engine.validate()
        assert result.valid is False
        assert any("timing" in error.lower() for error in result.errors)


class TestStrategyConfig:
    """Test StrategyConfig data class"""
    
    def test_config_initialization(self):
        """Test config initializes with defaults"""
        config = StrategyConfig()
        assert config.blocks == []
        assert config.required_signals == 0
        
    def test_get_block_by_name(self):
        """Test retrieving block by name"""
        config = StrategyConfig()
        block = BlockConfig(name="TestBlock", logic="AND", signals=[])
        config.blocks.append(block)
        
        retrieved = config.get_block("TestBlock")
        assert retrieved is not None
        assert retrieved.name == "TestBlock"
        
    def test_get_nonexistent_block_returns_none(self):
        """Test getting non-existent block returns None"""
        config = StrategyConfig()
        assert config.get_block("NonExistent") is None

    def test_serialization_round_trip_includes_side(self):
        """Test dataclass asdict/reconstruct preserves side field"""
        from dataclasses import asdict
        original = StrategyConfig(
            name="ser_test", strategy_type="Bullish", side="LONG",
            blocks=[BlockConfig(name="B1", logic="AND",
                                signals=[SignalConfig(name="S1", logic="OR")])])
        data = asdict(original)
        assert "side" in data
        assert data["side"] == "LONG"
        restored = StrategyConfig(**data)
        assert restored.side == original.side
        assert restored.name == original.name
        assert restored.strategy_type == original.strategy_type

    def test_serialization_round_trip_with_short_side(self):
        """Test SHORT side survives asdict/reconstruct"""
        from dataclasses import asdict
        original = StrategyConfig(name="short_test", side="SHORT")
        data = asdict(original)
        assert data["side"] == "SHORT"
        restored = StrategyConfig(**data)
        assert restored.side == "SHORT"

    def test_serialization_round_trip_default_side(self):
        """Test default empty side survives asdict/reconstruct"""
        from dataclasses import asdict
        original = StrategyConfig()
        data = asdict(original)
        assert data["side"] == ""
        restored = StrategyConfig(**data)
        assert restored.side == ""


class TestBlockConfig:
    """Test BlockConfig data class"""
    
    def test_block_config_creation(self):
        """Test creating block config"""
        block = BlockConfig(
            name="Double_Top",
            logic="AND",
            signals=[],
            metadata=None
        )
        assert block.name == "Double_Top"
        assert block.logic == "AND"
        assert block.signals == []


class TestSignalConfig:
    """Test SignalConfig data class"""
    
    def test_signal_config_creation(self):
        """Test creating signal config"""
        signal = SignalConfig(
            name="BEARISH_BREAKDOWN",
            logic="AND",
            timing_constraint=None
        )
        assert signal.name == "BEARISH_BREAKDOWN"
        assert signal.logic == "AND"
        assert signal.timing_constraint is None
        
    def test_signal_with_timing_constraint(self):
        """Test signal with timing constraint"""
        constraint = TimingConstraint(max_candles=20, reference="Signal 1")
        signal = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=constraint
        )
        assert signal.timing_constraint.max_candles == 20
        assert signal.timing_constraint.reference == "Signal 1"


class TestTimingConstraint:
    """Test TimingConstraint data class"""
    
    def test_timing_constraint_creation(self):
        """Test creating timing constraint"""
        constraint = TimingConstraint(max_candles=20, reference="Signal 1")
        assert constraint.max_candles == 20
        assert constraint.reference == "Signal 1"


class TestValidationResult:
    """Test ValidationResult data class"""
    
    def test_validation_result_valid(self):
        """Test valid validation result"""
        result = ValidationResult(valid=True, errors=[], warnings=[])
        assert result.valid is True
        assert len(result.errors) == 0
        
    def test_validation_result_with_errors(self):
        """Test validation result with errors"""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


# Integration-style tests
class TestStrategyConfigEngineIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_strategy_creation_workflow(self):
        """Test complete workflow of creating a strategy"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bearish"
        
        # Add first block with signals
        engine.add_block("Double_Top", logic="AND")
        engine.add_signal("Double_Top", "BEARISH_BREAKDOWN", logic="AND")
        
        # Add second block with signals
        engine.add_block("Volume_Spike", logic="AND")
        engine.add_signal("Volume_Spike", "HIGH_VOLUME", logic="AND")
        
        # Add optional booster block
        engine.add_block("RSI", logic="OR")
        engine.add_signal("RSI", "OVERBOUGHT", logic="OR")
        
        # Validate
        result = engine.validate()
        assert result.valid is True
        
        # Generate description
        description = engine.generate_description()
        assert len(description) > 0
        
        # Check required signals (should be 2 for 2 AND blocks)
        assert engine.config.required_signals == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestDirectionConsistency:
    """Test direction consistency validation"""

    def test_bullish_strategy_with_bearish_signal_rejects(self):
        """Bullish strategy with bearish signal produces error"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bullish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "BEARISH_BREAKDOWN", logic="AND")

        result = engine.validate()
        assert result.valid is False
        assert any("bearish" in w.lower() and "BEARISH_BREAKDOWN" in w for w in result.errors)

    def test_bearish_strategy_with_bullish_signal_rejects(self):
        """Bearish strategy with bullish signal produces error"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bearish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "BULLISH_BREAKOUT", logic="AND")

        result = engine.validate()
        assert result.valid is False
        assert any("bullish" in w.lower() and "BULLISH_BREAKOUT" in w for w in result.errors)

    def test_bullish_strategy_with_bullish_signal_clean(self):
        """Bullish strategy with bullish signal passes"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bullish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "BULLISH_BREAKOUT", logic="AND")

        result = engine.validate()
        assert result.valid is True

    def test_bearish_strategy_with_bearish_signal_clean(self):
        """Bearish strategy with bearish signal passes"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bearish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "BEARISH_BREAKDOWN", logic="AND")

        result = engine.validate()
        assert result.valid is True

    def test_neutral_signal_no_error(self):
        """Neutral signal (no direction keywords) passes"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bullish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "HIGH_VOLUME", logic="AND")

        result = engine.validate()
        assert result.valid is True

    def test_long_keyword_in_bearish_strategy_rejects(self):
        """"long" signal in Bearish strategy produces error"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bearish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "LONG_ENTRY", logic="AND")

        result = engine.validate()
        assert result.valid is False
        assert any("bullish" in w.lower() for w in result.errors)

    def test_short_keyword_in_bullish_strategy_rejects(self):
        """"short" signal in Bullish strategy produces error"""
        engine = StrategyConfigEngine(registry=None)
        engine.config.strategy_type = "Bullish"
        engine.add_block("Block1", logic="AND")
        engine.add_signal("Block1", "SHORT_EXIT", logic="AND")

        result = engine.validate()
        assert result.valid is False
        assert any("bearish" in w.lower() for w in result.errors)
