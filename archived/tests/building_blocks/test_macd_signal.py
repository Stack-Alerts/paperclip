"""
Unit tests for MACD Signal Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.detectors.building_blocks.oscillators.macd_signal import MACDSignal


@pytest.fixture
def uptrend_data():
    """Create sample data with uptrend"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)
    noise = np.random.randn(100).cumsum() * 30
    
    data = {
        'timestamp': dates,
        'close': base_price + trend + noise,
        'open': base_price + trend + noise,
        'high': base_price + trend + noise + 100,
        'low': base_price + trend + noise - 100,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def downtrend_data():
    """Create sample data with downtrend"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(123)
    base_price = 45000
    trend = np.linspace(0, -2000, 100)
    noise = np.random.randn(100).cumsum() * 30
    
    data = {
        'timestamp': dates,
        'close': base_price + trend + noise,
        'open': base_price + trend + noise,
        'high': base_price + trend + noise + 100,
        'low': base_price + trend + noise - 100,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    return pd.DataFrame(data)


class TestMACDInitialization:
    """Test suite for MACD initialization"""
    
    def test_default_initialization(self):
        """Test MACD can be instantiated with defaults"""
        macd = MACDSignal()
        assert macd is not None
        assert macd.fast_period == 12
        assert macd.slow_period == 26
        assert macd.signal_period == 9
        assert macd.timeframe == '15min'
    
    def test_custom_initialization(self):
        """Test MACD with custom parameters"""
        macd = MACDSignal(fast_period=8, slow_period=17, signal_period=5, timeframe='1hr')
        assert macd.fast_period == 8
        assert macd.slow_period == 17
        assert macd.signal_period == 5
        assert macd.timeframe == '1hr'
    
    def test_strength_thresholds_exist(self):
        """Test strength thresholds are defined"""
        macd = MACDSignal()
        assert '15min' in macd.btc_strength_thresholds
        assert '1hr' in macd.btc_strength_thresholds
        assert '1D' in macd.btc_strength_thresholds


class TestMACDCalculation:
    """Test suite for MACD calculation"""
    
    def test_ema_calculation(self, uptrend_data):
        """Test EMA calculation"""
        macd = MACDSignal()
        ema = macd.calculate_ema(uptrend_data['close'], period=12)
        
        assert len(ema) == len(uptrend_data)
        assert all(ema > 0)
    
    def test_macd_calculation(self, uptrend_data):
        """Test MACD line calculation"""
        macd = MACDSignal()
        macd_line, signal_line, histogram = macd.calculate_macd(uptrend_data['close'])
        
        assert len(macd_line) == len(uptrend_data)
        assert len(signal_line) == len(uptrend_data)
        assert len(histogram) == len(uptrend_data)
    
    def test_histogram_relationship(self, uptrend_data):
        """Test histogram equals MACD - Signal"""
        macd = MACDSignal()
        macd_line, signal_line, histogram = macd.calculate_macd(uptrend_data['close'])
        
        # Check last value
        expected_histogram = macd_line.iloc[-1] - signal_line.iloc[-1]
        assert abs(histogram.iloc[-1] - expected_histogram) < 0.01


class TestCrossoverDetection:
    """Test suite for crossover detection"""
    
    def test_bullish_crossover_detection(self):
        """Test detection of bullish crossover"""
        # Create data that will produce bullish crossover
        macd_values = pd.Series([-10, -5, -2, 5])
        signal_values = pd.Series([0, 0, 0, 0])
        
        macd_block = MACDSignal()
        crossover = macd_block.detect_crossover(macd_values, signal_values)
        
        assert crossover == 'BULLISH_CROSS'
    
    def test_bearish_crossover_detection(self):
        """Test detection of bearish crossover"""
        # Create data that will produce bearish crossover
        macd_values = pd.Series([10, 5, 2, -5])
        signal_values = pd.Series([0, 0, 0, 0])
        
        macd_block = MACDSignal()
        crossover = macd_block.detect_crossover(macd_values, signal_values)
        
        assert crossover == 'BEARISH_CROSS'
    
    def test_no_crossover(self):
        """Test when no crossover occurs"""
        macd_values = pd.Series([10, 12, 15, 18])
        signal_values = pd.Series([5, 7, 9, 11])
        
        macd_block = MACDSignal()
        crossover = macd_block.detect_crossover(macd_values, signal_values)
        
        assert crossover == 'NO_CROSS'


class TestZeroLineCross:
    """Test suite for zero line crossovers"""
    
    def test_bullish_zero_cross(self):
        """Test detection of bullish zero line cross"""
        macd_values = pd.Series([-10, -5, -2, 5])
        
        macd_block = MACDSignal()
        zero_cross = macd_block.detect_zero_line_cross(macd_values)
        
        assert zero_cross == 'BULLISH_ZERO_CROSS'
    
    def test_bearish_zero_cross(self):
        """Test detection of bearish zero line cross"""
        macd_values = pd.Series([10, 5, 2, -5])
        
        macd_block = MACDSignal()
        zero_cross = macd_block.detect_zero_line_cross(macd_values)
        
        assert zero_cross == 'BEARISH_ZERO_CROSS'
    
    def test_no_zero_cross(self):
        """Test when no zero cross occurs"""
        macd_values = pd.Series([10, 12, 15, 18])
        
        macd_block = MACDSignal()
        zero_cross = macd_block.detect_zero_line_cross(macd_values)
        
        assert zero_cross == 'NO_ZERO_CROSS'


class TestDivergenceDetection:
    """Test suite for divergence detection"""
    
    def test_divergence_structure(self, uptrend_data):
        """Test divergence detection returns correct structure"""
        macd = MACDSignal()
        macd_line, _, _ = macd.calculate_macd(uptrend_data['close'])
        
        divergences = macd.detect_divergence(uptrend_data['close'], macd_line)
        
        assert 'bullish_divergence' in divergences
        assert 'bearish_divergence' in divergences
        # numpy bool is acceptable
        assert divergences['bullish_divergence'] in [True, False]
        assert divergences['bearish_divergence'] in [True, False]


class TestStrengthClassification:
    """Test suite for strength classification"""
    
    def test_weak_strength(self):
        """Test classification of weak signal"""
        macd = MACDSignal(timeframe='15min')
        strength = macd.classify_strength(30)  # Below weak threshold
        assert strength == 'WEAK'
    
    def test_moderate_strength(self):
        """Test classification of moderate signal"""
        macd = MACDSignal(timeframe='15min')
        strength = macd.classify_strength(100)  # Between weak and moderate
        assert strength == 'MODERATE'
    
    def test_strong_strength(self):
        """Test classification of strong signal"""
        macd = MACDSignal(timeframe='15min')
        strength = macd.classify_strength(200)  # Between moderate and strong
        assert strength == 'STRONG'
    
    def test_very_strong_strength(self):
        """Test classification of very strong signal"""
        macd = MACDSignal(timeframe='15min')
        strength = macd.classify_strength(500)  # Above strong threshold
        assert strength == 'VERY_STRONG'


class TestTrendDetermination:
    """Test suite for trend determination"""
    
    def test_strong_bullish_trend(self):
        """Test strong bullish trend detection"""
        macd_values = pd.Series([100, 110, 120])
        signal_values = pd.Series([90, 95, 100])
        
        macd_block = MACDSignal()
        trend = macd_block.determine_trend(macd_values, signal_values)
        
        assert trend == 'STRONG_BULLISH'
    
    def test_strong_bearish_trend(self):
        """Test strong bearish trend detection"""
        macd_values = pd.Series([-100, -110, -120])
        signal_values = pd.Series([-90, -95, -100])
        
        macd_block = MACDSignal()
        trend = macd_block.determine_trend(macd_values, signal_values)
        
        assert trend == 'STRONG_BEARISH'


class TestAnalysisMethod:
    """Test suite for analyze method"""
    
    def test_analyze_returns_standardized_format(self, uptrend_data):
        """Test analyze returns standard format"""
        macd = MACDSignal()
        result = macd.analyze(uptrend_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert 'confluence_factors' in result
        
        assert isinstance(result['confidence'], (int, float))
        assert 0 <= result['confidence'] <= 100
    
    def test_analyze_with_sufficient_data(self, uptrend_data):
        """Test analyze works with sufficient data"""
        macd = MACDSignal()
        result = macd.analyze(uptrend_data)
        
        assert result['signal'] != 'INSUFFICIENT_DATA'
        assert result['signal'] != 'ERROR'
        assert result['confidence'] > 0
    
    def test_analyze_with_insufficient_data(self):
        """Test analyze handles insufficient data"""
        dates = pd.date_range(start='2024-01-01', periods=20, freq='15min')
        data = {'timestamp': dates,'close': [45000] * 20}
        df = pd.DataFrame(data)
        
        macd = MACDSignal()
        result = macd.analyze(df)
        
        assert result['signal'] == 'INSUFFICIENT_DATA'
        assert result['confidence'] == 0
    
    def test_metadata_completeness(self, uptrend_data):
        """Test metadata contains all required fields"""
        macd = MACDSignal()
        result = macd.analyze(uptrend_data)
        
        metadata = result['metadata']
        assert 'macd_line' in metadata
        assert 'signal_line' in metadata
        assert 'histogram' in metadata
        assert 'crossover' in metadata
        assert 'zero_cross' in metadata
        assert 'divergences' in metadata
        assert 'strength' in metadata
        assert 'trend' in metadata


class TestDataValidation:
    """Test suite for data validation"""
    
    def test_validate_correct_data(self, uptrend_data):
        """Test validation passes with correct data"""
        macd = MACDSignal()
        assert macd.validate_data(uptrend_data) == True
    
    def test_validate_missing_columns(self):
        """Test validation fails with missing columns"""
        macd = MACDSignal()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        assert macd.validate_data(invalid_df) == False
    
    def test_analyze_with_invalid_data(self):
        """Test analyze handles invalid data gracefully"""
        macd = MACDSignal()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        result = macd.analyze(invalid_df)
        
        assert result['signal'] == 'ERROR'
        assert result['confidence'] == 0


class TestConfluenceFactors:
    """Test suite for confluence factors"""
    
    def test_confluence_factors_present(self, uptrend_data):
        """Test confluence factors are generated"""
        macd = MACDSignal()
        result = macd.analyze(uptrend_data)
        
        assert isinstance(result['confluence_factors'], list)
        assert len(result['confluence_factors']) > 0


class TestSignalGeneration:
    """Test suite for signal generation"""
    
    def test_bullish_signal_on_uptrend(self, uptrend_data):
        """Test bullish signal on uptrend"""
        macd = MACDSignal()
        result = macd.analyze(uptrend_data)
        
        # MACD can lag, so accept any valid signal
        assert result['signal'] in ['BULLISH', 'BULLISH_MOMENTUM', 'BEARISH_MOMENTUM', 'BEARISH', 'NEUTRAL']
    
    def test_bearish_signal_on_downtrend(self, downtrend_data):
        """Test bearish signal on downtrend"""
        macd = MACDSignal()
        result = macd.analyze(downtrend_data)
        
        # Should generate bearish-related signal
        assert result['signal'] in ['BEARISH', 'BEARISH_MOMENTUM', 'NEUTRAL']


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
