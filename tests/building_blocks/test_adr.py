"""
Unit tests for ADR (Average Daily Range) Building Block
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.detectors.building_blocks.volatility.adr import ADR


@pytest.fixture
def daily_data():
    """Create sample daily OHLCV data"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='1D')
    np.random.seed(42)
    base_price = 45000
    
    # Create varying daily ranges
    ranges = np.random.uniform(1000, 2000, 30)
    
    data = {
        'timestamp': dates,
        'open': [base_price] * 30,
        'high': [base_price + r/2 for r in ranges],
        'low': [base_price - r/2 for r in ranges],
        'close': [base_price] * 30,
        'volume': np.random.uniform(1000, 10000, 30)
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def intraday_data():
    """Create sample intraday data (15min) that spans multiple days"""
    # 3 days of 15min data
    dates = pd.date_range(start='2024-01-01', periods=288, freq='15min')
    np.random.seed(42)
    base_price = 45000
    
    data = {
        'timestamp': dates,
        'open': base_price + np.random.randn(288).cumsum() * 10,
        'high': base_price + np.random.randn(288).cumsum() * 10 + np.random.uniform(50, 200, 288),
        'low': base_price + np.random.randn(288).cumsum() * 10 - np.random.uniform(50, 200, 288),
        'close': base_price + np.random.randn(288).cumsum() * 10,
        'volume': np.random.uniform(100, 1000, 288)
    }
    df = pd.DataFrame(data)
    
    # Ensure OHLC logic
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


class TestADRInitialization:
    """Test suite for ADR initialization"""
    
    def test_default_initialization(self):
        """Test ADR can be instantiated with defaults"""
        adr = ADR()
        assert adr is not None
        assert adr.period == 14
        assert adr.timeframe == '1D'
    
    def test_custom_initialization(self):
        """Test ADR with custom parameters"""
        adr = ADR(period=20, timeframe='15min')
        assert adr.period == 20
        assert adr.timeframe == '15min'
    
    def test_range_thresholds_exist(self):
        """Test Bitcoin range thresholds are defined"""
        adr = ADR()
        assert 'calm' in adr.btc_range_thresholds
        assert 'normal' in adr.btc_range_thresholds
        assert 'extreme' in adr.btc_range_thresholds


class TestDailyRangeCalculation:
    """Test suite for daily range calculation"""
    
    def test_daily_range_calculation(self, daily_data):
        """Test daily range is calculated correctly"""
        adr = ADR(timeframe='1D')
        daily_ranges = adr.calculate_daily_range(daily_data)
        
        assert len(daily_ranges) == len(daily_data)
        assert all(daily_ranges >= 0)  # Ranges should be positive
    
    def test_intraday_to_daily_conversion(self, intraday_data):
        """Test conversion from intraday to daily data"""
        adr = ADR(timeframe='15min')
        daily_ranges = adr.calculate_daily_range(intraday_data)
        
        # Should have 3 days of data
        assert len(daily_ranges) == 3
        assert all(daily_ranges > 0)


class TestADRCalculation:
    """Test suite for ADR calculation"""
    
    def test_adr_with_sufficient_data(self, daily_data):
        """Test ADR calculation with sufficient data"""
        adr = ADR(period=14)
        daily_ranges = adr.calculate_daily_range(daily_data)
        adr_value = adr.calculate_adr(daily_ranges)
        
        assert adr_value > 0
        assert isinstance(adr_value, (int, float))
    
    def test_adr_with_insufficient_data(self):
        """Test ADR with less data than period"""
        dates = pd.date_range(start='2024-01-01', periods=5, freq='1D')
        data = {
            'timestamp': dates,
            'high': [45500] * 5,
            'low': [44500] * 5,
            'close': [45000] * 5
        }
        df = pd.DataFrame(data)
        
        adr = ADR(period=14)
        daily_ranges = adr.calculate_daily_range(df)
        adr_value = adr.calculate_adr(daily_ranges)
        
        # Should still return a value (mean of available data)
        assert adr_value == 1000.0


class TestRangePercentile:
    """Test suite for range percentile calculation"""
    
    def test_percentile_calculation(self, daily_data):
        """Test percentile ranking works correctly"""
        adr = ADR()
        daily_ranges = adr.calculate_daily_range(daily_data)
        
        # Test with minimum range
        min_range = daily_ranges.min()
        percentile = adr.calculate_range_percentile(min_range, daily_ranges)
        assert percentile < 20  # Should be in lower percentiles
        
        # Test with maximum range
        max_range = daily_ranges.max()
        percentile = adr.calculate_range_percentile(max_range, daily_ranges)
        assert percentile > 80  # Should be in upper percentiles


class TestRangeClassification:
    """Test suite for range classification"""
    
    def test_calm_classification(self):
        """Test classification of calm range"""
        adr = ADR()
        classification = adr.classify_range(1.5)  # 1.5% range
        assert classification == 'CALM'
    
    def test_normal_classification(self):
        """Test classification of normal range"""
        adr = ADR()
        classification = adr.classify_range(3.0)  # 3% range
        assert classification == 'NORMAL'
    
    def test_elevated_classification(self):
        """Test classification of elevated range"""
        adr = ADR()
        classification = adr.classify_range(5.0)  # 5% range
        assert classification == 'ELEVATED'
    
    def test_extreme_classification(self):
        """Test classification of extreme range"""
        adr = ADR()
        classification = adr.classify_range(10.0)  # 10% range
        assert classification == 'EXTREME'


class TestExpansionContraction:
    """Test suite for expansion/contraction detection"""
    
    def test_expanding_ranges(self):
        """Test detection of expanding ranges"""
        # Create expanding ranges
        expanding = pd.Series([1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000])
        
        adr = ADR()
        trend = adr.calculate_expansion_contraction(expanding, lookback=5)
        assert trend == 'EXPANDING'
    
    def test_contracting_ranges(self):
        """Test detection of contracting ranges"""
        # Create contracting ranges
        contracting = pd.Series([2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300, 1200, 1100, 1000])
        
        adr = ADR()
        trend = adr.calculate_expansion_contraction(contracting, lookback=5)
        assert trend == 'CONTRACTING'
    
    def test_stable_ranges(self):
        """Test detection of stable ranges"""
        # Create stable ranges
        stable = pd.Series([1500] * 11)
        
        adr = ADR()
        trend = adr.calculate_expansion_contraction(stable, lookback=5)
        assert trend == 'STABLE'


class TestTargetSuggestions:
    """Test suite for profit target suggestions"""
    
    def test_target_structure(self):
        """Test target suggestions have correct structure"""
        adr = ADR()
        targets = adr.suggest_targets(adr=1500, current_price=45000)
        
        # Should have targets for default multipliers
        assert '0.5x_ADR' in targets
        assert '1.0x_ADR' in targets
        assert '1.5x_ADR' in targets
        assert '2.0x_ADR' in targets
        
        # Each target should have required fields
        for target_data in targets.values():
            assert 'multiplier' in target_data
            assert 'distance' in target_data
            assert 'long_target' in target_data
            assert 'short_target' in target_data
            assert 'percent' in target_data
    
    def test_target_calculations(self):
        """Test target calculations are correct"""
        adr = ADR()
        targets = adr.suggest_targets(adr=1000, current_price=45000)
        
        # Check 1x ADR target
        target_1x = targets['1.0x_ADR']
        assert target_1x['distance'] == 1000
        assert target_1x['long_target'] == 46000
        assert target_1x['short_target'] == 44000


class TestPositionSizing:
    """Test suite for position sizing factor"""
    
    def test_high_volatility_reduces_size(self):
        """Test high volatility reduces position size"""
        adr = ADR()
        # Current range is 2x the average
        factor = adr.calculate_position_sizing_factor(current_range_pct=8.0, adr_pct=4.0)
        assert factor < 1.0  # Should reduce position
    
    def test_low_volatility_increases_size(self):
        """Test low volatility increases position size"""
        adr = ADR()
        # Current range is 0.5x the average
        factor = adr.calculate_position_sizing_factor(current_range_pct=2.0, adr_pct=4.0)
        assert factor > 1.0  # Should increase position
    
    def test_normal_volatility_standard_size(self):
        """Test normal volatility keeps standard position size"""
        adr = ADR()
        # Current range equals average
        factor = adr.calculate_position_sizing_factor(current_range_pct=4.0, adr_pct=4.0)
        assert factor == 1.0  # Should keep standard size


class TestAnalysisMethod:
    """Test suite for analyze method"""
    
    def test_analyze_returns_standardized_format(self, daily_data):
        """Test analyze returns standard format"""
        adr = ADR()
        result = adr.analyze(daily_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'metadata' in result
        assert 'timestamp' in result
        assert 'timeframe' in result
        assert 'confluence_factors' in result
        
        assert isinstance(result['confidence'], (int, float))
        assert 0 <= result['confidence'] <= 100
    
    def test_analyze_with_sufficient_data(self, daily_data):
        """Test analyze works with sufficient data"""
        adr = ADR(period=14)
        result = adr.analyze(daily_data)
        
        assert result['signal'] != 'INSUFFICIENT_DATA'
        assert result['signal'] != 'ERROR'
        assert result['confidence'] > 0
    
    def test_analyze_with_insufficient_data(self):
        """Test analyze handles insufficient data"""
        dates = pd.date_range(start='2024-01-01', periods=1, freq='1D')
        data = {
            'timestamp': dates,
            'high': [45500],
            'low': [44500],
            'close': [45000]
        }
        df = pd.DataFrame(data)
        
        adr = ADR()
        result = adr.analyze(df)
        
        assert result['signal'] == 'INSUFFICIENT_DATA'
        assert result['confidence'] == 0
    
    def test_metadata_completeness(self, daily_data):
        """Test metadata contains all required fields"""
        adr = ADR()
        result = adr.analyze(daily_data)
        
        metadata = result['metadata']
        assert 'adr_value' in metadata
        assert 'adr_percent' in metadata
        assert 'current_range' in metadata
        assert 'current_range_percent' in metadata
        assert 'current_price' in metadata
        assert 'range_classification' in metadata
        assert 'range_percentile' in metadata
        assert 'range_trend' in metadata
        assert 'targets' in metadata
        assert 'position_sizing_factor' in metadata


class TestDataValidation:
    """Test suite for data validation"""
    
    def test_validate_correct_data(self, daily_data):
        """Test validation passes with correct data"""
        adr = ADR()
        assert adr.validate_data(daily_data) == True
    
    def test_validate_missing_columns(self):
        """Test validation fails with missing columns"""
        adr = ADR()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        assert adr.validate_data(invalid_df) == False
    
    def test_analyze_with_invalid_data(self):
        """Test analyze handles invalid data gracefully"""
        adr = ADR()
        invalid_df = pd.DataFrame({'wrong': [1, 2, 3]})
        result = adr.analyze(invalid_df)
        
        assert result['signal'] == 'ERROR'
        assert result['confidence'] == 0


class TestConfluenceFactors:
    """Test suite for confluence factors"""
    
    def test_confluence_factors_present(self, daily_data):
        """Test confluence factors are generated"""
        adr = ADR()
        result = adr.analyze(daily_data)
        
        assert isinstance(result['confluence_factors'], list)
        assert len(result['confluence_factors']) > 0
    
    def test_range_classification_in_confluence(self, daily_data):
        """Test range classification appears in confluence"""
        adr = ADR()
        result = adr.analyze(daily_data)
        
        factors_text = ' '.join(result['confluence_factors']).lower()
        classification = result['metadata']['range_classification'].lower()
        assert classification in factors_text


class TestEdgeCases:
    """Test suite for edge cases"""
    
    def test_zero_range_data(self):
        """Test with data where all prices are identical"""
        dates = pd.date_range(start='2024-01-01', periods=20, freq='1D')
        data = {
            'timestamp': dates,
            'high': [45000] * 20,
            'low': [45000] * 20,
            'close': [45000] * 20
        }
        df = pd.DataFrame(data)
        
        adr = ADR()
        result = adr.analyze(df)
        
        # ADR should be zero or very close
        assert result['metadata']['adr_value'] == 0.0
        assert result['metadata']['range_classification'] == 'CALM'
    
    def test_different_periods(self, daily_data):
        """Test ADR works with different periods"""
        for period in [7, 14, 21, 30]:
            adr = ADR(period=period)
            result = adr.analyze(daily_data)
            
            assert result['metadata']['period'] == period
            assert result['signal'] != 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
