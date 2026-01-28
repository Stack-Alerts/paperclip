"""
Unit Tests for Exit Condition Persistence
Sprint 1.8 - Tasks 1.8.89-1.8.90

Tests exit condition serialization and deserialization.
"""

import pytest
import json
from src.strategy_builder.core.strategy_config_engine import (
    ExitCondition,
    RecheckConfig,
    StrategyConfig,
    BlockConfig,
    SignalConfig
)
from src.strategy_builder.persistence.strategy_persistence import StrategyPersistence


class TestExitConditionSerialization:
    """Test exit condition serialization - Task 1.8.89"""
    
    def setup_method(self):
        """Setup persistence manager for each test"""
        self.persistence = StrategyPersistence()
    
    def test_serialize_basic_exit_condition(self):
        """Test serialization of basic exit condition"""
        exit_cond = ExitCondition(
            signal_name="HOD_REJECTION",
            percentage=0.5,
            exit_mode="ABSOLUTE",
            binding_level="STRATEGY"
        )
        
        serialized = self.persistence._exit_condition_to_dict(exit_cond)
        
        assert serialized['signal_name'] == "HOD_REJECTION"
        assert serialized['percentage'] == 0.5
        assert serialized['exit_mode'] == "ABSOLUTE"
        assert serialized['binding_level'] == "STRATEGY"
        assert serialized['tp_proximity_threshold'] == 2.0
        assert serialized['reversal_trigger'] == 0.5
        assert serialized['recheck_config'] is None
        assert serialized['recheck_chain'] == []
    
    def test_serialize_flexible_mode_exit(self):
        """Test serialization of FLEXIBLE mode exit condition"""
        exit_cond = ExitCondition(
            signal_name="BELOW_HOD",
            percentage=0.3,
            exit_mode="FLEXIBLE",
            tp_proximity_threshold=1.5,
            reversal_trigger=0.3,
            binding_level="BLOCK"
        )
        
        serialized = self.persistence._exit_condition_to_dict(exit_cond)
        
        assert serialized['exit_mode'] == "FLEXIBLE"
        assert serialized['tp_proximity_threshold'] == 1.5
        assert serialized['reversal_trigger'] == 0.3
    
    def test_serialize_exit_with_recheck(self):
        """Test serialization of exit condition with RECHECK"""
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
        
        serialized = self.persistence._exit_condition_to_dict(exit_cond)
        
        assert serialized['recheck_config'] is not None
        assert serialized['recheck_config']['bar_delay'] == 10
        assert serialized['recheck_config']['must_still_be_true'] is True
        assert serialized['recheck_config']['signal_name'] == "BEARISH_BREAKDOWN"
    
    def test_serialize_exit_with_recheck_chain(self):
        """Test serialization of exit condition with nested RECHECK chain"""
        recheck1 = RecheckConfig(bar_delay=5, must_still_be_true=True, signal_name="HOD_REJECTION")
        recheck2 = RecheckConfig(bar_delay=3, must_still_be_true=True, signal_name="BELOW_HOD")
        
        exit_cond = ExitCondition(
            signal_name="BEARISH_BREAKDOWN",
            percentage=0.35,
            recheck_chain=[recheck1, recheck2]
        )
        
        serialized = self.persistence._exit_condition_to_dict(exit_cond)
        
        assert len(serialized['recheck_chain']) == 2
        assert serialized['recheck_chain'][0]['signal_name'] == "HOD_REJECTION"
        assert serialized['recheck_chain'][1]['signal_name'] == "BELOW_HOD"
    
    def test_serialize_signal_level_exit(self):
        """Test serialization of signal-level exit condition"""
        exit_cond = ExitCondition(
            signal_name="BELOW_HOD",
            percentage=0.15,
            binding_level="SIGNAL",
            parent_signal="AT_HOD"
        )
        
        serialized = self.persistence._exit_condition_to_dict(exit_cond)
        
        assert serialized['binding_level'] == "SIGNAL"
        assert serialized.get('parent_signal') == "AT_HOD"


class TestExitConditionDeserialization:
    """Test exit condition deserialization - Task 1.8.90"""
    
    def setup_method(self):
        """Setup persistence manager for each test"""
        self.persistence = StrategyPersistence()
    
    def test_deserialize_basic_exit_condition(self):
        """Test deserialization of basic exit condition"""
        data = {
            'signal_name': "HOD_REJECTION",
            'percentage': 0.5,
            'exit_mode': "ABSOLUTE",
            'tp_proximity_threshold': 2.0,
            'reversal_trigger': 0.5,
            'binding_level': "STRATEGY",
            'recheck_config': None,
            'recheck_chain': []
        }
        
        exit_cond = self.persistence._dict_to_exit_condition(data)
        
        assert exit_cond.signal_name == "HOD_REJECTION"
        assert exit_cond.percentage == 0.5
        assert exit_cond.exit_mode == "ABSOLUTE"
        assert exit_cond.binding_level == "STRATEGY"
    
    def test_deserialize_flexible_mode_exit(self):
        """Test deserialization of FLEXIBLE mode exit condition"""
        data = {
            'signal_name': "BELOW_HOD",
            'percentage': 0.3,
            'exit_mode': "FLEXIBLE",
            'tp_proximity_threshold': 1.5,
            'reversal_trigger': 0.3,
            'binding_level': "BLOCK",
            'recheck_config': None,
            'recheck_chain': []
        }
        
        exit_cond = self.persistence._dict_to_exit_condition(data)
        
        assert exit_cond.exit_mode == "FLEXIBLE"
        assert exit_cond.tp_proximity_threshold == 1.5
        assert exit_cond.reversal_trigger == 0.3
    
    def test_deserialize_exit_with_recheck(self):
        """Test deserialization of exit condition with RECHECK"""
        data = {
            'signal_name': "PATTERN_FORMING",
            'percentage': 0.25,
            'exit_mode': "ABSOLUTE",
            'tp_proximity_threshold': 2.0,
            'reversal_trigger': 0.5,
            'binding_level': "STRATEGY",
            'recheck_config': {
                'bar_delay': 10,
                'must_still_be_true': True,
                'signal_name': "BEARISH_BREAKDOWN"
            },
            'recheck_chain': []
        }
        
        exit_cond = self.persistence._dict_to_exit_condition(data)
        
        assert exit_cond.recheck_config is not None
        assert exit_cond.recheck_config.bar_delay == 10
        assert exit_cond.recheck_config.must_still_be_true is True
        assert exit_cond.recheck_config.signal_name == "BEARISH_BREAKDOWN"
    
    def test_deserialize_exit_with_recheck_chain(self):
        """Test deserialization of exit condition with nested RECHECK chain"""
        data = {
            'signal_name': "BEARISH_BREAKDOWN",
            'percentage': 0.35,
            'exit_mode': "ABSOLUTE",
            'tp_proximity_threshold': 2.0,
            'reversal_trigger': 0.5,
            'binding_level': "STRATEGY",
            'recheck_config': None,
            'recheck_chain': [
                {'bar_delay': 5, 'must_still_be_true': True, 'signal_name': "HOD_REJECTION"},
                {'bar_delay': 3, 'must_still_be_true': True, 'signal_name': "BELOW_HOD"}
            ]
        }
        
        exit_cond = self.persistence._dict_to_exit_condition(data)
        
        assert len(exit_cond.recheck_chain) == 2
        assert exit_cond.recheck_chain[0].signal_name == "HOD_REJECTION"
        assert exit_cond.recheck_chain[1].signal_name == "BELOW_HOD"
    
    def test_roundtrip_strategy_level_exits(self):
        """Test serialization/deserialization round-trip for strategy-level exits"""
        config = StrategyConfig(
            name="Test Strategy",
            blocks=[],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.3, binding_level="STRATEGY"),
                ExitCondition(signal_name="BEARISH_BREAKDOWN", percentage=0.25, exit_mode="FLEXIBLE", binding_level="STRATEGY")
            ]
        )
        
        # Serialize
        serialized = self.persistence._config_to_dict(config)
        
        # Deserialize
        restored = self.persistence._dict_to_config(serialized)
        
        assert len(restored.exit_conditions) == 2
        assert restored.exit_conditions[0].signal_name == "BEARISH"
        assert restored.exit_conditions[0].percentage == 0.3
        assert restored.exit_conditions[1].signal_name == "BEARISH_BREAKDOWN"
        assert restored.exit_conditions[1].exit_mode == "FLEXIBLE"
    
    def test_roundtrip_block_level_exits(self):
        """Test serialization/deserialization round-trip for block-level exits"""
        block = BlockConfig(
            name="hod_block",
            signals=[],
            logic_type="AND",
            exit_conditions=[
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.4, binding_level="BLOCK")
            ]
        )
        
        config = StrategyConfig(name="Test", blocks=[block])
        
        # Serialize
        serialized = self.persistence._config_to_dict(config)
        
        # Deserialize
        restored = self.persistence._dict_to_config(serialized)
        
        assert len(restored.blocks) == 1
        assert len(restored.blocks[0].exit_conditions) == 1
        assert restored.blocks[0].exit_conditions[0].signal_name == "HOD_REJECTION"
        assert restored.blocks[0].exit_conditions[0].percentage == 0.4
    
    def test_roundtrip_signal_level_exits(self):
        """Test serialization/deserialization round-trip for signal-level exits"""
        signal = SignalConfig(
            name="AT_HOD",
            exit_conditions=[
                ExitCondition(
                    signal_name="BELOW_HOD",
                    percentage=0.2,
                    binding_level="SIGNAL",
                    parent_signal="AT_HOD"
                )
            ]
        )
        
        block = BlockConfig(name="hod", signals=[signal], logic_type="AND")
        config = StrategyConfig(name="Test", blocks=[block])
        
        # Serialize
        serialized = self.persistence._config_to_dict(config)
        
        # Deserialize
        restored = self.persistence._dict_to_config(serialized)
        
        assert len(restored.blocks[0].signals) == 1
        assert len(restored.blocks[0].signals[0].exit_conditions) == 1
        assert restored.blocks[0].signals[0].exit_conditions[0].signal_name == "BELOW_HOD"
        assert restored.blocks[0].signals[0].exit_conditions[0].parent_signal == "AT_HOD"
    
    def test_roundtrip_multi_level_exits(self):
        """Test serialization/deserialization round-trip for exits at all levels"""
        signal = SignalConfig(
            name="AT_HOD",
            exit_conditions=[
                ExitCondition(signal_name="BELOW_HOD", percentage=0.15, binding_level="SIGNAL", parent_signal="AT_HOD")
            ]
        )
        
        block = BlockConfig(
            name="hod",
            signals=[signal],
            logic_type="AND",
            exit_conditions=[
                ExitCondition(signal_name="HOD_REJECTION", percentage=0.35, binding_level="BLOCK")
            ]
        )
        
        config = StrategyConfig(
            name="Test",
            blocks=[block],
            exit_conditions=[
                ExitCondition(signal_name="BEARISH", percentage=0.25, binding_level="STRATEGY")
            ]
        )
        
        # Serialize
        serialized = self.persistence._config_to_dict(config)
        
        # Deserialize
        restored = self.persistence._dict_to_config(serialized)
        
        # Verify strategy level
        assert len(restored.exit_conditions) == 1
        assert restored.exit_conditions[0].percentage == 0.25
        
        # Verify block level
        assert len(restored.blocks[0].exit_conditions) == 1
        assert restored.blocks[0].exit_conditions[0].percentage == 0.35
        
        # Verify signal level
        assert len(restored.blocks[0].signals[0].exit_conditions) == 1
        assert restored.blocks[0].signals[0].exit_conditions[0].percentage == 0.15
    
    def test_json_serialization_complete(self):
        """Test complete JSON serialization including exit conditions"""
        config = StrategyConfig(
            name="Complete Test",
            blocks=[
                BlockConfig(
                    name="test_block",
                    signals=[
                        SignalConfig(
                            name="TEST_SIGNAL",
                            exit_conditions=[
                                ExitCondition(signal_name="EXIT_SIG", percentage=0.1, binding_level="SIGNAL", parent_signal="TEST_SIGNAL")
                            ]
                        )
                    ],
                    logic_type="AND",
                    exit_conditions=[
                        ExitCondition(signal_name="BLOCK_EXIT", percentage=0.3, binding_level="BLOCK")
                    ]
                )
            ],
            exit_conditions=[
                ExitCondition(signal_name="STRATEGY_EXIT", percentage=0.4, exit_mode="FLEXIBLE", binding_level="STRATEGY")
            ]
        )
        
        # Full JSON round-trip
        json_str = json.dumps(self.persistence._config_to_dict(config))
        restored_dict = json.loads(json_str)
        restored_config = self.persistence._dict_to_config(restored_dict)
        
        # Verify all exit conditions survived
        assert len(restored_config.exit_conditions) == 1
        assert len(restored_config.blocks[0].exit_conditions) == 1
        assert len(restored_config.blocks[0].signals[0].exit_conditions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
