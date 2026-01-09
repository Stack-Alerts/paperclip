"""
Unit tests for Break of Structure Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.break_of_structure import BreakOfStructure


@pytest.fixture
def uptrend_data():
    dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
    np.random.seed(42)
    # Create uptrend
    highs = [45000 + i*10 + np.random.uniform(-50, 50) for i in range(50)]
    lows = [h - 150 for h in highs]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        bos = BreakOfStructure()
        assert bos.timeframe == '15min'
        assert bos.swing_lookback == 10


class TestAnalysis:
    def test_standardized_format(self, uptrend_data):
        bos = BreakOfStructure()
        result = bos.analyze(uptrend_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_bos(self, uptrend_data):
        bos = BreakOfStructure()
        result = bos.analyze(uptrend_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_BOS']


class TestValidation:
    def test_missing_columns(self):
        bos = BreakOfStructure()
        assert bos.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        bos = BreakOfStructure()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert bos.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
