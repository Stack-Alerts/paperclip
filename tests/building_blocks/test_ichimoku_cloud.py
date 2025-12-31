"""
Unit tests for Ichimoku Cloud Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.trend.ichimoku_cloud import IchimokuCloud


@pytest.fixture
def uptrend_data():
    """Create uptrending data"""
    dates = pd.date_range(start='2024-01-01', periods=70, freq='15min')
    np.random.seed(42)
    highs = [45000 + i * 50 + np.random.uniform(0, 50) for i in range(70)]
    lows = [h - 200 for h in highs]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


@pytest.fixture
def downtrend_data():
    """Create downtrending data"""
    dates = pd.date_range(start='2024-01-01', periods=70, freq='15min')
    np.random.seed(42)
    highs = [45000 - i * 50 + np.random.uniform(0, 50) for i in range(70)]
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
        ich = IchimokuCloud()
        assert ich.timeframe == '15min'
        assert ich.tenkan_period == 9
        assert ich.kijun_period == 26
        assert ich.senkou_period == 52


class TestAnalysis:
    def test_standardized_format(self, uptrend_data):
        ich = IchimokuCloud()
        result = ich.analyze(uptrend_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_trend(self, uptrend_data):
        ich = IchimokuCloud()
        result = ich.analyze(uptrend_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL']
    
    def test_cloud_components(self, uptrend_data):
        ich = IchimokuCloud()
        result = ich.analyze(uptrend_data)
        assert 'tenkan' in result['metadata']
        assert 'kijun' in result['metadata']
        assert 'senkou_a' in result['metadata']
        assert 'senkou_b' in result['metadata']


class TestValidation:
    def test_missing_columns(self):
        ich = IchimokuCloud()
        assert ich.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        ich = IchimokuCloud()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='15min'),
            'high': [45100]*30, 'low': [44900]*30, 'close': [45000]*30
        })
        assert ich.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
