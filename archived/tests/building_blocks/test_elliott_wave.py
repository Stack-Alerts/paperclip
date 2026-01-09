"""
Unit tests for Elliott Wave blocks
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.elliott_wave.elliott_wave_count import ElliottWaveCount
from src.detectors.building_blocks.elliott_wave.elliott_wave_oscillator import ElliottWaveOscillator


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


class TestElliottWaveCount:
    def test_init(self):
        b = ElliottWaveCount()
        assert b.timeframe == '15min'
    
    def test_analysis(self, data):
        b = ElliottWaveCount()
        r = b.analyze(data)
        assert 'signal' in r


class TestElliottWaveOscillator:
    def test_init(self):
        b = ElliottWaveOscillator()
        assert b.fast_period == 5
    
    def test_analysis(self, data):
        b = ElliottWaveOscillator()
        r = b.analyze(data)
        assert 'signal' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
