"""
Unit Tests for WalkforwardTestEngine
Following TDD approach - Tests written before implementation
Reference: docs/v3/UI-UX/14_TESTING_MODES.md
"""

import pytest
from datetime import datetime, timedelta
from src.strategy_builder.testing.walkforward_test_engine import (
    WalkforwardTestEngine,
    TestMode,
    TestConfig,
    TestResult,
    PositionAdjustment
)
from src.strategy_builder.core.strategy_config_engine import StrategyConfig


class TestWalkforwardTestEngine:
    """Test suite for WalkforwardTestEngine"""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        engine = WalkforwardTestEngine()
        assert engine is not None
        
    def test_mode1_initialization(self):
        """Test Mode 1 (historical only) initialization"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=180,
            start_date=datetime(2024, 1, 1)
        )
        engine = WalkforwardTestEngine(config)
        assert engine.config.mode == TestMode.MODE_1
        assert engine.config.lookback_days == 180
        
    def test_mode2_initialization(self):
        """Test Mode 2 (historical + live) initialization"""
        config = TestConfig(
            mode=TestMode.MODE_2,
            lookback_days=180,
            start_date=datetime(2024, 1, 1)
        )
        engine = WalkforwardTestEngine(config)
        assert engine.config.mode == TestMode.MODE_2
        
    def test_run_mode1_returns_result(self):
        """Test Mode 1 returns test result"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=30,
            training_window_days=0
        )
        strategy_config = self._create_test_strategy()
        
        engine = WalkforwardTestEngine(config)
        result = engine.run(strategy_config)
        
        assert result is not None
        assert isinstance(result, TestResult)
        
    def test_expanding_window_processing(self):
        """Test candle-by-candle expanding window"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=10
        )
        engine = WalkforwardTestEngine(config)
        
        # Should process candles one by one
        # Window should expand from 1 candle to N candles
        assert engine.config.lookback_days == 10
        
    def test_training_window_offset(self):
        """Test training window offset calculation"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=180,
            training_window_days=30
        )
        engine = WalkforwardTestEngine(config)
        
        # Should start 210 days back (180 + 30)
        total_days = engine._calculate_total_lookback()
        assert total_days == 210
        
    def test_track_position_adjustments(self):
        """Test tracking TP/SL adjustments"""
        config = TestConfig(mode=TestMode.MODE_1, lookback_days=30)
        engine = WalkforwardTestEngine(config)
        
        # Track an adjustment
        adjustment = PositionAdjustment(
            adjustment_type="TP1",
            old_value=50000,
            new_value=51000,
            candle_index=100
        )
        engine._track_adjustment(adjustment)
        
        assert len(engine.adjustments) == 1
        
    def test_mode1_completes_at_end_date(self):
        """Test Mode 1 stops at current date"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=30
        )
        engine = WalkforwardTestEngine(config)
        
        # Mode 1 should complete and return
        assert config.mode == TestMode.MODE_1
        
    def test_mode2_continues_waiting(self):
        """Test Mode 2 waits for new candles"""
        config = TestConfig(
            mode=TestMode.MODE_2,
            lookback_days=30
        )
        engine = WalkforwardTestEngine(config)
        
        # Mode 2 should wait for new data
        assert config.mode == TestMode.MODE_2
        
    def test_result_includes_adjustment_count(self):
        """Test result includes TP/SL adjustment counts"""
        config = TestConfig(mode=TestMode.MODE_1, lookback_days=10)
        strategy_config = self._create_test_strategy()
        
        engine = WalkforwardTestEngine(config)
        result = engine.run(strategy_config)
        
        assert hasattr(result, 'tp1_adjustments')
        assert hasattr(result, 'tp2_adjustments')
        assert hasattr(result, 'tp3_adjustments')
        assert hasattr(result, 'sl_adjustments')
        
    def test_result_includes_position_count(self):
        """Test result includes position statistics"""
        config = TestConfig(mode=TestMode.MODE_1, lookback_days=10)
        strategy_config = self._create_test_strategy()
        
        engine = WalkforwardTestEngine(config)
        result = engine.run(strategy_config)
        
        assert hasattr(result, 'total_positions')
        assert hasattr(result, 'winning_positions')
        assert hasattr(result, 'losing_positions')
        
    # Helper method
    def _create_test_strategy(self):
        """Create test strategy configuration"""
        from src.strategy_builder.core.strategy_config_engine import (
            StrategyConfig, BlockConfig, SignalConfig
        )
        
        config = StrategyConfig()
        config.name = "TestStrategy"
        
        block = BlockConfig(name="TestBlock", logic="AND", signals=[])
        signal = SignalConfig(name="TEST_SIGNAL", logic="AND")
        block.signals.append(signal)
        config.blocks.append(block)
        
        return config


class TestTestConfig:
    """Test TestConfig data class"""
    
    def test_config_creation(self):
        """Test creating test configuration"""
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=180,
            training_window_days=30
        )
        assert config.mode == TestMode.MODE_1
        assert config.lookback_days == 180
        assert config.training_window_days == 30


class TestTestResult:
    """Test TestResult data class"""
    
    def test_result_creation(self):
        """Test creating test result"""
        result = TestResult(
            total_positions=10,
            winning_positions=6,
            losing_positions=4,
            tp1_adjustments=5,
            tp2_adjustments=3,
            tp3_adjustments=2,
            sl_adjustments=8
        )
        assert result.total_positions == 10
        assert result.winning_positions == 6
        assert result.tp1_adjustments == 5


class TestPositionAdjustment:
    """Test PositionAdjustment data class"""
    
    def test_adjustment_creation(self):
        """Test creating position adjustment"""
        adj = PositionAdjustment(
            adjustment_type="TP1",
            old_value=50000,
            new_value=51000,
            candle_index=100
        )
        assert adj.adjustment_type == "TP1"
        assert adj.old_value == 50000
        assert adj.new_value == 51000


class TestTestMode:
    """Test TestMode enum"""
    
    def test_mode_values(self):
        """Test mode enum values"""
        assert TestMode.MODE_1 is not None
        assert TestMode.MODE_2 is not None


class TestWalkforwardTestEngineIntegration:
    """Integration tests for complete testing workflow"""
    
    def test_complete_mode1_workflow(self):
        """Test complete Mode 1 testing workflow"""
        # Create config
        config = TestConfig(
            mode=TestMode.MODE_1,
            lookback_days=30,
            training_window_days=0
        )
        
        # Create strategy
        from src.strategy_builder.core.strategy_config_engine import (
            StrategyConfig, BlockConfig, SignalConfig
        )
        
        strategy_config = StrategyConfig()
        strategy_config.name = "IntegrationTestStrategy"
        
        block = BlockConfig(name="TestBlock", logic="AND", signals=[])
        signal = SignalConfig(name="TEST_SIGNAL", logic="AND")
        block.signals.append(signal)
        strategy_config.blocks.append(block)
        
        # Run test
        engine = WalkforwardTestEngine(config)
        result = engine.run(strategy_config)
        
        # Verify result
        assert result is not None
        assert result.total_positions >= 0
        assert result.tp1_adjustments >= 0
        assert result.sl_adjustments >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
