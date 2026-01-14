"""
Mitigation Block Building Block
Category: SMC/ICT
Purpose: Detect mitigation blocks - ICT institutional position mitigation
"""
"""
Building Block Classification: EVENT BLOCK
Mode: SELECTIVE
Purpose: Mitigation block detection, fires when formed

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='mitigation_block',
    category='SMC_ICT',
    class_name='MitigationBlock',
    default_weight=20,
    valid_signals=[
        # Granular SMC signals
        'BEARISH_MITIGATION', 'BULLISH_MITIGATION',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'BEARISH_MITIGATION': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'BULLISH_MITIGATION': {
                'base_points': 20,
                'formula': 'scaled'
        },
        'ERROR': {
                'points': 0
        },
        'INSUFFICIENT_DATA': {
                'points': 0
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
        }
}
)
class MitigationBlock:
    """
    Mitigation Block Detector - ICT/SMC Concept (ENHANCED 2026-01-04)
    
    Identifies zones where institutions need to mitigate (close/reduce)
    their positions. These are unfilled orders or imbalances that price
    must return to before continuing in the intended direction.
    
    Mitigation Characteristics:
    - Unfilled institutional orders
    - Price gaps/imbalances
    - Must be filled before continuation
    - High probability retracement zone
    
    Types:
    - Bullish Mitigation: Unfilled buy orders below (support)
    - Bearish Mitigation: Unfilled sell orders above (resistance)
    
    Trading Application:
    - Entry on return to mitigation zone
    - Expect bounce/rejection
    - Continuation after mitigation
    
    ENHANCEMENTS (2026-01-04):
    - Multi-Timeframe Mitigation: Checks multiple timeframes for alignment
    - Strength Scoring: Gap size, volume, age-based quality assessment
    - Historical Fill Rate: Tracks which mitigations get filled
    
    Parameters:
        lookback: Periods for gap detection (default: 20)
        gap_threshold: Minimum gap % to identify (default: 0.2%)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 gap_threshold: float = 0.2, **kwargs):
        """Initialize Mitigation Block detector"""
        self.timeframe = timeframe
        self.lookback = lookback
        self.gap_threshold = gap_threshold
        
        # ENHANCEMENT 3: Historical Fill Rate (2026-01-04)
        self.mitigation_history = []  # Track mitigations and fills
        self.max_history = 50
    
    def _determine_dual_signals(self, mit_type: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        if mit_type == 'BULLISH_MITIGATION':
            granular = 'BULLISH_MITIGATION'
            simple = 'BULLISH'
        elif mit_type == 'BEARISH_MITIGATION':
            granular = 'BEARISH_MITIGATION'
            simple = 'BEARISH'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        return granular, simple
    
    def detect_bullish_mitigation(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bullish mitigation zone (unfilled buy orders below)
        
        CRITICAL FIX for Bitcoin: Traditional gaps rare in 24/7 crypto markets.
        Instead, detect:
        1. Strong bullish impulse candles (institutional buying)
        2. Areas not yet retested (mitigation pending)
        3. Imbalances in price action
        """
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for strong bullish candles that created mitigation zones
        for i in range(len(recent) - 3):  # Need 3 bars after to check retest
            bar = recent.iloc[i]
            
            # Strong bullish candle criteria
            body = bar['close'] - bar['open']
            full_range = bar['high'] - bar['low']
            
            if full_range == 0:
                continue
                
            body_pct = (body / full_range) * 100
            move_pct = (body / bar['open']) * 100
            
            # Strong bullish move: body >50% of range, move >0.2% (more lenient for Bitcoin)
            if body > 0 and body_pct > 50 and move_pct > 0.2:
                mitigation_low = float(bar['low'])
                mitigation_high = float(bar['close'])  # Use close for bullish
                
                # Check if price is APPROACHING this zone (within 3%)
                distance_pct = ((current_price - mitigation_high) / current_price) * 100
                
                # Signal when price is above zone AND approaching (within 10%)
                if current_price > mitigation_high and distance_pct < 10.0:
                    return {
                        'type': 'BULLISH_MITIGATION',
                        'mitigation_high': mitigation_high,
                        'mitigation_low': mitigation_low,
                        'gap_size': mitigation_high - mitigation_low,
                        'gap_pct': round(move_pct, 3),
                        'current_price': current_price,
                        'distance_pct': round(((current_price - mitigation_high) / current_price) * 100, 2),
                        'timestamp': df['timestamp'].iloc[-1],
                        'bars_ago': len(recent) - i - 1
                    }
        
        return None
    
    def detect_bearish_mitigation(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Detect bearish mitigation zone (unfilled sell orders above)
        
        CRITICAL FIX for Bitcoin: Traditional gaps rare in 24/7 crypto markets.
        Instead, detect:
        1. Strong bearish impulse candles (institutional selling)
        2. Areas not yet retested (mitigation pending)
        3. Imbalances in price action
        """
        if len(df) < self.lookback:
            return None
        
        recent = df.tail(self.lookback)
        current_price = float(df['close'].iloc[-1])
        
        # Look for strong bearish candles that created mitigation zones
        for i in range(len(recent) - 3):  # Need 3 bars after to check retest
            bar = recent.iloc[i]
            
            # Strong bearish candle criteria
            body = bar['open'] - bar['close']  # Bearish body
            full_range = bar['high'] - bar['low']
            
            if full_range == 0:
                continue
                
            body_pct = (body / full_range) * 100
            move_pct = (body / bar['open']) * 100
            
            # Strong bearish move: body >50% of range, move >0.2% (more lenient for Bitcoin)
            if body > 0 and body_pct > 50 and move_pct > 0.2:
                mitigation_high = float(bar['high'])
                mitigation_low = float(bar['close'])  # Use close for bearish
                
                # Check if price is APPROACHING this zone (within 3%)
                distance_pct = ((mitigation_low - current_price) / current_price) * 100
                
                # Signal when price is below zone AND approaching (within 10%)
                if current_price < mitigation_low and distance_pct < 10.0:
                    return {
                        'type': 'BEARISH_MITIGATION',
                        'mitigation_high': mitigation_high,
                        'mitigation_low': mitigation_low,
                        'gap_size': mitigation_high - mitigation_low,
                        'gap_pct': round(move_pct, 3),
                        'current_price': current_price,
                        'distance_pct': round(((mitigation_low - current_price) / current_price) * 100, 2),
                        'timestamp': df['timestamp'].iloc[-1],
                        'bars_ago': len(recent) - i - 1
                    }
        
        return None
    
    def check_mtf_mitigation(self, df: pd.DataFrame, mitigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ENHANCEMENT 1: Multi-Timeframe Mitigation (2026-01-04)
        Check multiple timeframes for mitigation alignment
        """
        if len(df) < 200:  # Need enough data for higher TFs
            return {'has_mtf': False}
        
        mitigation_type = mitigation_data['type']
        current_price = mitigation_data['current_price']
        
        # Create synthetic higher timeframes by resampling
        # Short TF: 20-bar lookback (5 hours on 15min)
        # Medium TF: 60-bar lookback (15 hours on 15min)
        # Long TF: 100-bar lookback (25 hours on 15min)
        
        short_tf = df.tail(20)
        medium_tf = df.tail(60)
        long_tf = df.tail(100)
        
        mtf_signals = []
        
        # Check each timeframe for mitigation in same direction
        for tf_name, tf_data in [('short', short_tf), ('medium', medium_tf), ('long', long_tf)]:
            if mitigation_type == 'BULLISH_MITIGATION':
                tf_mit = self.detect_bullish_mitigation(tf_data)
            else:
                tf_mit = self.detect_bearish_mitigation(tf_data)
            
            if tf_mit:
                mtf_signals.append(tf_name)
        
        has_mtf = len(mtf_signals) >= 2  # At least 2 TFs aligned
        all_tf_aligned = len(mtf_signals) == 3  # All 3 TFs aligned
        
        return {
            'has_mtf': has_mtf,
            'all_tf_aligned': all_tf_aligned,
            'aligned_timeframes': mtf_signals,
            'alignment_count': len(mtf_signals)
        }
    
    def calculate_strength_score(self, df: pd.DataFrame, mitigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ENHANCEMENT 2: Mitigation Strength Scoring (2026-01-04)
        Score based on gap size, volume, and age
        """
        if 'volume' not in df.columns:
            return {'strength_score': 50, 'strength_rating': 'MODERATE'}
        
        # 1. Gap Size Score (0-40 points)
        gap_pct = mitigation_data['gap_pct']
        if gap_pct > 1.0:
            gap_score = 40
        elif gap_pct > 0.5:
            gap_score = 30
        elif gap_pct > 0.3:
            gap_score = 20
        else:
            gap_score = 10
        
        # 2. Volume Score (0-30 points) - higher volume = stronger
        bars_ago = mitigation_data.get('bars_ago', 10)
        if bars_ago < len(df):
            mit_bar_idx = len(df) - bars_ago - 1
            mit_volume = df['volume'].iloc[mit_bar_idx]
            avg_volume = df['volume'].tail(50).mean()
            
            volume_ratio = mit_volume / avg_volume if avg_volume > 0 else 1.0
            
            if volume_ratio > 2.0:
                volume_score = 30
            elif volume_ratio > 1.5:
                volume_score = 20
            elif volume_ratio > 1.0:
                volume_score = 15
            else:
                volume_score = 5
        else:
            volume_score = 15  # Default
        
        # 3. Age Score (0-30 points) - fresher = stronger
        if bars_ago <= 5:
            age_score = 30
        elif bars_ago <= 10:
            age_score = 20
        elif bars_ago <= 15:
            age_score = 10
        else:
            age_score = 5
        
        # Total strength score
        total_score = gap_score + volume_score + age_score
        
        # Rating
        if total_score >= 80:
            rating = 'VERY_STRONG'
        elif total_score >= 60:
            rating = 'STRONG'
        elif total_score >= 40:
            rating = 'MODERATE'
        else:
            rating = 'WEAK'
        
        return {
            'strength_score': total_score,
            'strength_rating': rating,
            'gap_score': gap_score,
            'volume_score': volume_score,
            'age_score': age_score
        }
    
    def update_fill_history(self, df: pd.DataFrame, mitigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ENHANCEMENT 3: Historical Fill Rate (2026-01-04)
        Track if mitigation zones get filled
        """
        current_price = float(df['close'].iloc[-1])
        mit_high = mitigation_data['mitigation_high']
        mit_low = mitigation_data['mitigation_low']
        
        # Check if we've filled any historical mitigations
        fills_detected = 0
        for hist_mit in self.mitigation_history:
            if not hist_mit.get('filled', False):
                # Check if current price filled this mitigation
                if hist_mit['type'] == 'BULLISH_MITIGATION':
                    if current_price <= hist_mit['mitigation_high']:
                        hist_mit['filled'] = True
                        fills_detected += 1
                else:  # BEARISH
                    if current_price >= hist_mit['mitigation_low']:
                        hist_mit['filled'] = True
                        fills_detected += 1
        
        # Add current mitigation to history
        self.mitigation_history.append({
            'type': mitigation_data['type'],
            'mitigation_high': mit_high,
            'mitigation_low': mit_low,
            'timestamp': mitigation_data['timestamp'],
            'filled': False
        })
        
        # Keep only recent history
        if len(self.mitigation_history) > self.max_history:
            self.mitigation_history.pop(0)
        
        # Calculate fill rate
        if len(self.mitigation_history) >= 5:
            filled_count = sum(1 for m in self.mitigation_history if m.get('filled', False))
            fill_rate = (filled_count / len(self.mitigation_history)) * 100
            
            return {
                'has_history': True,
                'fill_rate': round(fill_rate, 1),
                'sample_size': len(self.mitigation_history),
                'filled_count': filled_count
            }
        else:
            return {
                'has_history': False,
                'fill_rate': None,
                'sample_size': len(self.mitigation_history)
            }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method - tracks both CONTINUOUS approach state and NEW zone entries (ENHANCED 2026-01-04)"""
        if not all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns (need open, high, low, close, timestamp)', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback + 5:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': f'Need at least {self.lookback + 5} bars', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect mitigation zones
        bullish_mit = self.detect_bullish_mitigation(df)
        bearish_mit = self.detect_bearish_mitigation(df)
        
        # Choose active mitigation (prefer closest)
        active_mit = None
        signal = 'NEUTRAL'  # confidence = 60 for valid signal
        
        if bullish_mit and bearish_mit:
            # Choose closest one
            if bullish_mit['distance_pct'] < bearish_mit['distance_pct']:
                active_mit = bullish_mit
                signal = 'BULLISH'  # confidence = 60 for valid signal
            else:
                active_mit = bearish_mit
                signal = 'BEARISH'  # confidence = 60 for valid signal
        elif bullish_mit:
            active_mit = bullish_mit
            signal = 'BULLISH'  # confidence = 60 for valid signal
        elif bearish_mit:
            active_mit = bearish_mit
            signal = 'BEARISH'  # confidence = 60 for valid signal
        
        if not active_mit:
            granular_signal, simple_signal = self._determine_dual_signals('NEUTRAL')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'message': 'No mitigation zones detected',
                    'is_new_event': False
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': ['No unfilled gaps - clean price action']
            }
        
        # **NEW:** Event tracking - detect when price ENTERS approach zone
        is_new_event = False
        bars_in_approach = 0
        
        # Check if we just started approaching (wasn't approaching last bar, is now)
        if len(df) > self.lookback + 6:
            # Check previous bar's state
            prev_bullish = self.detect_bullish_mitigation(df.iloc[:-1])
            prev_bearish = self.detect_bearish_mitigation(df.iloc[:-1])
            
            # Determine if previous bar had ANY mitigation signal
            had_prev_signal = (prev_bullish is not None or prev_bearish is not None)
            
            # New event if we NOW have signal but DIDN'T before
            is_new_event = not had_prev_signal
            
            # If continuing, approximate bars in approach
            if not is_new_event:
                bars_in_approach = 1  # At least 1 bar approaching
        
        # ENHANCEMENT 1: Check multi-timeframe alignment
        mtf_data = self.check_mtf_mitigation(df, active_mit)
        
        # ENHANCEMENT 2: Calculate strength score
        strength_data = self.calculate_strength_score(df, active_mit)
        
        # ENHANCEMENT 3: Update historical fill rate
        fill_data = self.update_fill_history(df, active_mit)
        
        # Calculate confidence based on gap size and distance (ENHANCED)
        confidence = 70  # Base confidence for mitigation
        if active_mit['gap_pct'] > 0.5:
            confidence += 10
        if active_mit['distance_pct'] < 2.0:
            confidence += 15  # Very close
        elif active_mit['distance_pct'] < 5.0:
            confidence += 10  # Close
        
        # Fresh approach boost
        if is_new_event:
            confidence += 5
        
        # ENHANCEMENT BONUSES
        if mtf_data.get('all_tf_aligned'):
            confidence += 10  # All timeframes aligned
        elif mtf_data.get('has_mtf'):
            confidence += 5  # Some timeframes aligned
        
        if strength_data['strength_rating'] == 'VERY_STRONG':
            confidence += 10
        elif strength_data['strength_rating'] == 'STRONG':
            confidence += 5
        
        if fill_data.get('has_history') and fill_data['fill_rate'] >= 70:
            confidence += 5  # High historical fill rate
        
        confidence = min(100, confidence)
        
        # Build confluence factors (ENHANCED)
        confluence_factors = []
        
        # Event-specific confluence
        if is_new_event:
            if signal == 'BULLISH':
                confluence_factors.append('⭐ NEW BULLISH MITIGATION APPROACH (fresh retracement opportunity!)')
            else:
                confluence_factors.append('⭐ NEW BEARISH MITIGATION APPROACH (fresh retracement opportunity!)')
        elif bars_in_approach > 0:
            confluence_factors.append(f'Continuing approach to mitigation ({bars_in_approach} bars)')
        
        confluence_factors.append(f'Mitigation Type: {active_mit["type"]}')
        confluence_factors.append(f'Zone: ${active_mit["mitigation_low"]:.2f} - ${active_mit["mitigation_high"]:.2f}')
        confluence_factors.append(f'Gap Size: {active_mit["gap_pct"]:.3f}%')
        confluence_factors.append(f'Distance: {active_mit["distance_pct"]:.2f}%')
        
        # ENHANCEMENT 1: MTF confluence
        if mtf_data.get('all_tf_aligned'):
            confluence_factors.append(f'MTF: ALL {mtf_data["alignment_count"]} timeframes aligned (+10 confidence)')
        elif mtf_data.get('has_mtf'):
            confluence_factors.append(f'MTF: {mtf_data["alignment_count"]} timeframes aligned (+5 confidence)')
        
        # ENHANCEMENT 2: Strength confluence
        confluence_factors.append(f'Strength: {strength_data["strength_rating"]} (score: {strength_data["strength_score"]}/100)')
        
        # ENHANCEMENT 3: Historical fill rate
        if fill_data.get('has_history'):
            confluence_factors.append(f'Historical fill rate: {fill_data["fill_rate"]}% ({fill_data["filled_count"]}/{fill_data["sample_size"]})')
        
        confluence_factors.append('Unfilled institutional orders - expect retracement')
        confluence_factors.append('High probability entry on mitigation')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(active_mit['type'])
        
        # Metadata (ENHANCED)
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'mitigation_type': active_mit['type'],
            'mitigation_high': active_mit['mitigation_high'],
            'mitigation_low': active_mit['mitigation_low'],
            'gap_size': active_mit['gap_size'],
            'gap_pct': active_mit['gap_pct'],
            'current_price': active_mit['current_price'],
            'distance_pct': active_mit['distance_pct'],
            'mitigation_timestamp': active_mit['timestamp'],
            'is_new_event': is_new_event,
            'bars_in_approach': bars_in_approach,
            # ENHANCEMENTS
            'has_mtf_alignment': mtf_data.get('has_mtf', False),
            'all_tf_aligned': mtf_data.get('all_tf_aligned', False),
            'aligned_timeframes': mtf_data.get('aligned_timeframes', []),
            'strength_score': strength_data['strength_score'],
            'strength_rating': strength_data['strength_rating'],
            'has_fill_history': fill_data.get('has_history', False),
            'historical_fill_rate': fill_data.get('fill_rate'),
            'fill_sample_size': fill_data.get('sample_size', 0)
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
