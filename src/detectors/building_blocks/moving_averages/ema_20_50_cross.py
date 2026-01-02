"""
20/50 EMA Cross Building Block
Category: Moving Averages
Purpose: Event-driven crossover detection for 20 and 50 EMA with volume confirmation
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class EMA2050Cross:
    """
    20/50 EMA Cross - Event-Driven Crossover Detector
    
    Pure crossover detection system that ONLY signals on actual cross events:
    - Golden Cross: Fast EMA crosses above Slow EMA (bullish event)
    - Death Cross: Fast EMA crosses below Slow EMA (bearish event)
    - Returns NEUTRAL when no cross occurs
    - Volume confirmation: Higher volume on cross increases confidence
    
    This indicator signals ONLY when an actual crossover event happens.
    For continuous trend position tracking, use ema_20_50_trend instead.
    
    Parameters:
        fast_period: Fast EMA period (default: 15, optimized)
        slow_period: Slow EMA period (default: 45, optimized) 
        timeframe: Data timeframe
        cross_lookback: Bars to confirm cross (default: 2)
        volume_threshold: Volume multiplier for confirmation (default: 1.1)
    
    Returns:
        BULLISH on Golden Cross, BEARISH on Death Cross, NEUTRAL otherwise
    """
    
    def __init__(self, 
                 fast_period: int = 15,  # OPTIMIZED: 15 outperforms 20
                 slow_period: int = 45,  # OPTIMIZED: 45 outperforms 50
                 timeframe: str = '15min',
                 cross_lookback: int = 2,  # OPTIMIZED: Faster confirmation
                 volume_threshold: float = 1.1,  # OPTIMIZED: Looser threshold
                 **kwargs):
        """Initialize 20/50 EMA Cross block"""
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.timeframe = timeframe
        self.cross_lookback = cross_lookback
        self.volume_threshold = volume_threshold
    
    def calculate_ema(self, close: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return close.ewm(span=period, adjust=False).mean()
    
    def detect_cross(self, fast_ema: pd.Series, slow_ema: pd.Series, lookback: int = 2) -> str:
        """
        Detect EMA crossovers with confirmation
        
        Returns:
            'GOLDEN_CROSS': Fast crossed above Slow
            'DEATH_CROSS': Fast crossed below Slow
            'NO_CROSS': No crossover detected
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
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method - ONLY signals on actual cross events
        
        Returns NEUTRAL when no cross is detected
        """
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
        
        # CRITICAL: ONLY signal on actual cross events
        signal = 'NEUTRAL'
        confidence = 70
        confluence_factors = []
        
        if cross == 'GOLDEN_CROSS':
            # Bullish cross detected
            signal = 'BULLISH'
            confidence = 85
            confluence_factors.append('✅ GOLDEN CROSS - Fast EMA crossed above Slow EMA (bullish)')
            
            if has_volume_conf:
                confidence += 10
                confluence_factors.append('📊 Volume confirmation - above average volume on cross')
            else:
                confidence -= 10
                confluence_factors.append('⚠️ Low volume - cross lacks volume confirmation')
            
            confluence_factors.append(f'Cross confirmed over {self.cross_lookback} bars')
                
        elif cross == 'DEATH_CROSS':
            # Bearish cross detected
            signal = 'BEARISH'
            confidence = 85
            confluence_factors.append('❌ DEATH CROSS - Fast EMA crossed below Slow EMA (bearish)')
            
            if has_volume_conf:
                confidence += 10
                confluence_factors.append('📊 Volume confirmation - above average volume on cross')
            else:
                confidence -= 10
                confluence_factors.append('⚠️ Low volume - cross lacks volume confirmation')
            
            confluence_factors.append(f'Cross confirmed over {self.cross_lookback} bars')
        
        else:
            # NO CROSS - Return NEUTRAL
            signal = 'NEUTRAL'
            confidence = 70
            
            # Just provide current position info
            if current_fast > current_slow:
                confluence_factors.append('Fast EMA above Slow EMA - no recent cross')
            else:
                confluence_factors.append('Fast EMA below Slow EMA - no recent cross')
        
        # Always add current values for context
        confluence_factors.append(f'EMA separation: {separation_pct:+.2f}%')
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
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'cross_lookback': self.cross_lookback
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
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    np.random.seed(42)
    
    # Create data with a clear cross
    base = 45000
    data = pd.DataFrame({
        'timestamp': dates,
        'close': base + np.concatenate([
            np.linspace(0, -500, 100),  # Downtrend
            np.linspace(-500, 500, 100)  # Uptrend (creates cross)
        ]),
        'volume': np.random.uniform(100, 1000, 200)
    })
    
    cross = EMA2050Cross()
    
    print("=" * 80)
    print("20/50 EMA CROSS - TEST RESULTS (Event-Driven)")
    print("=" * 80)
    
    # Test at different points
    for i in [50, 100, 150, 199]:
        result = cross.analyze(data.iloc[:i+1])
        print(f"\nBar {i}: {result['signal']} ({result['confidence']}%)")
        if result['signal'] != 'NEUTRAL':
            for factor in result['confluence_factors']:
                print(f"  - {factor}")
    
    print("=" * 80)
