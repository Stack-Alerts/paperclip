"""Unit test for Premium Discount Zones - Block 58/66"""
import pytest
import pandas as pd
from src.detectors.building_blocks.market_structure.premium_discount_zones import PremiumDiscountZones

@pytest.fixture
def sample_data():
    prices = list(range(44000, 45000, 20))
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=len(prices), freq='1h'),
        'open': prices, 'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices], 'close': prices, 'volume': [100] * len(prices)
    })

class TestPremiumDiscountZones:
    def test_init(self):
        b = PremiumDiscountZones()
        assert b.timeframe == '15min'
    
    def test_analyze(self, sample_data):
        b = PremiumDiscountZones()
        r = b.analyze(sample_data)
        assert all(k in r for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_insufficient_data(self):
        b = PremiumDiscountZones()
        small = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=5, freq='1h'),
                              'open': [44000]*5, 'high': [44100]*5, 'low': [43900]*5, 'close': [44000]*5, 'volume': [100]*5})
        r = b.analyze(small)
        assert r['signal'] == 'INSUFFICIENT_DATA'

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
