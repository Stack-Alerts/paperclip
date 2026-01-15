"""
20/50 EMA Cross Building Block
Category: Moving Averages
Purpose: Event-driven crossover detection for 20 and 50 EMA with volume confirmation
"""
"""
Building Block Classification: SIGNAL BLOCK
Mode: EVENT-DRIVEN
Purpose: EMA crossover signals, selective on golden/death cross

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
    name='ema_20_50_cross',
    category='MOVING_AVERAGES',
    class_name='EMA2050Cross',
    default_weight=12,
    valid_signals=[
        # Cross events - GRANULAR
        'GOLDEN_CROSS', 'DEATH_CROSS',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'GOLDEN_CROSS': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Golden cross - Fast EMA crossed above Slow EMA (bullish)'
        },
        'DEATH_CROSS': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Death cross - Fast EMA crossed below Slow EMA (bearish)'
        },
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'No crossover detected - monitoring EMAs'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Golden cross - bullish (simple)'
        },
        'BEARISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Death cross - bearish (simple)'
        },
        
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
    description='EMA 20/50 Cross - Event-driven golden/death cross detector with volume confirmation',
    tags=['moving_averages', 'ema', 'crossover', 'golden_cross', 'death_cross', 'signal_block']
)
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
    
    def _determine_dual_signals(self, cross: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Granular: specific cross event
        if cross == 'GOLDEN_CROSS':
            granular = 'GOLDEN_CROSS'
            simple = 'BULLISH'
        elif cross == 'DEATH_CROSS':
            granular = 'DEATH_CROSS'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
    
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
            signal = 'GOLDEN_CROSS'
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
            signal = 'DEATH_CROSS'
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
        
        # **EVENT TRACKING** - Detect fresh crossover vs continuing cross confirmation
        is_new_event = False
        bars_in_state = 0
        
        if len(df) > min_required + 1:
            # Calculate previous bar's signal
            prev_df = df.iloc[:-1]
            prev_fast_ema = self.calculate_ema(prev_df['close'], self.fast_period)
            prev_slow_ema = self.calculate_ema(prev_df['close'], self.slow_period)
            prev_cross = self.detect_cross(prev_fast_ema, prev_slow_ema, lookback=self.cross_lookback)
            
            # Determine previous signal
            if prev_cross == 'GOLDEN_CROSS':
                prev_signal = 'BULLISH'
            elif prev_cross == 'DEATH_CROSS':
                prev_signal = 'BEARISH'
            else:
                prev_signal = 'NEUTRAL'
            
            # Detect signal change (new event)
            is_new_event = (signal != prev_signal)
            
            # Approximate bars in current state (minimal tracking)
            if not is_new_event:
                bars_in_state = 1  # At least 1 bar
        
        # Boost confidence for fresh cross events
        if is_new_event and signal != 'NEUTRAL':
            confidence = min(100, confidence + 5)
            confluence_factors.insert(0, f'⭐ NEW EVENT: Fresh {cross.replace("_", " ").lower()} detected!')
        elif signal != 'NEUTRAL' and bars_in_state > 0:
            confluence_factors.insert(0, f'Continuing {cross.replace("_", " ").lower()} confirmation ({bars_in_state} bars)')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(cross)
        
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
            'cross_lookback': self.cross_lookback,
            'is_new_event': is_new_event,  # EVENT TRACKING
            'bars_in_state': bars_in_state,   # EVENT TRACKING
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
