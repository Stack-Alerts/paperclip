"""
Unit tests for RSI Divergence Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence


@pytest.fixture
def sample_data():
    """Create sample data"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 2000, 100)
    noise = np.random.randn(100).cumsum() * 50
    
    return pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + noise,
        'open': base + trend + noise,
        'high': base + trend + noise + 100,
        'low': base + trend + noise - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })


class TestRSIInitialization:
    def test_default_initialization(self):
        rsi = RSIDivergence()
        assert rsi.period == 14
        assert rsi.overbought == 70
        assert rsi.oversold == 30
    
    def test_custom_initialization(self):
        rsi = RSIDivergence(period=20, overbought=75, oversold=25)
        assert rsi.period == 20
        assert rsi.overbought == 75
        assert rsi.oversold == 25


class TestRSICalculation:
    def test_rsi_calculation(self, sample_data):
        rsi = RSIDivergence()
        rsi_values = rsi.calculate_rsi(sample_data['close'])
        assert len(rsi_values) == len(sample_data)
        # RSI should be between 0 and 100
        valid_rsi = rsi_values.dropna()
        assert all(valid_rsi >= 0)
        assert all(valid_rsi <= 100)


class TestLevelClassification:
    def test_extreme_overbought(self):
        rsi = RSIDivergence()
        assert rsi.classify_level(85) == 'EXTREME_OVERBOUGHT'
    
    def test_overbought(self):
        rsi = RSIDivergence()
        assert rsi.classify_level(75) == 'OVERBOUGHT'
    
    def test_neutral(self):
        rsi = RSIDivergence()
        assert rsi.classify_level(50) == 'NEUTRAL'
    
    def test_oversold(self):
        rsi = RSIDivergence()
        assert rsi.classify_level(25) == 'OVERSOLD'
    
    def test_extreme_oversold(self):
        rsi = RSIDivergence()
        assert rsi.classify_level(15) == 'EXTREME_OVERSOLD'


class TestDivergenceDetection:
    def test_divergence_structure(self, sample_data):
        rsi = RSIDivergence()
        rsi_values = rsi.calculate_rsi(sample_data['close'])
        divergences = rsi.detect_divergence(sample_data['close'], rsi_values)
        
        assert 'bullish_divergence' in divergences
        assert 'bearish_divergence' in divergences
        assert 'hidden_bullish' in divergences
        assert 'hidden_bearish' in divergences


class TestAnalysisMethod:
    def test_returns_standardized_format(self, sample_data):
        rsi = RSIDivergence()
        result = rsi.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert 'confluence_factors' in result
    
    def test_with_sufficient_data(self, sample_data):
        rsi = RSIDivergence()
        result = rsi.analyze(sample_data)
        
        assert result['signal'] != 'INSUFFICIENT_DATA'
        assert result['signal'] != 'ERROR'
        assert result['confidence'] > 0
    
    def test_with_insufficient_data(self):
        dates = pd.date_range(start='2024-01-01', periods=10, freq='15min')
        df = pd.DataFrame({'timestamp': dates, 'close': [45000] * 10})
        
        rsi = RSIDivergence()
        result = rsi.analyze(df)
        
        assert result['signal'] == 'INSUFFICIENT_DATA'
    
    def test_metadata_completeness(self, sample_data):
        rsi = RSIDivergence()
        result = rsi.analyze(sample_data)
        
        assert 'rsi_value' in result['metadata']
        assert 'level' in result['metadata']
        assert 'divergences' in result['metadata']
        assert 'period' in result['metadata']


class TestDataValidation:
    def test_validate_correct_data(self, sample_data):
        rsi = RSIDivergence()
        assert rsi.validate_data(sample_data) == True
    
    def test_validate_missing_columns(self):
        rsi = RSIDivergence()
        assert rsi.validate_data(pd.DataFrame({'wrong': [1, 2, 3]})) == False
    
    def test_with_invalid_data(self):
        rsi = RSIDivergence()
        result = rsi.analyze(pd.DataFrame({'wrong': [1, 2, 3]}))
        assert result['signal'] == 'ERROR'


class TestConfluenceFactors:
    def test_confluence_present(self, sample_data):
        rsi = RSIDivergence()
        result = rsi.analyze(sample_data)
        assert isinstance(result['confluence_factors'], list)
        assert len(result['confluence_factors']) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
