"""
Unit tests for Triangle Patterns (Ascending, Descending, Symmetrical)
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.patterns.ascending_triangle import AscendingTrianglePattern
from src.detectors.building_blocks.patterns.descending_triangle import DescendingTrianglePattern
from src.detectors.building_blocks.patterns.symmetrical_triangle import SymmetricalTrianglePattern


@pytest.fixture
def base_data():
    """Create base data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=40, freq='1h')
    prices = list(range(44000, 44000 + 40 * 100, 100))
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 200 for p in prices],
        'low': [p - 200 for p in prices],
        'close': prices,
        'volume': [100] * 40
    })


class TestAscendingTriangle:
    def test_init(self):
        pattern = AscendingTrianglePattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 20
    
    def test_analysis(self, base_data):
        pattern = AscendingTrianglePattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['NO_PATTERN', 'PATTERN_FORMING', 'BREAKOUT_CONFIRMED']
    
    def test_missing_columns(self):
        pattern = AscendingTrianglePattern()
        result = pattern.analyze(pd.DataFrame({'wrong': [1]}))
        assert result['signal'] == 'ERROR'


class TestDescendingTriangle:
    def test_init(self):
        pattern = DescendingTrianglePattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 20
    
    def test_analysis(self, base_data):
        pattern = DescendingTrianglePattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['NO_PATTERN', 'PATTERN_FORMING', 'BREAKDOWN_CONFIRMED']
    
    def test_missing_columns(self):
        pattern = DescendingTrianglePattern()
        result = pattern.analyze(pd.DataFrame({'wrong': [1]}))
        assert result['signal'] == 'ERROR'


class TestSymmetricalTriangle:
    def test_init(self):
        pattern = SymmetricalTrianglePattern()
        assert pattern.timeframe == '15min'
        assert pattern.min_pattern_bars == 20
    
    def test_analysis(self, base_data):
        pattern = SymmetricalTrianglePattern()
        result = pattern.analyze(base_data)
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['NO_PATTERN', 'PATTERN_FORMING', 'BREAKOUT_UP', 'BREAKOUT_DOWN']
    
    def test_missing_columns(self):
        pattern = SymmetricalTrianglePattern()
        result = pattern.analyze(pd.DataFrame({'wrong': [1]}))
        assert result['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
