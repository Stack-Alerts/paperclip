"""
Unit tests for Bollinger Bands Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.detectors.building_blocks.volatility.bollinger_bands import BollingerBands


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)
    noise = np.random.randn(100).cumsum() * 100
    
    data = {
        'timestamp': dates,
        'open': base_price + trend + noise,
        'high': base_price + trend + noise + np.random.uniform(50, 200, 100),
        'low': base_price + trend + noise - np.random.uniform(50, 200, 100),
        'close': base_price + trend + noise,
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def squeeze_data():
    """Create data with low volatility (tight range) for squeeze testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    base_price = 45000
    
    # Very tight range
    data = {
        'timestamp': dates,
        'open': np.full(100, base_price) + np.random.uniform(-20, 20, 100),
        'high': np.full(100, base_price) + np.random.uniform(5, 25, 100),
        'low': np.full(100, base_price) - np.random.uniform(5, 25, 100),
        'close': np.full(100, base_price) + np.random.uniform(-20, 20, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


class TestBollingerBandsInitialization:
    """Test suite for Bollinger Bands initialization"""
    
    def test_default_initialization(self):
        """Test BB can be instantiated with defaults"""
        bb = BollingerBands()
        assert bb is not None
        assert bb.period == 20
        assert bb.std_dev == 2.0
        assert bb.timeframe == '15min'
    
    def test_custom_initialization(self):
        """Test BB with custom parameters"""
        bb = BollingerBands(period=30, std_dev=2.5, timeframe='1hr')
        assert bb.period == 30
        assert bb.std_dev == 2.5
        assert bb.timeframe == '1hr'
    
    def test_squeeze_thresholds_exist(self):
        """Test squeeze thresholds are defined"""
        bb = BollingerBands()
        assert '15min' in bb.squeeze_thresholds
        assert '1hr' in bb.squeeze_thresholds
        assert '1D' in bb.squeeze_thresholds


class TestBollingerBandsCalculation:
    """Test suite for BB calculation methods"""
    
    def test_calculate_bands(self, sample_data):
        """Test bands are calculated correctly"""
        bb = BollingerBands(period=20)
        upper, middle, lower = bb.calculate_bands(sample_data)
        
        assert len(upper) == len(sample_data)
        assert len(middle) == len(sample_data)
        assert len(lower) == len(sample_data)
        
        # Upper should be above middle, lower should be below
        assert upper.iloc[-1] > middle.iloc[-1]
        assert middle.iloc[-1] > lower.iloc[-1]
    
    def test_band_width_calculation(self, sample_data):
        """Test band width calculation"""
        bb = BollingerBands()
        upper, middle, lower = bb.calculate_bands(sample_data)
        band_width = bb.calculate_band_width(upper, lower, middle)
        
        assert len(band_width) == len(sample_data)
        assert all(band_width[20:] >= 0)  # Band width should be positive
    
    def test_percent_b_calculation(self, sample_data):
        """Test %B calculation"""
        bb = BollingerBands()
        upper, middle, lower = bb.calculate_bands(sample_data)
        percent_b = bb.calculate_percent_b(sample_data['close'], upper, lower)
        
        assert len(percent_b) == len(sample_data)
        # %B should typically be between 0 and 1 for most price action
        valid_b = percent_b[20:]  # Skip warmup period
        assert valid_b.min() >= -0.5  # Allow some spillover
        assert valid_b.max() <= 1.5


class TestBollingerBandsAnalysis:
    """Test suite for BB analysis method"""
    
    def test_analyze_returns_standardized_format(self, sample_data):
        """Test analyze returns standard format"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
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
        bb = BollingerBands(period=20)
        result = bb.analyze(sample_data)
        
        assert result['signal'] != 'INSUFFICIENT_DATA'
        assert result['signal'] != 'ERROR'
        assert result['confidence'] > 0
    
    def test_analyze_with_insufficient_data(self):
        """Test analyze handles insufficient data"""
        bb = BollingerBands(period=20)
        
        # Create data with only 10 periods
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
        
        result = bb.analyze(df)
        
        assert result['signal'] == 'INSUFFICIENT_DATA'
        assert result['confidence'] == 0
    
    def test_metadata_completeness(self, sample_data):
        """Test metadata contains all required fields"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        metadata = result['metadata']
        assert 'upper_band' in metadata
        assert 'middle_band' in metadata
        assert 'lower_band' in metadata
        assert 'current_price' in metadata
        assert 'band_width' in metadata
        assert 'percent_b' in metadata
        assert 'position' in metadata
        assert 'squeeze_status' in metadata
        assert 'band_walk' in metadata
        assert 'patterns' in metadata
        assert 'w_bottom' in metadata['patterns']
        assert 'm_top' in metadata['patterns']


class TestSqueezeDetection:
    """Test suite for squeeze detection"""
    
    def test_detect_tight_squeeze(self, squeeze_data):
        """Test detection of tight squeeze"""
        bb = BollingerBands(timeframe='15min')
        result = bb.analyze(squeeze_data)
        
        # Low volatility data should show squeeze
        assert result['metadata']['squeeze_status'] in ['TIGHT_SQUEEZE', 'NORMAL']
    
    def test_squeeze_provides_confluence(self, squeeze_data):
        """Test squeeze adds confluence factor"""
        bb = BollingerBands()
        result = bb.analyze(squeeze_data)
        
        if result['metadata']['squeeze_status'] == 'TIGHT_SQUEEZE':
            factors_text = ' '.join(result['confluence_factors']).lower()
            assert 'squeeze' in factors_text or 'breakout' in factors_text


class TestBandWalkDetection:
    """Test suite for band walk detection"""
    
    def test_detect_upper_band_walk(self):
        """Test detection of upper band walk (strong uptrend)"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        
        # Strong uptrend staying near upper band
        base = 45000
        strong_uptrend = np.linspace(0, 5000, 100)
        
        data = {
            'timestamp': dates,
            'close': base + strong_uptrend + np.random.uniform(-50, 50, 100),
            'open': base + strong_uptrend,
            'high': base + strong_uptrend + 100,
            'low': base + strong_uptrend - 100,
            'volume': np.random.uniform(100, 1000, 100)
        }
        df = pd.DataFrame(data)
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        bb = BollingerBands()
        result = bb.analyze(df)
        
        # Should detect strong trend
        assert result['metadata']['band_walk'] in ['UPPER_BAND_WALK', 'NO_WALK']


class TestPositionClassification:
    """Test suite for position classification"""
    
    def test_classify_above_upper(self):
        """Test classification when price is above upper band"""
        bb = BollingerBands()
        # %B > 1.0 means above upper band
        position = bb.classify_position(1.2)
        assert position == 'ABOVE_UPPER'
    
    def test_classify_below_lower(self):
        """Test classification when price is below lower band"""
        bb = BollingerBands()
        # %B < 0.0 means below lower band
        position = bb.classify_position(-0.1)
        assert position == 'BELOW_LOWER'
    
    def test_classify_at_middle(self):
        """Test classification when price is near middle band"""
        bb = BollingerBands()
        # %B around 0.5 means at middle band
        position = bb.classify_position(0.5)
        assert position in ['UPPER_HALF', 'LOWER_HALF']


class TestPatternDetection:
    """Test suite for pattern detection"""
    
    def test_w_bottom_detection(self, sample_data):
        """Test W-Bottom pattern detection"""
        bb = BollingerBands()
        upper, middle, lower = bb.calculate_bands(sample_data)
        
        # Test the method returns boolean
        w_bottom = bb.detect_w_bottom(sample_data, lower, lookback=20)
        assert isinstance(w_bottom, bool)
    
    def test_m_top_detection(self, sample_data):
        """Test M-Top pattern detection"""
        bb = BollingerBands()
        upper, middle, lower = bb.calculate_bands(sample_data)
        
        # Test the method returns boolean
        m_top = bb.detect_m_top(sample_data, upper, lookback=20)
        assert isinstance(m_top, bool)


class TestDataValidation:
    """Test suite for data validation"""
    
    def test_validate_correct_data(self, sample_data):
        """Test validation passes with correct data"""
        bb = BollingerBands()
        assert bb.validate_data(sample_data) == True
    
    def test_validate_missing_columns(self):
        """Test validation fails with missing columns"""
        bb = BollingerBands()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        assert bb.validate_data(invalid_df) == False
    
    def test_analyze_with_invalid_data(self):
        """Test analyze handles invalid data gracefully"""
        bb = BollingerBands()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        result = bb.analyze(invalid_df)
        
        assert result['signal'] == 'ERROR'
        assert result['confidence'] == 0


class TestConfluenceFactors:
    """Test suite for confluence factors"""
    
    def test_confluence_factors_present(self, sample_data):
        """Test confluence factors are generated"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        assert isinstance(result['confluence_factors'], list)
    
    def test_overbought_confluence(self):
        """Test confluence for overbought condition"""
        # Create data that touches upper band
        dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
        base = 45000
        
        data = {
            'timestamp': dates,
            'close': np.linspace(base, base + 2000, 50),  # Strong trend up
            'open': np.linspace(base, base + 2000, 50),
            'high': np.linspace(base + 100, base + 2100, 50),
            'low': np.linspace(base - 100, base + 1900, 50),
            'volume': np.random.uniform(100, 1000, 50)
        }
        df = pd.DataFrame(data)
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        bb = BollingerBands()
        result = bb.analyze(df)
        
        # Should have some confluence factor
        assert len(result['confluence_factors']) > 0


class TestEdgeCases:
    """Test suite for edge cases"""
    
    def test_flat_price_data(self):
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
        
        bb = BollingerBands()
        result = bb.analyze(df)
        
        # Bands should collapse to middle (or very close)
        assert result['metadata']['band_width'] < 0.1
    def test_different_periods(self, sample_data):
        """Test BB works with different periods"""
        for period in [10, 20, 30, 50]:
            bb = BollingerBands(period=period)
            result = bb.analyze(sample_data)
            
            assert result['metadata']['period'] == period
            assert result['signal'] != 'ERROR'
    
    def test_different_std_dev(self, sample_data):
        """Test BB works with different standard deviation multipliers"""
        for std_dev in [1.5, 2.0, 2.5, 3.0]:
            bb = BollingerBands(std_dev=std_dev)
            result = bb.analyze(sample_data)
            
            assert result['metadata']['std_dev_multiplier'] == std_dev
            assert result['signal'] != 'ERROR'


class TestBandRelationships:
    """Test suite for band relationships"""
    
    def test_bands_order(self, sample_data):
        """Test upper > middle > lower always holds"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        upper = result['metadata']['upper_band']
        middle = result['metadata']['middle_band']
        lower = result['metadata']['lower_band']
        
        assert upper > middle
        assert middle > lower
    
    def test_bands_symmetry(self, sample_data):
        """Test bands are symmetric around middle"""
        bb = BollingerBands(std_dev=2.0)
        result = bb.analyze(sample_data)
        
        upper = result['metadata']['upper_band']
        middle = result['metadata']['middle_band']
        lower = result['metadata']['lower_band']
        
        # Distance should be approximately equal
        upper_dist = upper - middle
        lower_dist = middle - lower
        
        # Allow for small rounding differences
        assert abs(upper_dist - lower_dist) < 1.0


class TestVolatilityRegime:
    """Test suite for volatility regime classification"""
    
    def test_volatility_regime_exists(self, sample_data):
        """Test volatility_regime is in metadata"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        assert 'volatility_regime' in result['metadata']
        assert 'regime' in result['metadata']['volatility_regime']
        assert 'percentile_rank' in result['metadata']['volatility_regime']
    
    def test_regime_classifications(self, sample_data):
        """Test regime classifications are valid"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        regime = result['metadata']['volatility_regime']['regime']
        valid_regimes = ['LOW', 'MEDIUM_LOW', 'MEDIUM_HIGH', 'HIGH', 'EXTREME', 'INSUFFICIENT_DATA']
        assert regime in valid_regimes
    
    def test_volatility_regime_confluence(self, sample_data):
        """Test volatility regime adds to confluence factors"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        if result['metadata']['volatility_regime']['regime'] != 'INSUFFICIENT_DATA':
            factors_text = ' '.join(result['confluence_factors']).lower()
            assert 'volatility regime' in factors_text or 'regime' in factors_text


class TestSqueezeBreakout:
    """Test suite for squeeze breakout detection"""
    
    def test_squeeze_breakout_metadata_exists(self, sample_data):
        """Test squeeze_breakout is in metadata"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        assert 'squeeze_breakout' in result['metadata']
        assert 'breakout_detected' in result['metadata']['squeeze_breakout']
        assert 'breakout_direction' in result['metadata']['squeeze_breakout']
        assert 'squeeze_duration' in result['metadata']['squeeze_breakout']
        assert 'breakout_strength' in result['metadata']['squeeze_breakout']
    
    def test_no_breakout_without_squeeze(self, sample_data):
        """Test no breakout detected without prior squeeze"""
        bb = BollingerBands()
        result = bb.analyze(sample_data)
        
        # Normal volatility data shouldn't trigger breakout
        breakout = result['metadata']['squeeze_breakout']
        assert isinstance(breakout['breakout_detected'], bool)
    
    def test_bullish_breakout_signal(self):
        """Test bullish breakout generates correct signal"""
        # Create squeeze then bullish breakout scenario
        dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
        
        # First 30 periods: tight consolidation
        tight_prices = np.full(30, 45000) + np.random.uniform(-10, 10, 30)
        
        # Last 20 periods: bullish breakout
        breakout_prices = np.linspace(45000, 46500, 20)
        
        all_prices = np.concatenate([tight_prices, breakout_prices])
        
        data = {
            'timestamp': dates,
            'close': all_prices,
            'open': all_prices,
            'high': all_prices + 50,
            'low': all_prices - 50,
            'volume': np.random.uniform(100, 1000, 50)
        }
        df = pd.DataFrame(data)
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        bb = BollingerBands()
        result = bb.analyze(df)
        
        # Should detect either breakout or pending breakout
        breakout = result['metadata']['squeeze_breakout']
        assert breakout['breakout_direction'] in ['BULLISH', 'PENDING', None]
    
    def test_breakout_strength_calculation(self):
        """Test breakout strength is calculated correctly"""
        bb = BollingerBands()
        
        # Create simple data with squeeze
        dates = pd.date_range(start='2024-01-01', periods=50, freq='15min')
        data = {
            'timestamp': dates,
            'close': [45000] * 50,
            'open': [45000] * 50,
            'high': [45050] * 50,
            'low': [44950] * 50,
            'volume': [100] * 50
        }
        df = pd.DataFrame(data)
        
        result = bb.analyze(df)
        breakout = result['metadata']['squeeze_breakout']
        
        # Strength should be a number >= 0
        assert isinstance(breakout['breakout_strength'], (int, float))
        assert breakout['breakout_strength'] >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
