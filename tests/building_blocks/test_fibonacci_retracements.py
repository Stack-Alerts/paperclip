"""
Unit test for Fibonacci Retracements Building Block
Block 66/66 - Supply/Demand & Fibonacci - FINAL BLOCK!
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.fibonacci.fibonacci_retracements import FibonacciRetracements


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


class TestFibonacciRetracements:
    def test_initialization(self):
        """Test block initialization"""
        block = FibonacciRetracements()
        assert block.timeframe == '15min'
        assert block.fib_levels == [0.236, 0.382, 0.5, 0.618, 0.786]
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = FibonacciRetracements()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'fib_levels' in result['metadata']
        assert 'swing_high' in result['metadata']
        assert 'swing_low' in result['metadata']
        assert 'closest_level' in result['metadata']
    
    def test_fibonacci_levels_calculated(self, sample_data):
        """Test that all Fibonacci levels are calculated"""
        block = FibonacciRetracements()
        result = block.analyze(sample_data)
        
        fib_levels = result['metadata']['fib_levels']
        assert 'fib_23' in fib_levels
        assert 'fib_38' in fib_levels
        assert 'fib_50' in fib_levels
        assert 'fib_61' in fib_levels  # Golden ratio
        assert 'fib_78' in fib_levels
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = FibonacciRetracements()
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
            'open': [44000] * 10,
            'high': [44100] * 10,
            'low': [43900] * 10,
            'close': [44000] * 10,
            'volume': [100] * 10
        })
        result = block.analyze(small_data)
        assert result['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
