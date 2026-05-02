"""
Tests for TP/SL Calculator

Tests all 3 modes: Fibonacci, Hybrid, Fixed
Validates risk/reward calculations, ATR, and edge cases

Author: BTC_Engine_v3
Date: February 2026
"""

import pytest
from decimal import Decimal

from src.optimizer_v3.core.tpsl_calculator import (
    TPSLCalculator,
    TPSLLevels,
    get_tpsl_calculator
)
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import millis_to_nanos


# Create a reusable BarType for tests using from_str()
_test_bar_type = BarType.from_str("BTC.BINANCE-15-MINUTE-LAST-EXTERNAL")


def create_bar(open_price: float, high: float, low: float, close: float, volume: float = 1000.0, timestamp_ms: int = 1000000) -> Bar:
    """Helper to create test bars with proper NautilusTrader BarType"""
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


def create_bars_with_swing(swing_low: float, swing_high: float, num_bars: int = 20) -> list:
    """Create test bars with specific swing high/low"""
    bars = []
    for i in range(num_bars):
        # Create bars that form a range
        mid_price = (swing_high + swing_low) / 2
        high = swing_high if i == num_bars // 2 else mid_price + 50
        low = swing_low if i == num_bars // 4 else mid_price - 50
        bars.append(create_bar(
            open_price=mid_price,
            high=high,
            low=low,
            close=mid_price,
            timestamp_ms=1000000 + i * 1000
        ))
    return bars


def create_bars_with_atr(atr: float, num_bars: int = 20) -> list:
    """Create test bars with specific ATR"""
    bars = []
    base_price = 50000.0
    
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


class TestTPSLCalculator:
    """Test TP/SL Calculator"""
    
    def test_initialization(self):
        """Test calculator initialization"""
        calc = TPSLCalculator()
        assert calc is not None
    
    def test_singleton_pattern(self):
        """Test singleton pattern"""
        calc1 = get_tpsl_calculator()
        calc2 = get_tpsl_calculator()
        assert calc1 is calc2
    
    def test_fibonacci_calculation_long(self):
        """Test Fibonacci TP/SL calculation for LONG"""
        calc = TPSLCalculator()
        
        # Create test bars with swing
        lookback_bars = create_bars_with_swing(
            swing_low=49000.0,
            swing_high=50000.0
        )
        
        levels = calc.calculate_levels(
            entry_price=49800.0,
            mode='Fibonacci',
            lookback_bars=lookback_bars,
            config={},
            entry_side='LONG'
        )
        
        # Verify calculation mode
        assert levels.calculation_mode == 'Fibonacci'
        
        # Verify SL below swing low
        assert levels.stop_loss < 49000
        assert abs(levels.stop_loss - 48951.0) < 1  # 49000 * 0.999
        
        # Verify swing levels recorded
        assert levels.swing_high == 50000.0
        assert levels.swing_low == 49000.0
        
        # Verify TP at Fib levels
        swing_range = 50000 - 49000  # 1000
        expected_tp1 = 49800 + (1000 * 1.618)
        expected_tp2 = 49800 + (1000 * 2.618)
        expected_tp3 = 49800 + (1000 * 4.236)
        
        assert abs(levels.take_profit_1 - expected_tp1) < 10
        assert abs(levels.take_profit_2 - expected_tp2) < 10
        assert abs(levels.take_profit_3 - expected_tp3) < 10
        
        # Verify risk/reward
        assert levels.risk_reward_ratio > 1.5
        assert levels.risk_reward_ratio < 2.0
    
    def test_fibonacci_calculation_short(self):
        """Test Fibonacci TP/SL calculation for SHORT"""
        calc = TPSLCalculator()
        
        lookback_bars = create_bars_with_swing(
            swing_low=49000.0,
            swing_high=50000.0
        )
        
        levels = calc.calculate_levels(
            entry_price=49800.0,
            mode='Fibonacci',
            lookback_bars=lookback_bars,
            config={},
            entry_side='SHORT'
        )
        
        # Verify SL above swing high
        assert levels.stop_loss > 50000
        assert abs(levels.stop_loss - 50050.0) < 1  # 50000 * 1.001
        
        # Verify TP below entry (downward)
        assert levels.take_profit_1 < 49800
        assert levels.take_profit_2 < levels.take_profit_1
        assert levels.take_profit_3 < levels.take_profit_2
    
    def test_fixed_calculation_long(self):
        """Test Fixed % TP/SL calculation for LONG"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fixed',
            lookback_bars=[],
            config={'fixed_sl_percent': 1.0, 'fixed_tp_percent': 2.0},
            entry_side='LONG'
        )
        
        # Verify calculation mode
        assert levels.calculation_mode == 'Fixed'
        
        # Verify SL 1% below
        assert levels.stop_loss == 50000 * 0.99  # 49500
        
        # Verify TP at percentage targets
        assert levels.take_profit_1 == 50000 * 1.02  # 51000 (2%)
        assert levels.take_profit_2 == 50000 * 1.04  # 52000 (4%)
        assert levels.take_profit_3 == 50000 * 1.06  # 53000 (6%)
        
        # Verify risk/reward
        assert levels.risk_reward_ratio == 2.0
    
    def test_fixed_calculation_short(self):
        """Test Fixed % TP/SL calculation for SHORT"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fixed',
            lookback_bars=[],
            config={'fixed_sl_percent': 1.0, 'fixed_tp_percent': 2.0},
            entry_side='SHORT'
        )
        
        # Verify SL 1% above
        assert levels.stop_loss == 50000 * 1.01  # 50500
        
        # Verify TP below entry
        assert levels.take_profit_1 == 50000 * 0.98  # 49000 (2% down)
        assert levels.take_profit_2 == 50000 * 0.96  # 48000 (4% down)
        assert levels.take_profit_3 == 50000 * 0.94  # 47000 (6% down)
    
    def test_hybrid_calculation_with_atr(self):
        """Test Hybrid TP/SL with ATR buffer"""
        calc = TPSLCalculator()
        
        # Create bars with known ATR
        lookback_bars = create_bars_with_swing(49000.0, 50000.0, 20)
        
        # Test with ATR buffer enabled
        levels = calc.calculate_levels(
            entry_price=49800.0,
            mode='Hybrid',
            lookback_bars=lookback_bars,
            config={'use_atr_buffer': True},
            entry_side='LONG'
        )
        
        # Verify calculation mode
        assert levels.calculation_mode == 'Hybrid'
        
        # SL should be below Fibonacci SL due to ATR buffer
        fib_levels = calc._calculate_fibonacci_levels(49800.0, lookback_bars, 'LONG')
        assert levels.stop_loss < fib_levels.stop_loss
    
    def test_hybrid_calculation_without_atr(self):
        """Test Hybrid TP/SL without ATR buffer"""
        calc = TPSLCalculator()
        
        lookback_bars = create_bars_with_swing(49000.0, 50000.0, 20)
        
        # Test with ATR buffer disabled
        levels = calc.calculate_levels(
            entry_price=49800.0,
            mode='Hybrid',
            lookback_bars=lookback_bars,
            config={'use_atr_buffer': False},
            entry_side='LONG'
        )
        
        # Should match Fibonacci levels
        fib_levels = calc._calculate_fibonacci_levels(49800.0, lookback_bars, 'LONG')
        assert levels.stop_loss == fib_levels.stop_loss
    
    def test_atr_calculation(self):
        """Test ATR calculation accuracy"""
        calc = TPSLCalculator()
        
        # Create bars with known ATR
        # Note: create_bars_with_atr creates bars with high-low = 2*atr
        bars = create_bars_with_atr(atr=200.0, num_bars=20)
        
        atr = calc._calculate_atr(bars, period=14)
        
        # ATR should be approximately 400 (high-low = 2 * 200)
        assert abs(atr - 400.0) < 50  # Allow 50 variance
    
    def test_atr_calculation_insufficient_data(self):
        """Test ATR fallback with insufficient data"""
        calc = TPSLCalculator()
        
        # Create only 5 bars
        bars = create_bars_with_atr(atr=200.0, num_bars=5)
        
        atr = calc._calculate_atr(bars, period=14)
        
        # Should fallback to simple range
        assert atr > 0
    
    def test_fibonacci_fallback_insufficient_data(self):
        """Test Fibonacci fallback to Fixed when insufficient data"""
        calc = TPSLCalculator()
        
        # Only 5 bars (less than minimum 10)
        lookback_bars = create_bars_with_swing(49000.0, 50000.0, 5)
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fibonacci',
            lookback_bars=lookback_bars,
            config={},
            entry_side='LONG'
        )
        
        # Should fallback to Fixed with defaults
        assert levels.calculation_mode == 'Fixed'
    
    def test_fibonacci_empty_bars(self):
        """Test Fibonacci with no lookback bars"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fibonacci',
            lookback_bars=[],
            config={},
            entry_side='LONG'
        )
        
        # Should fallback to Fixed
        assert levels.calculation_mode == 'Fixed'
    
    def test_invalid_mode(self):
        """Test invalid TP/SL mode raises error"""
        calc = TPSLCalculator()
        
        with pytest.raises(ValueError, match="Unknown TP/SL mode"):
            calc.calculate_levels(
                entry_price=50000.0,
                mode='InvalidMode',
                lookback_bars=[],
                config={},
                entry_side='LONG'
            )
    
    def test_risk_reward_zero_risk(self):
        """Test risk/reward calculation with zero risk (edge case)"""
        calc = TPSLCalculator()
        
        # Create scenario where SL == entry (shouldn't happen but test defensively)
        levels = calc._calculate_fixed_levels(
            entry_price=50000.0,
            config={'fixed_sl_percent': 0.0, 'fixed_tp_percent': 2.0},
            entry_side='LONG'
        )
        
        # Risk = 0, should handle gracefully
        assert levels.risk_reward_ratio == 0.0
    
    def test_custom_fixed_percentages(self):
        """Test Fixed mode with custom percentages"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fixed',
            lookback_bars=[],
            config={'fixed_sl_percent': 0.5, 'fixed_tp_percent': 3.0},
            entry_side='LONG'
        )
        
        # Verify custom SL (0.5%)
        assert levels.stop_loss == 50000 * 0.995  # 49750
        
        # Verify custom TP (3%)
        assert levels.take_profit_1 == 50000 * 1.03  # 51500
    
    def test_default_fixed_percentages(self):
        """Test Fixed mode with default percentages"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fixed',
            lookback_bars=[],
            config={},  # No percentages provided
            entry_side='LONG'
        )
        
        # Should use defaults: SL 1%, TP 2%
        assert levels.stop_loss == 50000 * 0.99
        assert levels.take_profit_1 == 50000 * 1.02
    
    def test_dataclass_attributes(self):
        """Test TPSLLevels dataclass attributes"""
        calc = TPSLCalculator()
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fixed',
            lookback_bars=[],
            config={},
            entry_side='LONG'
        )
        
        # Verify all required attributes present
        assert hasattr(levels, 'stop_loss')
        assert hasattr(levels, 'take_profit_1')
        assert hasattr(levels, 'take_profit_2')
        assert hasattr(levels, 'take_profit_3')
        assert hasattr(levels, 'calculation_mode')
        assert hasattr(levels, 'swing_high')
        assert hasattr(levels, 'swing_low')
        assert hasattr(levels, 'risk_reward_ratio')
        
        # Verify types
        assert isinstance(levels.stop_loss, float)
        assert isinstance(levels.take_profit_1, float)
        assert isinstance(levels.calculation_mode, str)
        
        # Optional fields should be None for Fixed mode
        assert levels.swing_high is None
        assert levels.swing_low is None


class TestTPSLCalculatorIntegration:
    """Integration tests with real-world scenarios"""
    
    def test_bull_market_scenario(self):
        """Test TP/SL in bull market conditions"""
        calc = TPSLCalculator()
        
        # Create uptrending bars
        bars = []
        for i in range(20):
            base = 49000 + (i * 50)  # Uptrend
            bars.append(create_bar(base, base + 100, base - 50, base + 50, timestamp_ms=1000000 + i * 1000))
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fibonacci',
            lookback_bars=bars,
            config={},
            entry_side='LONG'
        )
        
        # Should have positive risk/reward
        assert levels.risk_reward_ratio > 1.0
        assert levels.take_profit_1 > 50000
        assert levels.stop_loss < 50000
    
    def test_bear_market_scenario(self):
        """Test TP/SL in bear market conditions"""
        calc = TPSLCalculator()
        
        # Create downtrending bars
        bars = []
        for i in range(20):
            base = 51000 - (i * 50)  # Downtrend  
            bars.append(create_bar(base, base + 50, base - 100, base - 50, timestamp_ms=1000000 + i * 1000))
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Fibonacci',
            lookback_bars=bars,
            config={},
            entry_side='SHORT'
        )
        
        # Should have positive risk/reward for SHORT
        assert levels.risk_reward_ratio > 1.0
        assert levels.take_profit_1 < 50000  # TP below for SHORT
        assert levels.stop_loss > 50000  # SL above for SHORT
    
    def test_volatile_market_scenario(self):
        """Test TP/SL in high volatility"""
        calc = TPSLCalculator()
        
        # Create volatile bars (large swings)
        bars = create_bars_with_atr(atr=500.0, num_bars=20)
        
        levels = calc.calculate_levels(
            entry_price=50000.0,
            mode='Hybrid',
            lookback_bars=bars,
            config={'use_atr_buffer': True},
            entry_side='LONG'
        )
        
        # Wider SL in volatile conditions
        sl_distance = abs(50000 - levels.stop_loss)
        assert sl_distance > 400  # Wider than typical
