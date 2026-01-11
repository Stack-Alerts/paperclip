"""
Institutional-Grade Unit Tests for TP/SL Calculations
======================================================

Tests the Dynamic TP and SL calculators to ensure:
- Correct directional logic for LONG/SHORT
- Fibonacci projections work properly
- All validation checks pass
- No regression bugs

Author: Institutional Research
Date: 2026-01-11
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.universal_optimizer.modules.dynamic_tp_calculator import (
    DynamicTPCalculator,
    TPLevels
)
from src.strategies.universal_optimizer.modules.dynamic_sl_calculator import (
    AdaptiveSLCalculator,
    AdaptiveSLResult
)


class TestFibonacciTPCalculator:
    """Test Fibonacci TP calculations (FIXED version)"""
    
    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV data for testing"""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='15min')
        
        # Create realistic price action with swing
        base_price = 45000
        prices = []
        for i in range(100):
            # Simulate swing: low at start, high in middle, back down
            if i < 30:
                price = base_price + (i * 20)  # Rising
            elif i < 60:
                price = base_price + 600 - ((i - 30) * 15)  # Falling
            else:
                price = base_price + 150 + ((i - 60) * 10)  # Rising again
            prices.append(price)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + np.random.uniform(10, 50) for p in prices],
            'low': [p - np.random.uniform(10, 50) for p in prices],
            'close': [p + np.random.uniform(-20, 20) for p in prices],
            'volume': [np.random.uniform(100, 1000) for _ in prices]
        })
        
        return df
    
    def test_fibonacci_long_tps_above_entry(self, sample_df):
        """Test LONG: All TPs must be above entry price"""
        calculator = DynamicTPCalculator(tp_mode='FIBONACCI')
        
        entry_price = 45200.0
        entry_bar = 70
        side = 'LONG'
        
        result = calculator.calculate_tp_levels(
            df=sample_df,
            entry_price=entry_price,
            entry_bar=entry_bar,
            side=side
        )
        
        # CRITICAL: All TPs must be above entry for LONG
        assert result.tp1 > entry_price, f"TP1 ({result.tp1}) must be above entry ({entry_price}) for LONG"
        assert result.tp2 > entry_price, f"TP2 ({result.tp2}) must be above entry ({entry_price}) for LONG"
        assert result.tp3 > entry_price, f"TP3 ({result.tp3}) must be above entry ({entry_price}) for LONG"
        
        # SL must be below entry for LONG
        assert result.sl < entry_price, f"SL ({result.sl}) must be below entry ({entry_price}) for LONG"
        
        # TPs should be in order (tp1 < tp2 < tp3)
        assert result.tp1 < result.tp2 < result.tp3, "TPs should be in ascending order for LONG"
        
        # Method should be FIBONACCI_PROJECTION (fixed version)
        assert result.method == 'FIBONACCI_PROJECTION', f"Expected FIBONACCI_PROJECTION, got {result.method}"
    
    def test_fibonacci_short_tps_below_entry(self, sample_df):
        """Test SHORT: All TPs must be below entry price"""
        calculator = DynamicTPCalculator(tp_mode='FIBONACCI')
        
        entry_price = 45800.0
        entry_bar = 40
        side = 'SHORT'
        
        result = calculator.calculate_tp_levels(
            df=sample_df,
            entry_price=entry_price,
            entry_bar=entry_bar,
            side=side
        )
        
        # CRITICAL: All TPs must be below entry for SHORT
        assert result.tp1 < entry_price, f"TP1 ({result.tp1}) must be below entry ({entry_price}) for SHORT"
        assert result.tp2 < entry_price, f"TP2 ({result.tp2}) must be below entry ({entry_price}) for SHORT"
        assert result.tp3 < entry_price, f"TP3 ({result.tp3}) must be below entry ({entry_price}) for SHORT"
        
        # SL must be above entry for SHORT
        assert result.sl > entry_price, f"SL ({result.sl}) must be above entry ({entry_price}) for SHORT"
        
        # TPs should be in order (tp1 > tp2 > tp3)
        assert result.tp1 > result.tp2 > result.tp3, "TPs should be in descending order for SHORT"
        
        # Method should be FIBONACCI_PROJECTION
        assert result.method == 'FIBONACCI_PROJECTION', f"Expected FIBONACCI_PROJECTION, got {result.method}"
    
    def test_fibonacci_tp_distances_reasonable(self, sample_df):
        """Test that TP distances are within reasonable ranges"""
        calculator = DynamicTPCalculator(tp_mode='FIBONACCI')
        
        entry_price = 45500.0
        entry_bar = 60
        
        for side in ['LONG', 'SHORT']:
            result = calculator.calculate_tp_levels(
                df=sample_df,
                entry_price=entry_price,
                entry_bar=entry_bar,
                side=side
            )
            
            # Calculate distances
            if side == 'LONG':
                tp1_dist_pct = ((result.tp1 - entry_price) / entry_price) * 100
                tp2_dist_pct = ((result.tp2 - entry_price) / entry_price) * 100
                tp3_dist_pct = ((result.tp3 - entry_price) / entry_price) * 100
            else:
                tp1_dist_pct = ((entry_price - result.tp1) / entry_price) * 100
                tp2_dist_pct = ((entry_price - result.tp2) / entry_price) * 100
                tp3_dist_pct = ((entry_price - result.tp3) / entry_price) * 100
            
            # TP1: 0.5-3% range
            assert 0.5 <= tp1_dist_pct <= 3.0, f"TP1 distance {tp1_dist_pct}% outside reasonable range"
            
            # TP3: Should be larger but not extreme (max 8%)
            assert tp3_dist_pct <= 8.0, f"TP3 distance {tp3_dist_pct}% too large"
            
            # TP2 should be between TP1 and TP3
            assert tp1_dist_pct < tp2_dist_pct < tp3_dist_pct, "TP distances should be ordered"
    
    def test_fibonacci_metadata_complete(self, sample_df):
        """Test that metadata contains all required fields"""
        calculator = DynamicTPCalculator(tp_mode='FIBONACCI')
        
        result = calculator.calculate_tp_levels(
            df=sample_df,
            entry_price=45500.0,
            entry_bar=60,
            side='LONG'
        )
        
        # Check metadata fields
        assert 'swing_range' in result.metadata
        assert 'recent_high' in result.metadata
        assert 'recent_low' in result.metadata
        assert 'projection_type' in result.metadata
        assert 'tp1_pct' in result.metadata
        assert 'tp2_pct' in result.metadata
        assert 'tp3_pct' in result.metadata
        
        # Verify swing range is positive
        assert result.metadata['swing_range'] > 0
        
        # Verify projection type
        assert result.metadata['projection_type'] == 'fibonacci_extensions'


class TestPercentageTPCalculator:
    """Test percentage-based TP fallback"""
    
    def test_percentage_long_tps(self):
        """Test LONG percentage TPs"""
        calculator = DynamicTPCalculator(tp_mode='PERCENTAGE')
        
        # Create minimal df (percentage mode doesn't need real data)
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=10, freq='15min'),
            'open': [45000] * 10,
            'high': [45100] * 10,
            'low': [44900] * 10,
            'close': [45000] * 10,
            'volume': [100] * 10
        })
        
        entry_price = 45000.0
        fallback_pcts = {'tp1': 1.0, 'tp2': 2.0, 'tp3': 3.5}
        
        result = calculator.calculate_tp_levels(
            df=df,
            entry_price=entry_price,
            entry_bar=5,
            side='LONG',
            fallback_pcts=fallback_pcts
        )
        
        # Verify percentages applied correctly
        expected_tp1 = entry_price * 1.01  # +1%
        expected_tp2 = entry_price * 1.02  # +2%
        expected_tp3 = entry_price * 1.035  # +3.5%
        
        assert abs(result.tp1 - expected_tp1) < 1.0, "TP1 percentage incorrect"
        assert abs(result.tp2 - expected_tp2) < 1.0, "TP2 percentage incorrect"
        assert abs(result.tp3 - expected_tp3) < 1.0, "TP3 percentage incorrect"
    
    def test_percentage_short_tps(self):
        """Test SHORT percentage TPs"""
        calculator = DynamicTPCalculator(tp_mode='PERCENTAGE')
        
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=10, freq='15min'),
            'open': [45000] * 10,
            'high': [45100] * 10,
            'low': [44900] * 10,
            'close': [45000] * 10,
            'volume': [100] * 10
        })
        
        entry_price = 45000.0
        fallback_pcts = {'tp1': 1.0, 'tp2': 2.0, 'tp3': 3.5}
        
        result = calculator.calculate_tp_levels(
            df=df,
            entry_price=entry_price,
            entry_bar=5,
            side='SHORT',
            fallback_pcts=fallback_pcts
        )
        
        # Verify percentages applied correctly (negative for SHORT)
        expected_tp1 = entry_price * 0.99  # -1%
        expected_tp2 = entry_price * 0.98  # -2%
        expected_tp3 = entry_price * 0.965  # -3.5%
        
        assert abs(result.tp1 - expected_tp1) < 1.0, "TP1 percentage incorrect"
        assert abs(result.tp2 - expected_tp2) < 1.0, "TP2 percentage incorrect"
        assert abs(result.tp3 - expected_tp3) < 1.0, "TP3 percentage incorrect"


class TestAdaptiveSLCalculator:
    """Test Adaptive SL calculations"""
    
    @pytest.fixture
    def sample_df(self):
        """Create sample data for SL testing"""
        dates = pd.date_range(start='2025-01-01', periods=50, freq='15min')
        base_price = 45000
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': [base_price + np.random.uniform(-100, 100) for _ in range(50)],
            'high': [base_price + np.random.uniform(50, 150) for _ in range(50)],
            'low': [base_price + np.random.uniform(-150, -50) for _ in range(50)],
            'close': [base_price + np.random.uniform(-100, 100) for _ in range(50)],
            'volume': [np.random.uniform(100, 1000) for _ in range(50)]
        })
        
        return df
    
    def test_sl_long_below_entry(self, sample_df):
        """Test LONG: SL must be below entry"""
        calculator = AdaptiveSLCalculator()
        
        entry_price = 45200.0
        entry_bar = 30
        side = 'LONG'
        
        result = calculator.calculate_sl_levels(
            df=sample_df,
            entry_price=entry_price,
            entry_bar=entry_bar,
            side=side
        )
        
        # Both emergency and working SL must be below entry for LONG
        assert result.emergency_sl < entry_price, f"Emergency SL ({result.emergency_sl}) must be below entry for LONG"
        assert result.working_sl < entry_price, f"Working SL ({result.working_sl}) must be below entry for LONG"
        
        # Emergency SL should be wider than working SL
        assert result.emergency_sl < result.working_sl, "Emergency SL should be wider (lower) than working SL for LONG"
    
    def test_sl_short_above_entry(self, sample_df):
        """Test SHORT: SL must be above entry"""
        calculator = AdaptiveSLCalculator()
        
        entry_price = 45200.0
        entry_bar = 30
        side = 'SHORT'
        
        result = calculator.calculate_sl_levels(
            df=sample_df,
            entry_price=entry_price,
            entry_bar=entry_bar,
            side=side
        )
        
        # Both emergency and working SL must be above entry for SHORT
        assert result.emergency_sl > entry_price, f"Emergency SL ({result.emergency_sl}) must be above entry for SHORT"
        assert result.working_sl > entry_price, f"Working SL ({result.working_sl}) must be above entry for SHORT"
        
        # Emergency SL should be wider than working SL
        assert result.emergency_sl > result.working_sl, "Emergency SL should be wider (higher) than working SL for SHORT"
    
    def test_sl_distance_reasonable(self, sample_df):
        """Test SL distances are within reasonable bounds"""
        calculator = AdaptiveSLCalculator(
            absolute_min_pct=0.7,
            absolute_max_pct=2.0
        )
        
        entry_price = 45200.0
        entry_bar = 30
        
        for side in ['LONG', 'SHORT']:
            result = calculator.calculate_sl_levels(
                df=sample_df,
                entry_price=entry_price,
                entry_bar=entry_bar,
                side=side
            )
            
            # Calculate distance percentages
            working_sl_dist_pct = abs(result.working_sl - entry_price) / entry_price * 100
            emergency_sl_dist_pct = abs(result.emergency_sl - entry_price) / entry_price * 100
            
            # Working SL should be within bounds (with floating point tolerance)
            assert 0.69 <= working_sl_dist_pct <= 2.01, f"Working SL distance {working_sl_dist_pct}% outside bounds"
            
            # Emergency SL should be wider (2.5% default)
            assert emergency_sl_dist_pct >= working_sl_dist_pct - 0.01, "Emergency SL should be wider than working SL"


class TestTPSLIntegration:
    """Test TP and SL work together correctly"""
    
    def test_tp_sl_risk_reward_ratio(self):
        """Test that TP/SL combinations provide good risk:reward"""
        tp_calculator = DynamicTPCalculator(tp_mode='FIBONACCI')
        sl_calculator = AdaptiveSLCalculator()
        
        # Create sample data
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=100, freq='15min'),
            'open': [45000 + i * 10 for i in range(100)],
            'high': [45000 + i * 10 + 50 for i in range(100)],
            'low': [45000 + i * 10 - 50 for i in range(100)],
            'close': [45000 + i * 10 for i in range(100)],
            'volume': [100] * 100
        })
        
        entry_price = 45500.0
        entry_bar = 50
        side = 'LONG'
        
        # Calculate TP and SL
        tp_result = tp_calculator.calculate_tp_levels(df, entry_price, entry_bar, side)
        sl_result = sl_calculator.calculate_sl_levels(df, entry_price, entry_bar, side)
        
        # Calculate risk:reward ratios
        risk = abs(entry_price - sl_result.working_sl)
        reward_tp1 = abs(tp_result.tp1 - entry_price)
        reward_tp2 = abs(tp_result.tp2 - entry_price)
        reward_tp3 = abs(tp_result.tp3 - entry_price)
        
        rr_tp1 = reward_tp1 / risk if risk > 0 else 0
        rr_tp2 = reward_tp2 / risk if risk > 0 else 0
        rr_tp3 = reward_tp3 / risk if risk > 0 else 0
        
        # Minimum R:R ratios (institutional standards)
        assert rr_tp1 >= 0.8, f"TP1 R:R {rr_tp1:.2f} below minimum 0.8:1"
        assert rr_tp2 >= 1.5, f"TP2 R:R {rr_tp2:.2f} below minimum 1.5:1"
        assert rr_tp3 >= 2.5, f"TP3 R:R {rr_tp3:.2f} below minimum 2.5:1"


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
