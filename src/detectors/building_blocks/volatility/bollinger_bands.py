"""
Bollinger Bands Building Block
Category: Volatility Indicators
Purpose: Volatility indicator using standard deviations around moving average
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class BollingerBands:
    """
    Bollinger Bands - Volatility Indicator
    
    Uses standard deviations around a moving average to identify overbought/oversold
    conditions, volatility expansion/contraction, and potential reversal patterns.
    
    Created by John Bollinger, Bollinger Bands consist of:
    - Middle Band: Simple Moving Average (typically 20 periods)
    - Upper Band: SMA + (Standard Deviation × Multiplier)
    - Lower Band: SMA - (Standard Deviation × Multiplier)
    
    Parameters:
        period: SMA calculation period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)
        timeframe: Timeframe string (e.g., '15min', '1hr', '4hr', '1D')
    
    Returns:
        Standardized dict with band values, position, squeeze detection, and patterns
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, timeframe: str = '15min', **kwargs):
        """
        Initialize Bollinger Bands block with parameters
        
        Args:
            period: SMA calculation period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
            timeframe: Timeframe for the data
        """
        self.period = period
        self.std_dev = std_dev
        self.timeframe = timeframe
        
        # Squeeze detection thresholds (band width as percentage of price)
        self.squeeze_thresholds = {
            '15min': {'tight': 0.5, 'normal': 1.5, 'wide': 3.0},
            '1hr': {'tight': 0.8, 'normal': 2.0, 'wide': 4.0},
            '4hr': {'tight': 1.0, 'normal': 2.5, 'wide': 5.0},
            '1D': {'tight': 1.5, 'normal': 3.5, 'wide': 7.0},
        }
    
    def calculate_bands(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands (Upper, Middle, Lower)
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band) Series
        """
        # Middle band is Simple Moving Average
        middle_band = df['close'].rolling(window=self.period).mean()
        
        # Calculate standard deviation
        std = df['close'].rolling(window=self.period).std()
        
        # Upper and lower bands
        upper_band = middle_band + (std * self.std_dev)
        lower_band = middle_band - (std * self.std_dev)
        
        return upper_band, middle_band, lower_band
    
    def calculate_band_width(self, upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
        """
        Calculate Bollinger Band Width
        
        Band Width = (Upper Band - Lower Band) / Middle Band
        Used to identify squeeze (low volatility) and expansion (high volatility)
        
        Args:
            upper: Upper band series
            lower: Lower band series
            middle: Middle band series
            
        Returns:
            Band width as percentage
        """
        return ((upper - lower) / middle) * 100
    
    def calculate_percent_b(self, close: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
        """
        Calculate %B (Percent B)
        
        %B = (Close - Lower Band) / (Upper Band - Lower Band)
        - %B > 1.0: Price above upper band (overbought)
        - %B < 0.0: Price below lower band (oversold)
        - %B = 0.5: Price at middle band
        
        Args:
            close: Close price series
            upper: Upper band series
            lower: Lower band series
            
        Returns:
            %B values
        """
        return (close - lower) / (upper - lower)
    
    def detect_squeeze(self, band_width: float, price: float) -> str:
        """
        Detect Bollinger Squeeze (low volatility before breakout)
        
        Args:
            band_width: Current band width percentage
            price: Current price
            
        Returns:
            Squeeze classification
        """
        thresholds = self.squeeze_thresholds.get(
            self.timeframe,
            self.squeeze_thresholds['15min']
        )
        
        if band_width < thresholds['tight']:
            return 'TIGHT_SQUEEZE'
        elif band_width < thresholds['normal']:
            return 'NORMAL'
        elif band_width < thresholds['wide']:
            return 'EXPANDING'
        else:
            return 'WIDE'
    
    def detect_squeeze_breakout(self, band_width_series: pd.Series, 
                                close_series: pd.Series, 
                                upper_series: pd.Series,
                                lower_series: pd.Series,
                                lookback: int = 10) -> Dict[str, Any]:
        """
        Detect Bollinger Squeeze Breakout
        
        A squeeze breakout occurs when:
        1. Band width was in TIGHT_SQUEEZE recently
        2. Band width is now expanding
        3. Price breaks decisively through upper or lower band
        
        Args:
            band_width_series: Series of band width values
            close_series: Series of close prices
            upper_series: Series of upper band values
            lower_series: Series of lower band values
            lookback: Periods to look back for squeeze
            
        Returns:
            Dictionary with breakout status and details
        """
        if len(band_width_series) < lookback:
            return {
                'breakout_detected': False,
                'breakout_direction': None,
                'squeeze_duration': 0,
                'breakout_strength': 0.0
            }
        
        # Get thresholds
        thresholds = self.squeeze_thresholds.get(
            self.timeframe,
            self.squeeze_thresholds['15min']
        )
        
        # Check recent band widths
        recent_widths = band_width_series.iloc[-lookback:].values
        current_width = band_width_series.iloc[-1]
        
        # Was there a squeeze recently?
        squeeze_count = sum(recent_widths < thresholds['tight'])
        
        if squeeze_count < 3:  # Need at least 3 periods in squeeze
            return {
                'breakout_detected': False,
                'breakout_direction': None,
                'squeeze_duration': 0,
                'breakout_strength': 0.0
            }
        
        # Check if bands are expanding now
        width_change = current_width - recent_widths[-2]
        is_expanding = width_change > 0 and current_width > thresholds['tight']
        
        if not is_expanding:
            return {
                'breakout_detected': False,
                'breakout_direction': 'PENDING',
                'squeeze_duration': squeeze_count,
                'breakout_strength': 0.0
            }
        
        # Determine breakout direction
        current_price = close_series.iloc[-1]
        current_upper = upper_series.iloc[-1]
        current_lower = lower_series.iloc[-1]
        band_range = current_upper - current_lower
        
        # Bullish breakout: price breaks above upper band
        if current_price > current_upper:
            breakout_strength = ((current_price - current_upper) / band_range) * 100
            return {
                'breakout_detected': True,
                'breakout_direction': 'BULLISH',
                'squeeze_duration': squeeze_count,
                'breakout_strength': round(breakout_strength, 2)
            }
        
        # Bearish breakout: price breaks below lower band
        elif current_price < current_lower:
            breakout_strength = ((current_lower - current_price) / band_range) * 100
            return {
                'breakout_detected': True,
                'breakout_direction': 'BEARISH',
                'squeeze_duration': squeeze_count,
                'breakout_strength': round(breakout_strength, 2)
            }
        
        # Bands expanding but price still in range
        else:
            return {
                'breakout_detected': False,
                'breakout_direction': 'PENDING',
                'squeeze_duration': squeeze_count,
                'breakout_strength': 0.0
            }
    
    def detect_band_walk(self, percent_b: pd.Series, lookback: int = 5) -> str:
        """
        Detect 'Band Walk' - when price consistently stays near band edge in trending market
        
        Args:
            percent_b: %B values series
            lookback: Periods to check
            
        Returns:
            Band walk status
        """
        if len(percent_b) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent_b = percent_b.iloc[-lookback:].values
        
        # Upper band walk (strong uptrend)
        if np.mean(recent_b > 0.8) >= 0.6:  # 60%+ of time above 0.8
            return 'UPPER_BAND_WALK'
        
        # Lower band walk (strong downtrend)
        if np.mean(recent_b < 0.2) >= 0.6:  # 60%+ of time below 0.2
            return 'LOWER_BAND_WALK'
        
        return 'NO_WALK'
    
    def detect_w_bottom(self, df: pd.DataFrame, lower_band: pd.Series, lookback: int = 20) -> bool:
        """
        Detect W-Bottom pattern (bullish reversal)
        
        W-Bottom criteria:
        - First low penetrates lower band
        - Rally to middle
        - Second low holds above lower band (bullish divergence)
        - Break above middle band confirms
        
        Args:
            df: OHLCV DataFrame
            lower_band: Lower band series
            lookback: Periods to search for pattern
            
        Returns:
            True if W-Bottom detected
        """
        if len(df) < lookback:
            return False
        
        # Simplified W-Bottom detection
        recent_data = df.iloc[-lookback:]
        recent_lower = lower_band.iloc[-lookback:]
        
        # Find lows
        lows = recent_data['low'].values
        closes = recent_data['close'].values
        lower_vals = recent_lower.values
        
        # Check for price touching/penetrating lower band
        touches_lower = closes < (lower_vals * 1.01)  # Within 1% of lower band
        
        if touches_lower.sum() >= 2:  # At least 2 touches
            return True
        
        return False
    
    def detect_m_top(self, df: pd.DataFrame, upper_band: pd.Series, lookback: int = 20) -> bool:
        """
        Detect M-Top pattern (bearish reversal)
        
        M-Top criteria:
        - First high penetrates upper band
        - Pull back to middle
        - Second high fails to penetrate upper band (bearish divergence)
        - Break below middle band confirms
        
        Args:
            df: OHLCV DataFrame
            upper_band: Upper band series
            lookback: Periods to search for pattern
            
        Returns:
            True if M-Top detected
        """
        if len(df) < lookback:
            return False
        
        # Simplified M-Top detection
        recent_data = df.iloc[-lookback:]
        recent_upper = upper_band.iloc[-lookback:]
        
        # Find highs
        highs = recent_data['high'].values
        closes = recent_data['close'].values
        upper_vals = recent_upper.values
        
        # Check for price touching/penetrating upper band
        touches_upper = closes > (upper_vals * 0.99)  # Within 1% of upper band
        
        if touches_upper.sum() >= 2:  # At least 2 touches
            return True
        
        return False
    
    def classify_position(self, percent_b: float) -> str:
        """
        Classify price position relative to bands
        
        Args:
            percent_b: Current %B value
            
        Returns:
            Position classification
        """
        if percent_b > 1.0:
            return 'ABOVE_UPPER'
        elif percent_b > 0.8:
            return 'NEAR_UPPER'
        elif percent_b > 0.6:
            return 'UPPER_HALF'
        elif percent_b > 0.4:
            return 'LOWER_HALF'
        elif percent_b > 0.2:
            return 'NEAR_LOWER'
        else:
            return 'BELOW_LOWER'
    
    def classify_volatility_regime(self, band_width_series: pd.Series, lookback: int = 50) -> Dict[str, Any]:
        """
        Classify current volatility regime based on historical band width percentiles
        
        This helps traders adapt their strategy to market conditions:
        - LOW: Consolidation phase, expect breakout soon
        - MEDIUM: Normal volatility, standard strategies work
        - HIGH: Increased volatility, widen stops
        - EXTREME: Very high volatility, reduce position size or stay out
        
        Args:
            band_width_series: Historical band width values
            lookback: Periods to analyze for percentile calculation
            
        Returns:
            Dictionary with regime classification and percentile rank
        """
        if len(band_width_series) < lookback:
            return {
                'regime': 'INSUFFICIENT_DATA',
                'percentile_rank': 0.0,
                'current_bandwidth': 0.0,
                'historical_median': 0.0,
                'historical_std': 0.0
            }
        
        # Get historical bandwidth values
        historical_widths = band_width_series.iloc[-lookback:].values
        current_width = band_width_series.iloc[-1]
        
        # Calculate percentile rank (where current width ranks in history)
        percentile_rank = (np.sum(historical_widths < current_width) / len(historical_widths)) * 100
        
        # Calculate historical statistics
        historical_median = np.median(historical_widths)
        historical_std = np.std(historical_widths)
        
        # Classify regime based on percentile
        if percentile_rank < 20:
            regime = 'LOW'  # Bottom 20% - very tight range, breakout imminent
        elif percentile_rank < 50:
            regime = 'MEDIUM_LOW'  # 20-50% - below average volatility
        elif percentile_rank < 80:
            regime = 'MEDIUM_HIGH'  # 50-80% - above average volatility
        elif percentile_rank < 95:
            regime = 'HIGH'  # 80-95% - high volatility
        else:
            regime = 'EXTREME'  # Top 5% - extreme volatility
        
        return {
            'regime': regime,
            'percentile_rank': round(percentile_rank, 2),
            'current_bandwidth': round(current_width, 2),
            'historical_median': round(historical_median, 2),
            'historical_std': round(historical_std, 2),
            'z_score': round((current_width - historical_median) / historical_std, 2) if historical_std > 0 else 0.0
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for Bollinger Bands building block
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters:
                - lookback_walk: Periods for band walk detection (default: 5)
                - lookback_pattern: Periods for pattern detection (default: 20)
        
        Returns:
            {
                'signal': str,  # Position classification
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # Band values, patterns, etc.
                'timestamp': datetime,
                'timeframe': str,
                'confluence_factors': list
            }
        """
        # Validate input data
        if not self.validate_data(df):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Need minimum periods for calculation
        if len(df) < self.period:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {
                    'error': f'Need at least {self.period} periods, got {len(df)}',
                    'required_periods': self.period,
                    'provided_periods': len(df)
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate Bollinger Bands
        upper, middle, lower = self.calculate_bands(df)
        
        # Get current values
        current_price = float(df['close'].iloc[-1])
        current_upper = float(upper.iloc[-1])
        current_middle = float(middle.iloc[-1])
        current_lower = float(lower.iloc[-1])
        
        # Calculate band width and %B
        band_width_series = self.calculate_band_width(upper, lower, middle)
        percent_b_series = self.calculate_percent_b(df['close'], upper, lower)
        
        current_band_width = float(band_width_series.iloc[-1])
        current_percent_b = float(percent_b_series.iloc[-1])
        
        # Get parameters
        lookback_walk = kwargs.get('lookback_walk', 5)
        lookback_pattern = kwargs.get('lookback_pattern', 20)
        
        # Detect squeeze
        squeeze_status = self.detect_squeeze(current_band_width, current_price)
        
        # Detect squeeze breakout
        squeeze_breakout = self.detect_squeeze_breakout(
            band_width_series, df['close'], upper, lower, lookback=10
        )
        
        # Detect band walk
        band_walk = self.detect_band_walk(percent_b_series, lookback_walk)
        
        # Detect patterns
        w_bottom = self.detect_w_bottom(df, lower, lookback_pattern)
        m_top = self.detect_m_top(df, upper, lookback_pattern)
        
        # Classify volatility regime
        volatility_regime = self.classify_volatility_regime(band_width_series, lookback=50)
        
        # Classify position
        position = self.classify_position(current_percent_b)
        
        # Calculate confidence based on data availability
        confidence = min(100, (len(df) / (self.period * 2)) * 100)
        
        # Adjust confidence based on pattern clarity
        if squeeze_status == 'TIGHT_SQUEEZE':
            confidence = min(100, confidence * 1.1)  # Boost for clear squeeze
        
        # Build confluence factors
        confluence_factors = []
        
        if position in ['ABOVE_UPPER', 'NEAR_UPPER']:
            confluence_factors.append('Price at/above upper band - overbought potential')
        elif position in ['BELOW_LOWER', 'NEAR_LOWER']:
            confluence_factors.append('Price at/below lower band - oversold potential')
        
        if squeeze_status == 'TIGHT_SQUEEZE':
            confluence_factors.append('Bollinger Squeeze detected - breakout imminent')
        elif squeeze_status == 'EXPANDING':
            confluence_factors.append('Bands expanding - volatility increasing')
        
        if band_walk == 'UPPER_BAND_WALK':
            confluence_factors.append('Upper band walk - strong uptrend')
        elif band_walk == 'LOWER_BAND_WALK':
            confluence_factors.append('Lower band walk - strong downtrend')
        
        if w_bottom:
            confluence_factors.append('W-Bottom pattern detected - bullish reversal signal')
        if m_top:
            confluence_factors.append('M-Top pattern detected - bearish reversal signal')
        
        # Add squeeze breakout confluence
        if squeeze_breakout['breakout_detected']:
            direction = squeeze_breakout['breakout_direction']
            strength = squeeze_breakout['breakout_strength']
            duration = squeeze_breakout['squeeze_duration']
            confluence_factors.append(
                f"SQUEEZE BREAKOUT: {direction} breakout detected (strength: {strength}%, squeeze duration: {duration} periods)"
            )
        elif squeeze_breakout['breakout_direction'] == 'PENDING':
            confluence_factors.append(
                f"Squeeze breakout pending - {squeeze_breakout['squeeze_duration']} periods in squeeze"
            )
        
        # Add volatility regime confluence
        if volatility_regime['regime'] != 'INSUFFICIENT_DATA':
            regime = volatility_regime['regime']
            percentile = volatility_regime['percentile_rank']
            
            if regime == 'LOW':
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Consolidation, breakout expected")
            elif regime == 'EXTREME':
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Extreme volatility, reduce position size")
            elif regime in ['HIGH', 'MEDIUM_HIGH']:
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Elevated volatility, widen stops")
            else:
                confluence_factors.append(f"Volatility regime: {regime} ({percentile}th percentile) - Normal conditions")
        
        # Determine signal
        if squeeze_breakout['breakout_detected']:
            # Squeeze breakout takes priority as it's a strong signal
            if squeeze_breakout['breakout_direction'] == 'BULLISH':
                signal = 'SQUEEZE_BREAKOUT_BULL'
            elif squeeze_breakout['breakout_direction'] == 'BEARISH':
                signal = 'SQUEEZE_BREAKOUT_BEAR'
            else:
                signal = position
        elif w_bottom:
            signal = 'BULLISH_REVERSAL'
        elif m_top:
            signal = 'BEARISH_REVERSAL'
        else:
            signal = position
        
        # Prepare metadata
        metadata = {
            'upper_band': round(current_upper, 2),
            'middle_band': round(current_middle, 2),
            'lower_band': round(current_lower, 2),
            'current_price': round(current_price, 2),
            'band_width': round(current_band_width, 2),
            'percent_b': round(current_percent_b, 4),
            'position': position,
            'squeeze_status': squeeze_status,
            'squeeze_breakout': squeeze_breakout,
            'volatility_regime': volatility_regime,
            'band_walk': band_walk,
            'patterns': {
                'w_bottom': w_bottom,
                'm_top': m_top
            },
            'period': self.period,
            'std_dev_multiplier': self.std_dev,
            'distance_from_middle': round(((current_price - current_middle) / current_middle) * 100, 2),
            'recent_band_widths': band_width_series.tail(10).tolist(),
            'recent_percent_b': percent_b_series.tail(10).tolist()
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data has required columns
        
        Args:
            df: Input DataFrame
            
        Returns:
            True if valid, False otherwise
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample Bitcoin data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    # Create sample data with realistic Bitcoin prices
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)  # Uptrend
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
    
    # Test Bollinger Bands block
    bb_block = BollingerBands(period=20, std_dev=2.0, timeframe='15min')
    result = bb_block.analyze(df)
    
    print("=" * 80)
    print("BOLLINGER BANDS BUILDING BLOCK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nBand Values:")
    print(f"  Upper Band: ${result['metadata']['upper_band']:.2f}")
    print(f"  Middle Band: ${result['metadata']['middle_band']:.2f}")
    print(f"  Lower Band: ${result['metadata']['lower_band']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"\nIndicators:")
    print(f"  Band Width: {result['metadata']['band_width']:.2f}%")
    print(f"  %B: {result['metadata']['percent_b']:.4f}")
    print(f"  Position: {result['metadata']['position']}")
    print(f"  Squeeze Status: {result['metadata']['squeeze_status']}")
    print(f"  Band Walk: {result['metadata']['band_walk']}")
    print(f"\nPatterns:")
    print(f"  W-Bottom: {result['metadata']['patterns']['w_bottom']}")
    print(f"  M-Top: {result['metadata']['patterns']['m_top']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
