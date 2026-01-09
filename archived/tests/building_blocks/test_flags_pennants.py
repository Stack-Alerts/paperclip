"""
Unit tests for Flag and Pennant Patterns
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.patterns.flag_pattern import FlagPattern
from src.detectors.building_blocks.patterns.pennant_pattern import PennantPattern


@pytest.fixture
def base_data():
    """Create base data with strong move"""
    # Strong move then consolidation
    prices = [44000] * 5 + list(range(44000, 46000, 200)) + [46000] * 10
    dates = pd.date_range(start='2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestFlagPattern:
    def test_init(self):
        pattern = FlagPattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 10
    
    def test_analysis(self, base_data):
        pattern = FlagPattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
        assert 'confidence' in result
    
    def test_missing_columns(self):
        pattern = FlagPattern()
        result = pattern.analyze(pd.DataFrame({'wrong': [1]}))
        assert result['signal'] == 'ERROR'


class TestPennantPattern:
    def test_init(self):
        pattern = PennantPattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 10
    
    def test_analysis(self, base_data):
        pattern = PennantPattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
        assert 'confidence' in result
    
    def test_missing_columns(self):
        pattern = PennantPattern()
        result = pattern.analyze(pd.DataFrame({'wrong': [1]}))
        assert result['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
