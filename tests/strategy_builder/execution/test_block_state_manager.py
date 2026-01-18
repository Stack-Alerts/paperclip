"""
Unit Tests for BlockStateManager
Real-time execution state tracking for strategy signals
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/21_BLOCK_STATE_MANAGER.md
"""

import pytest
from datetime import datetime

from src.strategy_builder.execution.block_state_manager import (
    BlockStateManager,
    SignalState,
    BlockExecutionState,
    StrategyExecutionState
)
from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint
)


class TestBlockStateManager:
    """Test suite for BlockStateManager"""
    
    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        assert manager is not None
        assert manager.config == config
        
    def test_track_signal_fired(self):
        """Test tracking when a signal fires"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        # Fire a signal
        manager.signal_fired(
            block_name="Block1",
            signal_name="SIGNAL1",
            candle_index=100
        )
        
        # Check it was tracked
        state = manager.get_signal_state("Block1", "SIGNAL1")
        assert state is not None
        assert state.fired is True
        assert state.candle_index == 100
        
    def test_track_multiple_signals(self):
        """Test tracking multiple signals"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        manager.signal_fired("Block1", "SIGNAL2", 105)
        
        state1 = manager.get_signal_state("Block1", "SIGNAL1")
        state2 = manager.get_signal_state("Block1", "SIGNAL2")
        
        assert state1.fired is True
        assert state2.fired is True
        assert state1.candle_index == 100
        assert state2.candle_index == 105
        
    def test_timing_window_tracking(self):
        """Test tracking timing windows for constraints"""
        config = self._create_strategy_with_timing()
        manager = BlockStateManager(config)
        
        # Fire first signal
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        # Check timing window is active
        window = manager.get_timing_window("Block1", "SIGNAL2")
        assert window is not None
        assert window['reference_signal'] == "SIGNAL1"
        assert window['max_candles'] == 20
        assert window['start_candle'] == 100
        
    def test_signal_within_timing_window(self):
        """Test signal firing within timing window"""
        config = self._create_strategy_with_timing()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        manager.signal_fired("Block1", "SIGNAL2", 115)  # Within 20 candles
        
        # Should be valid
        is_valid = manager.is_timing_valid("Block1", "SIGNAL2", 115)
        assert is_valid is True
        
    def test_signal_outside_timing_window(self):
        """Test signal firing outside timing window"""
        config = self._create_strategy_with_timing()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        # Check at candle 125 (25 candles later, max was 20)
        is_valid = manager.is_timing_valid("Block1", "SIGNAL2", 125)
        assert is_valid is False
        
    def test_reset_on_timing_violation(self):
        """Test strategy resets when timing constraint violated"""
        config = self._create_strategy_with_timing()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        # Violate timing window
        manager.check_and_reset_if_needed(125)
        
        # Strategy should be reset
        state = manager.get_signal_state("Block1", "SIGNAL1")
        assert state.fired is False
        
    def test_strategy_complete_check(self):
        """Test checking if strategy requirements are met"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        # Initially not complete
        assert manager.is_strategy_complete() is False
        
        # Fire all required signals
        manager.signal_fired("Block1", "SIGNAL1", 100)
        manager.signal_fired("Block1", "SIGNAL2", 105)
        
        # Should be complete
        assert manager.is_strategy_complete() is True
        
    def test_or_logic_blocks(self):
        """Test handling of OR logic blocks"""
        config = self._create_strategy_with_or_block()
        manager = BlockStateManager(config)
        
        # Fire only one signal from OR block
        manager.signal_fired("BlockOR", "SIGNAL_A", 100)
        
        # Should still meet requirements
        is_complete = manager.is_strategy_complete()
        assert is_complete is True
        
    def test_and_logic_blocks(self):
        """Test handling of AND logic blocks"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        # Fire only one of two required AND signals
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        # Should not be complete yet
        assert manager.is_strategy_complete() is False
        
        # Fire second required signal
        manager.signal_fired("Block1", "SIGNAL2", 105)
        
        # Now should be complete
        assert manager.is_strategy_complete() is True
        
    def test_reset_strategy(self):
        """Test manually resetting strategy state"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        manager.signal_fired("Block1", "SIGNAL2", 105)
        
        # Reset
        manager.reset()
        
        # All signals should be unfired
        state1 = manager.get_signal_state("Block1", "SIGNAL1")
        state2 = manager.get_signal_state("Block1", "SIGNAL2")
        
        assert state1.fired is False
        assert state2.fired is False
        
    def test_get_execution_state(self):
        """Test getting complete execution state"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        state = manager.get_execution_state()
        
        assert state is not None
        assert isinstance(state, StrategyExecutionState)
        assert len(state.block_states) > 0
        
    def test_candle_progression(self):
        """Test tracking candle progression"""
        config = self._create_test_strategy()
        manager = BlockStateManager(config)
        
        manager.on_candle(100)
        assert manager.current_candle == 100
        
        manager.on_candle(101)
        assert manager.current_candle == 101
        
    # Helper methods
    def _create_test_strategy(self):
        """Create simple test strategy"""
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(name="SIGNAL2", logic="AND")
        
        block.signals.append(signal1)
        block.signals.append(signal2)
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
            timing_constraint=TimingConstraint(
                max_candles=20,
                reference="SIGNAL1"
            )
        )
        
        block.signals.append(signal1)
        block.signals.append(signal2)
        config.blocks.append(block)
        
        return config
        
    def _create_strategy_with_or_block(self):
        """Create strategy with OR block"""
        config = StrategyConfig()
        config.name = "ORStrategy"
        
        block = BlockConfig(name="BlockOR", logic="OR", signals=[])
        signal_a = SignalConfig(name="SIGNAL_A", logic="OR")
        signal_b = SignalConfig(name="SIGNAL_B", logic="OR")
        
        block.signals.append(signal_a)
        block.signals.append(signal_b)
        config.blocks.append(block)
        
        return config


class TestSignalState:
    """Test SignalState data class"""
    
    def test_signal_state_creation(self):
        """Test creating signal state"""
        state = SignalState(
            block_name="Block1",
            signal_name="SIGNAL1",
            fired=True,
            candle_index=100
        )
        
        assert state.block_name == "Block1"
        assert state.signal_name == "SIGNAL1"
        assert state.fired is True
        assert state.candle_index == 100


class TestBlockExecutionState:
    """Test BlockExecutionState data class"""
    
    def test_block_state_creation(self):
        """Test creating block execution state"""
        state = BlockExecutionState(
            block_name="Block1",
            logic="AND",
            signals_fired=1,
            signals_required=2,
            complete=False
        )
        
        assert state.block_name == "Block1"
        assert state.logic == "AND"
        assert state.signals_fired == 1
        assert state.signals_required == 2
        assert state.complete is False


class TestStrategyExecutionState:
    """Test StrategyExecutionState data class"""
    
    def test_strategy_state_creation(self):
        """Test creating strategy execution state"""
        block_state = BlockExecutionState(
            block_name="Block1",
            logic="AND",
            signals_fired=2,
            signals_required=2,
            complete=True
        )
        
        state = StrategyExecutionState(
            strategy_name="TestStrategy",
            current_candle=100,
            complete=True,
            block_states=[block_state]
        )
        
        assert state.strategy_name == "TestStrategy"
        assert state.current_candle == 100
        assert state.complete is True
        assert len(state.block_states) == 1


class TestBlockStateManagerIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_execution_cycle(self):
        """Test complete signal execution cycle"""
        # Create strategy
        config = StrategyConfig()
        config.name = "CompleteStrategy"
        
        block = BlockConfig(name="Block1", logic="AND", signals=[])
        signal1 = SignalConfig(name="SIGNAL1", logic="AND")
        signal2 = SignalConfig(
            name="SIGNAL2",
            logic="AND",
            timing_constraint=TimingConstraint(max_candles=20, reference="SIGNAL1")
        )
        block.signals.extend([signal1, signal2])
        config.blocks.append(block)
        
        # Initialize manager
        manager = BlockStateManager(config)
        
        # Simulate candle progression
        manager.on_candle(100)
        manager.signal_fired("Block1", "SIGNAL1", 100)
        
        assert manager.is_strategy_complete() is False
        
        # Fire second signal within window
        manager.on_candle(115)
        manager.signal_fired("Block1", "SIGNAL2", 115)
        
        assert manager.is_strategy_complete() is True
        
        # Get final state
        state = manager.get_execution_state()
        assert state.complete is True
        
    def test_multi_block_execution(self):
        """Test execution with multiple blocks"""
        config = StrategyConfig()
        config.name = "MultiBlockStrategy"
        
        # Block 1
        block1 = BlockConfig(name="Block1", logic="AND", signals=[])
        block1.signals.append(SignalConfig(name="SIGNAL1", logic="AND"))
        config.blocks.append(block1)
        
        # Block 2
        block2 = BlockConfig(name="Block2", logic="AND", signals=[])
        block2.signals.append(SignalConfig(name="SIGNAL2", logic="AND"))
        config.blocks.append(block2)
        
        manager = BlockStateManager(config)
        
        # Fire signals
        manager.signal_fired("Block1", "SIGNAL1", 100)
        assert manager.is_strategy_complete() is False
        
        manager.signal_fired("Block2", "SIGNAL2", 105)
        assert manager.is_strategy_complete() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
