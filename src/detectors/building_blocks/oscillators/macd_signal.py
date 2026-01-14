"""
MACD (Moving Average Convergence Divergence) Signal Building Block
Category: Oscillator Indicators
Purpose: Trend-following momentum indicator for trend identification and reversals
"""
"""
Building Block Classification: SIGNAL BLOCK
Mode: EVENT-DRIVEN
Purpose: MACD crossover signals, selective on cross events

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional, Tuple

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='macd_signal',
    category='OSCILLATORS',
    class_name='MACDSignal',
    default_weight=25,
    valid_signals=['BULLISH_DIVERGENCE', 'BEARISH_DIVERGENCE', 'BULLISH_ZERO_CROSS', 'BEARISH_ZERO_CROSS', 'BULLISH_CROSS', 'BEARISH_CROSS', 'BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        # Divergences - Highest value (reversal signals, rare) - ADVANCED
        'BULLISH_DIVERGENCE': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish divergence - price lower low, MACD higher low (reversal signal)'
        },
        'BEARISH_DIVERGENCE': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish divergence - price higher high, MACD lower high (reversal signal)'
        },
        
        # Zero crosses - Major trend confirmation - ADVANCED
        'BULLISH_ZERO_CROSS': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'MACD crossed above zero - bullish trend confirmation'
        },
        'BEARISH_ZERO_CROSS': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'MACD crossed below zero - bearish trend confirmation'
        },
        
        # Regular crossovers - Standard signals - ADVANCED
        'BULLISH_CROSS': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'MACD crossed above signal line - bullish momentum'
        },
        'BEARISH_CROSS': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'MACD crossed below signal line - bearish momentum'
        },
        
        # Simple directional signals - BASIC (for simple users)
        'BULLISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Bullish MACD signal - any bullish event (simple)'
        },
        'BEARISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Bearish MACD signal - any bearish event (simple)'
        },
        
        # Neutral
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'description': 'No MACD signal - holding position'
        },
        
        # Status
        'ERROR': {
            'points': 0,
            'description': 'Analysis error occurred'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'description': 'Not enough data for analysis'
        }
    },
    description='MACD Signal - Moving Average Convergence Divergence crossover detector with divergence detection',
    tags=['oscillators', 'macd', 'momentum', 'crossover', 'divergence', 'signal_block']
)
class MACDSignal:
    """
    MACD (Moving Average Convergence Divergence) - Momentum Oscillator
    
    Developed by Gerald Appel, MACD shows the relationship between two moving averages.
    
    Components:
    - MACD Line: 12-period EMA - 26-period EMA
    - Signal Line: 9-period EMA of MACD Line
    - Histogram: MACD Line - Signal Line
    
    Signals:
    - Bullish: MACD crosses above Signal (golden cross)
    - Bearish: MACD crosses below Signal (death cross)
    - Divergence: Price makes new high/low but MACD doesn't
    - Zero Line Cross: MACD crosses above/below zero
    
    Parameters:
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
        timeframe: Data timeframe (e.g., '15min', '1hr', '4hr', '1D')
    
    Returns:
        Standardized dict with MACD values, signals, and divergences
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 24, 
                 signal_period: int = 8, timeframe: str = '15min', **kwargs):
        """
        Initialize MACD block with OPTIMIZED parameters (institutional tuning 2026-01-01)
        
        Args:
            fast_period: Fast EMA period (default: 10, optimized from 12)
            slow_period: Slow EMA period (default: 24, optimized from 26)
            signal_period: Signal line EMA period (default: 8, optimized from 9)
            timeframe: Timeframe of the data
            
        Optimization Results (27 combinations tested on 17,281 bars):
            Quality: 80/100
            Accuracy: 55.5%
            Signals: 1448 in 180 days (8.04/day)
            R/R: 6.36 (excellent)
            Follow-through: 6.3 bars
            Discovery: ~10-20% faster parameters consistently outperform classic settings
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.timeframe = timeframe
        
        # Bitcoin-specific MACD thresholds (what constitutes strong signal)
        self.btc_strength_thresholds = {
            '15min': {'weak': 50, 'moderate': 150, 'strong': 300},
            '1hr': {'weak': 100, 'moderate': 250, 'strong': 500},
            '4hr': {'weak': 200, 'moderate': 500, 'strong': 1000},
            '1D': {'weak': 500, 'moderate': 1000, 'strong': 2000}
        }
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            data: Price series
            period: EMA period
            
        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD, Signal Line, and Histogram
        
        Args:
            close: Close price series
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        # Calculate EMAs
        fast_ema = self.calculate_ema(close, self.fast_period)
        slow_ema = self.calculate_ema(close, self.slow_period)
        
        # MACD Line
        macd_line = fast_ema - slow_ema
        
        # Signal Line
        signal_line = self.calculate_ema(macd_line, self.signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def detect_crossover(self, macd: pd.Series, signal: pd.Series, lookback: int = 3) -> str:
        """
        Detect MACD/Signal line crossovers
        
        Args:
            macd: MACD line series
            signal: Signal line series
            lookback: Periods to confirm crossover
            
        Returns:
            'BULLISH_CROSS', 'BEARISH_CROSS', or 'NO_CROSS'
        """
        if len(macd) < lookback + 1:
            return 'INSUFFICIENT_DATA'
        
        # Current state
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        
        # Previous state
        previous_macd = macd.iloc[-2]
        previous_signal = signal.iloc[-2]
        
        # Bullish crossover: MACD crosses above Signal
        if previous_macd <= previous_signal and current_macd > current_signal:
            return 'BULLISH_CROSS'
        
        # Bearish crossover: MACD crosses below Signal
        elif previous_macd >= previous_signal and current_macd < current_signal:
            return 'BEARISH_CROSS'
        
        return 'NO_CROSS'
    
    def detect_zero_line_cross(self, macd: pd.Series) -> str:
        """
        Detect MACD zero line crossovers
        
        Args:
            macd: MACD line series
            
        Returns:
            'BULLISH_ZERO_CROSS', 'BEARISH_ZERO_CROSS', or 'NO_ZERO_CROSS'
        """
        if len(macd) < 2:
            return 'INSUFFICIENT_DATA'
        
        current_macd = macd.iloc[-1]
        previous_macd = macd.iloc[-2]
        
        # Bullish zero cross: MACD crosses above zero
        if previous_macd <= 0 and current_macd > 0:
            return 'BULLISH_ZERO_CROSS'
        
        # Bearish zero cross: MACD crosses below zero
        elif previous_macd >= 0 and current_macd < 0:
            return 'BEARISH_ZERO_CROSS'
        
        return 'NO_ZERO_CROSS'
    
    def detect_divergence(self, price: pd.Series, macd: pd.Series, lookback: int = 20) -> Dict[str, bool]:
        """
        Detect bullish and bearish divergences
        
        Bullish Divergence: Price makes lower low, MACD makes higher low
        Bearish Divergence: Price makes higher high, MACD makes lower high
        
        Args:
            price: Price series
            macd: MACD line series
            lookback: Periods to search for divergence
            
        Returns:
            Dict with bullish and bearish divergence flags
        """
        if len(price) < lookback:
            return {'bullish_divergence': False, 'bearish_divergence': False}
        
        recent_price = price.iloc[-lookback:]
        recent_macd = macd.iloc[-lookback:]
        
        # Find lows and highs
        price_lows = recent_price.nsmallest(2)
        price_highs = recent_price.nlargest(2)
        macd_lows = recent_macd.nsmallest(2)
        macd_highs = recent_macd.nlargest(2)
        
        # Bullish divergence: price lower low, MACD higher low
        bullish_div = False
        if len(price_lows) == 2 and len(macd_lows) == 2:
            price_making_lower_low = price_lows.iloc[1] < price_lows.iloc[0]
            macd_making_higher_low = macd_lows.iloc[1] > macd_lows.iloc[0]
            bullish_div = price_making_lower_low and macd_making_higher_low
        
        # Bearish divergence: price higher high, MACD lower high
        bearish_div = False
        if len(price_highs) == 2 and len(macd_highs) == 2:
            price_making_higher_high = price_highs.iloc[1] > price_highs.iloc[0]
            macd_making_lower_high = macd_highs.iloc[1] < macd_highs.iloc[0]
            bearish_div = price_making_higher_high and macd_making_lower_high
        
        return {
            'bullish_divergence': bullish_div,
            'bearish_divergence': bearish_div
        }
    
    def classify_strength(self, histogram_value: float) -> str:
        """
        Classify signal strength based on histogram value
        
        Args:
            histogram_value: Current histogram value
            
        Returns:
            Strength classification
        """
        thresholds = self.btc_strength_thresholds.get(
            self.timeframe,
            self.btc_strength_thresholds['15min']
        )
        
        abs_value = abs(histogram_value)
        
        if abs_value < thresholds['weak']:
            return 'WEAK'
        elif abs_value < thresholds['moderate']:
            return 'MODERATE'
        elif abs_value < thresholds['strong']:
            return 'STRONG'
        else:
            return 'VERY_STRONG'
    
    def determine_trend(self, macd: pd.Series, signal: pd.Series) -> str:
        """
        Determine overall trend based on MACD positioning
        
        Args:
            macd: MACD line series
            signal: Signal line series
            
        Returns:
            Trend classification
        """
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        
        # Above zero and rising
        if current_macd > 0 and current_macd > current_signal:
            return 'STRONG_BULLISH'
        elif current_macd > 0 and current_macd <= current_signal:
            return 'WEAKENING_BULLISH'
        # Below zero and falling
        elif current_macd < 0 and current_macd < current_signal:
            return 'STRONG_BEARISH'
        elif current_macd < 0 and current_macd >= current_signal:
            return 'WEAKENING_BEARISH'
        else:
            return 'NEUTRAL'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method for MACD Signal building block
        
        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume, timestamp]
            **kwargs: Additional parameters:
                - divergence_lookback: Periods for divergence detection (default: 20)
        
        Returns:
            {
                'signal': str,  # Trade signal
                'confidence': float,  # 0-100 confidence score
                'metadata': dict,  # MACD values, crossovers, etc.
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
        
        # Need minimum data
        min_required = self.slow_period + self.signal_period
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {
                    'error': f'Need at least {min_required} periods, got {len(df)}',
                    'required_periods': min_required,
                    'provided_periods': len(df)
                },
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate MACD
        macd_line, signal_line, histogram = self.calculate_macd(df['close'])
        
        # Get current values
        current_macd = float(macd_line.iloc[-1])
        current_signal = float(signal_line.iloc[-1])
        current_histogram = float(histogram.iloc[-1])
        current_price = float(df['close'].iloc[-1])
        
        # Detect crossovers
        crossover = self.detect_crossover(macd_line, signal_line)
        zero_cross = self.detect_zero_line_cross(macd_line)
        
        # Detect divergences
        divergence_lookback = kwargs.get('divergence_lookback', 20)
        divergences = self.detect_divergence(df['close'], macd_line, divergence_lookback)
        
        # Classify strength
        strength = self.classify_strength(current_histogram)
        
        # Determine trend
        trend = self.determine_trend(macd_line, signal_line)
        
        # Calculate confidence based on data quality and signal strength
        data_quality = min(100, (len(df) / min_required) * 100)
        
        # Adjust confidence based on strength and crossovers
        confidence = data_quality * 0.7  # Base confidence
        
        if crossover in ['BULLISH_CROSS', 'BEARISH_CROSS']:
            confidence += 20  # Strong signal from crossover
        if zero_cross in ['BULLISH_ZERO_CROSS', 'BEARISH_ZERO_CROSS']:
            confidence += 10  # Additional confidence from zero cross
        if strength in ['STRONG', 'VERY_STRONG']:
            confidence += 10  # Strong momentum
        
        confidence = min(100, confidence)
        
        # Build confluence factors
        confluence_factors = []
        
        if crossover == 'BULLISH_CROSS':
            confluence_factors.append(f'MACD bullish crossover - {strength} signal')
        elif crossover == 'BEARISH_CROSS':
            confluence_factors.append(f'MACD bearish crossover - {strength} signal')
        
        if zero_cross == 'BULLISH_ZERO_CROSS':
            confluence_factors.append('MACD crossed above zero - trend confirmation')
        elif zero_cross == 'BEARISH_ZERO_CROSS':
            confluence_factors.append('MACD crossed below zero - downtrend confirmation')
        
        if divergences['bullish_divergence']:
            confluence_factors.append('Bullish divergence detected - potential reversal')
        if divergences['bearish_divergence']:
            confluence_factors.append('Bearish divergence detected - potential reversal')
        
        confluence_factors.append(f'Trend: {trend}')
        confluence_factors.append(f'Signal strength: {strength}')
        
        # Determine primary signal with PRIORITY ORDER (rare signals first)
        # Priority: Divergence > Zero Cross > Regular Cross > Neutral
        signal = 'NEUTRAL'
        
        # Highest priority: Divergences (rare, reversal signals)
        if divergences['bullish_divergence']:
            signal = 'BULLISH_DIVERGENCE'
            confidence = min(100, confidence + 5)  # Boost for rare signal
        elif divergences['bearish_divergence']:
            signal = 'BEARISH_DIVERGENCE'
            confidence = min(100, confidence + 5)  # Boost for rare signal
        
        # Next priority: Zero line crosses (major trend confirmation)
        elif zero_cross == 'BULLISH_ZERO_CROSS':
            signal = 'BULLISH_ZERO_CROSS'
        elif zero_cross == 'BEARISH_ZERO_CROSS':
            signal = 'BEARISH_ZERO_CROSS'
        
        # Standard priority: Regular crossovers
        elif crossover == 'BULLISH_CROSS':
            signal = 'BULLISH_CROSS'
        elif crossover == 'BEARISH_CROSS':
            signal = 'BEARISH_CROSS'
        
        # Else: NEUTRAL (no signal)
        
        # Prepare metadata
        metadata = {
            'macd_line': round(current_macd, 2),
            'signal_line': round(current_signal, 2),
            'histogram': round(current_histogram, 2),
            'current_price': round(current_price, 2),
            'crossover': crossover,
            'zero_cross': zero_cross,
            'divergences': divergences,
            'strength': strength,
            'trend': trend,
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'signal_period': self.signal_period,
            'recent_macd': macd_line.tail(10).tolist(),
            'recent_signal': signal_line.tail(10).tolist(),
            'recent_histogram': histogram.tail(10).tolist()
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
        required_cols = ['close']
        return all(col in df.columns for col in required_cols)


# Usage example
if __name__ == "__main__":
    # Test with sample Bitcoin data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    
    # Create sample data with trend
    np.random.seed(42)
    base_price = 45000
    trend = np.linspace(0, 2000, 100)  # Uptrend
    noise = np.random.randn(100).cumsum() * 50
    
    data = {
        'timestamp': dates,
        'close': base_price + trend + noise,
        'open': base_price + trend + noise,
        'high': base_price + trend + noise + 100,
        'low': base_price + trend + noise - 100,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    df = pd.DataFrame(data)
    
    # Test MACD block
    macd_block = MACDSignal(fast_period=12, slow_period=26, signal_period=9, timeframe='15min')
    result = macd_block.analyze(df)
    
    print("=" * 80)
    print("MACD SIGNAL BUILDING BLOCK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nMACD Values:")
    print(f"  MACD Line: {result['metadata']['macd_line']:.2f}")
    print(f"  Signal Line: {result['metadata']['signal_line']:.2f}")
    print(f"  Histogram: {result['metadata']['histogram']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"\nSignals:")
    print(f"  Crossover: {result['metadata']['crossover']}")
    print(f"  Zero Cross: {result['metadata']['zero_cross']}")
    print(f"  Bullish Divergence: {result['metadata']['divergences']['bullish_divergence']}")
    print(f"  Bearish Divergence: {result['metadata']['divergences']['bearish_divergence']}")
    print(f"\nAnalysis:")
    print(f"  Strength: {result['metadata']['strength']}")
    print(f"  Trend: {result['metadata']['trend']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
