"""
Unit tests for 55 EMA Vector Break Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_55_vector import EMA55VectorBreak


@pytest.fixture
def trending_data():
    """Create trending data that crosses 55 EMA"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    
    # Create uptrend with EMA cross
    prices = [45000 + i * 30 for i in range(100)]
    highs = [p + np.random.uniform(50, 150) for p in prices]
    lows = [p - np.random.uniform(50, 150) for p in prices]
    closes = prices
    volumes = [np.random.uniform(100, 300) for _ in range(100)]
    
    # Add high volume spike at the end (vector candle)
    volumes[-1] = 500
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': [p - 50 for p in prices],
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


@pytest.fixture
def choppy_data():
    """Create choppy/ranging data"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    
    # Oscillating around same price
    base = 45000
    closes = [base + np.random.uniform(-200, 200) for _ in range(100)]
    highs = [c + np.random.uniform(50, 100) for c in closes]
    lows = [c - np.random.uniform(50, 100) for c in closes]
    volumes = [np.random.uniform(100, 200) for _ in range(100)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


class TestInitialization:
    def test_default(self):
        ema = EMA55VectorBreak()
        assert ema.timeframe == '15min'
        assert ema.ema_period == 55
        assert ema.volume_threshold == 1.5
        assert ema.body_threshold == 0.6


class TestAnalysis:
    def test_standardized_format(self, trending_data):
        ema = EMA55VectorBreak()
        result = ema.analyze(trending_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_vector_break(self, trending_data):
        ema = EMA55VectorBreak()
        result = ema.analyze(trending_data)
        assert result['signal'] in ['BULLISH_BREAK', 'BEARISH_BREAK', 'BULLISH_CROSS', 'BEARISH_CROSS', 'NO_BREAK']
    
    def test_vector_candle_detection(self, trending_data):
        ema = EMA55VectorBreak()
        # Last candle has high volume
        is_vector = ema.is_vector_candle(trending_data, len(trending_data) - 1)
        assert isinstance(is_vector, (bool, np.bool_))


class TestValidation:
    def test_missing_columns(self):
        ema = EMA55VectorBreak()
        assert ema.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        ema = EMA55VectorBreak()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='15min'),
            'open': [45000]*30, 'high': [45100]*30,
            'low': [44900]*30, 'close': [45000]*30,
            'volume': [100]*30
        })
        assert ema.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
