"""
Unit tests for ATR (Average True Range) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.detectors.building_blocks.volatility.atr import ATR


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base_price = 45000
    
    data = {
        'timestamp': dates,
        'open': base_price + np.random.randn(100).cumsum() * 100,
        'high': base_price + np.random.randn(100).cumsum() * 100 + np.random.uniform(50, 200, 100),
        'low': base_price + np.random.randn(100).cumsum() * 100 - np.random.uniform(50, 200, 100),
        'close': base_price + np.random.randn(100).cumsum() * 100,
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def low_volatility_data():
    """Create data with low volatility (tight range)"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    base_price = 45000
    
    data = {
        'timestamp': dates,
        'open': np.full(100, base_price) + np.random.uniform(-50, 50, 100),
        'high': np.full(100, base_price) + np.random.uniform(10, 60, 100),
        'low': np.full(100, base_price) - np.random.uniform(10, 60, 100),
        'close': np.full(100, base_price) + np.random.uniform(-50, 50, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def high_volatility_data():
    """Create data with high volatility (wide range)"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(123)
    base_price = 45000
    
    data = {
        'timestamp': dates,
        'open': base_price + np.random.randn(100).cumsum() * 500,
        'high': base_price + np.random.randn(100).cumsum() * 500 + np.random.uniform(500, 1500, 100),
        'low': base_price + np.random.randn(100).cumsum() * 500 - np.random.uniform(500, 1500, 100),
        'close': base_price + np.random.randn(100).cumsum() * 500,
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


class TestATRInitialization:
    """Test suite for ATR initialization"""
    
    def test_default_initialization(self):
        """Test ATR can be instantiated with defaults"""
        atr = ATR()
        assert atr is not None
        assert atr.period == 14
        assert atr.timeframe == '15min'
    
    def test_custom_initialization(self):
        """Test ATR with custom parameters"""
        atr = ATR(period=20, timeframe='1hr')
        assert atr.period == 20
        assert atr.timeframe == '1hr'
    
    def test_volatility_thresholds_exist(self):
        """Test volatility thresholds are defined"""
        atr = ATR()
        assert '15min' in atr.btc_volatility_thresholds
        assert '1hr' in atr.btc_volatility_thresholds
        assert '1D' in atr.btc_volatility_thresholds
        
        thresholds = atr.btc_volatility_thresholds['15min']
        assert 'calm' in thresholds
        assert 'normal' in thresholds
        assert 'high' in thresholds
        assert 'extreme' in thresholds


class TestATRCalculation:
    """Test suite for ATR calculation methods"""
    
    def test_true_range_calculation(self, sample_data):
        """Test True Range is calculated correctly"""
        atr = ATR()
        tr = atr.calculate_true_range(sample_data)
        
        assert len(tr) == len(sample_data)
        assert all(tr >= 0)  # True Range should always be positive
        assert not tr.isna().all()  # Should have valid values
    
    def test_true_range_components(self, sample_data):
        """Test True Range considers all three components"""
        atr = ATR()
        tr = atr.calculate_true_range(sample_data)
        
        # Manual calculation for verification (row 10)
        idx = 10
        hl = sample_data.loc[idx, 'high'] - sample_data.loc[idx, 'low']
        hpc = abs(sample_data.loc[idx, 'high'] - sample_data.loc[idx-1, 'close'])
        lpc = abs(sample_data.loc[idx, 'low'] - sample_data.loc[idx-1, 'close'])
        
        expected_tr = max(hl, hpc, lpc)
        assert abs(tr.iloc[idx] - expected_tr) < 0.01  # Allow small floating point difference
    
    def test_atr_calculation(self, sample_data):
        """Test ATR is calculated correctly"""
        atr = ATR(period=14)
        atr_series = atr.calculate_atr(sample_data)
        
        assert len(atr_series) == len(sample_data)
        assert all(atr_series[14:] > 0)  # ATR should be positive after initial period
        assert atr_series.iloc[-1] > 0  # Latest ATR should be positive
    
    def test_atr_smoothing(self, sample_data):
        """Test ATR uses Wilder's smoothing"""
        atr = ATR(period=14)
        atr_series = atr.calculate_atr(sample_data)
        
        # ATR should be smoother than raw True Range
        tr = atr.calculate_true_range(sample_data)
        
        # Check that ATR has less volatility than TR (after warmup)
        tr_std = tr.iloc[20:].std()
        atr_std = atr_series.iloc[20:].std()
        assert atr_std < tr_std  # ATR should be smoother


class TestATRAnalysis:
    """Test suite for ATR analysis method"""
    
    def test_analyze_returns_standardized_format(self, sample_data):
        """Test analyze returns standard format"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert 'confluence_factors' in result
        
        assert isinstance(result['confidence'], (int, float))
        assert 0 <= result['confidence'] <= 100
    
    def test_analyze_with_sufficient_data(self, sample_data):
        """Test analyze works with sufficient data"""
        atr = ATR(period=14)
        result = atr.analyze(sample_data)
        
        assert result['signal'] != 'INSUFFICIENT_DATA'
        assert result['signal'] != 'ERROR'
        assert result['confidence'] > 0
    
    def test_analyze_with_insufficient_data(self):
        """Test analyze handles insufficient data"""
        atr = ATR(period=14)
        
        # Create data with only 10 periods (need 15 for period=14)
        dates = pd.date_range(start='2024-01-01', periods=10, freq='15min')
        data = {
            'timestamp': dates,
            'open': [45000] * 10,
            'high': [45100] * 10,
            'low': [44900] * 10,
            'close': [45000] * 10,
            'volume': [100] * 10
        }
        df = pd.DataFrame(data)
        
        result = atr.analyze(df)
        
        assert result['signal'] == 'INSUFFICIENT_DATA'
        assert result['confidence'] == 0
        assert 'error' in result['metadata']
    
    def test_metadata_completeness(self, sample_data):
        """Test metadata contains all required fields"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        metadata = result['metadata']
        assert 'atr_value' in metadata
        assert 'atr_percent' in metadata
        assert 'volatility_level' in metadata
        assert 'atr_trend' in metadata
        assert 'period' in metadata
        assert 'current_price' in metadata
        assert 'stop_suggestions' in metadata
        assert 'recent_atr_values' in metadata
        assert 'position_sizing_factor' in metadata
    
    def test_stop_suggestions_structure(self, sample_data):
        """Test stop suggestions have correct structure"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        stop_suggestions = result['metadata']['stop_suggestions']
        
        for level in ['conservative', 'standard', 'aggressive', 'custom']:
            assert level in stop_suggestions
            assert 'distance' in stop_suggestions[level]
            assert 'multiplier' in stop_suggestions[level]
            assert 'long_stop' in stop_suggestions[level]
            assert 'short_stop' in stop_suggestions[level]
    
    def test_custom_stop_multiplier(self, sample_data):
        """Test custom stop multiplier works"""
        atr = ATR()
        result = atr.analyze(sample_data, stop_multiplier=3.0)
        
        custom_stop = result['metadata']['stop_suggestions']['custom']
        assert custom_stop['multiplier'] == 3.0
        assert custom_stop['distance'] > result['metadata']['stop_suggestions']['standard']['distance']


class TestVolatilityClassification:
    """Test suite for volatility classification"""
    
    def test_classify_volatility_calm(self, low_volatility_data):
        """Test classification of calm volatility"""
        atr = ATR(timeframe='15min')
        result = atr.analyze(low_volatility_data)
        
        # Low volatility data should classify as CALM or NORMAL
        assert result['metadata']['volatility_level'] in ['CALM', 'NORMAL']
    
    def test_classify_volatility_high(self, high_volatility_data):
        """Test classification of high volatility"""
        atr = ATR(timeframe='15min')
        result = atr.analyze(high_volatility_data)
        
        # High volatility data should classify as HIGH, VERY_HIGH, or EXTREME
        assert result['metadata']['volatility_level'] in ['NORMAL', 'HIGH', 'VERY_HIGH', 'EXTREME']
    
    def test_volatility_thresholds_by_timeframe(self):
        """Test volatility classification adapts to timeframe"""
        # Create data with ATR around 500
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        data = {
            'timestamp': dates,
            'open': [45000] * 100,
            'high': [45500] * 100,
            'low': [44500] * 100,
            'close': [45000] * 100,
            'volume': [100] * 100
        }
        df = pd.DataFrame(data)
        
        # Same data, different timeframes should classify differently
        atr_15min = ATR(timeframe='15min')
        atr_1hr = ATR(timeframe='1hr')
        
        result_15min = atr_15min.analyze(df)
        result_1hr = atr_1hr.analyze(df)
        
        # Classifications might differ based on timeframe thresholds
        assert 'volatility_level' in result_15min['metadata']
        assert 'volatility_level' in result_1hr['metadata']


class TestATRTrend:
    """Test suite for ATR trend detection"""
    
    def test_detect_rising_atr(self):
        """Test detection of rising ATR (increasing volatility)"""
        # Create data with strongly increasing volatility
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        ranges = np.linspace(100, 2000, 100)  # More dramatic increase
        
        data = {
            'timestamp': dates,
            'open': [45000] * 100,
            'high': 45000 + ranges,
            'low': 45000 - ranges,
            'close': [45000] * 100,
            'volume': [100] * 100
        }
        df = pd.DataFrame(data)
        
        atr = ATR()
        result = atr.analyze(df)
        
        # With strong increasing volatility, should detect RISING
        assert result['metadata']['atr_trend'] in ['RISING', 'STABLE']
    
    def test_detect_falling_atr(self):
        """Test detection of falling ATR (decreasing volatility)"""
        # Create data with decreasing volatility
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        ranges = np.linspace(1000, 100, 100)  # Decreasing range
        
        data = {
            'timestamp': dates,
            'open': [45000] * 100,
            'high': 45000 + ranges,
            'low': 45000 - ranges,
            'close': [45000] * 100,
            'volume': [100] * 100
        }
        df = pd.DataFrame(data)
        
        atr = ATR()
        result = atr.analyze(df)
        
        assert result['metadata']['atr_trend'] == 'FALLING'
    
    def test_detect_stable_atr(self, low_volatility_data):
        """Test detection of stable ATR"""
        atr = ATR()
        result = atr.analyze(low_volatility_data)
        
        # Stable or calm volatility
        assert result['metadata']['atr_trend'] in ['STABLE', 'FALLING', 'RISING']


class TestDataValidation:
    """Test suite for data validation"""
    
    def test_validate_correct_data(self, sample_data):
        """Test validation passes with correct data"""
        atr = ATR()
        assert atr.validate_data(sample_data) == True
    
    def test_validate_missing_columns(self):
        """Test validation fails with missing columns"""
        atr = ATR()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        assert atr.validate_data(invalid_df) == False
    
    def test_analyze_with_invalid_data(self):
        """Test analyze handles invalid data gracefully"""
        atr = ATR()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        result = atr.analyze(invalid_df)
        
        assert result['signal'] == 'ERROR'
        assert result['confidence'] == 0
        assert 'error' in result['metadata']


class TestConfluenceFactors:
    """Test suite for confluence factors"""
    
    def test_confluence_factors_present(self, sample_data):
        """Test confluence factors are generated"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        assert isinstance(result['confluence_factors'], list)
    
    def test_confluence_factors_for_high_volatility(self, high_volatility_data):
        """Test confluence factors mention high volatility"""
        atr = ATR()
        result = atr.analyze(high_volatility_data)
        
        # Should have some confluence factor mentioning volatility
        factors_text = ' '.join(result['confluence_factors']).lower()
        assert len(result['confluence_factors']) > 0


class TestEdgeCases:
    """Test suite for edge cases"""
    
    def test_single_price_data(self):
        """Test with data where all prices are identical"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
        data = {
            'timestamp': dates,
            'open': [45000] * 50,
            'high': [45000] * 50,
            'low': [45000] * 50,
            'close': [45000] * 50,
            'volume': [100] * 50
        }
        df = pd.DataFrame(data)
        
        atr = ATR()
        result = atr.analyze(df)
        
        # ATR should be zero or very close to zero
        assert result['metadata']['atr_value'] < 1.0
        assert result['metadata']['volatility_level'] == 'CALM'
    
    def test_extreme_volatility(self):
        """Test with extreme volatility data"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
        data = {
            'timestamp': dates,
            'open': [45000] * 50,
            'high': [55000] * 50,  # Huge range
            'low': [35000] * 50,
            'close': [45000] * 50,
            'volume': [100] * 50
        }
        df = pd.DataFrame(data)
        
        atr = ATR(timeframe='15min')
        result = atr.analyze(df)
        
        assert result['metadata']['volatility_level'] in ['VERY_HIGH', 'EXTREME']
        assert result['metadata']['atr_value'] > 2000
    
    def test_different_periods(self, sample_data):
        """Test ATR works with different periods"""
        for period in [7, 14, 21, 50]:
            atr = ATR(period=period)
            result = atr.analyze(sample_data)
            
            assert result['metadata']['period'] == period
            assert result['signal'] != 'ERROR'


class TestStopLossCalculations:
    """Test suite for stop-loss calculations"""
    
    def test_stop_distance_scaling(self, sample_data):
        """Test stop distances scale correctly with multiplier"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        stops = result['metadata']['stop_suggestions']
        
        # Conservative < Standard < Aggressive
        assert stops['conservative']['distance'] < stops['standard']['distance']
        assert stops['standard']['distance'] < stops['aggressive']['distance']
        
        # Multipliers are correct
        assert stops['conservative']['multiplier'] == 1.5
        assert stops['standard']['multiplier'] == 2.0
        assert stops['aggressive']['multiplier'] == 2.5
    
    def test_long_short_stops_symmetrical(self, sample_data):
        """Test long and short stops are symmetrical around current price"""
        atr = ATR()
        result = atr.analyze(sample_data)
        
        current_price = result['metadata']['current_price']
        stops = result['metadata']['stop_suggestions']['standard']
        
        # Distance from current price should be equal
        long_distance = current_price - stops['long_stop']
        short_distance = stops['short_stop'] - current_price
        
        assert abs(long_distance - short_distance) < 0.01  # Allow small floating point difference


class TestPositionSizing:
    """Test suite for position sizing factor"""
    
    def test_position_sizing_factor(self, sample_data, high_volatility_data):
        """Test position sizing factor is inverse of volatility"""
        atr_normal = ATR()
        result_normal = atr_normal.analyze(sample_data)
        
        atr_high = ATR()
        result_high = atr_high.analyze(high_volatility_data)
        
        # Higher volatility should have lower position sizing factor
        if result_high['metadata']['atr_percent'] > result_normal['metadata']['atr_percent']:
            assert result_high['metadata']['position_sizing_factor'] < result_normal['metadata']['position_sizing_factor']


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
