"""
EMA Crossover Systems Building Block
Category: Institutional & Volume
Purpose: Standard EMA crossovers (20/50/200) for trend identification
"""
"""
Building Block Classification: HYBRID BLOCK
Mode: CONTINUOUS STATE + RARE EVENTS
Purpose: Continuous EMA alignment state (99.4%) + rare cross events (0.58%)

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events ← THIS BLOCK
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd


@register_block(
    name='ema_crossover',
    category='INSTITUTIONAL',
    class_name='EMACrossover',
    default_weight=15,
    valid_signals=[
        # Cross Events (rare - 0.58% of time - highest value) - GRANULAR
        'GOLDEN_CROSS', 'DEATH_CROSS',
        # Alignment States (continuous - 99.4% of time - standard value) - GRANULAR
        'BULLISH_ALIGNMENT', 'BEARISH_ALIGNMENT',
        # Simple directional signals - SIMPLE for basic users
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status Signals
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Cross events - RARE and significant (0.58% occurrence)
        'GOLDEN_CROSS': {
            'base_points': 35,
            'formula': 'scaled',
            'description': 'EMA 50/200 golden cross - rare bullish reversal signal'
        },
        'DEATH_CROSS': {
            'base_points': 35,
            'formula': 'scaled',
            'description': 'EMA 50/200 death cross - rare bearish reversal signal'
        },
        
        # Alignment states - Continuous trend confirmation (99.4% occurrence)
        'BULLISH_ALIGNMENT': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Fast EMA above slow EMA - bullish trend alignment'
        },
        'BEARISH_ALIGNMENT': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Fast EMA below slow EMA - bearish trend alignment'
        },
        
        # Simple directional signals - SIMPLE for basic users
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish EMA setup - any alignment (simple)'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish EMA setup - any alignment (simple)'
        },
        'NEUTRAL': {
            'base_points': 10,
            'formula': 'scaled',
            'description': 'EMAs converging - neutral (simple)'
        },
        
        # Status signals
        'ERROR': {
            'points': 0,
            'description': 'Analysis error occurred'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'description': 'Not enough data for analysis'
        }
    },
    description='EMA Crossover - Fast/slow EMA crosses (rare events) and trend alignment (continuous state)',
    tags=['institutional', 'ema', 'trend', 'crossover', 'hybrid_block', 'rare_events']
)
class EMACrossover:
    """
    EMA Crossover detection with enhancements
    
    Improvements:
    - Separation strength metric (trend quality)
    - Cross momentum detection (strength of reversal)
    """
    
    def __init__(self, timeframe: str = '15min', fast: int = 50, slow: int = 200, **kwargs):
        self.timeframe = timeframe
        self.fast = fast
        self.slow = slow
    
    def calculate_separation_strength(self, fast_ema: float, slow_ema: float) -> dict:
        """
        Measure EMA separation strength
        Stronger separation = stronger trend
        """
        separation_pct = abs(fast_ema - slow_ema) / slow_ema * 100
        
        if separation_pct > 3.0:
            strength = 'VERY_STRONG'
            bonus = 25
        elif separation_pct > 2.0:
            strength = 'STRONG'
            bonus = 20
        elif separation_pct > 1.0:
            strength = 'MODERATE'
            bonus = 15
        elif separation_pct < 0.5:
            strength = 'WEAK_CONVERGING'
            bonus = 5
        else:
            strength = 'NORMAL'
            bonus = 10
        
        return {
            'separation_pct': separation_pct,
            'strength': strength,
            'bonus': bonus
        }
    
    def detect_cross_strength(self, ema_fast: pd.Series, cross_type: str) -> int:
        """
        Measure strength of cross
        Fast cross with momentum = stronger signal
        """
        # Calculate slope of fast EMA during cross
        recent_slope = (ema_fast.iloc[-1] - ema_fast.iloc[-5]) / ema_fast.iloc[-5] * 100
        
        if cross_type == 'GOLDEN_CROSS':
            # Strong upward slope = strong golden cross
            if recent_slope > 2.0:
                return 95  # Very strong
            elif recent_slope > 1.0:
                return 92
            else:
                return 90  # Standard
        
        else:  # DEATH_CROSS
            # Strong downward slope = strong death cross
            if recent_slope < -2.0:
                return 95  # Very strong
            elif recent_slope < -1.0:
                return 92
            else:
                return 90  # Standard
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method with enhancements"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {'signal': 'ERROR', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        if len(df) < self.slow:
            return {'signal': 'INSUFFICIENT_DATA', 'confidence': 0, 'metadata': {}, 'timestamp': datetime.now(), 'timeframe': self.timeframe, 'confluence_factors': []}
        
        ema_fast = df['close'].ewm(span=self.fast).mean()
        ema_slow = df['close'].ewm(span=self.slow).mean()
        
        current_fast = float(ema_fast.iloc[-1])
        current_slow = float(ema_slow.iloc[-1])
        prev_fast = float(ema_fast.iloc[-2])
        prev_slow = float(ema_slow.iloc[-2])
        
        # Calculate separation strength (NEW)
        separation = self.calculate_separation_strength(current_fast, current_slow)
        
        # Golden cross / Death cross
        if current_fast > current_slow and prev_fast <= prev_slow:
            signal = 'GOLDEN_CROSS'
            # Enhanced confidence based on cross strength (NEW)
            confidence = self.detect_cross_strength(ema_fast, 'GOLDEN_CROSS')
            confluence_factors = [
                f'🌟 Golden Cross: EMA{self.fast} crossed above EMA{self.slow}',
                f'Cross momentum: {"Very Strong" if confidence == 95 else "Strong" if confidence == 92 else "Standard"}'
            ]
        elif current_fast < current_slow and prev_fast >= prev_slow:
            signal = 'DEATH_CROSS'
            # Enhanced confidence based on cross strength (NEW)
            confidence = self.detect_cross_strength(ema_fast, 'DEATH_CROSS')
            confluence_factors = [
                f'💀 Death Cross: EMA{self.fast} crossed below EMA{self.slow}',
                f'Cross momentum: {"Very Strong" if confidence == 95 else "Strong" if confidence == 92 else "Standard"}'
            ]
        elif current_fast > current_slow:
            signal = 'BULLISH_ALIGNMENT'
            confidence = 75
            confluence_factors = [
                'Bullish EMA alignment',
                f'Trend strength: {separation["strength"]} ({separation["separation_pct"]:.2f}%)'
            ]
        else:
            signal = 'BEARISH_ALIGNMENT'
            confidence = 75
            confluence_factors = [
                'Bearish EMA alignment',
                f'Trend strength: {separation["strength"]} ({separation["separation_pct"]:.2f}%)'
            ]
        
        # Enhanced metadata (NEW)
        metadata = {
            'fast_ema': round(current_fast, 2),
            'slow_ema': round(current_slow, 2),
            'separation_pct': round(separation['separation_pct'], 3),
            'separation_strength': separation['strength'],
            'separation_bonus': separation['bonus']
        }
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
