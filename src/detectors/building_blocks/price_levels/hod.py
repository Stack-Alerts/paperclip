"""
HOD (High of Day) Building Block
Category: Price Levels
Purpose: Daily high price level for support/resistance and breakout detection
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous high of day level

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any
from datetime import datetime, time
import pandas as pd
import numpy as np


class HOD:
    """
    HOD - High of Day Price Level (ENHANCED 2026-01-04)
    
    Tracks the highest price reached during the current trading day.
    Critical level for:
    - Resistance identification
    - Breakout detection
    - Range trading
    - Day trading setups
    
    ENHANCEMENTS (2026-01-04):
    - Added BULLISH signal generation for HOD breakouts
    - Added event tracking for HOD breaks and tests
    - Improved confidence variation (70-95% range)
    - Fixed breakout detection to track previous HOD
    
    Parameters:
        timeframe: Data timeframe
        day_start_hour: Hour when day starts (default: 0 UTC)
    
    Returns:
        Standardized dict with HOD level, distance, and breakout signals
    """
    
    def __init__(self, timeframe: str = '15min', day_start_hour: int = 0, **kwargs):
        """Initialize HOD block"""
        self.timeframe = timeframe
        self.day_start_hour = day_start_hour
        
        # ENHANCEMENT: Track previous state for event detection
        self.prev_hod = None
        self.prev_signal = None
        
        # Bitcoin-specific distance thresholds (% from HOD)
        self.btc_distance_thresholds = {
            'at_hod': 0.2,          # < 0.2% - at HOD
            'very_close': 0.5,      # 0.2-0.5% - very close
            'close': 1.0,           # 0.5-1% - close
            'moderate': 2.0,        # 1-2% - moderate distance
            'far': 2.0              # > 2% - far from HOD
        }
    
    def calculate_hod(self, df: pd.DataFrame) -> float:
        """
        Calculate High of Day from intraday data
        
        Args:
            df: DataFrame with timestamp and high columns
            
        Returns:
            HOD value
        """
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        # Get current date
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return highest high of the day
        return float(today_data['high'].max())
    
    def detect_breakout(self, current_price: float, hod: float, prev_hod: float = None, threshold_pct: float = 0.05) -> Dict[str, Any]:
        """
        ENHANCED: Detect HOD breakout by comparing to PREVIOUS HOD
        
        Args:
            current_price: Current price
            hod: Current High of Day  
            prev_hod: Previous HOD (to detect fresh breaks)
            threshold_pct: Threshold for breakout confirmation (default: 0.05%)
            
        Returns:
            Dict with breakout status and event info
        """
        if hod is None:
            return {
                'status': 'NO_HOD',
                'is_new_hod': False,
                'is_breakout': False
            }
        
        # Check if HOD was updated (new high made)
        is_new_hod = False
        if prev_hod is not None and hod > prev_hod:
            is_new_hod = True
        
        # Calculate distance from PREVIOUS HOD (not current, which updates)
        ref_hod = prev_hod if prev_hod is not None else hod
        distance_pct = ((current_price - ref_hod) / ref_hod) * 100
        
        # Determine breakout status
        if is_new_hod and distance_pct > threshold_pct:
            return {
                'status': 'BREAKOUT_CONFIRMED',
                'is_new_hod': True,
                'is_breakout': True
            }
        elif distance_pct > 0 and distance_pct <= threshold_pct:
            return {
                'status': 'BREAKING_OUT',
                'is_new_hod': is_new_hod,
                'is_breakout': False
            }
        else:
            return {
                'status': 'BELOW_HOD',
                'is_new_hod': False,
                'is_breakout': False
            }
    
    def calculate_distance(self, price: float, hod: float) -> float:
        """Calculate percentage distance from HOD"""
        if hod is None:
            return None
        return ((price - hod) / hod) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from HOD"""
        if distance_pct is None:
            return 'NO_HOD'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_hod']:
            return 'AT_HOD'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """
        ENHANCEMENT 3: Variable confidence based on signal type and distance
        """
        # Base confidence by signal
        if signal == 'BULLISH':
            base = 90  # Breakout = high confidence
        elif signal == 'BEARISH':
            base = 85  # Rejection at HOD = high confidence
        else:  # NEUTRAL
            base = 70  # Neutral = baseline
        
        # Adjust by distance
        if distance_class in ['AT_HOD', 'VERY_CLOSE']:
            base = min(100, base + 5)  # Near HOD = higher confidence
        elif distance_class == 'FAR':
            base = max(70, base - 5)  # Far from HOD = lower confidence
        
        # Fresh event boost
        if is_new_event:
            base = min(100, base + 5)
        
        return base
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method (ENHANCED)"""
        # Validate
        if not all(col in df.columns for col in ['timestamp', 'high', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Check minimum data
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate HOD
        hod = self.calculate_hod(df)
        
        if hod is None:
            return {
                'signal': 'NO_HOD_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate HOD', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # ENHANCEMENT 1: Detect breakout with prev_hod tracking
        breakout_info = self.detect_breakout(current_price, hod, self.prev_hod)
        breakout_status = breakout_info['status']
        is_new_hod = breakout_info['is_new_hod']
        is_breakout = breakout_info['is_breakout']
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, hod)
        distance_class = self.classify_distance(distance_pct)
        
        # Determine signal
        if breakout_status == 'BREAKOUT_CONFIRMED' or is_new_hod:
            signal = 'BULLISH'
        elif breakout_status == 'BREAKING_OUT':
            signal = 'NEUTRAL'
        elif distance_class in ['AT_HOD', 'VERY_CLOSE'] and distance_pct < 0:
            signal = 'BEARISH'  # Rejection at HOD
        else:
            signal = 'NEUTRAL'
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_hod:
            is_new_event = True  # New HOD = event
        
        # ENHANCEMENT 3: Variable confidence
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        # Build confluence
        confluence_factors = []
        
        # Event-specific confluence
        if is_new_event:
            if is_new_hod:
                confluence_factors.append('⭐ NEW HOD: Fresh high created - bullish breakout!')
            elif signal == 'BULLISH' and self.prev_signal != 'BULLISH':
                confluence_factors.append('⭐ NEW STATE: HOD breakout initiated')
            elif signal == 'BEARISH' and self.prev_signal != 'BEARISH':
                confluence_factors.append('⭐ NEW STATE: HOD rejection detected')
        
        if breakout_status == 'BREAKOUT_CONFIRMED':
            confluence_factors.append('HOD breakout confirmed - bullish signal')
        elif breakout_status == 'BREAKING_OUT':
            confluence_factors.append('Price breaking above HOD - watch for confirmation')
        elif distance_class in ['AT_HOD', 'VERY_CLOSE']:
            if distance_pct < 0:
                confluence_factors.append('Price testing HOD resistance - potential rejection')
            else:
                confluence_factors.append('Price at HOD - critical level')
        
        confluence_factors.append(f'HOD: ${hod:.2f}')
        confluence_factors.append(f'Distance from HOD: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking
        self.prev_hod = hod
        self.prev_signal = signal
        
        # Metadata
        metadata = {
            'hod': round(hod, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakout_status': breakout_status,
            'is_new_hod': is_new_hod,
            'is_breakout': is_breakout,
            'is_at_resistance': distance_class in ['AT_HOD', 'VERY_CLOSE'] and distance_pct < 0,
            'is_breaking_out': breakout_status in ['BREAKING_OUT', 'BREAKOUT_CONFIRMED'],
            'is_new_event': is_new_event  # ENHANCEMENT 2: Event tracking
        }
        
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }


if __name__ == "__main__":
    # Test
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    base = 45000
    highs = base + np.random.uniform(-200, 500, 50)
    closes = highs - np.random.uniform(0, 100, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'high': highs,
        'close': closes,
        'open': closes - 50,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    hod_block = HOD()
    result = hod_block.analyze(data)
    
    print("=" * 80)
    print("HOD (HIGH OF DAY) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nHOD Analysis:")
    print(f"  HOD: ${result['metadata']['hod']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakout Status: {result['metadata']['breakout_status']}")
    print(f"  At Resistance: {result['metadata']['is_at_resistance']}")
    print(f"  Breaking Out: {result['metadata']['is_breaking_out']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
