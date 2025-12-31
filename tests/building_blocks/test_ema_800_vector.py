"""
Unit tests for 800 EMA Vector Break Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_800_vector import EMA800VectorBreak


@pytest.fixture
def macro_trending_data():
    """Create very long-term trending data that crosses 800 EMA"""
    dates = pd.date_range(start='2024-01-01', periods=850, freq='1H')  # ~35 days hourly
    np.random.seed(42)
    
    # Create very long uptrend for macro analysis
    prices = [45000 + i * 15 for i in range(850)]
    highs = [p + np.random.uniform(50, 150) for p in prices]
    lows = [p - np.random.uniform(50, 150) for p in prices]
    closes = prices
    volumes = [np.random.uniform(100, 300) for _ in range(850)]
    
    # Add high volume spike at the end (vector candle)
    volumes[-1] = 600
    
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
        ema = EMA800VectorBreak()
        assert ema.timeframe == '15min'
        assert ema.ema_period == 800
        assert ema.volume_threshold == 1.5
        assert ema.body_threshold == 0.6


class TestAnalysis:
    def test_standardized_format(self, macro_trending_data):
        ema = EMA800VectorBreak()
        result = ema.analyze(macro_trending_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_signals(self, macro_trending_data):
        ema = EMA800VectorBreak()
        result = ema.analyze(macro_trending_data)
        assert result['signal'] in ['BULLISH_BREAK', 'BEARISH_BREAK', 'BULLISH_CROSS', 'BEARISH_CROSS', 'NO_BREAK']
    
    def test_vector_candle_detection(self, macro_trending_data):
        ema = EMA800VectorBreak()
        is_vector = ema.is_vector_candle(macro_trending_data, len(macro_trending_data) - 1)
        assert isinstance(is_vector, (bool, np.bool_))
    
    def test_macro_significance(self, macro_trending_data):
        """Test that 800 EMA is marked as macro cycle indicator"""
        ema = EMA800VectorBreak()
        result = ema.analyze(macro_trending_data)
        assert 'significance' in result['metadata']
        assert 'EXTREME' in result['metadata']['significance']


class TestValidation:
    def test_missing_columns(self):
        ema = EMA800VectorBreak()
        assert ema.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        ema = EMA800VectorBreak()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=400, freq='1H'),
            'open': [45000]*400, 'high': [45100]*400,
            'low': [44900]*400, 'close': [45000]*400,
            'volume': [100]*400
        })
        assert ema.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
