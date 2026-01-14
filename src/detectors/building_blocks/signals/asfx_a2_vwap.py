"""
ASFX A2 VWAP - Building Block
==============================

SIGNAL BLOCK - Detects A2 entry signals with VWAP confirmation.

A2 signals (Austin Silver methodology):
- Bullish: Price closes below EMA 21, <50% of candle above EMA
- Bearish: Price closes above EMA 21, <50% of candle below EMA

VWAP filtering ensures signals align with institutional flow.

Author: Institutional Research
Date: 2026-01-05
Grade: TBD (pending walkforward test)
"""

from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='asfx_a2_vwap',
    category='SIGNALS',
    class_name='ASFXA2VWAP',
    default_weight=20,
    valid_signals=[
        # Granular VWAP signals
        'ABOVE_VWAP', 'BELOW_VWAP', 'AT_VWAP', 'VWAP_CROSS_UP', 'VWAP_CROSS_DOWN',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular VWAP signals
        'ABOVE_VWAP': {
                'base_points': 15,
                'formula': 'scaled'
        },
        'BELOW_VWAP': {
                'base_points': 15,
                'formula': 'scaled'
        },
        'AT_VWAP': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'VWAP_CROSS_UP': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'VWAP_CROSS_DOWN': {
                'base_points': 20,
                'formula': 'scaled'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'NEUTRAL': {
                'points': 0
        },
        
        # Status
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
        }
}
)
class ASFXA2VWAP:
    """
    ASFX A2 VWAP Signal Detector
    
    Building Block Classification: SIGNAL BLOCK
    Mode: SELECTIVE (only on A2 signal confirmations)
    
    Detects A2 entry signals based on EMA positioning and VWAP confirmation.
    Provides Fibonacci-based stop-loss levels.
    
    Designed for daily to 1H timeframes.
    """
    
    def __init__(
        self,
        ema_period: int = 21,
        vwap_filter: bool = True,
        min_strength: float = 50.0,
        **kwargs
    ):
        """
        Initialize ASFX A2 VWAP detector.
        
        Args:
            ema_period: EMA period for A2 signal detection
            vwap_filter: Require VWAP alignment (bullish above, bearish below)
            min_strength: Minimum signal strength (0-100%)
        """
        self.ema_period = ema_period
        self.vwap_filter = vwap_filter
        self.min_strength = min_strength
        self.prev_vwap_relation = None  # For cross detection
    
    def _determine_dual_signals(self, vwap_relation: str, is_cross: bool = False) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if is_cross:
            # Cross signals
            if vwap_relation == 'VWAP_CROSS_UP':
                return 'VWAP_CROSS_UP', 'BULLISH'
            elif vwap_relation == 'VWAP_CROSS_DOWN':
                return 'VWAP_CROSS_DOWN', 'BEARISH'
        
        # Position relative to VWAP
        if vwap_relation == 'ABOVE_VWAP':
            return 'ABOVE_VWAP', 'BULLISH'
        elif vwap_relation == 'BELOW_VWAP':
            return 'BELOW_VWAP', 'BEARISH'
        elif vwap_relation == 'AT_VWAP':
            return 'AT_VWAP', 'NEUTRAL'
        else:
            return 'NEUTRAL', 'NEUTRAL'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Analyze dataframe for A2 VWAP signals.
        
        Compatible with building block interface.
        """
        try:
            # Validation
            required_cols = {'open', 'high', 'low', 'close', 'volume', 'timestamp'}
            if not required_cols.issubset(df.columns):
                return self._error_response('Missing required columns')
            
            min_bars = max(50, self.ema_period + 10)
            if len(df) < min_bars:
                return self._error_response(f'Need at least {min_bars} bars')
            
            # Calculate EMA
            ema_21 = self._calculate_ema(df['close'], self.ema_period)
            
            # Calculate VWAP
            vwap = self._calculate_vwap(df)
            
            # Get current values
            current_bar = df.iloc[-1]
            current_ema = ema_21.iloc[-1]
            current_vwap = vwap.iloc[-1]
            current_price = current_bar['close']
            
            if np.isnan(current_ema) or np.isnan(current_vwap):
                return self._neutral_response(current_bar['timestamp'], current_price)
            
            # Determine VWAP relationship
            vwap_distance_pct = abs(current_price - current_vwap) / current_vwap * 100
            
            if vwap_distance_pct < 0.5:  # Within 0.5% of VWAP
                vwap_relation = 'AT_VWAP'
            elif current_price > current_vwap:
                vwap_relation = 'ABOVE_VWAP'
            else:
                vwap_relation = 'BELOW_VWAP'
            
            # Detect VWAP crosses
            is_cross = False
            prev_relation = self.prev_vwap_relation
            
            if prev_relation and prev_relation != vwap_relation:
                if prev_relation == 'BELOW_VWAP' and vwap_relation == 'ABOVE_VWAP':
                    vwap_relation = 'VWAP_CROSS_UP'
                    is_cross = True
                elif prev_relation == 'ABOVE_VWAP' and vwap_relation == 'BELOW_VWAP':
                    vwap_relation = 'VWAP_CROSS_DOWN'
                    is_cross = True
            
            self.prev_vwap_relation = vwap_relation if not is_cross else (
                'ABOVE_VWAP' if vwap_relation == 'VWAP_CROSS_UP' else 'BELOW_VWAP'
            )
            
            # DUAL SIGNAL ARCHITECTURE
            granular_signal, simple_signal = self._determine_dual_signals(vwap_relation, is_cross)
            
            # Calculate confidence
            base_confidence = 60
            if is_cross:
                base_confidence = 75  # Crosses are stronger signals
            elif vwap_relation == 'AT_VWAP':
                base_confidence = 70  # At VWAP is a key level
            
            confidence = base_confidence
            
            # Generate signal response with VWAP signals
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': confidence,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'current_price': round(current_price, 2),
                    'ema_21': round(current_ema, 2),
                    'vwap': round(current_vwap, 2),
                    'vwap_distance_pct': round(vwap_distance_pct, 2),
                    'is_cross': is_cross,
                    'vwap_relation': vwap_relation,
                },
                'timestamp': current_bar['timestamp'],
                'timeframe': '15min',
                'confluence_factors': [
                    f'Price {vwap_relation.lower().replace("_", " ")}',
                    f'VWAP: ${current_vwap:.2f}',
                    f'Distance: {vwap_distance_pct:.2f}%'
                ]
            }
            
        except Exception as e:
            return self._error_response(f'Analysis error: {str(e)[:100]}')
    
    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate EMA."""
        return prices.ewm(span=period, adjust=False).mean()
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate cumulative VWAP."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
    
    def _detect_bullish_a2(self, bar: pd.Series, ema: float) -> Optional[Dict]:
        """
        Detect bullish A2 signal.
        
        Conditions:
        - Close below EMA
        - <50% of candle above EMA
        """
        if bar['close'] >= ema:
            return None
        
        candle_range = bar['high'] - bar['low']
        if candle_range == 0:
            return None
        
        price_above_ema = bar['close'] - bar['low']
        pct_above = price_above_ema / candle_range
        
        if pct_above < 0.5:
            strength = (1 - pct_above) * 100
            return {
                'type': 'BULLISH_A2',
                'strength': strength,
                'strong': pct_above < 0.3,
            }
        
        return None
    
    def _detect_bearish_a2(self, bar: pd.Series, ema: float) -> Optional[Dict]:
        """
        Detect bearish A2 signal.
        
        Conditions:
        - Close above EMA
        - <50% of candle below EMA
        """
        if bar['close'] <= ema:
            return None
        
        candle_range = bar['high'] - bar['low']
        if candle_range == 0:
            return None
        
        price_below_ema = bar['high'] - bar['close']
        pct_below = price_below_ema / candle_range
        
        if pct_below < 0.5:
            strength = (1 - pct_below) * 100
            return {
                'type': 'BEARISH_A2',
                'strength': strength,
                'strong': pct_below < 0.3,
            }
        
        return None
    
    def _calculate_bullish_stop(self, bar: pd.Series, daily_high: float) -> Dict:
        """Calculate Fibonacci-based bullish stop-loss."""
        base_range = daily_high - bar['low']
        fib_extension = base_range * 1.618
        stop_level = bar['low'] - fib_extension
        
        return {
            'stop_loss': stop_level,
            'base_range': base_range,
            'distance': bar['close'] - stop_level,
        }
    
    def _calculate_bearish_stop(self, bar: pd.Series, daily_low: float) -> Dict:
        """Calculate Fibonacci-based bearish stop-loss."""
        base_range = bar['high'] - daily_low
        fib_extension = base_range * 1.618
        stop_level = bar['high'] + fib_extension
        
        return {
            'stop_loss': stop_level,
            'base_range': base_range,
            'distance': stop_level - bar['close'],
        }
    
    def _generate_signal(
        self,
        signal: Dict,
        timestamp: datetime,
        current_price: float,
        ema_value: float,
        vwap_value: float,
        stop_loss: Dict
    ) -> Dict[str, Any]:
        """Generate signal response."""
        
        # Calculate confidence
        base_confidence = 70
        
        if signal['strong']:
            base_confidence += 15
        
        if self.vwap_filter:
            base_confidence += 10
        
        confidence = max(50, min(95, base_confidence))
        
        # Calculate risk/reward
        risk = stop_loss['distance']
        reward = abs(vwap_value - current_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'signal': signal['type'],
            'confidence': confidence,
            'metadata': {
                'a2_strength': round(signal['strength'], 1),
                'is_strong': signal['strong'],
                'current_price': round(current_price, 2),
                'ema_21': round(ema_value, 2),
                'vwap': round(vwap_value, 2),
                'vwap_filtered': self.vwap_filter,
                'stop_loss': round(stop_loss['stop_loss'], 2),
                'risk': round(risk, 2),
                'reward': round(reward, 2),
                'risk_reward_ratio': round(risk_reward, 2),
                'fibonacci_base': round(stop_loss['base_range'], 2),
                'is_new_event': True,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': self._get_confluence_factors(signal, vwap_value, current_price)
        }
    
    def _get_confluence_factors(self, signal: Dict, vwap: float, price: float) -> List[str]:
        """Get confluence factors."""
        factors = []
        
        factors.append(f'A2 {signal["type"].split("_")[0].lower()} ({signal["strength"]:.0f}%)')
        
        if signal['strong']:
            factors.append('Strong signal (<30% candle)')
        
        if self.vwap_filter:
            if 'BULLISH' in signal['type']:
                factors.append(f'Above VWAP ({((price/vwap - 1) * 100):.1f}%)')
            else:
                factors.append(f'Below VWAP ({((1 - price/vwap) * 100):.1f}%)')
        
        factors.append('Fibonacci stop-loss (1.618)')
        
        return factors
    
    def _neutral_response(self, timestamp: datetime, price: float, reason: str = None) -> Dict[str, Any]:
        """Generate neutral response."""
        return {
            'signal': 'NEUTRAL',
            'confidence': 50,
            'metadata': {
                'current_price': round(price, 2),
                'reason': reason or 'No A2 signal detected',
                'is_new_event': False,
            },
            'timestamp': timestamp,
            'timeframe': '15min',
            'confluence_factors': ['No signal']
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
    print("ASFX A2 VWAP - Building Block")
    print("SIGNAL BLOCK - A2 entry signals with VWAP confirmation")
    print("Based on Austin Silver methodology")
