"""
Swing Point Identification Building Block - ENHANCED
Category: Market Structure (Reference/Metadata Block)
Purpose: Identifies significant swing highs and lows with strength scoring

ENHANCED VERSION (2026-01-03):
- Variable confidence based on swing strength
- Integration with quality blocks (ATR, Volume)
- Major/minor swing classification
- Event tracking
- Institutional-grade assessment
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous swing high/low tracking

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np

from src.detectors.building_blocks.registry import register_block


@register_block(
    name='swing_points',
    category='MARKET_STRUCTURE',
    class_name='SwingPoints',
    default_weight=15,
    valid_signals=[
        # Swing events - GRANULAR
        'SWING_HIGH_DETECTED', 'SWING_LOW_DETECTED', 'MINOR_SWING_HIGH_DETECTED', 'MINOR_SWING_LOW_DETECTED', 'MAJOR_SWING_HIGH_DETECTED', 'MAJOR_SWING_LOW_DETECTED', 'NO_SWINGS',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'INSUFFICIENT_DATA', 'ERROR'
    ],
    signal_tiers={
        # Major swings - Rare, high-strength (80+) - Booster quality
        'MAJOR_SWING_HIGH_DETECTED': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Major swing high (strength 80+) - strong resistance zone'
        },
        'MAJOR_SWING_LOW_DETECTED': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Major swing low (strength 80+) - strong support zone'
        },
        
        # Regular swings - Medium strength (40-79) - Primary component
        'SWING_HIGH_DETECTED': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Regular swing high (strength 40-79) - resistance zone'
        },
        'SWING_LOW_DETECTED': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Regular swing low (strength 40-79) - support zone'
        },
        
        # Minor swings - Low strength (<40) - Confirmation only
        'MINOR_SWING_HIGH_DETECTED': {
            'base_points': 12,
            'formula': 'scaled',
            'description': 'Minor swing high (strength <40) - weak resistance'
        },
        'MINOR_SWING_LOW_DETECTED': {
            'base_points': 12,
            'formula': 'scaled',
            'description': 'Minor swing low (strength <40) - weak support'
        },
        
        # Status signals
        'NO_SWINGS': {
            'points': 0,
            'description': 'No swing points detected'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Swing low detected - bullish (simple)'
        },
        'BEARISH': {
            'base_points': 18,
            'formula': 'scaled',
            'description': 'Swing high detected - bearish (simple)'
        },
        'NEUTRAL': {
            'base_points': 10,
            'formula': 'scaled',
            'description': 'No swings - neutral (simple)'
        },
        
        'ERROR': {
            'points': 0,
            'description': 'Analysis error occurred'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'description': 'Not enough data for analysis'
        }
    },
    description='Swing Points - Identifies swing highs/lows with strength-based scoring and major/minor classification',
    tags=['market_structure', 'swing_points', 'support_resistance', 'pivot', 'context_block']
)
class SwingPoints:
    """
    Identifies swing highs and lows with strength-based confidence
    
    ENHANCEMENTS:
    - Swing strength scoring (0-100) based on:
      * Magnitude (price distance)
      * Confirmation (bars confirming)
      * Volume (spike confirmation)
    - Variable confidence (55-85% based on strength)
    - Major/minor classification
    - Event tracking (new swings vs continuing)
    - ATR integration for normalized magnitude
    """
    
    def __init__(self, timeframe: str = '15min', lookback: int = 5, **kwargs):
        """
        Initialize Swing Points Detector
        
        Args:
            timeframe: Timeframe string
            lookback: Bars on each side to confirm swing (default 5)
        """
        self.timeframe = timeframe
        self.lookback = lookback
        self.last_swing_idx = None
        self.last_swing_type = None
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for magnitude normalization"""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        
        atr = np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
        return float(atr)
    
    def calculate_swing_strength(self, df: pd.DataFrame, swing_idx: int, 
                                 swing_type: str, atr: float) -> int:
        """
        Calculate swing strength 0-100 using quality block principles
        
        Factors:
        1. Magnitude (40 pts): Price distance normalized by ATR
        2. Confirmation (30 pts): Number of bars confirming swing
        3. Volume (30 pts): Volume spike at swing
        """
        strength_score = 0
        current_price = df['high'].iloc[swing_idx] if swing_type == 'HIGH' else df['low'].iloc[swing_idx]
        
        # FACTOR 1: Magnitude (0-40 points) - ATR normalized
        if atr > 0:
            # Get recent opposite swings for comparison
            lookback_range = min(50, swing_idx)
            if lookback_range > self.lookback * 2:
                if swing_type == 'HIGH':
                    # Distance from recent lows
                    recent_lows = df['low'].iloc[max(0, swing_idx-lookback_range):swing_idx]
                    if len(recent_lows) > 0:
                        magnitude = current_price - recent_lows.min()
                else:
                    # Distance from recent highs
                    recent_highs = df['high'].iloc[max(0, swing_idx-lookback_range):swing_idx]
                    if len(recent_highs) > 0:
                        magnitude = recent_highs.max() - current_price
                
                # Normalize by ATR (typical swing = 2-5 ATR)
                magnitude_in_atr = magnitude / atr if atr > 0 else 0
                magnitude_score = min(40, int(magnitude_in_atr * 8))  # 5 ATR = 40 points
                strength_score += magnitude_score
        
        # FACTOR 2: Confirmation bars (0-30 points)
        # How many bars on each side confirm this swing
        left_bars = min(self.lookback, swing_idx)
        right_bars = min(self.lookback, len(df) - swing_idx - 1)
        
        if swing_type == 'HIGH':
            # Count bars below this high
            left_confirmed = sum(df['high'].iloc[swing_idx-left_bars:swing_idx] < current_price)
            right_confirmed = sum(df['high'].iloc[swing_idx+1:swing_idx+right_bars+1] < current_price)
        else:
            # Count bars above this low
            left_confirmed = sum(df['low'].iloc[swing_idx-left_bars:swing_idx] > current_price)
            right_confirmed = sum(df['low'].iloc[swing_idx+1:swing_idx+right_bars+1] > current_price)
        
        total_confirmed = left_confirmed + right_confirmed
        max_possible = left_bars + right_bars
        confirmation_score = int((total_confirmed / max_possible) * 30) if max_possible > 0 else 0
        strength_score += confirmation_score
        
        # FACTOR 3: Volume (0-30 points)
        # Volume spike at swing indicates significance
        if 'volume' in df.columns:
            swing_volume = df['volume'].iloc[swing_idx]
            
            # Average volume (20-bar window)
            vol_window = min(20, swing_idx)
            if vol_window > 0:
                avg_volume = df['volume'].iloc[max(0, swing_idx-vol_window):swing_idx].mean()
                
                if avg_volume > 0:
                    volume_ratio = swing_volume / avg_volume
                    # Volume spike: 1.5x = 15pts, 2.0x = 30pts
                    volume_score = min(30, int((volume_ratio - 1.0) * 60))
                    volume_score = max(0, volume_score)
                    strength_score += volume_score
        
        return min(100, max(0, strength_score))
    
    def calculate_variable_confidence(self, strength: int) -> int:
        """
        Map swing strength to confidence level
        
        Institutional-grade confidence ranges:
        - Major swing (80+): 85% confidence - booster role
        - Strong swing (60-79): 75% confidence - primary component
        - Average swing (40-59): 65% confidence - confirmation
        - Minor swing (<40): 55% confidence - weak signal
        """
        if strength >= 80:
            return 85  # Major swing
        elif strength >= 60:
            return 75  # Strong swing
        elif strength >= 40:
            return 65  # Average swing
        else:
            return 55  # Minor swing
    
    def classify_swing(self, strength: int, swing_type: str) -> str:
        """Classify swing as MAJOR/NORMAL/MINOR"""
        prefix = ''
        if strength >= 80:
            prefix = 'MAJOR_'
        elif strength < 40:
            prefix = 'MINOR_'
        
        return f"{prefix}SWING_{swing_type}_DETECTED"
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method with ENHANCED strength assessment
        
        Returns swing points with:
        - Variable confidence (55-85%)
        - Strength scoring (0-100)
        - Major/minor classification
        - Event tracking
        """
        # Validation
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback * 2 + 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate ATR for magnitude normalization (quality block integration!)
        atr = self.calculate_atr(df, period=14)
        
        # Find all swings
        swings = []
        for i in range(self.lookback, len(df) - self.lookback):
            # Swing high: highest point in window
            if df['high'].iloc[i] == df['high'].iloc[i-self.lookback:i+self.lookback+1].max():
                strength = self.calculate_swing_strength(df, i, 'HIGH', atr)
                swings.append({
                    'type': 'HIGH',
                    'price': float(df['high'].iloc[i]),
                    'idx': i,
                    'strength': strength,
                    'timestamp': df['timestamp'].iloc[i]
                })
            
            # Swing low: lowest point in window
            elif df['low'].iloc[i] == df['low'].iloc[i-self.lookback:i+self.lookback+1].min():
                strength = self.calculate_swing_strength(df, i, 'LOW', atr)
                swings.append({
                    'type': 'LOW',
                    'price': float(df['low'].iloc[i]),
                    'idx': i,
                    'strength': strength,
                    'timestamp': df['timestamp'].iloc[i]
                })
        
        # Get last swing
        if swings:
            last_swing = swings[-1]
            swing_type = last_swing['type']
            swing_strength = last_swing['strength']
            
            # Variable confidence based on strength!
            confidence = self.calculate_variable_confidence(swing_strength)
            
            # Classify swing (major/normal/minor)
            signal = self.classify_swing(swing_strength, swing_type)
            
            # Event tracking: is this a NEW swing?
            is_new_event = (
                self.last_swing_idx != last_swing['idx'] or
                self.last_swing_type != swing_type
            )
            
            bars_since_last = len(df) - last_swing['idx'] - 1
            
            # Update tracking
            self.last_swing_idx = last_swing['idx']
            self.last_swing_type = swing_type
            
            # Confluence factors
            confluence_factors = [
                f"{signal.replace('_DETECTED', '')} at ${last_swing['price']:.2f}",
                f"Strength: {swing_strength}/100"
            ]
            
            if swing_strength >= 80:
                confluence_factors.append("⭐ MAJOR swing - booster quality!")
            elif swing_strength >= 60:
                confluence_factors.append("💪 Strong swing - primary component")
            elif swing_strength < 40:
                confluence_factors.append("⚠️ Minor swing - confirmation only")
            
            if is_new_event:
                confluence_factors.append(f"🆕 NEW swing detected")
            
            # Rich metadata for other blocks and confluence
            metadata = {
                'swing_count': len(swings),
                'swing_type': swing_type,
                'swing_price': last_swing['price'],
                'swing_strength': swing_strength,
                'swing_classification': 'MAJOR' if swing_strength >= 80 else 'STRONG' if swing_strength >= 60 else 'AVERAGE' if swing_strength >= 40 else 'MINOR',
                'is_new_event': is_new_event,
                'bars_since_swing': bars_since_last,
                'atr_value': round(atr, 2),
                'recent_swings': swings[-3:] if len(swings) >= 3 else swings,
                'last_swing_high': next((s['price'] for s in reversed(swings) if s['type'] == 'HIGH'), None),
                'last_swing_low': next((s['price'] for s in reversed(swings) if s['type'] == 'LOW'), None),
            }
            
        else:
            # No swings detected (rare)
            signal = 'NO_SWINGS'
            confidence = 30
            confluence_factors = ['No swing points detected in recent history']
            is_new_event = False
            metadata = {
                'swing_count': 0,
                'is_new_event': False
            }
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
