"""
Unit test for Swing Points Building Block
Block 57/66 - Market Structure
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.market_structure.swing_points import SwingPoints


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data"""
    prices = list(range(44000, 45000, 20))
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestSwingPoints:
    def test_initialization(self):
        """Test block initialization"""
        block = SwingPoints()
        assert block.timeframe == '15min'
        assert block.lookback == 5
    
    def test_custom_parameters(self):
        """Test custom parameter initialization"""
        block = SwingPoints(timeframe='1h', lookback=10)
        assert block.timeframe == '1h'
        assert block.lookback == 10
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = SwingPoints()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert 'confluence_factors' in result
    
    def test_analyze_insufficient_data(self):
        """Test with insufficient data"""
        block = SwingPoints()
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1h'),
            'open': [44000] * 5,
            'high': [44100] * 5,
            'low': [43900] * 5,
            'close': [44000] * 5,
            'volume': [100] * 5
        })
        result = block.analyze(small_data)
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_analyze_missing_columns(self):
        """Test with missing required columns"""
        block = SwingPoints()
        bad_data = pd.DataFrame({'close': [44000, 44100]})
        result = block.analyze(bad_data)
        assert result['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
