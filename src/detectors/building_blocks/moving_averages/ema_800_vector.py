"""
800 EMA Vector Break Building Block  
Category: Moving Averages
Purpose: Macro trend identification using 800-period EMA with PVSRA/TBD vector detection
"""
"""
Building Block Classification: SIGNAL BLOCK
Mode: EVENT-DRIVEN
Purpose: Price breaks through 800 EMA (macro), ultra selective

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
    name='ema_800_vector',
    category='MOVING_AVERAGES',
    class_name='EMA800VectorBreak',
    default_weight=12,
    valid_signals=['BULLISH_CLIMAX', 'BEARISH_CLIMAX', 'BULLISH_PSEUDO', 'BEARISH_PSEUDO', 'BULLISH', 'BEARISH', 'NEUTRAL', 'ERROR', 'INSUFFICIENT_DATA'],
    signal_tiers={
        # Granular signals (advanced users) - MACRO tier (highest scoring)
        'BULLISH_CLIMAX': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Bullish climax vector - crossed above 800 EMA with 200%+ volume (MACRO regime shift)'
        },
        'BEARISH_CLIMAX': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Bearish climax vector - crossed below 800 EMA with 200%+ volume (MACRO regime shift)'
        },
        'BULLISH_PSEUDO': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Bullish pseudo vector - crossed above 800 EMA with 150%+ volume (MACRO regime shift)'
        },
        'BEARISH_PSEUDO': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Bearish pseudo vector - crossed below 800 EMA with 150%+ volume (MACRO regime shift)'
        },
        
        # Simple signals (basic users)
        'BULLISH': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Bullish vector break - any volume (simple)'
        },
        'BEARISH': {
            'base_points': 25,
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
    description='EMA 800 Vector - Detects high-volume breaks through 800 EMA with PVSRA/TBD (MACRO regime shifts, maximum scoring)',
    tags=['moving_averages', 'ema', 'vector', 'pvsra', 'volume', 'macro', 'htf', 'signal_block']
)
class EMA800VectorBreak:
    """
    800 EMA Vector Break - Macro Trend Indicator with PVSRA/TBD Implementation
    
    The 800 EMA represents a very long-term macro trend indicator.
    On 15min charts, it identifies major market regime changes.
    
    Uses proper PVSRA/TBD vector candle detection:
    - Tier 2 (Climax): ≥200% volume from previous 10 candles
    - Tier 1 (Pseudo): ≥150% volume from previous 10 candles
    
    Signals:
    - Vector Break Up: Price breaks above 800 EMA with PVSRA vector
    - Vector Break Down: Price breaks below 800 EMA with PVSRA vector
    - EMA Slope: Rising (bullish) or falling (bearish)
    
    Returns:
        Standardized dict with EMA position, slope, and break signals
    """
    
    def __init__(self, 
                 period: int = 700,  # OPTIMIZED: 700 outperforms 800 (faster response)
                 timeframe: str = '15min',
                 slope_rising_threshold: float = 0.008,  # OPTIMIZED: Institutional tuning
                 slope_falling_threshold: float = -0.008,  # OPTIMIZED: Institutional tuning
                 volume_threshold: float = 1.5,
                 slope_lookback: int = 7,  # OPTIMIZED: Institutional tuning
                 vector_candle_multiplier: float = 1.5,
                 **kwargs):
        """
        Initialize 800 EMA Vector block with tunable parameters
        
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
        
        # Event tracking state
        self.prev_signal = 'NEUTRAL'
        self.bars_in_state = 0
        
        # Bitcoin-specific distance thresholds (% from EMA)
        self.btc_distance_levels = {
            'very_close': 0.5,
            'close': 1.0,
            'moderate': 2.0,
            'far': 3.0,
            'very_far': 3.0
        }
    
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
            
            # PVSRA Tier 2: Climax Vector (200%+)
            if current_volume >= (vol_ma_10 * 2.0):
                is_vector_candle = True
                vector_tier = "CLIMAX_GREEN" if is_bullish_candle else "CLIMAX_RED"
                
            # PVSRA Tier 1: Pseudo Vector (150%+)
            elif current_volume >= (vol_ma_10 * 1.5):
                is_vector_candle = True
                vector_tier = "PSEUDO_BLUE" if is_bullish_candle else "PSEUDO_PURPLE"
        
        signal = 'NEUTRAL'
        confidence = 70
        
        # Build confluence
        confluence_factors = []
        
        # EVENT TRACKING: Detect if this is a NEW event
        is_new_event = False
        
        # PVSRA/TBD VECTOR CROSS DETECTION
        # Emit GRANULAR signals for advanced users (MACRO significance - all 25 pts)
        if crossed_above and is_vector_candle:
            # Bullish vector break
            
            # CLIMAX vectors (200%+): Always take
            if "CLIMAX" in vector_tier:
                signal = 'BULLISH_CLIMAX'  # GRANULAR (MACRO)
                confidence = 95
                is_new_event = True  # Fresh vector cross
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (200%+ volume)')
                
                if slope in ['RISING', 'STRONG_RISING']:
                    confidence += 5
                    confluence_factors.append('✅ 800 EMA slope confirming uptrend')
                    
                confluence_factors.append('📈 BULLISH CLIMAX: Climax vector crossed above 800 EMA - MACRO regime shift')
            
            # PSEUDO vectors (150%+): Require slope confirmation
            elif "PSEUDO" in vector_tier:
                if slope in ['RISING', 'STRONG_RISING']:
                    signal = 'BULLISH_PSEUDO'  # GRANULAR (MACRO)
                    confidence = 90
                    is_new_event = True  # Fresh vector cross
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (150%+ volume)')
                    confluence_factors.append('✅ 800 EMA slope confirming uptrend - CONFIRMED')
                    confluence_factors.append('📈 BULLISH PSEUDO: Confirmed pseudo vector crossed above 800 EMA - MACRO regime shift')
                
        elif crossed_below and is_vector_candle:
            # Bearish vector break
            
            # CLIMAX vectors (200%+): Always take
            if "CLIMAX" in vector_tier:
                signal = 'BEARISH_CLIMAX'  # GRANULAR (MACRO)
                confidence = 95
                is_new_event = True  # Fresh vector cross
                confluence_factors.append(f'⚡ CLIMAX VECTOR: {vector_tier} (200%+ volume)')
                
                if slope in ['FALLING', 'STRONG_FALLING']:
                    confidence += 5
                    confluence_factors.append('✅ 800 EMA slope confirming downtrend')
                    
                confluence_factors.append('📉 BEARISH CLIMAX: Climax vector crossed below 800 EMA - MACRO regime shift')
            
            # PSEUDO vectors (150%+): Require slope confirmation
            elif "PSEUDO" in vector_tier:
                if slope in ['FALLING', 'STRONG_FALLING']:
                    signal = 'BEARISH_PSEUDO'  # GRANULAR (MACRO)
                    confidence = 90
                    is_new_event = True  # Fresh vector cross
                    confluence_factors.append(f'📊 PSEUDO VECTOR: {vector_tier} (150%+ volume)')
                    confluence_factors.append('✅ 800 EMA slope confirming downtrend - CONFIRMED')
                    confluence_factors.append('📉 BEARISH PSEUDO: Confirmed pseudo vector crossed below 800 EMA - MACRO regime shift')
        
        # Update event tracking state
        if signal != self.prev_signal:
            is_new_event = True
            self.bars_in_state = 1
        else:
            self.bars_in_state += 1
        
        self.prev_signal = signal
        
        # Status information  
        if signal == 'NEUTRAL':
            if current_position == 'ABOVE_EMA':
                confluence_factors.append('Price above 800 EMA - macro bull market')
            elif current_position == 'BELOW_EMA':
                confluence_factors.append('Price below 800 EMA - macro bear market')
            
            confluence_factors.append(f'Distance from 800 EMA: {distance_pct:+.2f}% ({distance_class})')
            confluence_factors.append('No cross event - holding position')
        
        # Add slope context
        if slope == 'RISING':
            confluence_factors.append('800 EMA trending up (macro bull cycle)')
        elif slope == 'FALLING':
            confluence_factors.append('800 EMA trending down (macro bear cycle)')
        elif slope == 'FLAT':
            confluence_factors.append('800 EMA flat - accumulation/distribution phase')
        
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
            'is_new_event': is_new_event,
            'bars_in_state': self.bars_in_state
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
