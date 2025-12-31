"""
Unit tests for Liquidity Sweep Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_action.liquidity_sweep import LiquiditySweep


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-50, 50) for _ in range(50)]
    lows = [h - 100 for h in highs]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    opens = [c - 10 for c in closes]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        sweep = LiquiditySweep()
        assert sweep.timeframe == '15min'
        assert sweep.min_sweep_pct == 0.15


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        sweep = LiquiditySweep()
        result = sweep.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_sweep(self, sample_data):
        sweep = LiquiditySweep()
        result = sweep.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_SWEEP']


class TestValidation:
    def test_missing_columns(self):
        sweep = LiquiditySweep()
        assert sweep.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        sweep = LiquiditySweep()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='15min'),
            'open': [45000]*3, 'high': [45100]*3, 'low': [44900]*3, 'close': [45050]*3
        })
        assert sweep.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
