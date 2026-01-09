"""
Unit tests for Double Top Pattern
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern


@pytest.fixture
def pattern_data():
    """Create data with Double Top pattern"""
    prices = [44000] * 10 + [46000] * 3 + [45000] * 5 + [46000] * 3 + [44500] * 14
    dates = pd.date_range(start='2024-01-01', periods=len(prices), freq='1h')
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestInitialization:
    def test_default(self):
        pattern = DoubleTopPattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 15


class TestAnalysis:
    def test_standardized_format(self, pattern_data):
        pattern = DoubleTopPattern()
        result = pattern.analyze(pattern_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_pattern(self, pattern_data):
        pattern = DoubleTopPattern()
        result = pattern.analyze(pattern_data)
        assert result['signal'] in ['PATTERN_CONFIRMED', 'PATTERN_FORMING', 'NO_PATTERN']


class TestValidation:
    def test_missing_columns(self):
        pattern = DoubleTopPattern()
        assert pattern.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        pattern = DoubleTopPattern()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
            'open': [45000]*10, 'high': [45100]*10,
            'low': [44900]*10, 'close': [45000]*10,
            'volume': [100]*10
        })
        assert pattern.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
