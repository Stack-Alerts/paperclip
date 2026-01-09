"""
Unit tests for Breaker Block Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_action.breaker_block import BreakerBlock


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    closes = [45000 + np.random.uniform(-50, 50) for _ in range(100)]
    opens = [c - 10 for c in closes]
    highs = [max(o, c) + 20 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 20 for o, c in zip(opens, closes)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    })


class TestInitialization:
    def test_default(self):
        breaker = BreakerBlock()
        assert breaker.timeframe == '15min'
        assert breaker.min_break_pct == 0.3


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        breaker = BreakerBlock()
        result = breaker.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_breaker(self, sample_data):
        breaker = BreakerBlock()
        result = breaker.analyze(sample_data)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_BREAKER']


class TestValidation:
    def test_missing_columns(self):
        breaker = BreakerBlock()
        assert breaker.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        breaker = BreakerBlock()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min'),
            'open': [45000]*5, 'high': [45100]*5, 'low': [44900]*5, 'close': [45050]*5
        })
        assert breaker.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
