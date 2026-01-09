"""
Unit tests for Triple Patterns
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.patterns.triple_top import TripleTopPattern
from src.detectors.building_blocks.patterns.triple_bottom import TripleBottomPattern


@pytest.fixture
def base_data():
    prices = list(range(44000, 45000, 50))
    dates = pd.date_range(start='2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestTripleTop:
    def test_init(self):
        p = TripleTopPattern()
        assert p.timeframe == '15min'
    
    def test_analysis(self, base_data):
        p = TripleTopPattern()
        r = p.analyze(base_data)
        assert 'signal' in r


class TestTripleBottom:
    def test_init(self):
        p = TripleBottomPattern()
        assert p.timeframe == '15min'
    
    def test_analysis(self, base_data):
        p = TripleBottomPattern()
        r = p.analyze(base_data)
        assert 'signal' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
