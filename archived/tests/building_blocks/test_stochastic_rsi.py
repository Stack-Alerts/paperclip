"""
Unit tests for Stochastic RSI Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.oscillators.stochastic_rsi import StochasticRSI


@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    return pd.DataFrame({
        'timestamp': dates,
        'close': base + np.random.randn(100).cumsum() * 100,
        'open': base + np.random.randn(100).cumsum() * 100,
        'high': base + np.random.randn(100).cumsum() * 100 + 100,
        'low': base + np.random.randn(100).cumsum() * 100 - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })


class TestInitialization:
    def test_default(self):
        sr = StochasticRSI()
        assert sr.rsi_period == 14
        assert sr.stoch_period == 14
        assert sr.k_smooth == 3
        assert sr.d_smooth == 3
    
    def test_custom(self):
        sr = StochasticRSI(rsi_period=20, stoch_period=20, k_smooth=5, d_smooth=5)
        assert sr.rsi_period == 20
        assert sr.stoch_period == 20


class TestCalculations:
    def test_rsi_calculation(self, sample_data):
        sr = StochasticRSI()
        rsi = sr.calculate_rsi(sample_data['close'])
        valid = rsi.dropna()
        assert all(valid >= 0) and all(valid <= 100)
    
    def test_stochastic_rsi_calculation(self, sample_data):
        sr = StochasticRSI()
        rsi = sr.calculate_rsi(sample_data['close'])
        k, d = sr.calculate_stochastic_rsi(rsi)
        assert len(k) == len(sample_data)
        assert len(d) == len(sample_data)


class TestCrossoverDetection:
    def test_bullish_cross(self):
        sr = StochasticRSI()
        k = pd.Series([30, 35, 40, 55])
        d = pd.Series([50, 50, 50, 50])
        assert sr.detect_crossover(k, d) == 'BULLISH_CROSS'
    
    def test_bearish_cross(self):
        sr = StochasticRSI()
        k = pd.Series([70, 65, 60, 45])
        d = pd.Series([50, 50, 50, 50])
        assert sr.detect_crossover(k, d) == 'BEARISH_CROSS'
    
    def test_no_cross(self):
        sr = StochasticRSI()
        k = pd.Series([60, 65, 70, 75])
        d = pd.Series([50, 55, 60, 65])
        assert sr.detect_crossover(k, d) == 'NO_CROSS'


class TestLevelClassification:
    def test_extreme_overbought(self):
        sr = StochasticRSI()
        assert sr.classify_level(95) == 'EXTREME_OVERBOUGHT'
    
    def test_overbought(self):
        sr = StochasticRSI()
        assert sr.classify_level(85) == 'OVERBOUGHT'
    
    def test_neutral(self):
        sr = StochasticRSI()
        assert sr.classify_level(50) == 'NEUTRAL'
    
    def test_oversold(self):
        sr = StochasticRSI()
        assert sr.classify_level(15) == 'OVERSOLD'
    
    def test_extreme_oversold(self):
        sr = StochasticRSI()
        assert sr.classify_level(5) == 'EXTREME_OVERSOLD'


class TestAnalysisMethod:
    def test_standardized_format(self, sample_data):
        sr = StochasticRSI()
        result = sr.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata', 'timestamp', 'timeframe', 'confluence_factors'])
    
    def test_with_sufficient_data(self, sample_data):
        sr = StochasticRSI()
        result = sr.analyze(sample_data)
        assert result['signal'] not in ['INSUFFICIENT_DATA', 'ERROR']
        assert result['confidence'] > 0
    
    def test_with_insufficient_data(self):
        df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=20, freq='15min'), 'close': [45000] * 20})
        sr = StochasticRSI()
        result = sr.analyze(df)
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_metadata_complete(self, sample_data):
        sr = StochasticRSI()
        result = sr.analyze(sample_data)
        m = result['metadata']
        assert all(k in m for k in ['k_value', 'd_value', 'level', 'crossover'])


class TestDataValidation:
    def test_valid_data(self, sample_data):
        sr = StochasticRSI()
        result = sr.analyze(sample_data)
        assert result['signal'] != 'ERROR'
    
    def test_invalid_data(self):
        sr = StochasticRSI()
        result = sr.analyze(pd.DataFrame({'wrong': [1, 2, 3]}))
        assert result['signal'] == 'ERROR'


class TestConfluence:
    def test_confluence_present(self, sample_data):
        sr = StochasticRSI()
        result = sr.analyze(sample_data)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
