"""
Unit tests for Wedge Patterns
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.patterns.rising_wedge import RisingWedgePattern
from src.detectors.building_blocks.patterns.falling_wedge import FallingWedgePattern


@pytest.fixture
def base_data():
    """Create base data"""
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


class TestRisingWedge:
    def test_init(self):
        pattern = RisingWedgePattern()
        assert pattern.timeframe == '15min'
    
    def test_analysis(self, base_data):
        pattern = RisingWedgePattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
    
    def test_error(self):
        pattern = RisingWedgePattern()
        assert pattern.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


class TestFallingWedge:
    def test_init(self):
        pattern = FallingWedgePattern()
        assert pattern.timeframe == '15min'
    
    def test_analysis(self, base_data):
        pattern = FallingWedgePattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
    
    def test_error(self):
        pattern = FallingWedgePattern()
        assert pattern.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
