"""
Unit tests for Wyckoff blocks
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.wyckoff.wyckoff_accumulation import WyckoffAccumulation
from src.detectors.building_blocks.wyckoff.wyckoff_distribution import WyckoffDistribution
from src.detectors.building_blocks.wyckoff.wyckoff_reaccumulation import WyckoffReaccumulation


@pytest.fixture
def data():
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


def test_accumulation(data):
    b = WyckoffAccumulation()
    r = b.analyze(data)
    assert 'signal' in r

def test_distribution(data):
    b = WyckoffDistribution()
    r = b.analyze(data)
    assert 'signal' in r

def test_reaccumulation(data):
    b = WyckoffReaccumulation()
    r = b.analyze(data)
    assert 'signal' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
