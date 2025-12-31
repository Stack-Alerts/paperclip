"""
Unit test for Supply & Demand Zones Building Block
Block 65/66 - Supply/Demand & Fibonacci
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.supply_demand.supply_demand_zones import SupplyDemandZones


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


class TestSupplyDemandZones:
    def test_initialization(self):
        """Test block initialization"""
        block = SupplyDemandZones()
        assert block.timeframe == '15min'
    
    def test_analyze_valid_data(self, sample_data):
        """Test analysis with valid data"""
        block = SupplyDemandZones()
        result = block.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert result['signal'] in ['DEMAND_ZONE', 'SUPPLY_ZONE', 'NO_ZONE']
        assert 'zone_type' in result['metadata']
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        block = SupplyDemandZones()
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
