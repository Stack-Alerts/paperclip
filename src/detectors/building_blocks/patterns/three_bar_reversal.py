"""
Three Bar Reversal - Building Block
====================================

PATTERN BLOCK - Detects 3-bar reversal patterns.

Pattern structure:
- Bar 1: Trend direction
- Bar 2: Continuation of trend
- Bar 3: Reversal signal (makes new extreme but closes opposite)

Two pattern types:
- NORMAL: Bar 3 trades beyond Bar 2, closes opposite
- ENHANCED: Bar 3 trades beyond Bar 1, closes opposite (stronger)

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
    name='three_bar_reversal',
    category='PATTERNS',
    class_name='ThreeBarReversal',
    default_weight=30,
    valid_signals=[
        # Granular pattern signals
        'BULLISH_3BAR', 'BEARISH_3BAR',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular signals
        'BULLISH_3BAR': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish 3-bar reversal - Bar 3 made new low but closed higher. Bullish reversal confirmed. Enter longs. Stop below Bar 3 low.'
        },
        'BEARISH_3BAR': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish 3-bar reversal - Bar 3 made new high but closed lower. Bearish reversal confirmed. Enter shorts. Stop above Bar 3 high.'
        },
        # Simple directional
        'BULLISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bullish 3-bar pattern - Short-term reversal signal to upside. Long positions favorable. Quick reversal pattern (3 candles).'
        },
        'BEARISH': {
                'base_points': 30,
                'formula': 'scaled',
                'description': 'Bearish 3-bar pattern - Short-term reversal signal to downside. Short positions favorable. Quick reversal pattern (3 candles).'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'No 3-bar reversal - Pattern conditions not met. Need 3 candles with trend continuation then reversal close.'
        },
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot detect 3-bar reversal. Check data quality and minimum bars requirement.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need at least minimum bars for 3-bar reversal detection. Wait for more price history.'
        }
}
)
class ThreeBarReversal:
    """
    Three Bar Reversal Pattern Detector
    
    Building Block Classification: PATTERN BLOCK
    Mode: SELECTIVE (only on 3-bar reversal patterns)
    
    Detects bullish and bearish 3-bar reversal patterns with
    optional trend filtering for higher accuracy.
    
    Designed for 1H to Daily timeframes.
    """
    
    def __init__(
        self,
        pattern_type: str = 'enhanced',  # 'normal', 'enhanced', 'both'
        trend_filter: bool = True,
        ema_fast: int = 9,
        ema_slow: int = 21,
        min_strength: float = 50.0,
        **kwargs
    ):
        """
        Initialize Three Bar Reversal detector.
        
        Args:
            pattern_type: 'normal', 'enhanced', or 'both'
            trend_filter: Require trend alignment
            ema_fast: Fast EMA for trend
            ema_slow: Slow EMA for trend
            min_strength: Minimum pattern strength (0-100%)
        """
        self.pattern_type = pattern_type.lower()
        self.trend_filter = trend_filter
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.min_strength = min_strength
    
    def _determine_dual_signals(self, pattern_type: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        # Map pattern-specific signals to simple directions
        if pattern_type == 'BULLISH_3BAR':
            granular = 'BULLISH_3BAR'
            simple = 'BULLISH'
        elif pattern_type == 'BEARISH_3BAR':
            granular = 'BEARISH_3BAR'
            simple = 'BEARISH'
        elif pattern_type == 'NEUTRAL':
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        elif pattern_type == 'ERROR':
            granular = 'ERROR'
            simple = 'NEUTRAL'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for 3-bar reversal patterns.
        
        Compatible with building block interface.
        """
        try:
            # Validation
            required_cols = {'open', 'high', 'low', 'close', 'timestamp'}
            if not required_cols.issubset(df.columns):
                return self._error_response('Missing required columns')
            
            min_bars = max(50, self.ema_slow + 10)
            if len(df) < min_bars:
                return self._error_response(f'Need at least {min_bars} bars')
            
            # Calculate trend if filtering enabled
            if self.trend_filter:
                ema_fast = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
                ema_slow = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
                trend = 'bullish' if ema_fast.iloc[-1] > ema_slow.iloc[-1] else 'bearish'
            else:
                trend = 'neutral'
            
            # Need minimum 3 bars
            if len(df) < 3:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1], trend)
            
            # Get last 3 bars
            bar1 = df.iloc[-3]
            bar2 = df.iloc[-2]
            bar3 = df.iloc[-1]
            
            # Detect patterns
            bullish_pattern = self._detect_bullish_pattern(bar1, bar2, bar3)
            bearish_pattern = self._detect_bearish_pattern(bar1, bar2, bar3)
            
            pattern = bullish_pattern or bearish_pattern
            
            if not pattern:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1], trend)
            
            # Check trend alignment if filter enabled
            if self.trend_filter:
                if pattern['type'] == 'BULLISH_3BAR' and trend != 'bullish':
                    return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1], 
                                                 trend, 'Failed trend filter')
                if pattern['type'] == 'BEARISH_3BAR' and trend != 'bearish':
                    return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                                 trend, 'Failed trend filter')
            
            # Check strength threshold
            if pattern['strength'] < self.min_strength:
                return self._neutral_response(df['timestamp'].iloc[-1], df['close'].iloc[-1],
                                             trend, f'Low strength ({pattern["strength"]:.1f}%)')
            
            # Generate signal
            return self._generate_signal(
                pattern,
                df['timestamp'].iloc[-1],
                df['close'].iloc[-1],
                trend
            )
            
        except Exception as e:
            return self._error_response(f'Analysis error: {str(e)[:100]}')
    
    def _detect_bullish_pattern(self, bar1: pd.Series, bar2: pd.Series, bar3: pd.Series) -> Optional[Dict]:
        """
        Detect bullish 3-bar reversal.
        
        Requirements:
        - Bar 1 & 2: Downtrend (closes lower)
        - Bar 3: Makes new low but closes above bar 2 close
        """
        # Check downtrend
        if bar1['close'] <= bar2['close']:
            return None
        
        # Bar 3 must make new low
        if bar3['low'] >= bar2['low']:
            return None
        
        # Bar 3 must close above bar 2 close (reversal)
        if bar3['close'] <= bar2['close']:
            return None
        
        # Determine pattern type
        is_enhanced = bar3['low'] < bar1['low']
        
        # Check if pattern type matches settings
        if self.pattern_type == 'normal' and is_enhanced:
            return None
        if self.pattern_type == 'enhanced' and not is_enhanced:
           return None
        
        # Calculate strength
        penetration = bar2['low'] - bar3['low']
        recovery = bar3['close'] - bar2['close']
        total_range = bar1['high'] - bar3['low']
        
        if total_range > 0:
            strength = ((penetration + recovery) / total_range) * 100
            if is_enhanced:
                strength = min(100, strength * 1.2)  # Boost enhanced patterns
        else:
            strength = 50
        
        return {
            'type': 'BULLISH_3BAR',
            'is_enhanced': is_enhanced,
            'strength': strength,
            'support': bar3['low'],
            'resistance': bar1['high'],
            'penetration': penetration,
            'recovery': recovery,
        }
    
    def _detect_bearish_pattern(self, bar1: pd.Series, bar2: pd.Series, bar3: pd.Series) -> Optional[Dict]:
        """
        Detect bearish 3-bar reversal.
        
        Requirements:
        - Bar 1 & 2: Uptrend (closes higher)
        - Bar 3: Makes new high but closes below bar 2 close
        """
        # Check uptrend
        if bar1['close'] >= bar2['close']:
            return None
        
        # Bar 3 must make new high
        if bar3['high'] <= bar2['high']:
            return None
        
        # Bar 3 must close below bar 2 close (reversal)
        if bar3['close'] >= bar2['close']:
            return None
        
        # Determine pattern type
        is_enhanced = bar3['high'] > bar1['high']
        
        # Check if pattern type matches settings
        if self.pattern_type == 'normal' and is_enhanced:
            return None
        if self.pattern_type == 'enhanced' and not is_enhanced:
            return None
        
        # Calculate strength
        penetration = bar3['high'] - bar2['high']
        recovery = bar2['close'] - bar3['close']
        total_range = bar3['high'] - bar1['low']
        
        if total_range > 0:
            strength = ((penetration + recovery) / total_range) * 100
            if is_enhanced:
                strength = min(100, strength * 1.2)  # Boost enhanced patterns
        else:
            strength = 50
        
        return {
            'type': 'BEARISH_3BAR',
            'is_enhanced': is_enhanced,
            'strength': strength,
            'resistance': bar3['high'],
            'support': bar1['low'],
            'penetration': penetration,
            'recovery': recovery,
        }
    
    def _generate_signal(
        self,
        pattern: Dict,
        timestamp: datetime,
        current_price: float,
        trend: str
    ) -> Dict[str, Any]:
        """Generate signal response."""
        
        # Calculate confidence
        base_confidence = 65
        
        if pattern['is_enhanced']:
            base_confidence += 15
        
        if self.trend_filter and ((pattern['type'] == 'BULLISH_3BAR' and trend == 'bullish') or 
                                  (pattern['type'] == 'BEARISH_3BAR' and trend == 'bearish')):
            base_confidence += 10
        
        if pattern['strength'] > 70:
            base_confidence += 5
        
        confidence = max(50, min(95, base_confidence))
        
        # Calculate targets
        if pattern['type'] == 'BULLISH_3BAR':
            stop_loss = pattern['support'] * 0.995
            target = pattern['resistance']
        else:
            stop_loss = pattern['resistance'] * 1.005
            target = pattern['support']
        
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
                'pattern_type': 'enhanced' if pattern['is_enhanced'] else 'normal',
                'strength': round(pattern['strength'], 1),
                'current_price': round(current_price, 2),
                'support': round(pattern['support'], 2),
                'resistance': round(pattern['resistance'], 2),
                'trend': trend,
                'trend_filtered': self.trend_filter,
                'penetration': round(pattern['penetration'], 2),
                'recovery': round(pattern['recovery'], 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': self._get_confluence_factors(pattern, trend)
        }
    
    def _get_confluence_factors(self, pattern: Dict, trend: str) -> List[str]:
        """Get confluence factors."""
        factors = []
        
        pattern_name = '3-bar ' + ('enhanced' if pattern['is_enhanced'] else 'normal')
        direction = 'bullish' if 'BULLISH' in pattern['type'] else 'bearish'
        factors.append(f'{pattern_name} {direction} ({pattern["strength"]:.0f}%)')
        
        if pattern['is_enhanced']:
            factors.append('Enhanced reversal (stronger)')
        
        if self.trend_filter:
            if (('BULLISH' in pattern['type'] and trend == 'bullish') or 
                ('BEARISH' in pattern['type'] and trend == 'bearish')):
                factors.append(f'Trend-aligned ({trend})')
        
        if pattern['strength'] > 70:
            factors.append('High strength pattern')
        
        factors.append('Clear support/resistance levels')
        
        return factors
    
    def _neutral_response(self, timestamp: datetime, price: float, trend: str, reason: str = None) -> Dict[str, Any]:
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
                'trend': trend,
                'reason': reason or 'No 3-bar pattern detected',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': ['No pattern']
        }
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Generate error response."""
        granular_signal, simple_signal = self._determine_dual_signals('ERROR')
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': 0,
            'metadata': {
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
                'error': error
            },
            'timestamp': datetime.now(),
            'timeframe': '15min',
            'confluence_factors': []
        }


if __name__ == "__main__":
    logger.info("Three Bar Reversal - Building Block")
    logger.info("PATTERN BLOCK - 3-bar reversal pattern detection")
    logger.info("Based on LuxAlgo methodology")
