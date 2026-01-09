"""
Unit tests for Asia Session 50% Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50


@pytest.fixture
def sample_data():
    # Create data covering Asia session (0-8 UTC)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    np.random.seed(42)
    highs = 45000 + np.random.uniform(0, 500, 200)
    lows = 45000 - np.random.uniform(0, 500, 200)
    closes = (highs + lows) / 2
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.uniform(100, 1000, 200)
    })


class TestInitialization:
    def test_default(self):
        asia = AsiaSession50()
        assert asia.asia_start == 0
        assert asia.asia_end == 8


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        asia = AsiaSession50()
        result = asia.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_valid_data(self, sample_data):
        asia = AsiaSession50()
        result = asia.analyze(sample_data)
        assert result['signal'] in ['NEUTRAL', 'NO_ASIA_DATA', 'BULLISH', 'BEARISH']


class TestValidation:
    def test_missing_columns(self):
        asia = AsiaSession50()
        assert asia.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
