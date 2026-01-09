"""
Unit tests for Balanced Price Range Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.balanced_price_range import BalancedPriceRange


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=30, freq='15min')
    np.random.seed(42)
    # Create ranging data
    highs = [45100 + np.random.uniform(-50, 50) for _ in range(30)]
    lows = [44900 + np.random.uniform(-50, 50) for _ in range(30)]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        bpr = BalancedPriceRange()
        assert bpr.timeframe == '15min'
        assert bpr.lookback == 20


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        bpr = BalancedPriceRange()
        result = bpr.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_balance(self, sample_data):
        bpr = BalancedPriceRange()
        result = bpr.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_BALANCE']


class TestValidation:
    def test_missing_columns(self):
        bpr = BalancedPriceRange()
        assert bpr.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        bpr = BalancedPriceRange()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert bpr.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
