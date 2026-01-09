"""
Unit test for VWAP Building Block
Block 60/66 - Institutional & Volume
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.institutional.vwap import VWAP


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


class TestVWAP:
    def test_initialization(self):
        """Test block initialization"""
        block = VWAP()
        assert block.timeframe == '15min'
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = VWAP()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['ABOVE_VWAP', 'BELOW_VWAP']
        assert 'vwap' in result['metadata']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = VWAP()
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


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
