"""
Unit tests for 20/50 EMA Cross Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.moving_averages.ema_20_50_cross import EMA2050Cross


@pytest.fixture
def sample_data():
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
        cross = EMA2050Cross()
        assert cross.fast_period == 20
        assert cross.slow_period == 50
    
    def test_custom(self):
        cross = EMA2050Cross(fast_period=10, slow_period=30)
        assert cross.fast_period == 10
        assert cross.slow_period == 30


class TestEMACalculation:
    def test_ema_calculation(self, sample_data):
        cross = EMA2050Cross()
        ema_20 = cross.calculate_ema(sample_data['close'], 20)
        ema_50 = cross.calculate_ema(sample_data['close'], 50)
        assert len(ema_20) == len(sample_data)
        assert len(ema_50) == len(sample_data)


class TestCrossDetection:
    def test_golden_cross(self):
        cross = EMA2050Cross()
        fast = pd.Series([44900, 45100, 45200, 45300])
        slow = pd.Series([45000, 45000, 45000, 45000])
        assert cross.detect_cross(fast, slow) == 'GOLDEN_CROSS'
    
    def test_death_cross(self):
        cross = EMA2050Cross()
        fast = pd.Series([45100, 44900, 44800, 44700])
        slow = pd.Series([45000, 45000, 45000, 45000])
        assert cross.detect_cross(fast, slow) == 'DEATH_CROSS'
    
    def test_no_cross(self):
        cross = EMA2050Cross()
        fast = pd.Series([45100, 45200, 45300, 45400])
        slow = pd.Series([45000, 45050, 45100, 45150])
        assert cross.detect_cross(fast, slow) == 'NO_CROSS'


class TestSeparation:
    def test_separation_calculation(self):
        cross = EMA2050Cross()
        sep = cross.calculate_separation(45500, 45000)
        assert abs(sep - 1.11) < 0.01
    
    def test_separation_classification(self):
        cross = EMA2050Cross()
        assert cross.classify_separation(0.2) == 'TIGHT'
        assert cross.classify_separation(0.5) == 'NORMAL'
        assert cross.classify_separation(1.5) == 'WIDE'
        assert cross.classify_separation(3.0) == 'VERY_WIDE'


class TestTrendDetermination:
    def test_strong_uptrend(self):
        cross = EMA2050Cross()
        assert cross.determine_trend(45600, 45300, 45800) == 'STRONG_UPTREND'
    
    def test_strong_downtrend(self):
        cross = EMA2050Cross()
        assert cross.determine_trend(44700, 45000, 44500) == 'STRONG_DOWNTREND'
    
    def test_early_uptrend(self):
        cross = EMA2050Cross()
        assert cross.determine_trend(44900, 45100, 45000) == 'EARLY_UPTREND'


class TestAnalysisMethod:
    def test_standardized_format(self, sample_data):
        cross = EMA2050Cross()
        result = cross.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_with_sufficient_data(self, sample_data):
        cross = EMA2050Cross()
        result = cross.analyze(sample_data)
        assert result['signal'] not in ['INSUFFICIENT_DATA', 'ERROR']
        assert result['confidence'] > 0
    
    def test_with_insufficient_data(self):
        df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=30, freq='15min'), 'close': [45000] * 30})
        cross = EMA2050Cross()
        result = cross.analyze(df)
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_metadata_complete(self, sample_data):
        cross = EMA2050Cross()
        result = cross.analyze(sample_data)
        m = result['metadata']
        assert all(k in m for k in ['fast_ema', 'slow_ema', 'cross', 'separation_pct', 'trend'])


class TestDataValidation:
    def test_valid_data(self, sample_data):
        cross = EMA2050Cross()
        result = cross.analyze(sample_data)
        assert result['signal'] != 'ERROR'
    
    def test_invalid_data(self):
        cross = EMA2050Cross()
        result = cross.analyze(pd.DataFrame({'wrong': [1, 2, 3]}))
        assert result['signal'] == 'ERROR'


class TestConfluence:
    def test_confluence_present(self, sample_data):
        cross = EMA2050Cross()
        result = cross.analyze(sample_data)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
