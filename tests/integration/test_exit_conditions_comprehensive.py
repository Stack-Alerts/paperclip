"""
Comprehensive Exit Conditions Test Suite

Tests ALL possible exit condition configurations:
- 3 binding levels (STRATEGY, BLOCK, SIGNAL)
- 2 exit modes (ABSOLUTE, FLEXIBLE)
- 2 recheck states (Enabled, Disabled)
- 2 timing modes (AT, WITHIN)

Total: 24+ base scenarios + edge cases = 50+ test cases

Author: BTC_Engine_v3
Date: 2026-02-16
"""

import pytest
from typing import List, Dict, Any
from dataclasses import dataclass
from unittest.mock import Mock, MagicMock
from nautilus_trader.model.data import Bar
from nautilus_trader.model.objects import Price

from src.optimizer_v3.core.exit_hierarchy_evaluator import (
    ExitHierarchyEvaluator,
    ExitDecision,
    PendingExitRecheck
)
from src.optimizer_v3.core.institutional_signal_evaluator import (
    ExitCondition,
    TradeState
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def evaluator():
    """Create fresh exit hierarchy evaluator"""
    return ExitHierarchyEvaluator()


@pytest.fixture
def mock_bar():
    """Create mock bar"""
    bar = Mock(spec=Bar)
    bar.close = 45000.0
    bar.open = 44900.0
    bar.high = 45100.0
    bar.low = 44800.0
    bar.volume = 100.0
    bar.ts_event = 1234567890000000000  # nanoseconds
    return bar


@pytest.fixture
def mock_lookback():
    """Create mock lookback bars"""
    bars = []
    for i in range(50):
        bar = Mock(spec=Bar)
        bar.close = 45000.0 + i * 10
        bar.open = 44900.0 + i * 10
        bar.high = 45100.0 + i * 10
        bar.low = 44800.0 + i * 10
        bar.volume = 100.0
        bar.ts_event = 1234567890000000000 + i * 1000000000
        bars.append(bar)
    return bars


@pytest.fixture
def mock_building_blocks():
    """Create mock building blocks that can simulate signal firing"""
    
    class MockBlock:
        def __init__(self, signal_to_fire=None):
            self.signal_to_fire = signal_to_fire
        
        def analyze(self, df):
            """Return signal if configured"""
            if self.signal_to_fire:
                return {'signal': self.signal_to_fire}
            return {'signal': 'NO_SIGNAL'}
    
    return {
        'asia_session_50_percent': MockBlock(),
        'hod_rejection': MockBlock(),
        'vwap_detector': MockBlock()
    }


@pytest.fixture
def trade_state_fresh():
    """Fresh trade state (no TP hits)"""
    return TradeState(
        entry_bar=100,
        entry_price=Price(45000.0, 2),
        entry_side='SHORT',
        entry_signals=[
            'asia_session_50_percent::AT_ASIA_50',
            'asia_session_50_percent::BELOW_ASIA_50'
        ],
        remaining_position=1.0
    )


@pytest.fixture
def trade_state_partial():
    """Trade state after partial TP hits"""
    return TradeState(
        entry_bar=100,
        entry_price=Price(45000.0, 2),
        entry_side='SHORT',
        entry_signals=[
            'asia_session_50_percent::AT_ASIA_50',
            'asia_session_50_percent::BELOW_ASIA_50'
        ],
        remaining_position=0.5,  # 50% already exited via TP
        tp_hits=['TP1', 'TP2']
    )


# ============================================================================
# CATEGORY A: BINDING LEVEL TESTS
# ============================================================================

class TestBindingLevels:
    """Test exit conditions at different binding levels"""
    
    def test_A1_strategy_level_exit(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """TC-001: Strategy-level exit applies to ALL trades"""
        # Configure block to fire ABOVE_ASIA_50
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        # Strategy-level exit condition
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='ABSOLUTE',
            binding_level='STRATEGY',
            recheck_config=None
        )
        
        exit_conditions = {
            'STRATEGY': [exit_cond],
            'BLOCK': {},
            'SIGNAL': {}
        }
        
        # Evaluate
        result = evaluator.evaluate(
            mock_bar,
            150,
            mock_lookback,
            exit_conditions,
            trade_state_fresh,
            mock_building_blocks
        )
        
        # Assertions
        assert result.should_exit == True
        assert result.binding_level == 'STRATEGY'
        assert result.percentage == 0.5  # 50% ABSOLUTE
        assert 'STRATEGY' in result.reason
    
    def test_A2_block_level_exit(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """TC-003: Block-level exit applies to trades using that block"""
        # Configure block to fire ABOVE_ASIA_50
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        # Block-level exit condition
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='ABSOLUTE',
            binding_level='BLOCK',
            recheck_config=None
        )
        
        exit_conditions = {
            'STRATEGY': [],
            'BLOCK': {'asia_session_50_percent': [exit_cond]},
            'SIGNAL': {}
        }
        
        # Evaluate
        result = evaluator.evaluate(
            mock_bar,
            150,
            mock_lookback,
            exit_conditions,
            trade_state_fresh,
            mock_building_blocks
        )
        
        # Assertions
        assert result.should_exit == True
        assert 'BLOCK' in result.binding_level  # Can be 'BLOCK(asia_session_50_percent)' with detail
        assert result.percentage == 0.5
        assert 'BLOCK' in result.reason
    
    def test_A3_signal_level_exit_binding_success(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """TC-005: Signal-level exit ONLY if bound signal fired for entry"""
        # Configure block to fire ABOVE_ASIA_50
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        # Signal-level exit bound to BELOW_ASIA_50
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='FLEXIBLE',
            binding_level='SIGNAL',
            recheck_config=None
        )
        
        exit_conditions = {
            'STRATEGY': [],
            'BLOCK': {},
            'SIGNAL': {
                'asia_session_50_percent::BELOW_ASIA_50': [exit_cond]
            }
        }
        
        # Trade entry includes BELOW_ASIA_50
        trade_state_fresh.entry_signals = [
            'asia_session_50_percent::AT_ASIA_50',
            'asia_session_50_percent::BELOW_ASIA_50'  # ✓ Binding satisfied
        ]
        
        # Evaluate
        result = evaluator.evaluate(
            mock_bar,
            150,
            mock_lookback,
            exit_conditions,
            trade_state_fresh,
            mock_building_blocks
        )
        
        # Assertions
        assert result.should_exit == True
        assert 'SIGNAL' in result.binding_level  # Can be 'SIGNAL(asia_session_50_percent' with detail
        assert result.percentage == 0.5  # 50% FLEXIBLE of 100% = 50%
    
    def test_A3_signal_level_exit_binding_failure(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """Signal-level exit DOES NOT fire if bound signal not in entry"""
        # Configure block to fire ABOVE_ASIA_50
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        # Signal-level exit bound to BELOW_ASIA_50
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='FLEXIBLE',
            binding_level='SIGNAL',
            recheck_config=None
        )
        
        exit_conditions = {
            'STRATEGY': [],
            'BLOCK': {},
            'SIGNAL': {
                'asia_session_50_percent::BELOW_ASIA_50': [exit_cond]
            }
        }
        
        # Trade entry does NOT include BELOW_ASIA_50
        trade_state_fresh.entry_signals = [
            'asia_session_50_percent::AT_ASIA_50',
            'hod_rejection::BELOW_HOD'  # ✗ BELOW_ASIA_50 not in entry
        ]
        
        # Evaluate
        result = evaluator.evaluate(
            mock_bar,
            150,
            mock_lookback,
            exit_conditions,
            trade_state_fresh,
            mock_building_blocks
        )
        
        # Assertions
        assert result.should_exit == False  # Binding failed!
        assert result.percentage == 0.0


# ============================================================================
# CATEGORY B: EXIT MODE TESTS
# ============================================================================

class TestExitModes:
    """Test ABSOLUTE vs FLEXIBLE exit modes"""
    
    def test_B1_absolute_mode_no_tp(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """TC-001: ABSOLUTE mode - percentage of original position"""
        # Configure block
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='ABSOLUTE',
            binding_level='STRATEGY',
            recheck_config=None
        )
        
        exit_conditions = {'STRATEGY': [exit_cond], 'BLOCK': {}, 'SIGNAL': {}}
        
        result = evaluator.evaluate(
            mock_bar, 150, mock_lookback,
            exit_conditions, trade_state_fresh, mock_building_blocks
        )
        
        # ABSOLUTE: 50% of original (100%) = 50%
        assert result.percentage == 0.5
    
    def test_B1_absolute_mode_with_tp(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_partial
    ):
        """ABSOLUTE mode after TP hits - still percentage of original"""
        # Configure block
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='ABSOLUTE',
            binding_level='STRATEGY',
            recheck_config=None
        )
        
        exit_conditions = {'STRATEGY': [exit_cond], 'BLOCK': {}, 'SIGNAL': {}}
        
        # Trade has 50% remaining (TP hits exited other 50%)
        result = evaluator.evaluate(
            mock_bar, 150, mock_lookback,
            exit_conditions, trade_state_partial, mock_building_blocks
        )
        
        # ABSOLUTE: min(50% requested, 50% remaining) = 50%
        assert result.percentage == 0.5  # Capped at remaining
    
    def test_B2_flexible_mode_no_tp(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_fresh
    ):
        """TC-002: FLEXIBLE mode - percentage of REMAINING position"""
        # Configure block
        mock_building_blocks['asia_session_50_percent'].signal_to_fire = 'ABOVE_ASIA_50'
        
        exit_cond = ExitCondition(
            signal_name='ABOVE_ASIA_50',
            percentage=0.5,
            mode='FLEXIBLE',
            binding_level='STRATEGY',
            recheck_config=None
        )
        
        exit_conditions = {'STRATEGY': [exit_cond], 'BLOCK': {}, 'SIGNAL': {}}
        
        result = evaluator.evaluate(
            mock_bar, 150, mock_lookback,
            exit_conditions, trade_state_fresh, mock_building_blocks
        )
        
        # FLEXIBLE: 50% of 100% remaining = 50%
        assert result.percentage == 0.5
    
    def test_B2_flexible_mode_with_tp(
        self,
        evaluator,
        mock_bar,
        mock_lookback,
        mock_building_blocks,
        trade_state_partial
    ):
        """FLEXIBLE mode after TP hits - percentage of REMAINING"""
        # Configure block
        