"""
Unit test for EMA Crossover Building Block
Block 62/66 - Institutional & Volume
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.institutional.ema_crossover import EMACrossover


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data"""
    prices = list(range(44000, 45000, 5))
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestEMACrossover:
    def test_initialization(self):
        """Test block initialization"""
        block = EMACrossover()
        assert block.timeframe == '15min'
        assert block.fast == 50
        assert block.slow == 200
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = EMACrossover()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['GOLDEN_CROSS', 'DEATH_CROSS', 'BULLISH_ALIGNMENT', 'BEARISH_ALIGNMENT']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = EMACrossover()
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1h'),
            'open': [44000] * 50,
            'high': [44100] * 50,
            'low': [43900] * 50,
            'close': [44000] * 50,
            'volume': [100] * 50
        })
        result = block.analyze(small_data)
        assert result['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
