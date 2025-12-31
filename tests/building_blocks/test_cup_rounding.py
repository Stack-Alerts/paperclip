"""
Unit tests for Cup and Handle and Rounding Bottom
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.patterns.cup_and_handle import CupAndHandlePattern
from src.detectors.building_blocks.patterns.rounding_bottom import RoundingBottomPattern


@pytest.fixture
def base_data():
    prices = list(range(44000, 45000, 25))
    dates = pd.date_range(start='2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestCupAndHandle:
    def test_init(self):
        p = CupAndHandlePattern()
        assert p.timeframe == '15min'
    
    def test_analysis(self, base_data):
        p = CupAndHandlePattern()
        r = p.analyze(base_data)
        assert 'signal' in r


class TestRoundingBottom:
    def test_init(self):
        p = RoundingBottomPattern()
        assert p.timeframe == '15min'
    
    def test_analysis(self, base_data):
        p = RoundingBottomPattern()
        r = p.analyze(base_data)
        assert 'signal' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
