"""
Unit tests for Fair Value Gap Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_action.fair_value_gap import FairValueGap


@pytest.fixture
def sample_data_with_fvg():
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    highs = [45000]
    lows = [44900]
    for i in range(99):
        if i == 50:
            highs.append(45100); lows.append(45000)
        elif i == 51:
            highs.append(45300); lows.append(45200)
        elif i == 52:
            highs.append(45400); lows.append(45250)
        else:
            highs.append(highs[-1] + np.random.uniform(-20, 20))
            lows.append(highs[-1] - 100)
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': [(h + l) / 2 for h, l in zip(highs, lows)]
    })


class TestInitialization:
    def test_default(self):
        fvg = FairValueGap()
        assert fvg.timeframe == '15min'
        assert fvg.min_gap_pct == 0.2


class TestAnalysis:
    def test_standardized_format(self, sample_data_with_fvg):
        fvg = FairValueGap()
        result = fvg.analyze(sample_data_with_fvg)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_fvg(self, sample_data_with_fvg):
        fvg = FairValueGap()
        result = fvg.analyze(sample_data_with_fvg)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_FVG']


class TestValidation:
    def test_missing_columns(self):
        fvg = FairValueGap()
        assert fvg.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        fvg = FairValueGap()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min'),
            'high': [45100]*5, 'low': [44900]*5, 'close': [45000]*5
        })
        assert fvg.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
