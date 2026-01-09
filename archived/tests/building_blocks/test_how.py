"""
Unit tests for HOW (High of Week) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_levels.how import HOW


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-500, 1000, 200)
    closes = highs - np.random.uniform(0, 200, 200)
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 200)
    })


class TestInitialization:
    def test_default(self):
        how = HOW()
        assert how.timeframe == '15min'
    
    def test_custom(self):
        how = HOW(timeframe='1h')
        assert how.timeframe == '1h'


class TestHOWCalculation:
    def test_calculates_how(self, sample_data):
        how = HOW()
        how_value = how.calculate_how(sample_data)
        assert how_value is not None
    
    def test_how_is_weekly_max(self, sample_data):
        how = HOW()
        how_value = how.calculate_how(sample_data)
        # Should be max of current week
        current_week = sample_data['timestamp'].iloc[-1].isocalendar()[1]
        current_year = sample_data['timestamp'].iloc[-1].isocalendar()[0]
        week_data = sample_data[
            (sample_data['timestamp'].dt.isocalendar().week == current_week) &
            (sample_data['timestamp'].dt.isocalendar().year == current_year)
        ]
        assert abs(how_value - week_data['high'].max()) < 0.01


class TestBreakoutDetection:
    def test_breakout_confirmed(self):
        how = HOW()
        assert how.detect_breakout(45100, 45000) == 'BREAKOUT_CONFIRMED'
    
    def test_breaking_out(self):
        how = HOW()
        assert how.detect_breakout(45020, 45000) == 'BREAKING_OUT'
    
    def test_below_how(self):
        how = HOW()
        assert how.detect_breakout(44900, 45000) == 'BELOW_HOW'


class TestDistanceClassification:
    def test_at_how(self):
        how = HOW()
        assert how.classify_distance(0.1) == 'AT_HOW'
    
    def test_very_close(self):
        how = HOW()
        assert how.classify_distance(0.5) == 'VERY_CLOSE'
    
    def test_far(self):
        how = HOW()
        assert how.classify_distance(6.0) == 'FAR'


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        how = HOW()
        result = how.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe'])
    
    def test_valid_data(self, sample_data):
        how = HOW()
        result = how.analyze(sample_data)
        assert result['signal'] not in ['ERROR', 'INSUFFICIENT_DATA']
    
    def test_metadata_complete(self, sample_data):
        how = HOW()
        result = how.analyze(sample_data)
        assert all(k in result['metadata'] for k in ['how', 'current_price', 'breakout_status'])


class TestValidation:
    def test_missing_columns(self):
        how = HOW()
        assert how.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_confluence(self, sample_data):
        how = HOW()
        assert len(how.analyze(sample_data)['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
