"""
Unit tests for Displacement Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.displacement import Displacement


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=30, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-100, 100) for _ in range(30)]
    lows = [h - 150 for h in highs]
    opens = [(h + l) / 2 for h, l in zip(highs, lows)]
    closes = [(h + l) / 2 + np.random.uniform(-50, 50) for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        disp = Displacement()
        assert disp.timeframe == '15min'
        assert disp.lookback == 20


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        disp = Displacement()
        result = disp.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_displacement(self, sample_data):
        disp = Displacement()
        result = disp.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NO_DISPLACEMENT']


class TestValidation:
    def test_missing_columns(self):
        disp = Displacement()
        assert disp.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        disp = Displacement()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert disp.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
