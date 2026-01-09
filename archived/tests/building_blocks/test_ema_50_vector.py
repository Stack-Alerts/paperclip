"""
Unit tests for 50 EMA Vector Break Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_50_vector import EMA50Vector


@pytest.fixture
def uptrend_data():
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 2000, 100)
    return pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(100).cumsum() * 50,
        'open': base + trend,
        'high': base + trend + 100,
        'low': base + trend - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })


class TestInitialization:
    def test_default(self):
        ema = EMA50Vector()
        assert ema.period == 50
        assert ema.timeframe == '15min'
    
    def test_custom(self):
        ema = EMA50Vector(period=20, timeframe='1hr')
        assert ema.period == 20
        assert ema.timeframe == '1hr'


class TestEMACalculation:
    def test_ema_calculation(self, uptrend_data):
        ema = EMA50Vector()
        ema_values = ema.calculate_ema(uptrend_data['close'])
        assert len(ema_values) == len(uptrend_data)
        assert all(ema_values > 0)


class TestSlopeCalculation:
    def test_rising_slope(self):
        ema = EMA50Vector()
        rising = pd.Series([100, 105, 110, 115, 120])
        assert ema.calculate_slope(rising) == 'RISING'
    
    def test_falling_slope(self):
        ema = EMA50Vector()
        falling = pd.Series([120, 115, 110, 105, 100])
        assert ema.calculate_slope(falling) == 'FALLING'
    
    def test_flat_slope(self):
        ema = EMA50Vector()
        flat = pd.Series([100, 100, 100, 100, 100])
        assert ema.calculate_slope(flat) == 'FLAT'


class TestVectorBreak:
    def test_bullish_break(self):
        ema = EMA50Vector()
        close = pd.Series([44900, 45100, 45200, 45300])
        ema_line = pd.Series([45000, 45000, 45000, 45000])
        assert ema.detect_vector_break(close, ema_line) == 'BULLISH_BREAK'
    
    def test_bearish_break(self):
        ema = EMA50Vector()
        close = pd.Series([45100, 44900, 44800, 44700])
        ema_line = pd.Series([45000, 45000, 45000, 45000])
        assert ema.detect_vector_break(close, ema_line) == 'BEARISH_BREAK'
    
    def test_no_break(self):
        ema = EMA50Vector()
        close = pd.Series([45100, 45200, 45300, 45400])
        ema_line = pd.Series([45000, 45050, 45100, 45150])
        assert ema.detect_vector_break(close, ema_line) == 'NO_BREAK'


class TestPositionClassification:
    def test_above_ema(self):
        ema = EMA50Vector()
        assert ema.classify_position(45500, 45000) == 'ABOVE_EMA'
    
    def test_below_ema(self):
        ema = EMA50Vector()
        assert ema.classify_position(44500, 45000) == 'BELOW_EMA'
    
    def test_at_ema(self):
        ema = EMA50Vector()
        assert ema.classify_position(45000, 45000) == 'AT_EMA'


class TestDistanceCalculation:
    def test_distance_calculation(self):
        ema = EMA50Vector()
        distance = ema.calculate_distance(45500, 45000)
        assert abs(distance - 1.11) < 0.01
    
    def test_distance_classification(self):
        ema = EMA50Vector()
        assert ema.classify_distance(0.3) == 'VERY_CLOSE'
        assert ema.classify_distance(0.8) == 'CLOSE'
        assert ema.classify_distance(1.5) == 'MODERATE'
        assert ema.classify_distance(2.5) == 'FAR'
        assert ema.classify_distance(5.0) == 'VERY_FAR'


class TestAnalysisMethod:
    def test_standardized_format(self, uptrend_data):
        ema = EMA50Vector()
        result = ema.analyze(uptrend_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_with_sufficient_data(self, uptrend_data):
        ema = EMA50Vector()
        result = ema.analyze(uptrend_data)
        assert result['signal'] not in ['INSUFFICIENT_DATA', 'ERROR']
        assert result['confidence'] > 0
    
    def test_with_insufficient_data(self):
        df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=30, freq='15min'), 'close': [45000] * 30})
        ema = EMA50Vector()
        result = ema.analyze(df)
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_metadata_complete(self, uptrend_data):
        ema = EMA50Vector()
        result = ema.analyze(uptrend_data)
        m = result['metadata']
        assert all(k in m for k in ['ema_value', 'current_price', 'position', 'slope', 'vector_break', 'distance_pct'])


class TestDataValidation:
    def test_valid_data(self, uptrend_data):
        ema = EMA50Vector()
        result = ema.analyze(uptrend_data)
        assert result['signal'] != 'ERROR'
    
    def test_invalid_data(self):
        ema = EMA50Vector()
        result = ema.analyze(pd.DataFrame({'wrong': [1, 2, 3]}))
        assert result['signal'] == 'ERROR'


class TestConfluence:
    def test_confluence_present(self, uptrend_data):
        ema = EMA50Vector()
        result = ema.analyze(uptrend_data)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
