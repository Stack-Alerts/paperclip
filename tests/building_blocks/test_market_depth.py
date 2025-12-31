"""
Unit test for Market Depth Building Block
Block 64/66 - Institutional & Volume
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.institutional.market_depth import MarketDepth


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


class TestMarketDepth:
    def test_initialization(self):
        """Test block initialization"""
        block = MarketDepth()
        assert block.timeframe == '15min'
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = MarketDepth()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['HIGH_LIQUIDITY', 'LOW_LIQUIDITY', 'NORMAL_LIQUIDITY']
        assert 'depth_ratio' in result['metadata']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = MarketDepth()
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
