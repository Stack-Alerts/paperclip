"""
Unit Tests for StrategyPersistence
Save/load strategies to/from JSON and YAML files
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/23_STRATEGY_PERSISTENCE.md
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from src.strategy_builder.persistence.strategy_persistence import (
    StrategyPersistence,
    PersistenceFormat,
    PersistenceResult
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint
)


class TestStrategyPersistence:
    """Test suite for StrategyPersistence"""
    
    def test_persistence_initialization(self):
        """Test persistence manager initializes correctly"""
        persistence = StrategyPersistence()
        
        assert persistence is not None
        
    def test_save_strategy_to_json(self):
        """Test saving strategy to JSON file"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_strategy.json"
            result = persistence.save(config, filepath, PersistenceFormat.JSON)
            
            assert result.success is True
            assert filepath.exists()
            
    def test_load_strategy_from_json(self):
        """Test loading strategy from JSON file"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_strategy.json"
            
            # Save first
            persistence.save(config, filepath, PersistenceFormat.JSON)
            
            # Load back
            result = persistence.load(filepath)
            
            assert result.success is True
            assert result.config is not None
            assert result.config.name == config.name
            
    def test_save_strategy_to_yaml(self):
        """Test saving strategy to YAML file"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_strategy.yaml"
            result = persistence.save(config, filepath, PersistenceFormat.YAML)
            
            assert result.success is True
            assert filepath.exists()
            
    def test_load_strategy_from_yaml(self):
        """Test loading strategy from YAML file"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_strategy.yaml"
            
            # Save first
            persistence.save(config, filepath, PersistenceFormat.YAML)
            
            # Load back
            result = persistence.load(filepath)
            
            assert result.success is True
            assert result.config is not None
            assert result.config.name == config.name
            
    def test_auto_detect_format_json(self):
        """Test auto-detecting JSON format from file extension"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "strategy.json"
            
            # Save without specifying format
            result = persistence.save(config, filepath)
            
            assert result.success is True
            assert filepath.exists()
            
    def test_auto_detect_format_yaml(self):
        """Test auto-detecting YAML format from file extension"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "strategy.yaml"
            
            # Save without specifying format
            result = persistence.save(config, filepath)
            
            assert result.success is True
            assert filepath.exists()
            
    def test_save_preserves_timing_constraints(self):
        """Test timing constraints are preserved in save/load"""
        config = self._create_strategy_with_timing()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            
            # Save and load
            persistence.save(config, filepath)
            result = persistence.load(filepath)
            
            # Check timing constraint preserved
            loaded_config = result.config
            signal = loaded_config.blocks[0].signals[1]
            
            assert signal.timing_constraint is not None
            assert signal.timing_constraint.max_candles == 20
            assert signal.timing_constraint.reference == "SIGNAL1"
            
    def test_save_preserves_block_logic(self):
        """Test block logic (AND/OR) is preserved"""
        config = StrategyConfig()
        config.name = "LogicTest"
        
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        block1.signals.append(SignalConfig(name="S1", logic="AND"))
        
        block2 = BlockConfig(name="Block2", logic="OR", signals=[])
        block2.signals.append(SignalConfig(name="S2", logic="OR"))
        
        config.blocks.extend([block1, block2])
        
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)
            
            loaded = result.config
            assert loaded.blocks[0].logic == "AND"
            assert loaded.blocks[1].logic == "OR"
            
    def test_load_nonexistent_file_fails(self):
        """Test loading non-existent file fails gracefully"""
        persistence = StrategyPersistence()
        
        filepath = Path("/nonexistent/path/strategy.json")
        result = persistence.load(filepath)
        
        assert result.success is False
        assert len(result.errors) > 0
        
    def test_save_invalid_path_fails(self):
        """Test saving to invalid path fails gracefully"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        filepath = Path("/invalid/path/strategy.json")
        result = persistence.save(config, filepath)
        
        assert result.success is False
        assert len(result.errors) > 0
        
    def test_load_corrupted_json_fails(self):
        """Test loading corrupted JSON fails gracefully"""
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "corrupted.json"
            
            # Write invalid JSON
            with open(filepath, 'w') as f:
                f.write("{invalid json content")
                
            result = persistence.load(filepath)
            
            assert result.success is False
            assert len(result.errors) > 0
            
    def test_version_compatibility(self):
        """Test version information is saved and checked"""
        config = self._create_test_strategy()
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            
            persistence.save(config, filepath)
            
            # Check version in file
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            assert 'version' in data
            assert data['version'] is not None
            
    def test_metadata_preservation(self):
        """Test metadata (description, etc.) is preserved"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        config.description = "This is a test description"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)
        
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)
            
            assert result.config.description == config.description
            
    # Helper methods
    def _create_test_strategy(self):
        """Create simple test strategy"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        config.description = "Test strategy for persistence"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND")
        
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        return config
        
    def _create_strategy_with_timing(self):
        """Create strategy with timing constraints"""
        config = StrategyConfig()
        config.name = "TimingStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="SIGNAL1")
        )
        
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        return config


class TestPersistenceFormat:
    """Test PersistenceFormat enum"""
    
    def test_format_enums_exist(self):
        """Test format enums exist"""
        assert PersistenceFormat.JSON is not None
        assert PersistenceFormat.YAML is not None


class TestPersistenceResult:
    """Test PersistenceResult dataclass"""
    
    def test_result_success(self):
        """Test creating successful result"""
        config = StrategyConfig()
        config.name = "Test"
        
        result = PersistenceResult(
            success=True,
            config=config,
            errors=[]
        )
        
        assert result.success is True
        assert result.config == config
        assert len(result.errors) == 0
        
    def test_result_failure(self):
        """Test creating failure result"""
        result = PersistenceResult(
            success=False,
            config=None,
            errors=["Error 1", "Error 2"]
        )
        
        assert result.success is False
        assert result.config is None
        assert len(result.errors) == 2


class TestStrategyPersistenceIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_save_load_cycle(self):
        """Test complete save and load cycle"""
        # Create complex strategy
        config = StrategyConfig()
        config.name = "CompleteStrategy"
        config.description = "Full integration test"
        
        # Block 1
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="SIGNAL1")
        )
        block1.signals.extend([signal1, signal2])
        
        # Block 2
        block2 = BlockConfig(name="Block2", logic="OR", signals=[])
        signal3 = SignalConfig(name="SIGNAL3", logic="OR")
        signal4 = SignalConfig(name="SIGNAL4", logic="OR")
        block2.signals.extend([signal3, signal4])
        
        config.blocks.extend([block1, block2])
        
        # Save and load
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "complete.json"
            
            # Save
            save_result = persistence.save(config, filepath)
            assert save_result.success is True
            
            # Load
            load_result = persistence.load(filepath)
            assert load_result.success is True
            
            # Verify all details preserved
            loaded = load_result.config
            assert loaded.name == config.name
            assert loaded.description == config.description
            assert len(loaded.blocks) == 2
            assert loaded.blocks[0].name == "Block1"
            assert loaded.blocks[1].name == "Block2"
            assert loaded.blocks[0].logic == "AND"
            assert loaded.blocks[1].logic == "OR"
            assert len(loaded.blocks[0].signals) == 2
            assert len(loaded.blocks[1].signals) == 2
            
    def test_json_and_yaml_interoperability(self):
        """Test strategy can be saved in one format and read in another"""
        config = StrategyConfig()
        config.name = "InteropTest"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)
        
        persistence = StrategyPersistence()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            yaml_path = Path(tmpdir) / "test.yaml"
            
            # Save as JSON
            persistence.save(config, json_path)
            
            # Load from JSON
            result1 = persistence.load(json_path)
            
            # Save loaded config as YAML
            persistence.save(result1.config, yaml_path)
            
            # Load from YAML
            result2 = persistence.load(yaml_path)
            
            # Should be identical
            assert result2.config.name == config.name
            assert len(result2.config.blocks) == len(config.blocks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestParametersMetadataIndented:
    """Round-trip tests for parameters, metadata, and indented fields"""

    def test_parameters_round_trip_json(self):
        """Test parameters field survives JSON save/load round-trip"""
        config = StrategyConfig()
        config.name = "ParamTest"
        block = BlockConfig(
            name="TestBlock",
            logic="AND",
            signals=[],
            parameters={"lookback": 50, "threshold": 0.75}
        )
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)

        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)

            assert result.success
            loaded = result.config
            assert loaded.blocks[0].parameters == {"lookback": 50, "threshold": 0.75}

    def test_parameters_round_trip_yaml(self):
        """Test parameters field survives YAML save/load round-trip"""
        config = StrategyConfig()
        config.name = "ParamTestYaml"
        block = BlockConfig(
            name="TestBlock",
            logic="AND",
            signals=[],
            parameters={"lookback": 100, "enabled": True}
        )
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)

        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"
            persistence.save(config, filepath)
            result = persistence.load(filepath)

            assert result.success
            loaded = result.config
            assert loaded.blocks[0].parameters == {"lookback": 100, "enabled": True}

    def test_parameters_default_empty_dict(self):
        """Test parameters defaults to empty dict when not in file"""
        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            import json
            data = {
                "name": "Test",
                "description": "",
                "version": "1.0.0",
                "blocks": [{"name": "Block1", "logic": "AND", "signals": []}]
            }
            with open(filepath, 'w') as f:
                json.dump(data, f)
            result = persistence.load(filepath)
            assert result.success
            assert result.config.blocks[0].parameters == {}

    def test_metadata_round_trip_json(self):
        """Test metadata field survives JSON save/load round-trip"""
        config = StrategyConfig()
        config.name = "MetaTest"
        block = BlockConfig(
            name="TestBlock",
            logic="AND",
            signals=[],
            metadata={"category": "PATTERN", "type": "SIGNAL"}
        )
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)

        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)

            assert result.success
            loaded = result.config
            assert loaded.blocks[0].metadata == {"category": "PATTERN", "type": "SIGNAL"}

    def test_metadata_default_none(self):
        """Test metadata defaults to None when not in file"""
        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            import json
            data = {
                "name": "Test",
                "description": "",
                "version": "1.0.0",
                "blocks": [{"name": "Block1", "logic": "AND", "signals": []}]
            }
            with open(filepath, 'w') as f:
                json.dump(data, f)
            result = persistence.load(filepath)
            assert result.success
            assert result.config.blocks[0].metadata is None

    def test_indented_round_trip_json(self):
        """Test indented field survives JSON save/load round-trip"""
        config = StrategyConfig()
        config.name = "IndentTest"
        block = BlockConfig(
            name="TestBlock",
            logic="AND",
            signals=[],
            indented=True
        )
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)

        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)

            assert result.success
            loaded = result.config
            assert loaded.blocks[0].indented is True

    def test_indented_default_false(self):
        """Test indented defaults to False when not in file"""
        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            import json
            data = {
                "name": "Test",
                "description": "",
                "version": "1.0.0",
                "blocks": [{"name": "Block1", "logic": "AND", "signals": []}]
            }
            with open(filepath, 'w') as f:
                json.dump(data, f)
            result = persistence.load(filepath)
            assert result.success
            assert result.config.blocks[0].indented is False

    def test_all_three_fields_round_trip_together(self):
        """Test parameters, metadata, and indented all survive round-trip"""
        config = StrategyConfig()
        config.name = "AllFieldsTest"
        block = BlockConfig(
            name="TestBlock",
            logic="AND",
            signals=[],
            metadata={"source": "registry"},
            indented=True,
            parameters={"param1": 10, "param2": "hello"}
        )
        block.signals.append(SignalConfig(name="S1", logic="AND"))
        config.blocks.append(block)

        persistence = StrategyPersistence()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.json"
            persistence.save(config, filepath)
            result = persistence.load(filepath)

            assert result.success
            loaded = result.config
            assert loaded.blocks[0].metadata == {"source": "registry"}
            assert loaded.blocks[0].indented is True
            assert loaded.blocks[0].parameters == {"param1": 10, "param2": "hello"}
