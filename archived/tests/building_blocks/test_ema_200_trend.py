"""
Unit tests for 200 EMA Trend Filter Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=250, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 5000, 250)
    return pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(250).cumsum() * 100,
        'open': base + trend,
        'high': base + trend + 200,
        'low': base + trend - 200,
        'volume': np.random.uniform(100, 1000, 250)
    })


class TestInitialization:
    def test_default(self):
        ema = EMA200Trend()
        assert ema.period == 200
    
    def test_custom(self):
        ema = EMA200Trend(period=100)
        assert ema.period == 100


class TestEMACalculation:
    def test_calculation(self, sample_data):
        ema = EMA200Trend()
        ema_values = ema.calculate_ema(sample_data['close'])
        assert len(ema_values) == len(sample_data)


class TestSlopeCalculation:
    def test_strong_uptrend(self):
        ema = EMA200Trend()
        rising = pd.Series(np.linspace(100, 150, 20))
        assert ema.calculate_slope(rising) == 'STRONG_UPTREND'
    
    def test_uptrend(self):
        ema = EMA200Trend()
        rising = pd.Series(np.linspace(100, 110, 20))
        assert ema.calculate_slope(rising) in ['UPTREND', 'STRONG_UPTREND']
    
    def test_sideways(self):
        ema = EMA200Trend()
        flat = pd.Series([100] * 20)
        assert ema.calculate_slope(flat) == 'SIDEWAYS'


class TestPositionClassification:
    def test_above(self):
        ema = EMA200Trend()
        assert ema.classify_position(46000, 45000) == 'ABOVE_200EMA'
    
    def test_below(self):
        ema = EMA200Trend()
        assert ema.classify_position(44000, 45000) == 'BELOW_200EMA'
    
    def test_at(self):
        ema = EMA200Trend()
        assert ema.classify_position(45000, 45000) == 'AT_200EMA'


class TestDistanceClassification:
    def test_touching(self):
        ema = EMA200Trend()
        assert ema.classify_distance(0.3) == 'TOUCHING'
    
    def test_near(self):
        ema = EMA200Trend()
        assert ema.classify_distance(1.5) == 'NEAR'
    
    def test_moderate(self):
        ema = EMA200Trend()
        assert ema.classify_distance(3.5) == 'MODERATE'
    
    def test_extended(self):
        ema = EMA200Trend()
        assert ema.classify_distance(7.0) == 'EXTENDED'
    
    def test_overextended(self):
        ema = EMA200Trend()
        assert ema.classify_distance(12.0) == 'OVEREXTENDED'


class TestTrendFilter:
    def test_longs_only(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter('ABOVE_200EMA', 'STRONG_UPTREND') == 'LONGS_ONLY'
    
    def test_shorts_only(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter('BELOW_200EMA', 'STRONG_DOWNTREND') == 'SHORTS_ONLY'
    
    def test_longs_preferred(self):
        ema = EMA200Trend()
        assert ema.determine_trend_filter('ABOVE_200EMA', 'SIDEWAYS') == 'LONGS_PREFERRED'


class TestAnalysisMethod:
    def test_standardized_format(self, sample_data):
        ema = EMA200Trend()
        result = ema.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_with_sufficient_data(self, sample_data):
        ema = EMA200Trend()
        result = ema.analyze(sample_data)
        assert result['signal'] not in ['INSUFFICIENT_DATA', 'ERROR']
        assert result['confidence'] > 0
    
    def test_with_insufficient_data(self):
        df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'), 'close': [45000] * 100})
        ema = EMA200Trend()
        result = ema.analyze(df)
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_metadata_complete(self, sample_data):
        ema = EMA200Trend()
        result = ema.analyze(sample_data)
        m = result['metadata']
        assert all(k in m for k in ['ema_200', 'position', 'slope', 'distance_pct', 'trend_filter'])


class TestDataValidation:
    def test_valid_data(self, sample_data):
        ema = EMA200Trend()
        result = ema.analyze(sample_data)
        assert result['signal'] != 'ERROR'
    
    def test_invalid_data(self):
        ema = EMA200Trend()
        result = ema.analyze(pd.DataFrame({'wrong': [1, 2, 3]}))
        assert result['signal'] == 'ERROR'


class TestConfluence:
    def test_confluence_present(self, sample_data):
        ema = EMA200Trend()
        result = ema.analyze(sample_data)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
