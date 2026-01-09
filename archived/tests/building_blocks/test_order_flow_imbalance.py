"""
Unit test for Order Flow Imbalance Building Block
Block 63/66 - Institutional & Volume
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.institutional.order_flow_imbalance import OrderFlowImbalance


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data with varied candles"""
    dates = pd.date_range('2024-01-01', periods=50, freq='1h')
    # Mix of up and down candles
    opens = [44000 + (i % 10) * 50 for i in range(50)]
    closes = [44100 - (i % 10) * 30 for i in range(50)]
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': [max(o, c) + 50 for o, c in zip(opens, closes)],
        'low': [min(o, c) - 50 for o, c in zip(opens, closes)],
        'close': closes,
        'volume': [100 + i for i in range(50)]
    })


class TestOrderFlowImbalance:
    def test_initialization(self):
        """Test block initialization"""
        block = OrderFlowImbalance()
        assert block.timeframe == '15min'
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = OrderFlowImbalance()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['BUY_IMBALANCE', 'SELL_IMBALANCE', 'BALANCED']
        assert 'up_volume' in result['metadata']
        assert 'down_volume' in result['metadata']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = OrderFlowImbalance()
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
