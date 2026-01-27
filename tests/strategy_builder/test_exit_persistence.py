"""
Unit tests for Exit Condition Persistence
Tests serialization and deserialization of exit conditions
Sprint 1.8 Task 1.8.16
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.strategy_builder.persistence.strategy_persistence import (
    StrategyPersistence,
    PersistenceFormat
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    ExitCondition,
    RecheckConfig
)


class TestExitConditionSerialization:
    """Test exit condition serialization to dict"""
    
    def test_exit_condition_to_dict_minimal(self):
        """Test serialization with minimal exit condition"""
        persistence = StrategyPersistence()
        
        exit_cond = ExitCondition(signal_name="BEARISH")
        result = persistence._exit_condition_to_dict(exit_cond)
        
        assert result['signal_name'] == "BEARISH"
        assert result['percentage'] == 0.5
        assert result['exit_mode'] == "ABSOLUTE"
        assert result['tp_proximity_threshold'] == 2.0
        assert result['reversal_trigger'] == 0.5
        assert result['binding_level'] == "STRATEGY"
        assert 'recheck_config' not in result
        assert 'recheck_chain' not in result
    
    def test_exit_condition_to_dict_full(self):
        """Test serialization with full exit condition"""
        persistence = StrategyPersistence()
        
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
            parent_signal="PATTERN_FORMING",
            binding_level="BLOCK"
        )
        
        result = persistence._exit_condition_to_dict(exit_cond)
        
        assert result['signal_name'] == "BEARISH_BREAKDOWN"
        assert result['percentage'] == 0.35
        assert result['exit_mode'] == "FLEXIBLE"
        assert result['tp_proximity_threshold'] == 3.0
        assert result['reversal_trigger'] == 0.8
        assert result['binding_level'] == "BLOCK"
        assert result['parent_signal'] == "PATTERN_FORMING"
        assert 'recheck_config' in result
        assert result['recheck_config']['enabled'] == True
        assert result['recheck_config']['bar_delay'] == 10
    
    def test_exit_condition_to_dict_with_recheck_chain(self):
        """Test serialization with nested recheck chain"""
        persistence = StrategyPersistence()
        
        recheck1 = RecheckConfig(enabled=True, bar_delay=5)
        recheck2 = RecheckConfig(enabled=True, bar_delay=3)
        
        exit_cond = ExitCondition(
            signal_name="BELOW_HOD",
            percentage=0.25,
            recheck_chain=[recheck1, recheck2]
        )
        
        result = persistence._exit_condition_to_dict(exit_cond)
        
        assert 'recheck_chain' in result
        assert len(result['recheck_chain']) == 2
        assert result['recheck_chain'][0]['bar_delay'] == 5
        assert result['recheck_chain'][1]['bar_delay'] == 3


class TestExitConditionDeserialization:
    """Test exit condition deserialization from dict"""
    
    def test_dict_to_exit_condition_minimal(self):
        """Test deserialization with minimal data"""
        persistence = StrategyPersistence()
        
        data = {
            'signal_name': 'BEARISH',
            'percentage': 0.3,
            'exit_mode': 'ABSOLUTE',
            'binding_level': 'STRATEGY'
        }
        
        exit_cond = persistence._dict_to_exit_condition(data)
        
        assert exit_cond.signal_name == "BEARISH"
        assert exit_cond.percentage == 0.3
        assert exit_cond.exit_mode == "ABSOLUTE"
        assert exit_cond.binding_level == "STRATEGY"
        assert exit_cond.tp_proximity_threshold == 2.0  # Default
        assert exit_cond.reversal_trigger == 0.5  # Default
        assert exit_cond.recheck_config is None
        assert exit_cond.recheck_chain == []
    
    def test_dict_to_exit_condition_full(self):
        """Test deserialization with full data"""
        persistence = StrategyPersistence()
        
        data = {
            'signal_name': 'BEARISH_BREAKDOWN',
            'percentage': 0.35,
            'exit_mode': 'FLEXIBLE',
            'tp_proximity_threshold': 3.0,
            'reversal_trigger': 0.8,
            'binding_level': 'BLOCK',
            'parent_signal': 'PATTERN_FORMING',
            'recheck_config': {
                'enabled': True,
                'bar_delay': 10,
                'validation_mode': 'SIGNAL',
                'parent_signal': 'AT_HOD'
            }
        }
        
        exit_cond = persistence._dict_to_exit_condition(data)
        
        assert exit_cond.signal_name == "BEARISH_BREAKDOWN"
        assert exit_cond.percentage == 0.35
        assert exit_cond.exit_mode == "FLEXIBLE"
        assert exit_cond.tp_proximity_threshold == 3.0
        assert exit_cond.reversal_trigger == 0.8
        assert exit_cond.binding_level == "BLOCK"
        assert exit_cond.parent_signal == "PATTERN_FORMING"
        assert exit_cond.recheck_config is not None
        assert exit_cond.recheck_config.enabled == True
        assert exit_cond.recheck_config.bar_delay == 10
    
    def test_dict_to_exit_condition_with_recheck_chain(self):
        """Test deserialization with recheck chain"""
        persistence = StrategyPersistence()
        
        data = {
            'signal_name': 'BELOW_HOD',
            'percentage': 0.25,
            'recheck_chain': [
                {'enabled': True, 'bar_delay': 5, 'validation_mode': 'SIGNAL'},
                {'enabled': True, 'bar_delay': 3, 'validation_mode': 'RECHECK'}
            ]
        }
        
        exit_cond = persistence._dict_to_exit_condition(data)
        
        assert len(exit_cond.recheck_chain) == 2
        assert exit_cond.recheck_chain[0].bar_delay == 5
        assert exit_cond.recheck_chain[1].bar_delay == 3


class TestExitConditionRoundTrip:
    """Test complete serialization round-trip"""
    
    def test_strategy_level_exit_conditions_roundtrip(self):
        """Test strategy-level exit conditions survive save/load"""
        persistence = StrategyPersistence()
        
        config = StrategyConfig()
        config.name = "Test Strategy"
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.3),
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.25, exit_mode="FLEXIBLE")
        ]
        
        # Add a block to make it valid
        block = BlockConfig(name="hod", logic="AND")
        block.signals.append(SignalConfig(name="AT_HOD", logic="AND"))
        config.blocks.append(block)
        
        # Save to dict
        data = persistence._config_to_dict(config)
        
        # Verify strategy-level exits in dict
        assert 'exit_conditions' in data
        assert len(data['exit_conditions']) == 2
        assert data['exit_conditions'][0]['signal_name'] == "BEARISH"
        assert data['exit_conditions'][1]['signal_name'] == "HOD_REJECTION"
        
        # Load from dict
        loaded_config = persistence._dict_to_config(data)
        
        # Verify strategy-level exits restored
        assert len(loaded_config.exit_conditions) == 2
        assert loaded_config.exit_conditions[0].signal_name == "BEARISH"
        assert loaded_config.exit_conditions[0].percentage == 0.3
        assert loaded_config.exit_conditions[1].signal_name == "HOD_REJECTION"
        assert loaded_config.exit_conditions[1].percentage == 0.25
        assert loaded_config.exit_conditions[1].exit_mode == "FLEXIBLE"
    
    def test_block_level_exit_conditions_roundtrip(self):
        """Test block-level exit conditions survive save/load"""
        persistence = StrategyPersistence()
        
        config = StrategyConfig()
        config.name = "Test Strategy"
        
        block = BlockConfig(name="hod", logic="AND")
        block.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.4, binding_level="BLOCK")
        ]
        block.signals.append(SignalConfig(name="AT_HOD", logic="AND"))
        config.blocks.append(block)
        
        # Save to dict
        data = persistence._config_to_dict(config)
        
        # Verify block-level exits in dict
        assert 'exit_conditions' in data['blocks'][0]
        assert len(data['blocks'][0]['exit_conditions']) == 1
        assert data['blocks'][0]['exit_conditions'][0]['signal_name'] == "HOD_REJECTION"
        
        # Load from dict
        loaded_config = persistence._dict_to_config(data)
        
        # Verify block-level exits restored
        assert len(loaded_config.blocks[0].exit_conditions) == 1
        assert loaded_config.blocks[0].exit_conditions[0].signal_name == "HOD_REJECTION"
        assert loaded_config.blocks[0].exit_conditions[0].percentage == 0.4
    
    def test_signal_level_exit_conditions_roundtrip(self):
        """Test signal-level exit conditions survive save/load"""
        persistence = StrategyPersistence()
        
        config = StrategyConfig()
        config.name = "Test Strategy"
        
        signal = SignalConfig(name="AT_HOD", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="BELOW_HOD", percentage=0.2, binding_level="SIGNAL")
        ]
        
        block = BlockConfig(name="hod", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        # Save to dict
        data = persistence._config_to_dict(config)
        
        # Verify signal-level exits in dict
        assert 'exit_conditions' in data['blocks'][0]['signals'][0]
        assert len(data['blocks'][0]['signals'][0]['exit_conditions']) == 1
        
        # Load from dict
        loaded_config = persistence._dict_to_config(data)
        
        # Verify signal-level exits restored
        signal_loaded = loaded_config.blocks[0].signals[0]
        assert len(signal_loaded.exit_conditions) == 1
        assert signal_loaded.exit_conditions[0].signal_name == "BELOW_HOD"
        assert signal_loaded.exit_conditions[0].percentage == 0.2
    
    def test_multi_level_exit_conditions_roundtrip(self):
        """Test exit conditions at all three levels survive save/load"""
        persistence = StrategyPersistence()
        
        config = StrategyConfig()
        config.name = "Multi-Level Exit Test"
        
        # Strategy-level exits
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.3, binding_level="STRATEGY")
        ]
        
        # Block-level exits
        signal = SignalConfig(name="AT_HOD", logic="AND")
        signal.exit_conditions = [
            ExitCondition(signal_name="BELOW_HOD", percentage=0.15, binding_level="SIGNAL")
        ]
        
        block = BlockConfig(name="hod", logic="AND")
        block.exit_conditions = [
            ExitCondition(signal_name="HOD_REJECTION", percentage=0.25, binding_level="BLOCK")
        ]
        block.signals.append(signal)
        config.blocks.append(block)
        
        # Save to dict
        data = persistence._config_to_dict(config)
        
        # Load from dict
        loaded_config = persistence._dict_to_config(data)
        
        # Verify all three levels
        assert len(loaded_config.exit_conditions) == 1
        assert loaded_config.exit_conditions[0].signal_name == "BEARISH"
        
        assert len(loaded_config.blocks[0].exit_conditions) == 1
        assert loaded_config.blocks[0].exit_conditions[0].signal_name == "HOD_REJECTION"
        
        assert len(loaded_config.blocks[0].signals[0].exit_conditions) == 1
        assert loaded_config.blocks[0].signals[0].exit_conditions[0].signal_name == "BELOW_HOD"


class TestExitConditionFilePersistence:
    """Test file-level persistence"""
    
    def test_save_load_json_with_exit_conditions(self):
        """Test saving and loading JSON file with exit conditions"""
        persistence = StrategyPersistence()
        
        config = StrategyConfig()
        config.name = "File Test Strategy"
        config.exit_conditions = [
            ExitCondition(signal_name="BEARISH", percentage=0.5, exit_mode="FLEXIBLE")
        ]
        
        block = BlockConfig(name="hod", logic="AND")
        block.signals.append(SignalConfig(name="AT_HOD", logic="AND"))
        config.blocks.append(block)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = Path(f.name)
        
        try:
            result = persistence.save(config, filepath, PersistenceFormat.JSON)
            assert result.success == True
            
            # Verify file exists
            assert filepath.exists()
            
            # Load from file
            load_result = persistence.load(filepath)
            assert load_result.success == True
            assert load_result.config is not None
            
            # Verify exit conditions restored
            loaded_config = load_result.config
            assert len(loaded_config.exit_conditions) == 1
            assert loaded_config.exit_conditions[0].signal_name == "BEARISH"
            assert loaded_config.exit_conditions[0].percentage == 0.5
            assert loaded_config.exit_conditions[0].exit_mode == "FLEXIBLE"
            
        finally:
            # Cleanup
            if filepath.exists():
                filepath.unlink()
    
    def test_backward_compatibility_without_exit_conditions(self):
        """Test loading old config files without exit conditions"""
        persistence = StrategyPersistence()
        
        # Create old-style config without exit conditions
        old_data = {
            'version': '1.0.0',
            'name': 'Old Strategy',
            'description': 'Legacy config',
            'blocks': [
                {
                    'name': 'hod',
                    'logic': 'AND',
                    'signals': [
                        {'name': 'AT_HOD', 'logic': 'AND'}
                    ]
                }
            ]
        }
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(old_data, f)
            filepath = Path(f.name)
        
        try:
            # Load should succeed
            result = persistence.load(filepath)
            assert result.success == True
            assert result.config is not None
            
            # Exit conditions should be empty lists (defaults)
            config = result.config
            assert config.exit_conditions == []
            assert config.blocks[0].exit_conditions == []
            assert config.blocks[0].signals[0].exit_conditions == []
            
        finally:
            # Cleanup
            if filepath.exists():
                filepath.unlink()
