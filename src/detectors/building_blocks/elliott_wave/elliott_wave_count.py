"""
Elliott Wave Count Building Block
Category: Elliott Wave Pattern Recognition
Purpose: Identifies 5-wave impulse and 3-wave corrective patterns
Multi-Timeframe Enhanced: Uses HTF for context, LTF for timing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class ElliottWaveCount:
    """
    Elliott Wave Pattern Detector (Multi-Timeframe Enhanced)
    
    Identifies wave structures for institutional-grade analysis
    
    Single Timeframe Mode (use_mtf=False):
    - Analyzes given timeframe only
    - Confidence: 40-80%
    - Use: Basic wave detection
    
    Multi-Timeframe Mode (use_mtf=True):
    - Analyzes Daily + 4H + 15min
    - Confidence: 70-95%
    - Booster: +30-75 points
    - Use: High-conviction mega booster
    
    Success rate: High when properly identified (higher with MTF)
    """
    
    def __init__(self, timeframe: str = '15min', use_mtf: bool = True, **kwargs):
        self.timeframe = timeframe
        self.use_mtf = use_mtf
    
    def find_pivots(self, df: pd.DataFrame, lookback: int = 5) -> List[Dict]:
        """Find swing points"""
        pivots = []
        
        for i in range(lookback, len(df) - lookback):
            # Swing high
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                pivots.append({
                    'idx': i,
                    'price': df['high'].iloc[i],
                    'type': 'HIGH',
                    'timestamp': df['timestamp'].iloc[i]
                })
            # Swing low
            elif df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                pivots.append({
                    'idx': i,
                    'price': df['low'].iloc[i],
                    'type': 'LOW',
                    'timestamp': df['timestamp'].iloc[i]
                })
        
        return pivots
    
    def analyze_single_timeframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze single timeframe (original logic)"""
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        pivots = self.find_pivots(df)
        
        if len(pivots) < 6:
            return {
                'signal': 'NO_PATTERN',
                'confidence': 0,
                'metadata': {},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Simplified wave detection - look for 5-wave structure
        recent_pivots = pivots[-6:]
        
        # Check for alternating highs/lows
        wave_structure = [p['type'] for p in recent_pivots]
        
        # Bullish 5-wave: LOW, HIGH, LOW, HIGH, LOW, HIGH
        if len(wave_structure) == 6 and wave_structure == ['LOW', 'HIGH', 'LOW', 'HIGH', 'LOW', 'HIGH']:
            wave_3_size = recent_pivots[3]['price'] - recent_pivots[2]['price']
            wave_1_size = recent_pivots[1]['price'] - recent_pivots[0]['price']
            
            # Wave 3 should be longer than wave 1
            if wave_3_size > wave_1_size:
                signal = 'WAVE_5_FORMING'
                confidence = 80
                
                confluence_factors = []
                confluence_factors.append("5-wave impulse pattern detected")
                confluence_factors.append(f"Wave 3 larger than Wave 1 (valid)")
                confluence_factors.append("Wave 5 forming - potential top")
                
                metadata = {
                    'pattern_type': 'ELLIOTT_5_WAVE',
                    'wave_count': 5,
                    'wave_3_extension': round((wave_3_size / wave_1_size - 1) * 100, 2),
                    'expected_completion': 'Wave 5 near completion'
                }
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'metadata': metadata,
                    'timestamp': df['timestamp'].iloc[-1],
                    'timeframe': self.timeframe,
                    'confluence_factors': confluence_factors
                }
        
        return {
            'signal': 'PATTERN_IN_PROGRESS',
            'confidence': 40,
            'metadata': {'pivot_count': len(recent_pivots)},
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': ['Wave structure developing']
        }
    
    def analyze_multi_timeframe(self, df_4h: pd.DataFrame, df_1d: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze Higher Timeframes for Elliott Wave context
        
        EXPERT MODE: Daily + 4H ONLY (15min removed - too noisy)
        
        REQUIRED Args:
            df_4h: 4H dataframe - REQUIRED
            df_1d: Daily dataframe - REQUIRED
        
        Strategy:
        - Daily (60% weight): PRIMARY context (most significant)
        - 4H (40% weight): INTERMEDIATE confirmation
        
        Why no 15min?
        - 15min Elliott Waves change constantly (noise)
        - Daily + 4H alignment = THE signal
        - Entry timing uses other blocks (better suited)
        
        Returns enhanced signal with MTF confidence and booster value
        
        Raises:
            ValueError: If any required dataframe is None or missing
        """
        # Validate REQUIRED inputs
        if df_4h is None:
            raise ValueError("MTF mode requires df_4h (4H dataframe). Provide actual 4H data or set use_mtf=False")
        if df_1d is None:
            raise ValueError("MTF mode requires df_1d (Daily dataframe). Provide actual Daily data or set use_mtf=False")
        
        # Analyze HTF only (Daily + 4H)
        daily_result = self.analyze_single_timeframe(df_1d)
        h4_result = self.analyze_single_timeframe(df_4h)
        
        # Calculate MTF alignment and confidence (HTF ONLY)
        alignment_score = 40  # Base
        booster_value = 0
        confluence_factors = []
        
        # Check Daily + 4H alignment (HTF focus)
        if daily_result['signal'] == 'WAVE_5_FORMING' and h4_result['signal'] == 'WAVE_5_FORMING':
            alignment_score = 100  # PERFECT
            booster_value = 75  # ULTRA
            confluence_factors.append('ULTRA: Daily + 4H Wave 5 alignment!')
            signal = 'WAVE_5_FORMING_DAILY'
            
        elif daily_result['signal'] == 'WAVE_5_FORMING':
            alignment_score = 85  # STRONG
            booster_value = 50  # MAJOR
            confluence_factors.append('Strong: Daily Wave 5 detected')
            signal = 'WAVE_5_FORMING_DAILY'
            
        elif h4_result['signal'] == 'WAVE_5_FORMING':
            alignment_score = 70  # GOOD
            booster_value = 30  # Strong
            confluence_factors.append('Good: 4H Wave 5 detected')
            signal = 'WAVE_5_FORMING_4H'
            
        else:
            signal = 'PATTERN_IN_PROGRESS'
            confluence_factors.append('No significant HTF wave alignment')
        
        # Calculate weighted MTF confidence (HTF ONLY: Daily 60%, 4H 40%)
        daily_conf = daily_result.get('confidence', 0)
        h4_conf = h4_result.get('confidence', 0)
        
        weighted_conf = (
            daily_conf * 0.6 +   # Daily primary
            h4_conf * 0.4         # 4H confirmation
        )
        
        mtf_confidence = min(95, (alignment_score + weighted_conf) / 2)
        
        # Add timeframe-specific confluence
        if daily_conf > 0:
            confluence_factors.append(f"Daily: {daily_result['signal']} ({daily_conf}%)")
        if h4_conf > 0:
            confluence_factors.append(f"4H: {h4_result['signal']} ({h4_conf}%)")
        if booster_value > 0:
            confluence_factors.append(f"MTF Booster: +{booster_value} points")
        
        # Build metadata
        metadata = {
            'mtf_analysis': True,
            'htf_only': True,  # Indicates HTF focus
            'alignment_score': alignment_score,
            'booster_value': booster_value,
            'daily_signal': daily_result.get('signal'),
            'h4_signal': h4_result.get('signal'),
            'daily_confidence': daily_conf,
            'h4_confidence': h4_conf,
            'timeframes_analyzed': ['1D', '4H']  # HTF only
        }
        
        return {
            'signal': signal,
            'confidence': round(mtf_confidence, 2),
            'booster_value': booster_value,
            'metadata': metadata,
            'timestamp': df_1d['timestamp'].iloc[-1],  # Use Daily timestamp
            'timeframe': 'MTF (Daily+4H)',  # Clearer label
            'confluence_factors': confluence_factors
        }
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Main analysis method
        
        MODE 1 - Single Timeframe (use_mtf=False):
            Args:
                df: Primary dataframe (any timeframe)
            Returns:
                Standard Elliott Wave analysis (40-80% confidence)
        
        MODE 2 - Multi-Timeframe (use_mtf=True):
            Args:
                df: 15min dataframe - REQUIRED
                df_4h: 4H dataframe - REQUIRED (pass via kwargs)
                df_1d: Daily dataframe - REQUIRED (pass via kwargs)
            Returns:
                Enhanced MTF Elliott Wave analysis (70-95% confidence, +30-75 booster)
            Raises:
                ValueError: If df_4h or df_1d not provided when use_mtf=True
        
        Example Single TF:
            ew = ElliottWaveCount(use_mtf=False)
            result = ew.analyze(df_15min)
        
        Example Multi TF:
            ew = ElliottWaveCount(use_mtf=True)
            result = ew.analyze(df_15min, df_4h=df_4h, df_1d=df_1d)
        """
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Route to appropriate analysis method
        if self.use_mtf:
            # MTF MODE - Requires df_4h and df_1d (STRICT)
            df_4h = kwargs.get('df_4h')
            df_1d = kwargs.get('df_1d')
            
            if df_4h is None or df_1d is None:
                raise ValueError(
                    "Multi-Timeframe mode (use_mtf=True) requires both df_4h and df_1d. "
                    f"Got df_4h={'provided' if df_4h is not None else 'MISSING'}, "
                    f"df_1d={'provided' if df_1d is not None else 'MISSING'}. "
                    "Either provide both datasets or set use_mtf=False for single timeframe mode."
                )
            
            # Multi-Timeframe analysis (HTF only: Daily + 4H)
            return self.analyze_multi_timeframe(df_4h, df_1d)
        else:
            # Single Timeframe analysis (original logic)
            return self.analyze_single_timeframe(df)
