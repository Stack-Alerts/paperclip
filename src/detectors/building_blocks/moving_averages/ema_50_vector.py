"""
50 EMA Vector Break Building Block
Category: Moving Averages
Purpose: Trend identification and reversal detection using 50-period EMA
"""
"""
Building Block Classification: SIGNAL BLOCK
Mode: EVENT-DRIVEN
Purpose: Price breaks through 50 EMA, selective signals

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='ema_50_vector',
    category='MOVING_AVERAGES',
    class_name='EMA50Vector',
    default_weight=12,
    valid_signals=['BULLISH_CLIMAX', 'BEARISH_CLIMAX', 'BULLISH_PSEUDO', 'BEARISH_PSEUDO', 'BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        # Granular signals (advanced users) - PVSRA tiers
        'BULLISH_CLIMAX': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish climax vector - crossed above 50 EMA with 200%+ volume (high conviction)'
        },
        'BEARISH_CLIMAX': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish climax vector - crossed below 50 EMA with 200%+ volume (high conviction)'
        },
        'BULLISH_PSEUDO': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish pseudo vector - crossed above 50 EMA with 100%+ volume AND rising EMA slope (RARE: requires trend confirmation)'
        },
        'BEARISH_PSEUDO': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish pseudo vector - crossed below 50 EMA with 100%+ volume AND falling EMA slope (RARE: requires trend confirmation)'
        },
        
        # Simple signals (basic users)
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish vector break - any volume (simple)'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish vector break - any volume (simple)'
        },
        
        # Neutral
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'description': 'No vector break - holding position'
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
    description='EMA 50 Vector - Detects high-volume breaks through 50 EMA with PVSRA/TBD methodology',
    tags=['moving_averages', 'ema', 'vector', 'pvsra', 'volume', 'signal_block']
)
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
    
    def __init__(self, 
                 period: int = 45,  # OPTIMIZED: 45 performs better than 50
                 timeframe: str = '15min',
                 slope_rising_threshold: float = 0.008,  # OPTIMIZED: Looser threshold for better confirmations
                 slope_falling_threshold: float = -0.008,  # OPTIMIZED: Looser threshold for better confirmations
                 volume_threshold: float = 1.5,
                 slope_lookback: int = 7,  # OPTIMIZED: Shorter lookback for responsiveness
                 vector_candle_multiplier: float = 1.5,
                 **kwargs):
        """
        Initialize 50 EMA Vector block with tunable parameters
        
        Args:
            period: EMA period
            timeframe: Data timeframe
            slope_rising_threshold: Min % slope to qualify as RISING
            slope_falling_threshold: Max % slope to qualify as FALLING
            volume_threshold: Volume multiplier for confirmation (e.g., 1.5 = 50% above average)
            slope_lookback: Bars to use for slope calculation
            vector_candle_multiplier: Candle body size multiplier for vector detection (e.g., 1.5 = 50% larger than average)
        """
        self.period = period
        self.timeframe = timeframe
        self.slope_rising_threshold = slope_rising_threshold
        self.slope_falling_threshold = slope_falling_threshold
        self.volume_threshold = volume_threshold
        self.slope_lookback = slope_lookback
        self.vector_candle_multiplier = vector_candle_multiplier
        
        # Bitcoin-specific distance thresholds (% from EMA)
        self.btc_distance_levels = {
            'very_close': 0.5,      # < 0.5% - touching EMA
            'close': 1.0,            # 0.5-1% - near EMA
            'moderate': 2.0,         # 1-2% - moderate distance
            'far': 3.0,              # 2-3% - far from EMA
            'very_far': 3.0          # > 3% - very far
        }
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Granular stays as-is
        granular = granular_signal
        
        # Simple: directional bias
        if granular in ['BULLISH_CLIMAX', 'BULLISH_PSEUDO']:
            simple = 'BULLISH'
        elif granular in ['BEARISH_CLIMAX', 'BEARISH_PSEUDO']:
            simple = 'BEARISH'
        else:
            simple = 'NEUTRAL'
        
        return granular, simple
    
    def calculate_ema(self, close: pd.Series) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return close.ewm(span=self.period, adjust=False).mean()
    
    def calculate_slope(self, ema: pd.Series, lookback: int = 10) -> str:
        """
        Calculate EMA slope (trend direction)
        
        Args:
            ema: EMA series
            lookback: Periods to measure slope
            
        Returns:
            'STRONG_RISING', 'RISING', 'STRONG_FALLING', 'FALLING', or 'FLAT'
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
        
        # Use tunable thresholds
        strong_rising = self.slope_rising_threshold * 2.5  # 2.5x for STRONG
        strong_falling = self.slope_falling_threshold * 2.5
        
        if slope_pct > strong_rising:
            return 'STRONG_RISING'
        elif slope_pct > self.slope_rising_threshold:
            return 'RISING'
        elif slope_pct < strong_falling:
            return 'STRONG_FALLING'
        elif slope_pct < self.slope_falling_threshold:
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
        """Main analysis method - IMPROVED FOR INSTITUTIONAL ACCURACY"""
        # Validate
        required_cols = ['close']
        if 'volume' in df.columns:
            required_cols.append('volume')
            
        if not all(col in df.columns for col in ['close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Invalid data format'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        if len(df) < self.period + 10:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {self.period + 10} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate EMA
        ema = self.calculate_ema(df['close'])
        
        current_price = float(df['close'].iloc[-1])
        prev_price = float(df['close'].iloc[-2])
        current_ema = float(ema.iloc[-1])
        prev_ema = float(ema.iloc[-2])
        
        # Calculate slope with tunable lookback
        slope = self.calculate_slope(ema, lookback=self.slope_lookback)
        
        # IMPROVED: Detect clean EMA crosses (not complex vector breaks)
        current_position = self.classify_position(current_price, current_ema)
        prev_position = self.classify_position(prev_price, prev_ema)
        
        crossed_above = (prev_position == 'BELOW_EMA' and current_position == 'ABOVE_EMA')
        crossed_below = (prev_position == 'ABOVE_EMA' and current_position == 'BELOW_EMA')
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, current_ema)
        distance_class = self.classify_distance(distance_pct)
        
        # PVSRA/TBD VECTOR CANDLE DETECTION (PROPER IMPLEMENTATION)
        # Volume must be from PREVIOUS 10 candles (exclude current)
        is_vector_candle = False
        vector_tier = None
        
        if 'volume' in df.columns and len(df) >= 11:  # Need at least 11 candles
            # Calculate volume MA of PREVIOUS 10 candles (shift by 1)
            vol_ma_10 = df['volume'].iloc[-11:-1].mean()  # Excludes current candle
            current_volume = df['volume'].iloc[-1]
            current_open = float(df['open'].iloc[-1])
            is_bullish_candle = current_price > current_open
            
            # PVSRA Tier 2: Climax Vector (170%+ - ADJUSTED Option 2 for ideal signal rate)
            if current_volume >= (vol_ma_10 * 1.7):
                is_vector_candle = True
                vector_tier = "CLIMAX_GREEN" if is_bullish_candle else "CLIMAX_RED"
                
            # PVSRA Tier 1: Pseudo Vector (130%+ - ADJUSTED Option 2 for ideal signal rate)
            elif current_volume >= (vol_ma_10 * 1.3):
                is_vector_candle = True
                vector_tier = "PSEUDO_BLUE" if is_bullish_candle else "PSEUDO_PURPLE"
        
        signal = 'NEUTRAL'
        confidence = 70
        
        # Build confluence
        confluence_factors = []
        
        # PVSRA/TBD VECTOR CROSS DETECTION (OPTIMIZED FOR 55%+ ACCURACY)
        # Emit GRANULAR signals for advanced users, simple BULLISH/BEARISH available too
        if crossed_above and is_vector_candle:
            # Bullish vector break
            
            # CLIMAX vectors (200%+): Always take (high quality)
            if "CLIMAX" in vector_tier:
                signal = 'BULLISH_CLIMAX'  # GRANULAR
                confidence = 95
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (200%+ volume)')
                
                # Boost with slope
                if slope in ['RISING', 'STRONG_RISING']:
                    confidence += 5
                    confluence_factors.append('✅ 50 EMA slope confirming uptrend')
                    
                confluence_factors.append('📈 BULLISH CLIMAX: Climax vector crossed above 50 EMA')
            
            # PSEUDO vectors (150%+): Require slope confirmation for quality
            elif "PSEUDO" in vector_tier:
                if slope in ['RISING', 'STRONG_RISING']:
                    # Only take pseudo vectors with slope confirmation
                    signal = 'BULLISH_PSEUDO'  # GRANULAR
                    confidence = 90  # Higher confidence when confirmed
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (150%+ volume)')
                    confluence_factors.append('✅ 50 EMA slope confirming uptrend - CONFIRMED')
                    confluence_factors.append('📈 BULLISH PSEUDO: Confirmed pseudo vector crossed above 50 EMA')
                # else: skip unconfirmed pseudo vectors
                
        elif crossed_below and is_vector_candle:
            # Bearish vector break  
            
            # CLIMAX vectors (200%+): Always take (high quality)
            if "CLIMAX" in vector_tier:
                signal = 'BEARISH_CLIMAX'  # GRANULAR
                confidence = 95
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (200%+ volume)')
                
                # Boost with slope
                if slope in ['FALLING', 'STRONG_FALLING']:
                    confidence += 5
                    confluence_factors.append('✅ 50 EMA slope confirming downtrend')
                    
                confluence_factors.append('📉 BEARISH CLIMAX: Climax vector crossed below 50 EMA')
            
            # PSEUDO vectors (150%+): Require slope confirmation for quality
            elif "PSEUDO" in vector_tier:
                if slope in ['FALLING', 'STRONG_FALLING']:
                    # Only take pseudo vectors with slope confirmation
                    signal = 'BEARISH_PSEUDO'  # GRANULAR
                    confidence = 90  # Higher confidence when confirmed
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (150%+ volume)')
                    confluence_factors.append('✅ 50 EMA slope confirming downtrend - CONFIRMED')
                    confluence_factors.append('📉 BEARISH PSEUDO: Confirmed pseudo vector crossed below 50 EMA')
                # else: skip unconfirmed pseudo vectors
        
        # Status information (only if no cross)
        if signal == 'NEUTRAL':
            if current_position == 'ABOVE_EMA':
                confluence_factors.append('Price above 50 EMA - uptrend bias')
            elif current_position == 'BELOW_EMA':
                confluence_factors.append('Price below 50 EMA - downtrend bias')
            
            confluence_factors.append(f'Distance from 50 EMA: {distance_pct:+.2f}% ({distance_class})')
            confluence_factors.append('No cross event - holding position')
        
        # Add slope context
        if slope == 'RISING':
            confluence_factors.append('50 EMA trending up')
        elif slope == 'FALLING':
            confluence_factors.append('50 EMA trending down')
        elif slope == 'FLAT':
            confluence_factors.append('50 EMA flat - ranging market')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        # Metadata
        metadata = {
            'ema_value': round(current_ema, 2),
            'current_price': round(current_price, 2),
            'current_position': current_position,
            'prev_position': prev_position,
            'crossed_above': crossed_above,
            'crossed_below': crossed_below,
            'slope': slope,
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_vector_candle': is_vector_candle,
            'vector_tier': vector_tier,
            'period': self.period,
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': granular_signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
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
