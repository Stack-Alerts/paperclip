"""
Unit tests for LOD (Low of Day) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_levels.lod import LOD


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    base = 45000
    lows = base - np.random.uniform(0, 500, 50)
    closes = lows + np.random.uniform(0, 100, 50)
    return pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 50,
        'high': closes + 100,
        'volume': np.random.uniform(100, 1000, 50)
    })


class TestInitialization:
    def test_default(self):
        lod = LOD()
        assert lod.timeframe == '15min'
    
    def test_custom(self):
        lod = LOD(timeframe='1h')
        assert lod.timeframe == '1h'


class TestLODCalculation:
    def test_calculates_lod(self, sample_data):
        lod = LOD()
        lod_value = lod.calculate_lod(sample_data)
        assert lod_value is not None
    
    def test_lod_is_min_low(self, sample_data):
        lod = LOD()
        lod_value = lod.calculate_lod(sample_data)
        min_low = sample_data['low'].min()
        assert abs(lod_value - min_low) < 0.01


class TestBreakdownDetection:
    def test_breakdown_confirmed(self):
        lod = LOD()
        assert lod.detect_breakdown(44900, 45000) == 'BREAKDOWN_CONFIRMED'
    
    def test_breaking_down(self):
        lod = LOD()
        assert lod.detect_breakdown(44990, 45000) == 'BREAKING_DOWN'
    
    def test_above_lod(self):
        lod = LOD()
        assert lod.detect_breakdown(45100, 45000) == 'ABOVE_LOD'


class TestDistanceClassification:
    def test_at_lod(self):
        lod = LOD()
        assert lod.classify_distance(0.05) == 'AT_LOD'
    
    def test_very_close(self):
        lod = LOD()
        assert lod.classify_distance(0.3) == 'VERY_CLOSE'
    
    def test_far(self):
        lod = LOD()
        assert lod.classify_distance(3.0) == 'FAR'


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        lod = LOD()
        result = lod.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_valid_data(self, sample_data):
        lod = LOD()
        result = lod.analyze(sample_data)
        assert result['signal'] not in ['ERROR', 'INSUFFICIENT_DATA']
    
    def test_metadata_complete(self, sample_data):
        lod = LOD()
        result = lod.analyze(sample_data)
        assert all(k in result['metadata'] for k in ['lod', 'current_price', 'breakdown_status'])


class TestValidation:
    def test_missing_columns(self):
        lod = LOD()
        assert lod.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_confluence(self, sample_data):
        lod = LOD()
        assert len(lod.analyze(sample_data)['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
