"""
Unit tests for Market Structure Shift Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.market_structure_shift import MarketStructureShift


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-100, 100) for _ in range(50)]
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
        mss = MarketStructureShift()
        assert mss.timeframe == '15min'
        assert mss.swing_lookback == 10


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        mss = MarketStructureShift()
        result = mss.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_mss(self, sample_data):
        mss = MarketStructureShift()
        result = mss.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_MSS']


class TestValidation:
    def test_missing_columns(self):
        mss = MarketStructureShift()
        assert mss.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        mss = MarketStructureShift()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min'),
            'high': [45100]*5, 'low': [44900]*5, 'close': [45000]*5
        })
        assert mss.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
