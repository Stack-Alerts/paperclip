"""
Unit tests for Swing Failure Pattern Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.swing_failure_pattern import SwingFailurePattern


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=30, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-100, 100) for _ in range(30)]
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
        sfp = SwingFailurePattern()
        assert sfp.timeframe == '15min'
        assert sfp.swing_lookback == 10


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        sfp = SwingFailurePattern()
        result = sfp.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_sfp(self, sample_data):
        sfp = SwingFailurePattern()
        result = sfp.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NO_SFP']


class TestValidation:
    def test_missing_columns(self):
        sfp = SwingFailurePattern()
        assert sfp.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        sfp = SwingFailurePattern()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert sfp.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
