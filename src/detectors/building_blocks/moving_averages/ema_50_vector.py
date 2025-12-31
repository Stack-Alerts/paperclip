"""
50 EMA Vector Break Building Block
Category: Moving Averages
Purpose: Trend identification and reversal detection using 50-period EMA
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA50Vector:
    """
    50 EMA Vector Break - Trend Following Indicator
    
    The 50 EMA is a widely-watched intermediate trend indicator.
    Tracks price position relative to 50 EMA and detects decisive breaks.
    
    Signals:
    - Vector Break Up: Price breaks above 50 EMA with momentum
    - Vector Break Down: Price breaks below 50 EMA with momentum
    - EMA Slope: Rising (bullish) or falling (bearish)
    - Distance: How far price is from 50 EMA
    
    Parameters:
        period: EMA period (default: 50)
        timeframe: Data timeframe
    
    Returns:
        Standardized dict with EMA position, slope, and break signals
    """
    
    def __init__(self, period: int = 50, timeframe: str = '15min', **kwargs):
        """Initialize 50 EMA Vector block"""
        self.period = period
        self.timeframe = timeframe
        
        # Bitcoin-specific distance thresholds (% from EMA)
        self.btc_distance_levels = {
            'very_close': 0.5,      # < 0.5% - touching EMA
            'close': 1.0,            # 0.5-1% - near EMA
            'moderate': 2.0,         # 1-2% - moderate distance
            'far': 3.0,              # 2-3% - far from EMA
            'very_far': 3.0          # > 3% - very far
        }
    
    def calculate_ema(self, close: pd.Series) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return close.ewm(span=self.period, adjust=False).mean()
    
    def calculate_slope(self, ema: pd.Series, lookback: int = 5) -> str:
        """
        Calculate EMA slope (trend direction)
        
        Args:
            ema: EMA series
            lookback: Periods to measure slope
            
        Returns:
            'RISING', 'FALLING', or 'FLAT'
        """
        if len(ema) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent_ema = ema.iloc[-lookback:]
        
        # Linear regression to determine slope
        x = np.arange(len(recent_ema))
        y = recent_ema.values
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize slope by price level
        avg_price = y.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        if slope_pct > 0.01:
            return 'RISING'
        elif slope_pct < -0.01:
            return 'FALLING'
        else:
            return 'FLAT'
    
    def detect_vector_break(self, close: pd.Series, ema: pd.Series, lookback: int = 3) -> str:
        """
        Detect vector break (decisive cross with momentum)
        
        A vector break is more significant than a simple cross:
        - Price must cross EMA
        - Price must stay on new side for multiple periods
        - Price should be moving with momentum
        
        Args:
            close: Close price series
            ema: EMA series
            lookback: Periods to confirm break
            
        Returns:
            'BULLISH_BREAK', 'BEARISH_BREAK', or 'NO_BREAK'
        """
        if len(close) < lookback + 1:
            return 'INSUFFICIENT_DATA'
        
        # Current position
        current_above = close.iloc[-1] > ema.iloc[-1]
        
        # Previous position (before the break)
        previous_above = close.iloc[-(lookback+1)] > ema.iloc[-(lookback+1)]
        
        # Check if position changed
        if current_above == previous_above:
            return 'NO_BREAK'
        
        # Verify consistency on new side
        recent_closes = close.iloc[-lookback:]
        recent_emas = ema.iloc[-lookback:]
        
        if current_above:
            # Bullish break: all recent closes above EMA
            stays_above = sum(recent_closes > recent_emas) >= lookback - 1
            if stays_above:
                return 'BULLISH_BREAK'
        else:
            # Bearish break: all recent closes below EMA
            stays_below = sum(recent_closes < recent_emas) >= lookback - 1
            if stays_below:
                return 'BEARISH_BREAK'
        
        return 'NO_BREAK'
    
    def classify_position(self, close_price: float, ema_value: float) -> str:
        """
        Classify price position relative to EMA
        
        Args:
            close_price: Current close price
            ema_value: Current EMA value
            
        Returns:
            Position classification
        """
        if close_price > ema_value:
            return 'ABOVE_EMA'
        elif close_price < ema_value:
            return 'BELOW_EMA'
        else:
            return 'AT_EMA'
    
    def calculate_distance(self, close_price: float, ema_value: float) -> float:
        """Calculate percentage distance from EMA"""
        return ((close_price - ema_value) / ema_value) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance level"""
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_levels['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_levels['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_levels['moderate']:
            return 'MODERATE'
        elif abs_dist < self.btc_distance_levels['far']:
            return 'FAR'
        else:
            return 'VERY_FAR'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        # Validate
        if 'close' not in df.columns:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        if len(df) < self.period + 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {self.period + 1} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate EMA
        ema = self.calculate_ema(df['close'])
        
        current_price = float(df['close'].iloc[-1])
        current_ema = float(ema.iloc[-1])
        
        # Calculate slope
        slope = self.calculate_slope(ema, lookback=5)
        
        # Detect vector break
        vector_break = self.detect_vector_break(df['close'], ema, lookback=3)
        
        # Classify position
        position = self.classify_position(current_price, current_ema)
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, current_ema)
        distance_class = self.classify_distance(distance_pct)
        
        # Calculate confidence
        data_quality = min(100, (len(df) / (self.period * 2)) * 100)
        confidence = data_quality * 0.7
        
        if vector_break in ['BULLISH_BREAK', 'BEARISH_BREAK']:
            confidence += 25  # Strong signal
        if slope in ['RISING', 'FALLING'] and position != 'AT_EMA':
            confidence += 10  # Confirmed trend
        
        confidence = min(100, confidence)
        
        # Build confluence
        confluence_factors = []
        
        if vector_break == 'BULLISH_BREAK':
            confluence_factors.append('Bullish vector break - price decisively above 50 EMA')
        elif vector_break == 'BEARISH_BREAK':
            confluence_factors.append('Bearish vector break - price decisively below 50 EMA')
        
        if slope == 'RISING':
            confluence_factors.append('50 EMA rising - uptrend in progress')
        elif slope == 'FALLING':
            confluence_factors.append('50 EMA falling - downtrend in progress')
        
        confluence_factors.append(f'Price {position.lower().replace("_", " ")} ({distance_pct:+.2f}%)')
        confluence_factors.append(f'Distance classification: {distance_class}')
        
        # Determine signal
        if vector_break == 'BULLISH_BREAK' or (position == 'ABOVE_EMA' and slope == 'RISING'):
            signal = 'BULLISH'
        elif vector_break == 'BEARISH_BREAK' or (position == 'BELOW_EMA' and slope == 'FALLING'):
            signal = 'BEARISH'
        else:
            signal = 'NEUTRAL'
        
        # Metadata
        metadata = {
            'ema_value': round(current_ema, 2),
            'current_price': round(current_price, 2),
            'position': position,
            'slope': slope,
            'vector_break': vector_break,
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'period': self.period,
            'recent_ema': ema.tail(10).tolist(),
            'recent_prices': df['close'].tail(10).tolist()
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    np.random.seed(42)
    base = 45000
    trend = np.linspace(0, 2000, 100)
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + trend + np.random.randn(100).cumsum() * 50,
        'open': base + trend,
        'high': base + trend + 100,
        'low': base + trend - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })
    
    ema50 = EMA50Vector()
    result = ema50.analyze(data)
    
    print("=" * 80)
    print("50 EMA VECTOR BREAK - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\n50 EMA Analysis:")
    print(f"  EMA Value: ${result['metadata']['ema_value']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Position: {result['metadata']['position']}")
    print(f"  Slope: {result['metadata']['slope']}")
    print(f"  Vector Break: {result['metadata']['vector_break']}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
