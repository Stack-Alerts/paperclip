"""
Elliott Wave Oscillator Building Block
Category: Elliott Wave Pattern Recognition
Purpose: Momentum indicator confirming wave patterns (5-period SMA - 35-period SMA)
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous momentum state, always provides EWO value and direction

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
    name='elliott_wave_oscillator',
    category='ELLIOTT_WAVE',
    class_name='ElliottWaveOscillator',
    default_weight=22,
    valid_signals=[
        # Divergence Signals (highest priority) - GRANULAR
        'BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE',
        # Momentum Direction Signals - GRANULAR
        'BEARISH_MOMENTUM_INCREASING', 'BEARISH_MOMENTUM_WEAKENING',
        'BULLISH_MOMENTUM_INCREASING', 'BULLISH_MOMENTUM_WEAKENING',
        # Simple directional signals - SIMPLE for basic users
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status Signals
        'NEUTRAL_MOMENTUM', 'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Divergence signals - Highest value (reversal warning)
        'BEARISH_DIVERGENCE': {
            'base_points': 35,
            'formula': 'scaled',
            'description': 'Bearish divergence - Price making higher highs but EWO making lower highs. Reversal imminent. Take profit on longs, prepare shorts.'
        },
        'BULLISH_DIVERGENCE': {
            'base_points': 35,
            'formula': 'scaled',
            'description': 'Bullish divergence - Price making lower lows but EWO making higher lows. Reversal imminent. Take profit on shorts, prepare longs.'
        },
        
        # Momentum increasing signals - Strong trend confirmation
        'BEARISH_MOMENTUM_INCREASING': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish momentum accelerating - EWO diving deeper below zero. Strong downtrend. Add to shorts. Trail stops.'
        },
        'BULLISH_MOMENTUM_INCREASING': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish momentum accelerating - EWO rising higher above zero. Strong uptrend. Add to longs. Trail stops.'
        },
        
        # Momentum weakening signals - Trend losing strength
        'BEARISH_MOMENTUM_WEAKENING': {
            'base_points': 10,
            'formula': 'scaled',
            'description': 'Bearish momentum weakening - EWO rising toward zero. Downtrend losing steam. Tighten stops on shorts. Reversal possible.'
        },
        'BULLISH_MOMENTUM_WEAKENING': {
            'base_points': 10,
            'formula': 'scaled',
            'description': 'Bullish momentum weakening - EWO falling toward zero. Uptrend losing steam. Tighten stops on longs. Reversal possible.'
        },
        
        # Simple directional signals - SIMPLE for basic users
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish EWO - Oscillator above zero line. Bullish momentum detected. Long positions favorable.'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish EWO - Oscillator below zero line. Bearish momentum detected. Short positions favorable.'
        },
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'Neutral EWO - Oscillator near zero line. No clear momentum. Wait for decisive move before entering.'
        },
        
        # Neutral/Status signals
        'NEUTRAL_MOMENTUM': {
            'base_points': 5,
            'formula': 'scaled',
            'description': 'Neutral momentum - EWO hovering near zero. Market in equilibrium. No clear trend. Avoid entries until breakout.'
        },
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate Elliott Wave Oscillator. Check data quality and SMA periods.'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient data - Need at least 35 candles for EWO calculation. Wait for more price history.'
        }
    },
    description='Elliott Wave Oscillator - Momentum indicator (5-SMA minus 35-SMA) for wave confirmation',
    tags=['elliott_wave', 'momentum', 'divergence', 'context_block', 'oscillator']
)
class ElliottWaveOscillator:
    """
    Elliott Wave Oscillator
    
    Confirms wave patterns through momentum divergence
    EWO = 5-period SMA - 35-period SMA
    """
    
    def __init__(self, timeframe: str = '15min', fast_period: int = 5, slow_period: int = 35, **kwargs):
        self.timeframe = timeframe
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def _determine_dual_signals(self, signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        # Divergence signals (granular)
        if signal in ['BEARISH_DIVERGENCE', 'BULLISH_DIVERGENCE']:
            granular = signal
            simple = 'BEARISH' if 'BEARISH' in signal else 'BULLISH'
        # Momentum direction signals (granular)
        elif 'MOMENTUM' in signal:
            granular = signal
            if 'BULLISH' in signal:
                simple = 'BULLISH'
            elif 'BEARISH' in signal:
                simple = 'BEARISH'
            else:
                simple = 'NEUTRAL'
        # Already simple signals
        elif signal in ['BULLISH', 'BEARISH', 'NEUTRAL']:
            granular = signal
            simple = signal
        # Status signals
        elif signal in ['NEUTRAL_MOMENTUM', 'ERROR', 'INSUFFICIENT_DATA']:
            granular = signal
            simple = 'NEUTRAL'
        else:
            granular = signal
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.slow_period:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate EMO
        fast_sma = df['close'].rolling(window=self.fast_period).mean()
        slow_sma = df['close'].rolling(window=self.slow_period).mean()
        ewo = fast_sma - slow_sma
        
        current_ewo = float(ewo.iloc[-1])
        prev_ewo = float(ewo.iloc[-2]) if len(ewo) > 1 else 0
        
        # Check for divergence FIRST (highest priority signal)
        price_trend = 'UP' if df['close'].iloc[-1] > df['close'].iloc[-10] else 'DOWN'
        ewo_trend = 'UP' if current_ewo > ewo.iloc[-10] else 'DOWN'
        
        divergence_detected = None
        if price_trend == 'UP' and ewo_trend == 'DOWN':
            # CRITICAL FIX: Actually emit the divergence signal!
            signal = 'BEARISH_DIVERGENCE'
            confidence = 85
            divergence_detected = 'BEARISH_DIVERGENCE'
        elif price_trend == 'DOWN' and ewo_trend == 'UP':
            # CRITICAL FIX: Actually emit the divergence signal!
            signal = 'BULLISH_DIVERGENCE'
            confidence = 85
            divergence_detected = 'BULLISH_DIVERGENCE'
        else:
            # No divergence - use momentum signals
            divergence_detected = None
            
            # Check if near zero line (neutral momentum)
            if abs(current_ewo) < 0.5:  # Very close to zero
                signal = 'NEUTRAL_MOMENTUM'
                confidence = 50
            # Determine momentum signal based on direction and strength
            elif current_ewo > 0:
                if current_ewo > prev_ewo:
                    signal = 'BULLISH_MOMENTUM_INCREASING'
                    confidence = 75
                else:
                    signal = 'BULLISH_MOMENTUM_WEAKENING'
                    confidence = 60
            else:
                if current_ewo < prev_ewo:
                    signal = 'BEARISH_MOMENTUM_INCREASING'
                    confidence = 75
                else:
                    signal = 'BEARISH_MOMENTUM_WEAKENING'
                    confidence = 60
        
        # Build confluence factors
        confluence_factors = []
        confluence_factors.append(f"EWO: {current_ewo:.2f}")
        confluence_factors.append(f"Zero line: {'Above' if current_ewo > 0 else 'Below'}")
        
        if divergence_detected:
            confluence_factors.append(f"⚠️ {divergence_detected} - reversal warning!")
        
        momentum_dir = 'INCREASING' if abs(current_ewo) > abs(prev_ewo) else 'DECREASING'
        confluence_factors.append(f"Momentum: {momentum_dir}")
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'ewo_value': round(current_ewo, 2),
            'prev_ewo_value': round(prev_ewo, 2),
            'zero_line_position': 'ABOVE' if current_ewo > 0 else 'BELOW',
            'divergence_detected': divergence_detected if divergence_detected else 'NONE',
            'momentum_direction': momentum_dir,
            'price_trend_10bar': price_trend,
            'ewo_trend_10bar': ewo_trend
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': min(95, confidence),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
