"""
Unit test for Range Liquidity Building Block
Block 59/66 - Market Structure
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.market_structure.range_liquidity import RangeLiquidity


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


class TestRangeLiquidity:
    def test_initialization(self):
        """Test block initialization"""
        block = RangeLiquidity()
        assert block.timeframe == '15min'
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = RangeLiquidity()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['NEAR_BUY_SIDE_LIQUIDITY', 'NEAR_SELL_SIDE_LIQUIDITY']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = RangeLiquidity()
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
