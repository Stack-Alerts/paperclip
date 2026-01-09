"""Unit test for Anchored VWAP - Block 61/66"""
import pytest
import pandas as pd
from src.detectors.building_blocks.institutional.anchored_vwap import AnchoredVWAP

@pytest.fixture
def sample_data():
    prices = list(range(44000, 45000, 20))
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=len(prices), freq='1h'),
        'open': prices, 'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices], 'close': prices, 'volume': [100] * len(prices)
    })

class TestAnchoredVWAP:
    def test_init(self):
        assert AnchoredVWAP().anchor_idx == 0
    
    def test_analyze(self, sample_data):
        r = AnchoredVWAP().analyze(sample_data)
        assert 'VWAP' in r['signal']

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
