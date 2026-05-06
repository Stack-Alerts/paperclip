"""
Candle 2 Close - Building Block
================================

PATTERN BLOCK - Detects Candle 2 Closure reversal patterns.

4-candle pattern structure:
- Candle 1: Context (establishes range)
- Candle 2: Reversal (fails breakout, closes opposite)
- Candle 3: Expansion (confirms with expansion)
- Candle 4: Continuation (reinforces direction)

Based on TTrades Candle 2 Closure framework.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np

import logging
logger = logging.getLogger(__name__)

@register_block(
    name='candle_2_close',
    category='PATTERNS',
    class_name='Candle2Close',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals
        'BULLISH_C2_CLOSE', 'BEARISH_C2_CLOSE',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Pattern signals
        'BULLISH_C2_CLOSE': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish C2 Close - Failed downside breakout with bullish reversal. Enter longs at C2 zone. Stop below C2 low. Target C3 expansion high.'
        },
        'BEARISH_C2_CLOSE': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish C2 Close - Failed upside breakout with bearish reversal. Enter shorts at C2 zone. Stop above C2 high. Target C3 expansion low.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish C2 pattern - Failed breakdown with reversal. Long positions favorable. Use C2 equilibrium zone for entry. Stop below pattern.'
        },
        'BEARISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish C2 pattern - Failed breakout with reversal. Short positions favorable. Use C2 equilibrium zone for entry. Stop above pattern.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No C2 Close pattern - Failed breakout conditions not met. No reversal signal. Wait for 4-candle pattern formation.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot detect Candle 2 Close pattern. Check data quality and minimum bars requirement.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least 4 candles for C2 Close pattern detection. Wait for more price history.'
        }
}
)
class Candle2Close:
    """
    Candle 2 Closure Pattern Detector
    
    Building Block Classification: PATTERN BLOCK
    Mode: SELECTIVE (only on failed breakout reversals)
    
    Detects 4-candle reversal patterns where price fails a breakout
    and reverses with expansion confirmation.
    
    Designed for 1H to Daily timeframes.
    """
    
    def __init__(
        self,
        wick_threshold_pct: float = 75.0,
        detect_candle_2: bool = True,
        detect_candle_3: bool = True,
        reversal_filter: bool = True,
        reversal_lookback: int = 20,
        min_strength: float = 50.0,
        **kwargs
    ):
        """
        Initialize Candle 2 Close detector.
        
        Args:
            wick_threshold_pct: Wick % of range to use wick for zone
            detect_candle_2: Enable C2 reversal detection
            detect_candle_3: Require C3 expansion confirmation
            reversal_filter: Only signals at extremes
            reversal_lookback: Bars for extreme detection
            min_strength: Minimum pattern strength (0-100%)
        """
        self.wick_threshold_pct = wick_threshold_pct
        self.detect_candle_2 = detect_candle_2
        self.detect_candle_3 = detect_candle_3
        self.reversal_filter = reversal_filter
        self.reversal_lookback = reversal_lookback
        self.min_strength = min_strength
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular == 'BULLISH_C2_CLOSE':
            simple = 'BULLISH'
        elif granular == 'BEARISH_C2_CLOSE':
            simple = 'BEARISH'
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for Candle 2 Close patterns.
        
        Compatible with building block interface.
        """
        try:
            # Validation
            required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
            if not required_cols.issubset(df.columns):
                return self._error_response('Missing required columns')
            
            min_bars = max(50, self.reversal_lookback + 10)
            if len(df) < min_bars:
                return self._error_response(f'Need at least {min_bars} bars')
            
            # Need minimum 4 bars for pattern
            if len(df) < 4:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1])
            
            # Get last 4 bars
            c1 = df.iloc[-4]
            c2 = df.iloc[-3]
            c3 = df.iloc[-2]
            c4 = df.iloc[-1]
            
            # Detect patterns
            bullish_pattern = self._detect_bullish_pattern(c1, c2, c3, c4)
            bearish_pattern = self._detect_bearish_pattern(c1, c2, c3, c4)
            
            pattern = bullish_pattern or bearish_pattern
            
            if not pattern:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1])
            
            # Check reversal filter if enabled
            if self.reversal_filter:
                is_at_extreme = self._check_extreme(df, pattern['type'])
                if not is_at_extreme:
                    return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                                 reason='Failed reversal filter (not at extreme)')
            
            # Check strength threshold
            if pattern['strength'] < self.min_strength:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             reason=f'Low strength ({pattern["strength"]:.1f}%)')
            
            # Generate signal
            return self._generate_signal(
                pattern,
                df['timestamp'].iloc[-1],
                df['close'].iloc[-1]
            )
            
        except Exception as e:
            return self._error_response(f'Analysis error: {str(e)[:100]}')
    
    def _detect_bullish_pattern(self, c1: pd.Series, c2: pd.Series, 
                                c3: pd.Series, c4: pd.Series) -> Optional[Dict]:
        """
        Detect bullish Candle 2 Close pattern.
        
        Requirements:
        - C1: Down candle (close < open)
        - C2: Trades below C1 low, closes above C1 close
        - C3: Closes above C2 high (expansion)
        - C4: Continues upward
        """
        # C1 must be down (context)
        if c1['close'] >= c1['open']:
            return None
        
        if not self.detect_candle_2:
            return None
        
        # C2: Makes new low but closes above C1 close (reversal)
        if c2['low'] >= c1['low']:
            return None
        if c2['close'] <= c1['close']:
            return None
        
        if not self.detect_candle_3:
            # C2 only mode
            pass
        else:
            # C3: Closes above C2 high (expansion confirmation)
            if c3['close'] <= c2['high']:
                return None
        
        # Calculate equilibrium zones
        c2_zone_low = c1['low']
        c2_zone_high = c2['close']
        
        if self.detect_candle_3:
            c3_zone_low = c2['high']
            c3_zone_high = c3['high']
        else:
            c3_zone_low = c2['high']
            c3_zone_high = c2['high']
        
        # Calculate strength
        penetration = c1['low'] - c2['low']
        recovery = c2['close'] - c1['close']
        total_range = c1['high'] - c2['low']
        
        if total_range > 0:
            strength = ((penetration + recovery) / total_range) * 100
            if self.detect_candle_3 and c3['close'] > c2['high']:
                strength = min(100, strength * 1.15)  # Boost for C3 confirmation
        else:
            strength = 50
        
        return {
            'type': 'BULLISH_C2_CLOSE',
            'has_c3': self.detect_candle_3,
            'strength': strength,
            'c2_zone_low': c2_zone_low,
            'c2_zone_high': c2_zone_high,
            'c3_zone_low': c3_zone_low,
            'c3_zone_high': c3_zone_high,
            'penetration': penetration,
            'recovery': recovery,
        }
    
    def _detect_bearish_pattern(self, c1: pd.Series, c2: pd.Series,
                                c3: pd.Series, c4: pd.Series) -> Optional[Dict]:
        """
        Detect bearish Candle 2 Close pattern.
        
        Requirements:
        - C1: Up candle (close > open)
        - C2: Trades above C1 high, closes below C1 close
        - C3: Closes below C2 low (expansion)
        - C4: Continues downward
        """
        # C1 must be up (context)
        if c1['close'] <= c1['open']:
            return None
        
        if not self.detect_candle_2:
            return None
        
        # C2: Makes new high but closes below C1 close (reversal)
        if c2['high'] <= c1['high']:
            return None
        if c2['close'] >= c1['close']:
            return None
        
        if not self.detect_candle_3:
            # C2 only mode
            pass
        else:
            # C3: Closes below C2 low (expansion confirmation)
            if c3['close'] >= c2['low']:
                return None
        
        # Calculate equilibrium zones
        c2_zone_high = c1['high']
        c2_zone_low = c2['close']
        
        if self.detect_candle_3:
            c3_zone_high = c2['low']
            c3_zone_low = c3['low']
        else:
            c3_zone_high = c2['low']
            c3_zone_low = c2['low']
        
        # Calculate strength
        penetration = c2['high'] - c1['high']
        recovery = c1['close'] - c2['close']
        total_range = c2['high'] - c1['low']
        
        if total_range > 0:
            strength = ((penetration + recovery) / total_range) * 100
            if self.detect_candle_3 and c3['close'] < c2['low']:
                strength = min(100, strength * 1.15)  # Boost for C3 confirmation
        else:
            strength = 50
        
        return {
            'type': 'BEARISH_C2_CLOSE',
            'has_c3': self.detect_candle_3,
            'strength': strength,
            'c2_zone_high': c2_zone_high,
            'c2_zone_low': c2_zone_low,
            'c3_zone_high': c3_zone_high,
            'c3_zone_low': c3_zone_low,
            'penetration': penetration,
            'recovery': recovery,
        }
    
    def _check_extreme(self, df: pd.DataFrame, pattern_type: str) -> bool:
        """Check if pattern is at recent extreme."""
        lookback = min(self.reversal_lookback, len(df) - 4)
        if lookback < 5:
            return True  # Not enough data, allow pattern
        
        recent_bars = df.iloc[-lookback-4:-4]
        
        if 'BULLISH' in pattern_type:
            # Check if recent low
            current_low = df.iloc[-4]['low']
            recent_low = recent_bars['low'].min()
            return current_low <= recent_low * 1.002  # Within 0.2%
        else:
            # Check if recent high
            current_high = df.iloc[-4]['high']
            recent_high = recent_bars['high'].max()
            return current_high >= recent_high * 0.998  # Within 0.2%
    
    def _generate_signal(
        self,
        pattern: Dict,
        timestamp: datetime,
        current_price: float
    ) -> Dict[str, Any]:
        """Generate signal response."""
        
        # Calculate confidence
        base_confidence = 70
        
        if pattern['has_c3']:
            base_confidence += 10
        
        if self.reversal_filter:
            base_confidence += 10
        
        if pattern['strength'] > 70:
            base_confidence += 5
        
        confidence = max(50, min(95, base_confidence))
        
        # Calculate targets
        if 'BULLISH' in pattern['type']:
            stop_loss = pattern['c2_zone_low'] * 0.995
            target = pattern['c3_zone_high']
        else:
            stop_loss = pattern['c2_zone_high'] * 1.005
            target = pattern['c3_zone_low']
        
        risk = abs(current_price - stop_loss)
        reward = abs(target - current_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(pattern['type'])
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'pattern_confirmed': pattern['has_c3'],
                'strength': round(pattern['strength'], 1),
                'current_price': round(current_price, 2),
                'c2_zone_low': round(pattern['c2_zone_low'], 2),
                'c2_zone_high': round(pattern['c2_zone_high'], 2),
                'c3_zone_low': round(pattern['c3_zone_low'], 2),
                'c3_zone_high': round(pattern['c3_zone_high'], 2),
                'reversal_filtered': self.reversal_filter,
                'penetration': round(pattern['penetration'], 2),
                'recovery': round(pattern['recovery'], 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': self._get_confluence_factors(pattern)
        }
    
    def _get_confluence_factors(self, pattern: Dict) -> List[str]:
        """Get confluence factors."""
        factors = []
        
        direction = 'bullish' if 'BULLISH' in pattern['type'] else 'bearish'
        factors.append(f'C2 Close {direction} ({pattern["strength"]:.0f}%)')
        
        if pattern['has_c3']:
            factors.append('C3 expansion confirmed')
        else:
            factors.append('C2 reversal only')
        
        if self.reversal_filter:
            factors.append('At reversal extreme')
        
        if pattern['strength'] > 70:
            factors.append('High strength pattern')
        
        factors.append('Equilibrium zones defined')
        
        return factors
    
    def _neutral_response(self, timestamp: datetime, price: float, reason: str = None) -> Dict[str, Any]:
        """Generate neutral response."""
        granular_signal, simple_signal = self._determine_dual_signals('NEUTRAL')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 50,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'current_price': round(price, 2),
                'reason': reason or 'No C2 Close pattern detected',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': ['No pattern']
        }
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            'signal': 'ERROR',
            'confidence': 0,
            'metadata': {'error': error},
            'timestamp': datetime.now(),
            'timeframe': '15min',
            'confluence_factors': []
        }


if __name__ == "__main__":
    logger.info("Candle 2 Close - Building Block")
    logger.info("PATTERN BLOCK - 4-candle reversal pattern detection")
    logger.info("Based on TTrades Candle 2 Closure framework")
