"""
Unit tests for HOD (High of Day) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.detectors.building_blocks.price_levels.hod import HOD


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-200, 500, 50)
    closes = highs - np.random.uniform(0, 100, 50)
    
    return pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 50)
    })


class TestInitialization:
    def test_default(self):
        hod = HOD()
        assert hod.timeframe == '15min'
        assert hod.day_start_hour == 0
    
    def test_custom(self):
        hod = HOD(timeframe='1h', day_start_hour=9)
        assert hod.timeframe == '1h'
        assert hod.day_start_hour == 9


class TestHODCalculation:
    def test_calculates_hod(self, sample_data):
        hod = HOD()
        hod_value = hod.calculate_hod(sample_data)
        assert hod_value is not None
        assert hod_value > 0
    
    def test_hod_is_max_high(self, sample_data):
        hod = HOD()
        hod_value = hod.calculate_hod(sample_data)
        max_high = sample_data['high'].max()
        assert abs(hod_value - max_high) < 0.01


class TestBreakoutDetection:
    def test_breakout_confirmed(self):
        hod = HOD()
        assert hod.detect_breakout(45100, 45000) == 'BREAKOUT_CONFIRMED'
    
    def test_breaking_out(self):
        hod = HOD()
        assert hod.detect_breakout(45010, 45000) == 'BREAKING_OUT'
    
    def test_below_hod(self):
        hod = HOD()
        assert hod.detect_breakout(44900, 45000) == 'BELOW_HOD'


class TestDistanceCalculation:
    def test_distance_above(self):
        hod = HOD()
        dist = hod.calculate_distance(45500, 45000)
        assert abs(dist - 1.11) < 0.01
    
    def test_distance_below(self):
        hod = HOD()
        dist = hod.calculate_distance(44500, 45000)
        assert abs(dist + 1.11) < 0.01


class TestDistanceClassification:
    def test_at_hod(self):
        hod = HOD()
        assert hod.classify_distance(0.05) == 'AT_HOD'
    
    def test_very_close(self):
        hod = HOD()
        assert hod.classify_distance(0.3) == 'VERY_CLOSE'
    
    def test_close(self):
        hod = HOD()
        assert hod.classify_distance(0.7) == 'CLOSE'
    
    def test_moderate(self):
        hod = HOD()
        assert hod.classify_distance(1.5) == 'MODERATE'
    
    def test_far(self):
        hod = HOD()
        assert hod.classify_distance(3.0) == 'FAR'


class TestAnalysisMethod:
    def test_standardized_format(self, sample_data):
        hod = HOD()
        result = hod.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_with_valid_data(self, sample_data):
        hod = HOD()
        result = hod.analyze(sample_data)
        assert result['signal'] not in ['ERROR', 'INSUFFICIENT_DATA']
        assert result['confidence'] > 0
    
    def test_metadata_complete(self, sample_data):
        hod = HOD()
        result = hod.analyze(sample_data)
        m = result['metadata']
        assert all(k in m for k in ['hod', 'current_price', 'distance_pct', 'breakout_status'])


class TestDataValidation:
    def test_missing_columns(self):
        hod = HOD()
        df = pd.DataFrame({'wrong': [1, 2, 3]})
        result = hod.analyze(df)
        assert result['signal'] == 'ERROR'
    
    def test_empty_data(self):
        hod = HOD()
        df = pd.DataFrame({'timestamp': [], 'high': [], 'close': []})
        result = hod.analyze(df)
        assert result['signal'] == 'INSUFFICIENT_DATA'


class TestConfluence:
    def test_confluence_present(self, sample_data):
        hod = HOD()
        result = hod.analyze(sample_data)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
