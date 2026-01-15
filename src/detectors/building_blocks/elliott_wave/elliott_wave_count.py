"""
Elliott Wave Count Building Block
Category: Elliott Wave Pattern Recognition
Purpose: Identifies 5-wave impulse and 3-wave corrective patterns
Multi-Timeframe Enhanced: Uses HTF for context, LTF for timing

COMPLETE DOCUMENTATION:
    docs/v3/building_blocks/ELLIOTT_WAVE_COUNT_COMPLETE_GUIDE.md
    
    Includes:
    - Wave structure & signals (Wave 1-5)
    - Pivot placement guide
    - Fibonacci integration (entry/exit targets)
    - Trade entry/exit strategies
    - Risk management per wave
    - Real-world examples
    - Common pitfalls & solutions
    - 15min trading using 4H/Daily signals
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Always tracks current wave position (1-5), provides HTF context

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any, List, Optional

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='elliott_wave_count',
    category='ELLIOTT_WAVE',
    class_name='ElliottWaveCount',
    default_weight=22,
    valid_signals=[
        # Wave Position Signals (1-5) - GRANULAR for advanced users
        'WAVE_1_BULLISH', 'WAVE_1_BEARISH',
        'WAVE_2_BULLISH', 'WAVE_2_BEARISH',
        'WAVE_3_BULLISH', 'WAVE_3_BEARISH',
        'WAVE_4_BULLISH', 'WAVE_4_BEARISH',
        'WAVE_5_BULLISH', 'WAVE_5_BEARISH',
        # Simple directional signals - SIMPLE for basic users
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status Signals
        'WAVE_UNCERTAIN', 'INSUFFICIENT_PIVOTS',
        'NO_PATTERN', 'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Wave 5 signals - Highest booster (reversal imminent)
        'WAVE_5_BULLISH': {
            'base_points': 50,
            'formula': 'scaled',
            'description': 'Wave 5 complete (bullish) - Bearish reversal imminent. Take profit on longs. Consider short entry. Stop above Wave 5 high.'
        },
        'WAVE_5_BEARISH': {
            'base_points': 50,
            'formula': 'scaled',
            'description': 'Wave 5 complete (bearish) - Bullish reversal imminent. Take profit on shorts. Consider long entry. Stop below Wave 5 low.'
        },
        
        # Wave 3 signals - Strong trend continuation
        'WAVE_3_BULLISH': {
            'base_points': 40,
            'formula': 'scaled',
            'description': 'Wave 3 bullish - Strongest wave of impulse. Add to longs. Trail stops. Expect extended move. Never fade Wave 3.'
        },
        'WAVE_3_BEARISH': {
            'base_points': 40,
            'formula': 'scaled',
            'description': 'Wave 3 bearish - Strongest wave of impulse. Add to shorts. Trail stops. Expect extended move. Never fade Wave 3.'
        },
        
        # Wave 4 signals - Correction before Wave 5
        'WAVE_4_BULLISH': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Wave 4 correction (bullish) - Shallow pullback. Hold longs, add on dip. Wave 5 final push coming. Stop below Wave 4 low.'
        },
        'WAVE_4_BEARISH': {
            'base_points': 25,
            'formula': 'scaled',
            'description': 'Wave 4 correction (bearish) - Shallow bounce. Hold shorts, add on rally. Wave 5 final push coming. Stop above Wave 4 high.'
        },
        
        # Wave 2 signals - Early correction
        'WAVE_2_BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Wave 2 correction (bullish) - Deep retracement after Wave 1. Prime long entry. Wave 3 (strongest) next. Stop below Wave 2 low.'
        },
        'WAVE_2_BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Wave 2 correction (bearish) - Deep retracement after Wave 1. Prime short entry. Wave 3 (strongest) next. Stop above Wave 2 high.'
        },
        
        # Wave 1 signals - Trend initiation
        'WAVE_1_BULLISH': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Wave 1 bullish - New impulse starting. Early long entry favorable. Confirm with volume. Stop below Wave 1 start.'
        },
        'WAVE_1_BEARISH': {
            'base_points': 15,
            'formula': 'scaled',
            'description': 'Wave 1 bearish - New impulse starting. Early short entry favorable. Confirm with volume. Stop above Wave 1 start.'
        },
        
        # Simple directional signals - SIMPLE for basic users
        'BULLISH': {
            'base_points': 30,
            'formula': 'scaled',
            'description': 'Bullish wave detected - Elliott Wave impulse in progress. Long positions favorable. Use wave-based stops.'
        },
        'BEARISH': {
            'base_points': 30,
            'formula': 'scaled',
            'description': 'Bearish wave detected - Elliott Wave impulse in progress. Short positions favorable. Use wave-based stops.'
        },
        'NEUTRAL': {
            'base_points': 5,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'No clear wave structure - Market in transition or corrective phase. Wait for impulse wave to form before entering.'
        },
        
        # Status signals (no points)
        'WAVE_UNCERTAIN': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Wave count uncertain - Insufficient pivots or ambiguous structure. Wait for clearer wave pattern before trading.'
        },
        'INSUFFICIENT_PIVOTS': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient pivots - Need more price swings to identify wave structure. Monitor for swing points developing.'
        },
        'NO_PATTERN': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'No Elliott Wave pattern - Market not in clear impulse or corrective wave. Wait for structure to develop.'
        },
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate Elliott Wave count. Check data quality and timeframe completeness.'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient data - Need at least 50 candles for Elliott Wave analysis. Wait for more price history.'
        }
    },
    description='Elliott Wave Count - Identifies 5-wave impulse patterns with MTF context',
    tags=['elliott_wave', 'pattern_recognition', 'context_block', 'mtf_capable']
)
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
        """
        Initialize Elliott Wave Count
        
        Args:
            timeframe: Input timeframe (default '15min')
            use_mtf: Enable MTF analysis with internal resampling (default True)
        
        When use_mtf=True:
            - Accepts 15min data and internally resamples to 2hr, 4hr, Daily
            - Provides institutional-grade Elliott Wave counts
            - No external MTF data needed - all handled internally
        """
        self.timeframe = timeframe
        self.use_mtf = use_mtf
    
    def _determine_dual_signals(self, signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        # Wave-specific signals (granular) map to simple directional
        if 'BULLISH' in signal and 'WAVE_' in signal:
            granular = signal  # Keep specific wave (e.g., WAVE_3_BULLISH)
            simple = 'BULLISH'
        elif 'BEARISH' in signal and 'WAVE_' in signal:
            granular = signal  # Keep specific wave (e.g., WAVE_5_BEARISH)
            simple = 'BEARISH'
        # Phase signals (also granular)
        elif signal in ['WAVE_1_FORMING', 'WAVE_2_CORRECTION', 'WAVE_UNCLEAR']:
            granular = signal
            # Infer simple direction from context if possible, else NEUTRAL
            simple = 'NEUTRAL'
        # Already simple directional signals
        elif signal in ['BULLISH', 'BEARISH', 'NEUTRAL']:
            granular = signal  # Simple signal is also granular in this case
            simple = signal
        # Status signals (non-directional)
        elif signal in ['WAVE_UNCERTAIN', 'INSUFFICIENT_PIVOTS', 'NO_PATTERN', 'ERROR', 'INSUFFICIENT_DATA']:
            granular = signal
            simple = 'NEUTRAL'
        else:
            # Fallback
            granular = signal
            simple = 'NEUTRAL'
        return granular, simple
    
    def resample_timeframe(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """
        Resample 15min data to higher timeframe for MTF analysis
        
        Args:
            df: Source dataframe (15min)
            target_tf: Target timeframe ('2h', '4h', '1D')
        
        Returns:
            Resampled dataframe with OHLCV data
        """
        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)
        
        # Resample OHLCV
        resampled = df_copy.resample(target_tf).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Reset index to get timestamp back as column
        resampled.reset_index(inplace=True)
        
        return resampled
    
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
    
    def identify_current_wave(self, pivots: List[Dict]) -> Dict[str, Any]:
        """
        CONTINUOUS WAVE TRACKING: Always identify current wave position
        
        Returns current wave (1-5 or ABC), direction, confidence
        """
        if len(pivots) < 2:
            return {'wave': 'UNKNOWN', 'direction': None, 'confidence': 0, 'phase': 'INSUFFICIENT_DATA'}
        
        # Try to identify wave position from recent pivots
        recent = pivots[-8:] if len(pivots) >= 8 else pivots  # Look back further
        structure = [p['type'] for p in recent]
        
        # Analyze what we have
        wave_info = self.detect_wave_pattern(pivots)
        
        # If we found a complete pattern, use it
        if wave_info['wave'] is not None:
            return wave_info
        
        # Otherwise, estimate current position
        # Count alternating pivots to estimate wave
        if len(recent) >= 2:
            last_type = recent[-1]['type']
            
            # Simple heuristic: Count how many pivots we have
            # 2 pivots (L H or H L) = Wave 1
            # 3-4 pivots = Wave 2-3
            # 5-6 pivots = Wave 4-5
            
            if len(recent) == 2:
                if structure == ['LOW', 'HIGH']:
                    return {'wave': 1, 'direction': 'BULLISH', 'confidence': 50, 'phase': 'WAVE_1_FORMING', 'pattern': 'IMPULSE_EARLY'}
                elif structure == ['HIGH', 'LOW']:
                    return {'wave': 1, 'direction': 'BEARISH', 'confidence': 50, 'phase': 'WAVE_1_FORMING', 'pattern': 'IMPULSE_EARLY'}
            
            elif len(recent) >= 3:
                # Check if we're in correction (Wave 2 or 4)
                if structure[-3:] == ['HIGH', 'LOW', 'HIGH']:  # Potential Wave 2 bullish
                    return {'wave': 2, 'direction': 'BULLISH', 'confidence': 55, 'phase': 'WAVE_2_CORRECTION', 'pattern': 'IMPULSE_FORMING'}
                elif structure[-3:] == ['LOW', 'HIGH', 'LOW']:  # Potential Wave 2 bearish
                    return {'wave': 2, 'direction': 'BEARISH', 'confidence': 55, 'phase': 'WAVE_2_CORRECTION', 'pattern': 'IMPULSE_FORMING'}
        
        # Default: uncertain
        return {'wave': 'UNCERTAIN', 'direction': None, 'confidence': 34, 'phase': 'WAVE_UNCLEAR', 'pattern': 'DEVELOPING'}
    
    def detect_wave_pattern(self, pivots: List[Dict]) -> Dict[str, Any]:
        """
        ENHANCED: Detect Elliott Wave patterns with proper rules
        
        Returns wave count, direction, and validation
        """
        if len(pivots) < 6:
            return {'wave': None, 'direction': None, 'confidence': 0}
        
        recent = pivots[-6:]
        structure = [p['type'] for p in recent]
        
        # BULLISH 5-wave impulse: L H L H L H
        if structure == ['LOW', 'HIGH', 'LOW', 'HIGH', 'LOW', 'HIGH']:
            w1_size = recent[1]['price'] - recent[0]['price']
            w2_size = recent[1]['price'] - recent[2]['price']  # Retracement
            w3_size = recent[3]['price'] - recent[2]['price']
            w4_size = recent[3]['price'] - recent[4]['price']  # Retracement
            w5_size = recent[5]['price'] - recent[4]['price']
            
            # Elliott Wave rules
            valid_w3 = w3_size > w1_size  # Wave 3 longest
            valid_w2 = w2_size < w1_size * 0.9  # Wave 2 doesn't retrace >90%
            valid_w4 = w4_size < w3_size * 0.5  # Wave 4 shallow
            
            if valid_w3 and valid_w2 and valid_w4:
                return {
                    'wave': 5,
                    'direction': 'BULLISH',
                    'confidence': 80,
                    'w3_extension': round((w3_size / w1_size - 1) * 100, 2),
                    'pattern': 'IMPULSE'
                }
        
        # BEARISH 5-wave impulse: H L H L H L (BALANCED - realistic but flexible)
        elif structure == ['HIGH', 'LOW', 'HIGH', 'LOW', 'HIGH', 'LOW']:
            w1_size = recent[0]['price'] - recent[1]['price']
            w2_size = recent[2]['price'] - recent[1]['price']  # Retracement
            w3_size = recent[2]['price'] - recent[3]['price']
            w4_size = recent[4]['price'] - recent[3]['price']  # Retracement
            w5_size = recent[4]['price'] - recent[5]['price']
            
            # BALANCED RULES: Relaxed but still meaningful
            # Wave 3 >= 70% of Wave 1 (relaxed from 100% but realistic)
            valid_w3 = w3_size >= w1_size * 0.7
            # Wave 2 < 120% of Wave 1 (relaxed from 90% but not excessive)
            valid_w2 = w2_size < w1_size * 1.2
            # Wave 4 < 75% of Wave 3 (relaxed from 50% but reasonable)
            valid_w4 = w4_size < w3_size * 0.75
            
            if valid_w3 and valid_w2 and valid_w4:
                return {
                    'wave': 5,
                    'direction': 'BEARISH',
                    'confidence': 70,  # Reasonable confidence with balanced rules
                    'w3_extension': round((w3_size / w1_size - 1) * 100, 2) if w1_size > 0 else 0,
                    'pattern': 'IMPULSE'
                }
        
        # Check for Wave 3 in progress (4 pivots)
        if len(pivots) >= 4:
            recent4 = pivots[-4:]
            structure4 = [p['type'] for p in recent4]
            
            # Bullish Wave 3: L H L H
            if structure4 == ['LOW', 'HIGH', 'LOW', 'HIGH']:
                w1 = recent4[1]['price'] - recent4[0]['price']
                w3 = recent4[3]['price'] - recent4[2]['price']
                if w3 > w1:  # Wave 3 extending
                    return {
                        'wave': 3,
                        'direction': 'BULLISH',
                        'confidence': 70,
                        'w3_extension': round((w3 / w1 - 1) * 100, 2),
                        'pattern': 'IMPULSE_FORMING'
                    }
            
            # Bearish Wave 3: H L H L
            elif structure4 == ['HIGH', 'LOW', 'HIGH', 'LOW']:
                w1 = recent4[0]['price'] - recent4[1]['price']
                w3 = recent4[2]['price'] - recent4[3]['price']
                if w3 > w1:
                    return {
                        'wave': 3,
                        'direction': 'BEARISH',
                        'confidence': 70,
                        'w3_extension': round((w3 / w1 - 1) * 100, 2),
                        'pattern': 'IMPULSE_FORMING'
                    }
        
        # Check for Wave 4 (5 pivots: L H L H L for bullish, H L H L H for bearish)
        if len(pivots) >= 5:
            recent5 = pivots[-5:]
            structure5 = [p['type'] for p in recent5]
            
            # Bullish Wave 4: L H L H L (correction after Wave 3)
            if structure5 == ['LOW', 'HIGH', 'LOW', 'HIGH', 'LOW']:
                w1 = recent5[1]['price'] - recent5[0]['price']
                w3 = recent5[3]['price'] - recent5[2]['price']
                w4_retracement = recent5[3]['price'] - recent5[4]['price']
                # Wave 4 should retrace less than Wave 3
                if w3 > w1 and w4_retracement < w3 * 0.6:
                    return {
                        'wave': 4,
                        'direction': 'BULLISH',
                        'confidence': 65,
                        'pattern': 'CORRECTION_WAVE4'
                    }
            
            # Bearish Wave 4: H L H L H (correction after Wave 3)
            elif structure5 == ['HIGH', 'LOW', 'HIGH', 'LOW', 'HIGH']:
                w1 = recent5[0]['price'] - recent5[1]['price']
                w3 = recent5[2]['price'] - recent5[3]['price']
                w4_retracement = recent5[4]['price'] - recent5[3]['price']
                if w3 > w1 and w4_retracement < w3 * 0.6:
                    return {
                        'wave': 4,
                        'direction': 'BEARISH',
                        'confidence': 65,
                        'pattern': 'CORRECTION_WAVE4'
                    }
        
        # Check for Wave 1 (2 pivots minimum: L H for bullish, H L for bearish)
        if len(pivots) >= 2:
            recent2 = pivots[-2:]
            structure2 = [p['type'] for p in recent2]
            
            # Bullish Wave 1: L H (new impulse starting)
            if structure2 == ['LOW', 'HIGH']:
                w1_size = recent2[1]['price'] - recent2[0]['price']
                # Require meaningful move (> 2%)
                if w1_size > recent2[0]['price'] * 0.02:
                    return {
                        'wave': 1,
                        'direction': 'BULLISH',
                        'confidence': 55,
                        'pattern': 'IMPULSE_STARTING'
                    }
            
            # Bearish Wave 1: H L (new impulse starting)
            elif structure2 == ['HIGH', 'LOW']:
                w1_size = recent2[0]['price'] - recent2[1]['price']
                if w1_size > recent2[0]['price'] * 0.02:
                    return {
                        'wave': 1,
                        'direction': 'BEARISH',
                        'confidence': 55,
                        'pattern': 'IMPULSE_STARTING'
                    }
        
        return {'wave': None, 'direction': None, 'confidence': 0}
    
    def analyze_single_timeframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ENHANCED: Analyze single timeframe with proper wave detection"""
        if len(df) < 50:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # FIXED: Use lookback=5 for 4H (was too sensitive at 3)
        pivots = self.find_pivots(df, lookback=5)
        
        if len(pivots) < 4:
            return {
                'signal': 'INSUFFICIENT_PIVOTS',
                'confidence': 34,  # Enough data but no pattern yet
                'metadata': {'pivot_count': len(pivots), 'status': 'too_few_pivots'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [f'Only {len(pivots)} pivots found (need 4+)']
            }
        
        # ENHANCED: Always identify current wave position
        wave_info = self.identify_current_wave(pivots)
        
        if wave_info['wave'] == 'UNKNOWN':
            # Not enough pivots or structure for wave count
            granular_signal, simple_signal = self._determine_dual_signals('NO_PATTERN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': 0,
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'wave_count': 'UNKNOWN',
                    'pivot_count': len(pivots),
                    'phase': 'NO_PATTERN',
                    'last_6_pivots': [p['type'] for p in pivots[-6:]] if len(pivots) >= 6 else [p['type'] for p in pivots]
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [f'{len(pivots)} pivots - no clear pattern']
            }
        elif wave_info['wave'] == 'UNCERTAIN':
            # Structure exists but unclear which wave
            granular_signal, simple_signal = self._determine_dual_signals('WAVE_UNCERTAIN')
            return {
                'signal': granular_signal,
                'signal_simple': simple_signal,
                'confidence': wave_info.get('confidence', 34),
                'metadata': {
                    'signal_simple': simple_signal,
                    'signal_granular': granular_signal,
                    'wave_count': 'UNCERTAIN',
                    'pivot_count': len(pivots),
                    'phase': wave_info.get('phase', 'UNCLEAR'),
                    'last_6_pivots': [p['type'] for p in pivots[-6:]] if len(pivots) >= 6 else [p['type'] for p in pivots]
                },
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': [f'{len(pivots)} pivots - wave position unclear']
            }
        
        # ENHANCED: Build signal based on current wave position
        direction = wave_info['direction']
        wave_num = wave_info['wave']
        confidence = wave_info['confidence']
        phase = wave_info.get('phase', 'UNKNOWN')
        
        # Build signal name
        if wave_num == 5:
            signal = f'WAVE_5_{direction}'
            confluence_factors = [
                f"⭐ {direction} Wave 5 complete",
                f"Wave 3 extended {wave_info.get('w3_extension', 0)}%",
                f"Expect reversal - major exhaustion"
            ]
        elif wave_num == 3:
            signal = f'WAVE_3_{direction}'
            confluence_factors = [
                f"✅ {direction} Wave 3 in progress",
                f"Wave 3 extending {wave_info.get('w3_extension', 0)}%",
                f"Strong trend - continuation expected"
            ]
        elif wave_num == 4:
            signal = f'WAVE_4_{direction}'
            confluence_factors = [
                f"Wave 4 correction ({direction})",
                f"Shallow pullback expected",
                f"Wave 5 coming next"
            ]
        elif wave_num == 2:
            signal = f'WAVE_2_{direction}'
            confluence_factors = [
                f"Wave 2 correction ({direction})",
                f"Pullback after Wave 1",
                f"Wave 3 (strongest) coming"
            ]
        elif wave_num == 1:
            signal = f'WAVE_1_{direction}'
            confluence_factors = [
                f"Wave 1 forming ({direction})",
                f"New impulse starting",
                f"Early trend detection"
            ]
        else:
            signal = f'{phase}'
            confluence_factors = [f'Wave position: {phase}']
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'wave_count': wave_num,
            'direction': direction,
            'phase': phase,
            'pattern': wave_info.get('pattern'),
            'w3_extension': wave_info.get('w3_extension'),
            'pivot_count': len(pivots)
        }
        
        return {
            'signal': granular_signal,
            'signal_simple': simple_signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
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
        
        # ENHANCED: Check for ALL wave types (1-5)
        daily_sig = daily_result.get('signal', '')
        h4_sig = h4_result.get('signal', '')
        
        # Extract wave numbers and directions
        daily_wave = daily_result.get('metadata', {}).get('wave_count')
        h4_wave = h4_result.get('metadata', {}).get('wave_count')
        
        # Check Daily + 4H alignment (HTF focus) - ALL WAVES
        if daily_wave == 5 and h4_wave == 5:
            alignment_score = 100  # PERFECT
            booster_value = 75  # ULTRA
            confluence_factors.append('⭐ ULTRA: Daily + 4H Wave 5 alignment!')
            signal = daily_sig
            
        elif daily_wave == 5:
            alignment_score = 85  # STRONG
            booster_value = 50  # MAJOR
            confluence_factors.append('⭐ Strong: Daily Wave 5 detected')
            signal = daily_sig
            
        elif h4_wave == 5:
            alignment_score = 70  # GOOD
            booster_value = 30  # Strong
            confluence_factors.append('Good: 4H Wave 5 detected')
            signal = h4_sig
            
        elif daily_wave == 3 and h4_wave == 3:
            alignment_score = 85  # Strong trend
            booster_value = 40  # Good
            confluence_factors.append('Strong: Daily + 4H Wave 3 alignment')
            signal = daily_sig
            
        elif daily_wave == 3:
            alignment_score = 70
            booster_value = 25
            confluence_factors.append('Daily Wave 3 in progress')
            signal = daily_sig
            
        elif h4_wave == 3:
            alignment_score = 60
            booster_value = 15
            confluence_factors.append('4H Wave 3 in progress')
            signal = h4_sig
            
        # NEW: Handle Wave 1, 2, 4 with lower booster values
        elif daily_wave in [1, 2, 4] or h4_wave in [1, 2, 4]:
            # Prefer Daily over 4H
            if daily_wave in [1, 2, 4]:
                signal = daily_sig
                wave = daily_wave
                alignment_score = 55
            else:
                signal = h4_sig
                wave = h4_wave
                alignment_score = 50
            
            # Small booster for early waves
            if wave == 4:
                booster_value = 10  # Wave 4 = Wave 5 coming
                confluence_factors.append(f'HTF Wave 4 - Wave 5 next')
            elif wave == 2:
                booster_value = 5  # Wave 2 = Wave 3 coming
                confluence_factors.append(f'HTF Wave 2 - Wave 3 coming')
            elif wave == 1:
                booster_value = 3  # Wave 1 = early trend
                confluence_factors.append(f'HTF Wave 1 - trend starting')
        
        # Fallback: Use Daily if it has any signal, otherwise 4H
        elif daily_sig not in ['WAVE_UNCERTAIN', 'NO_PATTERN', 'INSUFFICIENT_PIVOTS']:
            signal = daily_sig
            alignment_score = 45
            confluence_factors.append(f'HTF wave detected: {daily_sig}')
        elif h4_sig not in ['WAVE_UNCERTAIN', 'NO_PATTERN', 'INSUFFICIENT_PIVOTS']:
            signal = h4_sig
            alignment_score = 42
            confluence_factors.append(f'4H wave detected: {h4_sig}')
        else:
            signal = daily_sig  # Pass through whatever Daily has
            confluence_factors.append('HTF analysis in progress')
        
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
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        # Build metadata
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
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
            'signal': granular_signal,
            'signal_simple': simple_signal,
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
            # MTF MODE - Check if external MTF data provided, otherwise resample internally
            df_4h = kwargs.get('df_4h')
            df_1d = kwargs.get('df_1d')
            
            if df_4h is None or df_1d is None:
                # No external MTF data - resample internally from 15min
                df_2h = self.resample_timeframe(df, '2h')
                df_4h_resampled = self.resample_timeframe(df, '4h')
                df_1d_resampled = self.resample_timeframe(df, '1D')
                
                # Use resampled data for MTF analysis
                return self.analyze_multi_timeframe(df_4h_resampled, df_1d_resampled)
            else:
                # External MTF data provided - use it directly
                return self.analyze_multi_timeframe(df_4h, df_1d)
        else:
            # Single Timeframe analysis (original logic)
            return self.analyze_single_timeframe(df)
