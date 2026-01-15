"""
255 EMA Vector Break Building Block  
Category: Moving Averages
Purpose: Long-term trend identification using 255-period EMA with PVSRA/TBD vector detection
"""
"""
Building Block Classification: SIGNAL BLOCK
Mode: EVENT-DRIVEN
Purpose: Price breaks through 255 EMA (HTF), very selective

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
    name='ema_255_vector',
    category='MOVING_AVERAGES',
    class_name='EMA255VectorBreak',
    default_weight=12,
    valid_signals=['BULLISH_CLIMAX', 'BEARISH_CLIMAX', 'BULLISH_PSEUDO', 'BEARISH_PSEUDO', 'BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        # Granular signals (advanced users) - PVSRA tiers for HTF
        'BULLISH_CLIMAX': {
            'base_points': 24,
            'formula': 'scaled',
            'description': 'Bullish climax vector - crossed above 255 EMA with 140%+ volume (major HTF trend shift)'
        },
        'BEARISH_CLIMAX': {
            'base_points': 24,
            'formula': 'scaled',
            'description': 'Bearish climax vector - crossed below 255 EMA with 140%+ volume (major HTF trend shift)'
        },
        'BULLISH_PSEUDO': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish pseudo vector - crossed above 255 EMA with 100%+ volume AND rising EMA slope (RARE: requires trend confirmation)'
        },
        'BEARISH_PSEUDO': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish pseudo vector - crossed below 255 EMA with 100%+ volume AND falling EMA slope (RARE: requires trend confirmation)'
        },
        
        # Simple signals (basic users)
        'BULLISH': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bullish vector break - any volume (simple)'
        },
        'BEARISH': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish vector break - any volume (simple)'
        },
        
        # Neutral
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'No vector break - holding position'
        },
        
        # Status
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error occurred'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Not enough data for analysis'
        }
    },
    description='EMA 255 Vector - Detects high-volume breaks through 255 EMA with PVSRA/TBD (major trend shifts, higher scoring)',
    tags=['moving_averages', 'ema', 'vector', 'pvsra', 'volume', 'htf', 'signal_block']
)
class EMA255VectorBreak:
    """
    255 EMA Vector Break - Long-Term Trend Indicator with PVSRA/TBD Implementation
    
    The 255 EMA represents a very long-term trend indicator.
    On 15min charts, it provides strong support/resistance for major trends.
    
    Uses proper PVSRA/TBD vector candle detection (OPTIMIZED AGGRESSIVE for strategic fit):
    - Tier 2 (Climax): ≥140% volume from previous 10 candles (OPTIMIZED AGGRESSIVE)
    - Tier 1 (Pseudo): ≥100% volume from previous 10 candles (OPTIMIZED AGGRESSIVE)
    
    Signals:
    - Vector Break Up: Price breaks above 255 EMA with PVSRA vector
    - Vector Break Down: Price breaks below 255 EMA with PVSRA vector
    - EMA Slope: Rising (bullish) or falling (bearish)
    
    Returns:
        Standardized dict with EMA position, slope, and break signals
    """
    
    def __init__(self, 
                 period: int = 230,  # OPTIMIZED: 230 outperforms 255 (faster response)
                 timeframe: str = '15min',
                 slope_rising_threshold: float = 0.008,  # OPTIMIZED: Institutional tuning
                 slope_falling_threshold: float = -0.008,  # OPTIMIZED: Institutional tuning
                 volume_threshold: float = 1.5,
                 slope_lookback: int = 7,  # OPTIMIZED: Institutional tuning
                 vector_candle_multiplier: float = 1.5,
                 **kwargs):
        """
        Initialize 255 EMA Vector block with tunable parameters
        
        Args:
            period: EMA period
            timeframe: Data timeframe
            slope_rising_threshold: Min % slope to qualify as RISING
            slope_falling_threshold: Max % slope to qualify as FALLING  
            volume_threshold: Not used (PVSRA built-in), kept for compatibility
            slope_lookback: Bars to use for slope calculation
            vector_candle_multiplier: Not used (PVSRA built-in), kept for compatibility
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
            'very_close': 0.5,
            'close': 1.0,
            'moderate': 2.0,
            'far': 3.0,
            'very_far': 3.0
        }
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
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
        
        Returns:
            'STRONG_RISING', 'RISING', 'STRONG_FALLING', 'FALLING', or 'FLAT'
        """
        if len(ema) < lookback:
            return 'INSUFFICIENT_DATA'
        
        recent_ema = ema.iloc[-lookback:]
        
        # Linear regression to determine slope
        x = np.arange(len(recent_ema))
        y = recent_ema.values
        
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize slope by price level
        avg_price = y.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        # Use tunable thresholds
        strong_rising = self.slope_rising_threshold * 2.5
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
    
    def classify_position(self, close_price: float, ema_value: float) -> str:
        """Classify price position relative to EMA"""
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
        """Main analysis method - PVSRA/TBD IMPLEMENTATION"""
        # Validate
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
            granular_signal, simple_signal = self._determine_dual_signals('INSUFFICIENT_DATA')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'error': f'Need {self.period + 10} periods, got {len(df)}'
                },
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
        
        # Calculate slope
        slope = self.calculate_slope(ema, lookback=self.slope_lookback)
        
        # Detect EMA crosses
        current_position = self.classify_position(current_price, current_ema)
        prev_position = self.classify_position(prev_price, prev_ema)
        
        crossed_above = (prev_position == 'BELOW_EMA' and current_position == 'ABOVE_EMA')
        crossed_below = (prev_position == 'ABOVE_EMA' and current_position == 'BELOW_EMA')
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, current_ema)
        distance_class = self.classify_distance(distance_pct)
        
        # PVSRA/TBD VECTOR CANDLE DETECTION
        is_vector_candle = False
        vector_tier = None
        
        if 'volume' in df.columns and len(df) >= 11:
            # Volume from PREVIOUS 10 candles (exclude current)
            vol_ma_10 = df['volume'].iloc[-11:-1].mean()
            current_volume = df['volume'].iloc[-1]
            current_open = float(df['open'].iloc[-1])
            is_bullish_candle = current_price > current_open
            
            # PVSRA Tier 2: Climax Vector (140%+ - OPTIMIZED AGGRESSIVE for strategic fit)
            if current_volume >= (vol_ma_10 * 1.4):
                is_vector_candle = True
                vector_tier = "CLIMAX_GREEN" if is_bullish_candle else "CLIMAX_RED"
                
            # PVSRA Tier 1: Pseudo Vector (100%+ = volume MA - OPTIMIZED AGGRESSIVE for strategic fit)
            elif current_volume >= (vol_ma_10 * 1.0):
                is_vector_candle = True
                vector_tier = "PSEUDO_BLUE" if is_bullish_candle else "PSEUDO_PURPLE"
        
        signal = 'NEUTRAL'
        confidence = 70
        
        # Build confluence
        confluence_factors = []
        
        # PVSRA/TBD VECTOR CROSS DETECTION
        # Emit GRANULAR signals for advanced users (HTF significance)
        if crossed_above and is_vector_candle:
            # Bullish vector break
            
            # CLIMAX vectors (140%+): Always take
            if "CLIMAX" in vector_tier:
                signal = 'BULLISH_CLIMAX'  # GRANULAR (HTF)
                confidence = 95
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (140%+ volume)')
                
                if slope in ['RISING', 'STRONG_RISING']:
                    confidence += 5
                    confluence_factors.append('✅ 255 EMA slope confirming uptrend')
                    
                confluence_factors.append('📈 BULLISH CLIMAX: Climax vector crossed above 255 EMA - MAJOR HTF trend shift')
            
            # PSEUDO vectors (100%+): Require slope NOT opposing (more lenient)
            elif "PSEUDO" in vector_tier:
                # Accept if slope is not falling (RISING, STRONG_RISING, or FLAT)
                if slope not in ['FALLING', 'STRONG_FALLING']:
                    signal = 'BULLISH_PSEUDO'  # GRANULAR (HTF)
                    confidence = 85 if slope in ['RISING', 'STRONG_RISING'] else 80
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (100%+ volume)')
                    if slope in ['RISING', 'STRONG_RISING']:
                        confluence_factors.append('✅ 255 EMA slope confirming uptrend')
                    else:
                        confluence_factors.append('⚠️  255 EMA slope neutral - moderate conviction')
                    confluence_factors.append('📈 BULLISH PSEUDO: Pseudo vector crossed above 255 EMA - HTF trend shift')
                
        elif crossed_below and is_vector_candle:
            # Bearish vector break
            
            # CLIMAX vectors (140%+): Always take
            if "CLIMAX" in vector_tier:
                signal = 'BEARISH_CLIMAX'  # GRANULAR (HTF)
                confidence = 95
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (140%+ volume)')
                
                if slope in ['FALLING', 'STRONG_FALLING']:
                    confidence += 5
                    confluence_factors.append('✅ 255 EMA slope confirming downtrend')
                    
                confluence_factors.append('📉 BEARISH CLIMAX: Climax vector crossed below 255 EMA - MAJOR HTF trend shift')
            
            # PSEUDO vectors (100%+): Require slope NOT opposing (more lenient)
            elif "PSEUDO" in vector_tier:
                # Accept if slope is not rising (FALLING, STRONG_FALLING, or FLAT)
                if slope not in ['RISING', 'STRONG_RISING']:
                    signal = 'BEARISH_PSEUDO'  # GRANULAR (HTF)
                    confidence = 85 if slope in ['FALLING', 'STRONG_FALLING'] else 80
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (100%+ volume)')
                    if slope in ['FALLING', 'STRONG_FALLING']:
                        confluence_factors.append('✅ 255 EMA slope confirming downtrend')
                    else:
                        confluence_factors.append('⚠️  255 EMA slope neutral - moderate conviction')
                    confluence_factors.append('📉 BEARISH PSEUDO: Pseudo vector crossed below 255 EMA - HTF trend shift')
        
        # Status information  
        if signal == 'NEUTRAL':
            if current_position == 'ABOVE_EMA':
                confluence_factors.append('Price above 255 EMA - long-term uptrend')
            elif current_position == 'BELOW_EMA':
                confluence_factors.append('Price below 255 EMA - long-term downtrend')
            
            confluence_factors.append(f'Distance from 255 EMA: {distance_pct:+.2f}% ({distance_class})')
            confluence_factors.append('No cross event - holding position')
        
        # Add slope context
        if slope == 'RISING':
            confluence_factors.append('255 EMA trending up (long-term bull trend)')
        elif slope == 'FALLING':
            confluence_factors.append('255 EMA trending down (long-term bear trend)')
        elif slope == 'FLAT':
            confluence_factors.append('255 EMA flat - consolidation phase')
        
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
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
