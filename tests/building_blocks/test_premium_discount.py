"""
Unit tests for Premium & Discount Zones Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.smc_ict.premium_discount import PremiumDiscount


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=30, freq='15min')
    np.random.seed(42)
    highs = [45000 + np.random.uniform(-200, 200) for _ in range(30)]
    lows = [h - 300 for h in highs]
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        pd_detector = PremiumDiscount()
        assert pd_detector.timeframe == '15min'
        assert pd_detector.lookback == 20


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        pd_detector = PremiumDiscount()
        result = pd_detector.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_zone(self, sample_data):
        pd_detector = PremiumDiscount()
        result = pd_detector.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL']
        assert 'zone' in result['metadata']


class TestValidation:
    def test_missing_columns(self):
        pd_detector = PremiumDiscount()
        assert pd_detector.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        pd_detector = PremiumDiscount()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'high': [45100]*10, 'low': [44900]*10, 'close': [45000]*10
        })
        assert pd_detector.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
