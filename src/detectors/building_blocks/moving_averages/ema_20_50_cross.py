"""
20/50 EMA Cross Building Block
Category: Moving Averages
Purpose: Medium-term trend identification using 20 and 50 EMA crossovers with volume confirmation
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA2050Cross:
    """
    20/50 EMA Cross - Medium-Term Trend Indicator with Volume Confirmation
    
    Classic moving average crossover system enhanced with volume analysis:
    - Golden Cross: Fast EMA crosses above Slow EMA (bullish)
    - Death Cross: Fast EMA crosses below Slow EMA (bearish)
    - Volume confirmation: Higher volume on cross increases confidence
    - EMA separation: Distance between EMAs shows trend strength
    
    Parameters:
        fast_period: Fast EMA period (default: 20)
        slow_period: Slow EMA period (default: 50) 
        timeframe: Data timeframe
        volume_confirmation: Require above-average volume for cross (default: True)
        volume_threshold: Volume multiplier for confirmation (default: 1.2)
    
    Returns:
        Standardized dict with cross signals, separation, and trend strength
    """
    
    def __init__(self, 
                 fast_period: int = 15,  # OPTIMIZED: 15 outperforms 20
                 slow_period: int = 45,  # OPTIMIZED: 45 outperforms 50 (matches vector findings!)
                 timeframe: str = '15min',
                 volume_confirmation: bool = True,
                 volume_threshold: float = 1.1,  # OPTIMIZED: Looser threshold for more signals
                 cross_lookback: int = 2,  # OPTIMIZED: Faster confirmation
                 **kwargs):
        """Initialize 20/50 EMA Cross block with tunable parameters"""
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.timeframe = timeframe
        self.volume_confirmation = volume_confirmation
        self.volume_threshold = volume_threshold
        self.cross_lookback = cross_lookback
        
        # Bitcoin-specific separation thresholds (% between EMAs)
        self.btc_separation_levels = {
            'tight': 0.3,
            'normal': 1.0,
            'wide': 2.0,
            'very_wide': 2.0
        }
    
    def calculate_ema(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return close.ewm(span=period, adjust=False).mean()
    
    def detect_cross(self, fast_ema: pd.Series, slow_ema: pd.Series, lookback: int = 3) -> str:
        """
        Detect EMA crossovers with confirmation
        
        Returns:
            'GOLDEN_CROSS', 'DEATH_CROSS', or 'NO_CROSS'
        """
        if len(fast_ema) < lookback + 1:
            return 'INSUFFICIENT_DATA'
        
        # Current position
        current_above = fast_ema.iloc[-1] > slow_ema.iloc[-1]
        
        # Previous position (before the cross)
        previous_above = fast_ema.iloc[-(lookback+1)] > slow_ema.iloc[-(lookback+1)]
        
        # Check if crossed
        if current_above == previous_above:
            return 'NO_CROSS'
        
        # Verify cross is sustained (all recent bars on new side)
        recent_fast = fast_ema.iloc[-lookback:]
        recent_slow = slow_ema.iloc[-lookback:]
        
        if current_above:
            # Golden cross: fast crossed above slow
            stays_above = sum(recent_fast > recent_slow) >= lookback - 1
            if stays_above:
                return 'GOLDEN_CROSS'
        else:
            # Death cross: fast crossed below slow
            stays_below = sum(recent_fast < recent_slow) >= lookback - 1
            if stays_below:
                return 'DEATH_CROSS'
        
        return 'NO_CROSS'
    
    def check_volume_confirmation(self, df: pd.DataFrame, volume_period: int = 20) -> bool:
        """Check if recent volume is above average"""
        if 'volume' not in df.columns or len(df) < volume_period + 1:
            return True  # Don't penalize if volume data unavailable
        
        avg_volume = df['volume'].iloc[-(volume_period+1):-1].mean()
        current_volume = df['volume'].iloc[-1]
        
        return current_volume >= (avg_volume * self.volume_threshold)
    
    def calculate_separation(self, fast_ema: float, slow_ema: float) -> float:
        """Calculate percentage separation between EMAs"""
        return ((fast_ema - slow_ema) / slow_ema) * 100
    
    def classify_separation(self, separation_pct: float) -> str:
        """Classify separation level"""
        abs_sep = abs(separation_pct)
        
        if abs_sep < self.btc_separation_levels['tight']:
            return 'TIGHT'
        elif abs_sep < self.btc_separation_levels['normal']:
            return 'NORMAL'
        elif abs_sep < self.btc_separation_levels['wide']:
            return 'WIDE'
        else:
            return 'VERY_WIDE'
    
    def determine_trend(self, fast_ema: float, slow_ema: float, price: float) -> str:
        """Determine overall trend based on EMA alignment"""
        if price > fast_ema > slow_ema:
            return 'STRONG_UPTREND'
        elif price > fast_ema and fast_ema < slow_ema:
            return 'EARLY_UPTREND'
        elif price < fast_ema < slow_ema:
            return 'STRONG_DOWNTREND'
        elif price < fast_ema and fast_ema > slow_ema:
            return 'EARLY_DOWNTREND'
        else:
            return 'NEUTRAL'
    
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
        min_required = self.slow_period + 10
        if len(df) < min_required:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need {min_required} periods, got {len(df)}'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate EMAs
        fast_ema = self.calculate_ema(df['close'], self.fast_period)
        slow_ema = self.calculate_ema(df['close'], self.slow_period)
        
        current_price = float(df['close'].iloc[-1])
        current_fast = float(fast_ema.iloc[-1])
        current_slow = float(slow_ema.iloc[-1])
        
        # Detect cross
        cross = self.detect_cross(fast_ema, slow_ema, lookback=self.cross_lookback)
        
        # Check volume confirmation
        has_volume_conf = self.check_volume_confirmation(df)
        
        # Calculate separation
        separation_pct = self.calculate_separation(current_fast, current_slow)
        separation_class = self.classify_separation(separation_pct)
        
        # Determine trend
        trend = self.determine_trend(current_fast, current_slow, current_price)
        
        # Determine signal and confidence
        signal = 'NEUTRAL'
        confidence = 70
        confluence_factors = []
        
        # Cross signals
        if cross == 'GOLDEN_CROSS':
            signal = 'BULLISH'
            confidence = 85
            confluence_factors.append('✅ GOLDEN CROSS - Fast EMA crossed above Slow EMA (bullish)')
            
            if has_volume_conf:
                confidence += 10
                confluence_factors.append('📊 Volume confirmation - above average volume on cross')
            elif self.volume_confirmation:
                confidence -= 10
                confluence_factors.append('⚠️ Low volume - cross lacks volume confirmation')
                
        elif cross == 'DEATH_CROSS':
            signal = 'BEARISH'
            confidence = 85
            confluence_factors.append('❌ DEATH CROSS - Fast EMA crossed below Slow EMA (bearish)')
            
            if has_volume_conf:
                confidence += 10
                confluence_factors.append('📊 Volume confirmation - above average volume on cross')
            elif self.volume_confirmation:
                confidence -= 10
                confluence_factors.append('⚠️ Low volume - cross lacks volume confirmation')
        
        # Trend-based signals (when no cross)
        elif trend == 'STRONG_UPTREND':
            signal = 'BULLISH'
            confidence = 75
            confluence_factors.append('📈 STRONG UPTREND - Price > Fast EMA > Slow EMA (perfect alignment)')
        elif trend == 'STRONG_DOWNTREND':
            signal = 'BEARISH'
            confidence = 75
            confluence_factors.append('📉 STRONG DOWNTREND - Price < Fast EMA < Slow EMA (perfect alignment)')
        elif trend == 'EARLY_UPTREND':
            signal = 'BULLISH'
            confidence = 65
            confluence_factors.append('📈 EARLY UPTREND - Price above Fast EMA, awaiting Slow EMA cross')
        elif trend == 'EARLY_DOWNTREND':
            signal = 'BEARISH'
            confidence = 65
            confluence_factors.append('📉 EARLY DOWNTREND - Price below Fast EMA, awaiting Slow EMA cross')
        
        # Separation boost
        if separation_class in ['WIDE', 'VERY_WIDE']:
            confidence = min(100, confidence + 5)
            confluence_factors.append(f'💪 {separation_class} separation - strong trend momentum')
        
        confluence_factors.append(f'EMA separation: {separation_pct:+.2f}% ({separation_class})')
        confluence_factors.append(f'Fast EMA ({self.fast_period}): ${current_fast:.2f}')
        confluence_factors.append(f'Slow EMA ({self.slow_period}): ${current_slow:.2f}')
        
        # Metadata
        metadata = {
            'fast_ema': round(current_fast, 2),
            'slow_ema': round(current_slow, 2),
            'current_price': round(current_price, 2),
            'cross': cross,
            'has_volume_confirmation': has_volume_conf,
            'separation_pct': round(separation_pct, 2),
            'separation_class': separation_class,
            'trend': trend,
            'fast_period': self.fast_period,
            'slow_period': self.slow_period
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now(),
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
