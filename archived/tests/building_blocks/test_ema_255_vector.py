"""
Unit tests for 255 EMA Vector Break Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_255_vector import EMA255VectorBreak


@pytest.fixture
def long_trending_data():
    """Create long trending data that crosses 255 EMA"""
    dates = pd.date_range(start='2024-01-01', periods=300, freq='15min')
    np.random.seed(42)
    
    # Create uptrend
    prices = [45000 + i * 20 for i in range(300)]
    highs = [p + np.random.uniform(50, 150) for p in prices]
    lows = [p - np.random.uniform(50, 150) for p in prices]
    closes = prices
    volumes = [np.random.uniform(100, 300) for _ in range(300)]
    
    # Add high volume spike at the end
    volumes[-1] = 500
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': [p - 50 for p in prices],
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


class TestInitialization:
    def test_default(self):
        ema = EMA255VectorBreak()
        assert ema.timeframe == '15min'
        assert ema.ema_period == 255
        assert ema.volume_threshold == 1.5
        assert ema.body_threshold == 0.6


class TestAnalysis:
    def test_standardized_format(self, long_trending_data):
        ema = EMA255VectorBreak()
        result = ema.analyze(long_trending_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_signals(self, long_trending_data):
        ema = EMA255VectorBreak()
        result = ema.analyze(long_trending_data)
        assert result['signal'] in ['BULLISH_BREAK', 'BEARISH_BREAK', 'BULLISH_CROSS', 'BEARISH_CROSS', 'NO_BREAK']
    
    def test_vector_candle_detection(self, long_trending_data):
        ema = EMA255VectorBreak()
        is_vector = ema.is_vector_candle(long_trending_data, len(long_trending_data) - 1)
        assert isinstance(is_vector, (bool, np.bool_))


class TestValidation:
    def test_missing_columns(self):
        ema = EMA255VectorBreak()
        assert ema.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        ema = EMA255VectorBreak()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': [45000]*100, 'high': [45100]*100,
            'low': [44900]*100, 'close': [45000]*100,
            'volume': [100]*100
        })
        assert ema.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
