"""
Wyckoff Distribution Phase Detector
Category: Wyckoff Method
Purpose: Identifies distribution phases (smart money selling to retail at tops)

Improved implementation matching Accumulation quality:
- Volume analysis (critical for Wyckoff)
- Range detection with realistic thresholds
- UTAD pattern detection (Phase C) - false breakout above
- Sign of Weakness detection (Phase D) - volume breakdown
- Phase tracking (A, B, C, D, NONE)
- Optimized for 2HR/4HR Bitcoin (lessons from Accumulation)
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class WyckoffDistribution:
    """
    Detects Wyckoff distribution phases using proper methodology
    Mirror of Accumulation but reversed (tops instead of bottoms)
    
    Phases:
    A: Buying climax (high volume euphoria)
    B: Range building (consolidation at top)
    C: UTAD (Upthrust After Distribution - false breakout above)
    D: Sign of Weakness (volume breakdown)
    NONE: Not in distribution
    """
    
    def __init__(self, timeframe: str = '15min', 
                 range_lookback: int = 50,           # Optimized for 2HR/4HR
                 volume_lookback: int = 50,
                 range_threshold_pct: float = 5.0,   # Tight range for true consolidation
                 utad_breakout_pct: float = 2.0,     # False breakout threshold
                 utad_volume_ratio: float = 0.90,    # Lower volume on UTAD (weak)
                 sow_breakdown_pct: float = 2.0,     # Breakdown threshold
                 sow_volume_ratio: float = 1.15,     # High volume on SOW (strong)
                 **kwargs):
        self.timeframe = timeframe
        self.range_lookback = range_lookback
        self.volume_lookback = volume_lookback
        self.range_threshold_pct = range_threshold_pct
        self.utad_breakout_pct = utad_breakout_pct
        self.utad_volume_ratio = utad_volume_ratio
        self.sow_breakdown_pct = sow_breakdown_pct
        self.sow_volume_ratio = sow_volume_ratio
    
    def detect_buying_climax(self, df: pd.DataFrame) -> tuple:
        """
        Detect buying climax (Phase A):
        - Very high volume (2x+ avg)
        - Highest high in recent period
        - Sharp reversal downward
        """
        if len(df) < self.volume_lookback:
            return False, 0
        
        volume_avg = df['volume'].iloc[-self.volume_lookback:].mean()
        recent_volume = df['volume'].iloc[-5:].max()
        
        # High volume spike (2x average) - retail euphoria
        high_volume = recent_volume > volume_avg * 2.0
        
        # Highest high in recent period
        recent_high = df['high'].iloc[-20:].max()
        is_highest = recent_high == df['high'].iloc[-self.volume_lookback:].max()
        
        # Reversal (close below high) - rejection
        if len(df) >= 5:
            reversal = df['close'].iloc[-1] < df['high'].iloc[-5:].max() * 0.98
        else:
            reversal = False
        
        if high_volume and is_highest:
            confidence = 85 if reversal else 75
            return True, confidence
        
        return False, 0
    
    def detect_range(self, df: pd.DataFrame) -> tuple:
        """
        Detect if price is in distribution range (Phase B):
        - Price consolidating at top (range < 5% of price)
        - Duration: at least 20 bars
        - Volume drops on rallies (smart money distributing quietly)
        """
        if len(df) < self.range_lookback:
            return False, 0, 0
        
        # Calculate range
        range_high = df['high'].iloc[-self.range_lookback:].max()
        range_low = df['low'].iloc[-self.range_lookback:].min()
        range_size = range_high - range_low
        current_price = df['close'].iloc[-1]
        
        # Range as percentage of price
        range_pct = (range_size / current_price) * 100
        
        # In consolidation if range < threshold (optimized for 2HR/4HR)
        in_range = range_pct < self.range_threshold_pct
        
        # Check volume declining on rallies (sign of distribution)
        volume_recent = df['volume'].iloc[-20:].mean()
        volume_earlier = df['volume'].iloc[-self.range_lookback:-20].mean()
        volume_declining = volume_recent < volume_earlier * 0.9
        
        if in_range:
            # Higher confidence if volume declining
            confidence = 70 if volume_declining else 60
            return True, confidence, range_high
        
        return False, 0, 0
    
    def detect_utad(self, df: pd.DataFrame, resistance_level: float) -> tuple:
        """
        Detect UTAD pattern (Phase C):
        - Price breaks above resistance (false breakout - trap!)
        - Volume on breakout LOWER than average (weak - not institutional)
        - Quick reversal back below resistance
        """
        if len(df) < 10 or resistance_level == 0:
            return False, 0
        
        # Check for breakout above resistance in last 10 bars
        recent_highs = df['high'].iloc[-10:]
        breakout_threshold = 1.0 + (self.utad_breakout_pct / 100.0)
        broke_resistance = recent_highs.max() > resistance_level * breakout_threshold
        
        if not broke_resistance:
            return False, 0
        
        # Volume should be LOWER (weak breakout - trap for retail)
        volume_avg = df['volume'].iloc[-50:-10].mean()
        breakout_volume = df['volume'].iloc[-10:].mean()
        low_volume_breakout = breakout_volume < volume_avg * self.utad_volume_ratio
        
        # Quick reversal back below resistance
        current_price = df['close'].iloc[-1]
        reversed = current_price < resistance_level
        
        if broke_resistance and low_volume_breakout and reversed:
            # UTAD DETECTED - Major shorting opportunity!
            return True, 90
        elif broke_resistance and reversed:
            # Reversed but volume not ideal
            return True, 75
        
        return False, 0
    
    def detect_sign_of_weakness(self, df: pd.DataFrame, support_level: float) -> tuple:
        """
        Detect Sign of Weakness (Phase D):
        - Price breaks below support
        - HIGH volume on breakdown (smart money selling)
        - Sustained move (not false breakdown)
        """
        if len(df) < 10 or support_level == 0:
            return False, 0
        
        # Check for breakdown below support
        recent_lows = df['low'].iloc[-10:]
        breakdown_threshold = 1.0 - (self.sow_breakdown_pct / 100.0)
        broke_support = recent_lows.min() < support_level * breakdown_threshold
        
        if not broke_support:
            return False, 0
        
        # Volume should be HIGH (institutional selling)
        volume_avg = df['volume'].iloc[-50:-10].mean()
        breakdown_volume = df['volume'].iloc[-10:].mean()
        high_volume_breakdown = breakdown_volume > volume_avg * self.sow_volume_ratio
        
        # Sustained move (close below support)
        current_price = df['close'].iloc[-1]
        sustained = current_price < support_level * 0.998
        
        if broke_support and high_volume_breakdown and sustained:
            # SOW DETECTED - Distribution confirmed!
            return True, 85
        elif broke_support and sustained:
            # Breakdown but volume not ideal
            return True, 70
        
        return False, 0
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method - Comprehensive Wyckoff distribution detection
        """
        # Input validation
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.range_lookback:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Detect Wyckoff events
        buying_climax, bc_conf = self.detect_buying_climax(df)
        in_range, range_conf, resistance = self.detect_range(df)
        
        # Calculate support for SOW detection
        support = df['low'].iloc[-self.range_lookback:].min() if in_range else 0
        
        utad, utad_conf = self.detect_utad(df, resistance)
        sow, sow_conf = self.detect_sign_of_weakness(df, support)
        
        # Determine signal and phase
        confluence_factors = []
        
        if utad:
            # UTAD DETECTED - Phase C (Major shorting opportunity!)
            signal = 'UTAD_DETECTED'
            confidence = utad_conf
            phase = 'C'
            confluence_factors.append('⭐ UTAD: False breakout above resistance')
            confluence_factors.append('✅ Quick reversal - retail trapped')
            
        elif sow:
            # SOW DETECTED - Phase D (Breakdown confirmed!)
            signal = 'SOW_BREAKDOWN'
            confidence = sow_conf
            phase = 'D'
            confluence_factors.append('⭐ SOW: Breakdown below support')
            confluence_factors.append('✅ High volume - smart money selling')
            
        elif in_range and buying_climax:
            # PHASE A - Buying climax in range
            signal = 'DISTRIBUTION_PHASE_A'
            confidence = bc_conf
            phase = 'A'
            confluence_factors.append('📈 Buying climax detected')
            confluence_factors.append('📊 High volume euphoria')
            
        elif in_range:
            # PHASE B - Range building at top
            signal = 'DISTRIBUTION_PHASE_B'
            confidence = range_conf
            phase = 'B'
            range_pct = ((resistance - support) / df['close'].iloc[-1]) * 100
            confluence_factors.append(f'📦 Distribution range: {range_pct:.1f}% of price')
            confluence_factors.append('🔇 Volume declining - quiet distribution')
            
        else:
            # NO DISTRIBUTION - Trending or accumulation
            signal = 'NO_DISTRIBUTION'
            confidence = 40
            phase = 'NONE'
            confluence_factors.append('📉 Price trending - not consolidating at top')
            confluence_factors.append('❌ No distribution pattern detected')
        
        # Build metadata
        metadata = {
            'phase': phase,
            'utad_detected': utad,
            'sow_detected': sow,
            'buying_climax': buying_climax,
            'in_range': in_range,
            'resistance_level': float(resistance) if resistance > 0 else 0,
            'support_level': float(support) if support > 0 else 0
        }
        
        return {
            'signal': signal,
            'confidence': int(confidence),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


def analyze_multi_timeframe(df_2hr: pd.DataFrame, df_4hr: pd.DataFrame) -> Dict[str, Any]:
    """
    Production helper for multi-timeframe Wyckoff distribution analysis (2HR + 4HR)
    
    This is the RECOMMENDED way to use Wyckoff Distribution in production.
    
    Args:
        df_2hr: 2-hour OHLCV dataframe (PRIMARY timeframe)
        df_4hr: 4-hour OHLCV dataframe (CONFIRMATION timeframe)
    
    Returns:
        dict with:
            - confluence: Total confluence points (20-155)
            - notes: List of analysis notes
            - 2hr_result: Full 2HR analysis result
            - 4hr_result: Full 4HR analysis result
            - mtf_aligned: Boolean if both timeframes agree
    
    Usage Example:
        result = analyze_multi_timeframe(df_2hr, df_4hr)
        total_confluence += result['confluence']
        notes.extend(result['notes'])
        
        if result['mtf_aligned']:
            print("🎯 Multi-timeframe distribution alignment detected!")
    """
    confluence = 0
    notes = []
    
    # === ANALYZE 2HR (PRIMARY) ===
    wyckoff_2hr = WyckoffDistribution(timeframe='2hr')
    result_2hr = wyckoff_2hr.analyze(df_2hr)
    
    # Add 2HR confluence
    if result_2hr['metadata']['phase'] == 'A':
        # Buying climax (rare on 2HR)
        confluence += 55
        notes.append('⭐ Wyckoff 2HR Phase A: Buying Climax - Top Zone')
        
    elif result_2hr['metadata']['phase'] == 'B':
        # Distribution range
        confluence += 45
        notes.append('⭐ Wyckoff 2HR Phase B: Distribution Range')
        
    elif result_2hr['metadata']['phase'] == 'C':
        # UTAD (critical shorting signal!)
        confluence += 65
        notes.append('🚨 Wyckoff 2HR Phase C: UTAD - MAJOR SHORT SIGNAL!')
        
    elif result_2hr['metadata']['phase'] == 'D':
        # SOW (breakdown confirmed)
        confluence += 60
        notes.append('⭐ Wyckoff 2HR Phase D: SOW - Weakness Confirmed')
        
    elif result_2hr['signal'] == 'NO_DISTRIBUTION':
        # Trending (not at top)
        confluence += 20
        notes.append('📉 Wyckoff 2HR: Trending Market')
    
    # === ANALYZE 4HR (CONFIRMATION) ===
    wyckoff_4hr = WyckoffDistribution(timeframe='4hr')
    result_4hr = wyckoff_4hr.analyze(df_4hr)
    
    # Add 4HR confirmation bonus
    if result_4hr['metadata']['phase'] == 'C':
        # UTAD on 4HR (very rare, mega signal!)
        confluence += 40
        notes.append('✅ Wyckoff 4HR CONFIRMS: UTAD - TRUE TOP!')
        
    elif result_4hr['metadata']['phase'] == 'D':
        # SOW on 4HR (rare confirmation)
        confluence += 35
        notes.append('✅ Wyckoff 4HR CONFIRMS: SOW - Major Weakness')
        
    elif result_4hr['metadata']['phase'] == 'B':
        # Distribution range on 4HR
        confluence += 30
        notes.append('✅ Wyckoff 4HR CONFIRMS: Distribution Range')
        
    elif result_4hr['metadata']['phase'] == 'A':
        # Buying climax on 4HR (very rare)
        confluence += 40
        notes.append('✅ Wyckoff 4HR CONFIRMS: Major Buying Climax')
    
    # === MULTI-TIMEFRAME ALIGNMENT BONUS ===
    mtf_aligned = False
    if (result_2hr['metadata']['phase'] in ['A', 'B', 'C', 'D'] and 
        result_4hr['metadata']['phase'] == result_2hr['metadata']['phase']):
        # Both timeframes in same phase!
        confluence += 50
        notes.append(f"🎯 MTF ALIGNMENT: Both 2HR & 4HR in Phase {result_2hr['metadata']['phase']}!")
        mtf_aligned = True
    
    return {
        'confluence': confluence,
        'notes': notes,
        '2hr_result': result_2hr,
        '4hr_result': result_4hr,
        'mtf_aligned': mtf_aligned,
        '2hr_phase': result_2hr['metadata']['phase'],
        '4hr_phase': result_4hr['metadata']['phase']
    }
