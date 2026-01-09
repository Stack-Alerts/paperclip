"""
Unit tests for LOW (Low of Week) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_levels.low import LOW


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    np.random.seed(42)
    base = 45000
    lows = base - np.random.uniform(0, 1000, 200)
    closes = lows + np.random.uniform(0, 200, 200)
    return pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 50,
        'high': closes + 100,
        'volume': np.random.uniform(100, 1000, 200)
    })


class TestInitialization:
    def test_default(self):
        low = LOW()
        assert low.timeframe == '15min'


class TestLOWCalculation:
    def test_calculates_low(self, sample_data):
        low = LOW()
        assert low.calculate_low(sample_data) is not None
    
    def test_low_is_weekly_min(self, sample_data):
        low_obj = LOW()
        low_value = low_obj.calculate_low(sample_data)
        current_week = sample_data['timestamp'].iloc[-1].isocalendar()[1]
        current_year = sample_data['timestamp'].iloc[-1].isocalendar()[0]
        week_data = sample_data[
            (sample_data['timestamp'].dt.isocalendar().week == current_week) &
            (sample_data['timestamp'].dt.isocalendar().year == current_year)
        ]
        assert abs(low_value - week_data['low'].min()) < 0.01


class TestBreakdownDetection:
    def test_breakdown_confirmed(self):
        low = LOW()
        assert low.detect_breakdown(44900, 45000) == 'BREAKDOWN_CONFIRMED'
    
    def test_above_low(self):
        low = LOW()
        assert low.detect_breakdown(45100, 45000) == 'ABOVE_LOW'


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        low = LOW()
        result = low.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_valid_data(self, sample_data):
        low = LOW()
        result = low.analyze(sample_data)
        assert result['signal'] not in ['ERROR', 'INSUFFICIENT_DATA']
    
    def test_metadata_complete(self, sample_data):
        low = LOW()
        result = low.analyze(sample_data)
        assert all(k in result['metadata'] for k in ['low', 'current_price', 'breakdown_status'])


class TestValidation:
    def test_missing_columns(self):
        low = LOW()
        assert low.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
