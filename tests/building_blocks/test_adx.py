"""
Unit tests for ADX Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.trend.adx import ADX


@pytest.fixture
def trending_data():
    """Create strongly trending upward data"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
    np.random.seed(42)
    highs = [45000 + i * 100 + np.random.uniform(0, 50) for i in range(50)]
    lows = [h - 200 for h in highs]
    closes = [(h + l) / 2 + np.random.uniform(-50, 50) for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


@pytest.fixture
def ranging_data():
    """Create ranging/choppy data"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-100, 100) for _ in range(50)]
    lows = [h - 200 for h in highs]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        adx = ADX()
        assert adx.timeframe == '15min'
        assert adx.period == 14


class TestAnalysis:
    def test_standardized_format(self, trending_data):
        adx = ADX()
        result = adx.analyze(trending_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_trending(self, trending_data):
        adx = ADX()
        result = adx.analyze(trending_data)
        assert result['signal'] in ['TRENDING', 'STRONG_TREND', 'VERY_STRONG_TREND']
    
    def test_detects_ranging(self, ranging_data):
        adx = ADX()
        result = adx.analyze(ranging_data)
        # Ranging data should have low ADX
        assert result['metadata']['adx'] < 50


class TestValidation:
    def test_missing_columns(self):
        adx = ADX()
        assert adx.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        adx = ADX()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert adx.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
