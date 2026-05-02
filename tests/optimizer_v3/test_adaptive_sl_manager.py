"""
Tests for Adaptive SL Manager

Tests emergency SL, adaptive SL, ATR, constraints, trailing logic

Author: BTC_Engine_v3
Date: February 2026
"""

import pytest

from src.optimizer_v3.core.adaptive_sl_manager import (
    AdaptiveSLManager,
    AdaptiveSLResult,
    get_adaptive_sl_manager
)
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import millis_to_nanos


# Create a reusable BarType for tests
_test_bar_type = BarType.from_str("BTC.BINANCE-15-MINUTE-LAST-EXTERNAL")


def create_bar(open_price: float, high: float, low: float, close: float, volume: float = 1000.0, timestamp_ms: int = 1000000) -> Bar:
    """Helper to create test bars"""
    return Bar(
        bar_type=_test_bar_type,
        open=Price.from_str(str(open_price)),
        high=Price.from_str(str(high)),
        low=Price.from_str(str(low)),
        close=Price.from_str(str(close)),
        volume=Quantity.from_str(str(volume)),
        ts_event=millis_to_nanos(timestamp_ms),
        ts_init=millis_to_nanos(timestamp_ms)
    )


def create_bars_with_atr(atr: float, num_bars: int = 20, base_price: float = 50000.0) -> list:
    """Create test bars with specific ATR"""
    bars = []
    
    for i in range(num_bars):
        # Create bars with consistent ATR
        high = base_price + atr
        low = base_price - atr
        bars.append(create_bar(
            open_price=base_price,
            high=high,
            low=low,
            close=base_price,
            timestamp_ms=1000000 + i * 1000
        ))
        base_price += 10  # Slight upward trend
    
    return bars


class TestAdaptiveSLManager:
    """Test Adaptive SL Manager"""
    
    def test_initialization(self):
        """Test manager initialization"""
        manager = AdaptiveSLManager()
        assert manager is not None
    
    def test_singleton_pattern(self):
        """Test singleton pattern"""
        manager1 = get_adaptive_sl_manager()
        manager2 = get_adaptive_sl_manager()
        assert manager1 is manager2
    
    def test_emergency_sl_long(self):
        """Test emergency SL during delay for LONG"""
        manager = AdaptiveSLManager()
        
        current_bar = create_bar(50100, 50200, 50000, 50100)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=5,  # Within delay
            lookback_bars=[],
            config={'delay_bars': 10, 'emergency_sl_percent': 1.0},
            entry_side='LONG'
        )
        
        # Verify emergency mode
        assert result.sl_mode == 'EMERGENCY'
        
        # Verify SL 1% below entry
        expected_sl = 50000 * 0.99  # 49500
        assert result.new_sl == expected_sl
        
        # Verify distance
        assert result.sl_distance == 500.0
        
        # Verify ATR is 0 (not used in emergency)
        assert result.atr_value == 0.0
        
        # Verify reason
        assert 'Emergency' in result.reason
        assert 'bar 5' in result.reason
    
    def test_emergency_sl_short(self):
        """Test emergency SL during delay for SHORT"""
        manager = AdaptiveSLManager()
        
        current_bar = create_bar(49900, 50000, 49800, 49900)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=3,  # Within delay
            lookback_bars=[],
            config={'delay_bars': 10, 'emergency_sl_percent': 1.0},
            entry_side='SHORT'
        )
        
        # Verify emergency mode
        assert result.sl_mode == 'EMERGENCY'
        
        # Verify SL 1% above entry
        expected_sl = 50000 * 1.01  # 50500
        assert result.new_sl == expected_sl
    
    def test_adaptive_sl_long(self):
        """Test adaptive SL post-delay for LONG"""
        manager = AdaptiveSLManager()
        
        # Create bars with known ATR (high-low = 400)
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,  # Past delay
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,  # 1.5x
                'min_sl': 5,      # 0.5%
                'max_sl': 20      # 2.0%
            },
            entry_side='LONG'
        )
        
        # Verify adaptive mode
        assert result.sl_mode == 'ADAPTIVE'
        
        # Verify ATR calculated
        assert result.atr_value > 0
        
        # SL should trail below current price
        assert result.new_sl < 50500  # Below current close
        assert result.new_sl >= 50000 * 0.995  # Not below entry threshold
    
    def test_adaptive_sl_short(self):
        """Test adaptive SL post-delay for SHORT"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        current_bar = create_bar(49500, 49600, 49400, 49500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,  # Past delay
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 5,
                'max_sl': 20
            },
            entry_side='SHORT'
        )
        
        # Verify adaptive mode
        assert result.sl_mode == 'ADAPTIVE'
        
        # SL should trail above current price
        assert result.new_sl > 49500  # Above current close
        assert result.new_sl <= 50000 * 1.005  # Not above entry threshold
    
    def test_delay_transition(self):
        """Test transition from emergency to adaptive SL"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        config = {
            'delay_bars': 10,
            'emergency_sl_percent': 1.0,
            'vol_lookback': 20,
            'vol_multi': 15,
            'min_sl': 5,
            'max_sl': 20
        }
        
        # Bar 9: Should be emergency
        result_during = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=9,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        
        assert result_during.sl_mode == 'EMERGENCY'
        
        # Bar 10: Should be adaptive
        result_after = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=10,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        
        assert result_after.sl_mode == 'ADAPTIVE'
    
    def test_min_constraint_enforcement(self):
        """Test minimum SL distance constraint"""
        manager = AdaptiveSLManager()
        
        # Create bars with very small ATR
        lookback_bars = create_bars_with_atr(atr=10.0, num_bars=20)
        
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 100,    # 10% minimum
                'max_sl': 200     # 20% maximum
            },
            entry_side='LONG'
        )
        
        # SL distance should be at least min_sl
        min_distance = 50000 * 0.10  # 5000
        assert result.sl_distance >= min_distance
    
    def test_max_constraint_enforcement(self):
        """Test maximum SL distance constraint"""
        manager = AdaptiveSLManager()
        
        # Create bars with very large ATR
        lookback_bars = create_bars_with_atr(atr=5000.0, num_bars=20)
        
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 5,      # 0.5%
                'max_sl': 20      # 2.0% maximum
            },
            entry_side='LONG'
        )
        
        # SL distance should not exceed max_sl
        max_distance = 50000 * 0.02  # 1000
        assert result.sl_distance <= max_distance
    
    def test_atr_calculation_accuracy(self):
        """Test ATR calculation"""
        manager = AdaptiveSLManager()
        
        # Create bars with known ATR
        bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        atr = manager._calculate_atr(bars, period=14)
        
        # ATR should be approximately 400 (high-low = 2 * 200)
        assert abs(atr - 400.0) < 50
    
    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data"""
        manager = AdaptiveSLManager()
        
        # Only 1 bar (need at least 2)
        bars = [create_bar(50000, 50100, 49900, 50000)]
        
        atr = manager._calculate_atr(bars)
        
        # Should return 0
        assert atr == 0.0
    
    def test_trailing_sl_lock_gains_long(self):
        """Test SL doesn't go below entry for LONG (lock gains)"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        # Price far above entry
        current_bar = create_bar(55000, 55100, 54900, 55000)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 5,
                'max_sl': 2000  # Very wide to test threshold
            },
            entry_side='LONG'
        )
        
        # SL should not go below entry threshold (0.5% below entry)
        min_allowed = 50000 * 0.995  # 49750
        assert result.new_sl >= min_allowed
    
    def test_trailing_sl_lock_gains_short(self):
        """Test SL doesn't go above entry for SHORT (lock gains)"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        # Price far below entry
        current_bar = create_bar(45000, 45100, 44900, 45000)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 5,
                'max_sl': 2000  # Very wide to test threshold
            },
            entry_side='SHORT'
        )
        
        # SL should not go above entry threshold (0.5% above entry)
        max_allowed = 50000 * 1.005  # 50250
        assert result.new_sl <= max_allowed
    
    def test_custom_emergency_sl_percent(self):
        """Test custom emergency SL percentage"""
        manager = AdaptiveSLManager()
        
        current_bar = create_bar(50100, 50200, 50000, 50100)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=5,
            lookback_bars=[],
            config={'delay_bars': 10, 'emergency_sl_percent': 0.5},  # 0.5%
            entry_side='LONG'
        )
        
        # Verify SL 0.5% below entry
        expected_sl = 50000 * 0.995  # 49750
        assert result.new_sl == expected_sl
    
    def test_default_config_values(self):
        """Test default configuration values"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        # Empty config - should use defaults
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=5,
            lookback_bars=lookback_bars,
            config={},  # No config
            entry_side='LONG'
        )
        
        # Should use default delay_bars=10
        # Bar 5 < 10, so emergency mode
        assert result.sl_mode == 'EMERGENCY'
    
    def test_vol_multi_scaling(self):
        """Test volatility multiplier scaling"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        # Test vol_multi = 10 (1.0x)
        result_1x = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 10,  # 1.0x
                'min_sl': 0,
                'max_sl': 10000
            },
            entry_side='LONG'
        )
        
        # Test vol_multi = 20 (2.0x)
        result_2x = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=lookback_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 20,  # 2.0x
                'min_sl': 0,
                'max_sl': 10000
            },
            entry_side='LONG'
        )
        
        # 2x should have wider SL distance
        assert result_2x.sl_distance > result_1x.sl_distance
    
    def test_dataclass_attributes(self):
        """Test AdaptiveSLResult dataclass attributes"""
        manager = AdaptiveSLManager()
        
        current_bar = create_bar(50100, 50200, 50000, 50100)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=5,
            lookback_bars=[],
            config={'delay_bars': 10, 'emergency_sl_percent': 1.0},
            entry_side='LONG'
        )
        
        # Verify all attributes present
        assert hasattr(result, 'new_sl')
        assert hasattr(result, 'sl_mode')
        assert hasattr(result, 'atr_value')
        assert hasattr(result, 'sl_distance')
        assert hasattr(result, 'reason')
        
        # Verify types
        assert isinstance(result.new_sl, float)
        assert isinstance(result.sl_mode, str)
        assert isinstance(result.atr_value, float)
        assert isinstance(result.sl_distance, float)
        assert isinstance(result.reason, str)


class TestAdaptiveSLIntegration:
    """Integration tests with realistic scenarios"""
    
    def test_volatile_market_wider_sl(self):
        """Test wider SL in volatile markets"""
        manager = AdaptiveSLManager()
        
        # High volatility bars
        volatile_bars = create_bars_with_atr(atr=1000.0, num_bars=20)
        
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=volatile_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 5,
                'max_sl': 200
            },
            entry_side='LONG'
        )
        
        # High volatility should result in wider SL
        assert result.sl_distance > 500
    
    def test_calm_market_tighter_sl(self):
        """Test tighter SL in calm markets"""
        manager = AdaptiveSLManager()
        
        # Low volatility bars
        calm_bars = create_bars_with_atr(atr=50.0, num_bars=20)
        
        current_bar = create_bar(50500, 50600, 50400, 50500)
        
        result = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=current_bar,
            bars_since_entry=15,
            lookback_bars=calm_bars,
            config={
                'delay_bars': 10,
                'vol_lookback': 20,
                'vol_multi': 15,
                'min_sl': 1,  # Very small min
                'max_sl': 200
            },
            entry_side='LONG'
        )
        
        # Low volatility should result in tighter SL (but respecting min)
        assert result.sl_distance < 1000
    
    def test_progression_through_trade(self):
        """Test SL progression from entry through trade lifecycle"""
        manager = AdaptiveSLManager()
        
        lookback_bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        config = {
            'delay_bars': 5,
            'emergency_sl_percent': 1.0,
            'vol_lookback': 20,
            'vol_multi': 15,
            'min_sl': 5,
            'max_sl': 20
        }
        
        # Bar 1: Emergency
        result_bar1 = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=create_bar(50100, 50200, 50000, 50100),
            bars_since_entry=1,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        assert result_bar1.sl_mode == 'EMERGENCY'
        
        # Bar 5: Still emergency (delay=5 means bar 5 is last emergency)
        result_bar5 = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=create_bar(50200, 50300, 50100, 50200),
            bars_since_entry=4,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        assert result_bar5.sl_mode == 'EMERGENCY'
        
        # Bar 6: Adaptive
        result_bar6 = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=create_bar(50300, 50400, 50200, 50300),
            bars_since_entry=5,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        assert result_bar6.sl_mode == 'ADAPTIVE'
        
        # Bar 20: Still adaptive, trailing
        result_bar20 = manager.update_sl(
            position_entry_price=50000.0,
            current_bar=create_bar(52000, 52100, 51900, 52000),
            bars_since_entry=20,
            lookback_bars=lookback_bars,
            config=config,
            entry_side='LONG'
        )
        assert result_bar20.sl_mode == 'ADAPTIVE'
        assert result_bar20.new_sl > result_bar6.new_sl  # SL should have trailed up
