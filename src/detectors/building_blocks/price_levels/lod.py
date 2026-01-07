"""
LOD (Low of Day) Building Block
Category: Price Levels
Purpose: Daily low price level for support/resistance and breakdown detection
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous low of day level

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np


class LOD:
    """
    LOD - Low of Day Price Level (ENHANCED 2026-01-04)
    
    Tracks the lowest price reached during the current trading day.
    Critical level for:
    - Support identification
    - Breakdown detection
    - Range trading
    - Day trading setups
    
    ENHANCEMENTS (2026-01-04):
    - Added BEARISH signal generation for LOD breakdowns
    - Added event tracking for LOD breaks and tests
    - Improved confidence variation (70-100% range)
    - Fixed breakdown detection to track previous LOD
    
    Parameters:
        timeframe: Data timeframe
        day_start_hour: Hour when day starts (default: 0 UTC)
    
    Returns:
        Standardized dict with LOD level, distance, and breakdown signals
    """
    
    def __init__(self, timeframe: str = '15min', day_start_hour: int = 0, **kwargs):
        """Initialize LOD block"""
        self.timeframe = timeframe
        self.day_start_hour = day_start_hour
        
        # ENHANCEMENT: Track previous state for event detection
        self.prev_lod = None
        self.prev_signal = None
        
        # RETEST CONFIRMATION: Track retests of LOD level
        self.confirmation_candles = 3  # Require 3 consecutive bars
        self.bounce_test_bars = []  # Track bars testing support
        self.breakdown_bars = []  # Track bars breaking below
        
        # Bitcoin-specific distance thresholds (% from LOD)
        self.btc_distance_thresholds = {
            'at_lod': 0.2,          # < 0.2% - at LOD
            'very_close': 0.5,      # 0.2-0.5% - very close
            'close': 1.0,           # 0.5-1% - close
            'moderate': 2.0,        # 1-2% - moderate distance
            'far': 2.0              # > 2% - far from LOD
        }
    
    def calculate_lod(self, df: pd.DataFrame) -> float:
        """Calculate Low of Day from intraday data"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        return float(today_data['low'].min())
    
    def detect_breakdown(self, current_price: float, lod: float, prev_lod: float = None, threshold_pct: float = 0.05) -> Dict[str, Any]:
        """
        ENHANCED: Detect LOD breakdown by comparing to PREVIOUS LOD
        
        Args:
            current_price: Current price
            lod: Current Low of Day
            prev_lod: Previous LOD (to detect fresh breaks)
            threshold_pct: Threshold for breakdown confirmation (default: 0.05%)
            
        Returns:
            Dict with breakdown status and event info
        """
        if lod is None:
            return {
                'status': 'NO_LOD',
                'is_new_lod': False,
                'is_breakdown': False
            }
        
        # Check if LOD was updated (new low made)
        is_new_lod = False
        if prev_lod is not None and lod < prev_lod:
            is_new_lod = True
        
        # Calculate distance from PREVIOUS LOD (not current, which updates)
        ref_lod = prev_lod if prev_lod is not None else lod
        distance_pct = ((current_price - ref_lod) / ref_lod) * 100
        
        # Determine breakdown status
        if is_new_lod and distance_pct < -threshold_pct:
            return {
                'status': 'BREAKDOWN_CONFIRMED',
                'is_new_lod': True,
                'is_breakdown': True
            }
        elif distance_pct < 0 and distance_pct >= -threshold_pct:
            return {
                'status': 'BREAKING_DOWN',
                'is_new_lod': is_new_lod,
                'is_breakdown': False
            }
        else:
            return {
                'status': 'ABOVE_LOD',
                'is_new_lod': False,
                'is_breakdown': False
            }
    
    def calculate_distance(self, price: float, lod: float) -> float:
        """Calculate percentage distance from LOD"""
        if lod is None:
            return None
        return ((price - lod) / lod) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from LOD"""
        if distance_pct is None:
            return 'NO_LOD'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_lod']:
            return 'AT_LOD'
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
        OPTIMIZED V2: Further reduced to hit 80-85% average
        """
        # Base confidence by signal (FURTHER OPTIMIZED)
        if signal == 'BEARISH':
            base = 60  # Breakdown (reduced from 65)
        elif signal == 'BULLISH':
            base = 65  # Bounce from LOD (reduced from 70)
        else:  # NEUTRAL
            base = 50  # Neutral (reduced from 55)
        
        # Adjust by distance (±15% for variation)
        if distance_class in ['AT_LOD', 'VERY_CLOSE']:
            base = min(95, base + 15)  # Near LOD
        elif distance_class == 'FAR':
            base = max(40, base - 15)  # Far from LOD
        
        # Fresh event boost (+15% for new events)
        if is_new_event:
            base = min(95, base + 15)
        
        return base
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method (ENHANCED)"""
        # Validate
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < 1:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'error': 'No data provided', 'is_new_event': False},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate LOD
        lod = self.calculate_lod(df)
        
        if lod is None:
            return {
                'signal': 'NO_LOD_DATA',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate LOD', 'is_new_event': False},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        
        # ENHANCEMENT 1: Detect breakdown with prev_lod tracking
        breakdown_info = self.detect_breakdown(current_price, lod, self.prev_lod)
        breakdown_status = breakdown_info['status']
        is_new_lod = breakdown_info['is_new_lod']
        is_breakdown = breakdown_info['is_breakdown']
        
        # Calculate distance
        distance_pct = self.calculate_distance(current_price, lod)
        distance_class = self.classify_distance(distance_pct)
        
        # RETEST CONFIRMATION: Track LOD retests
        confirmed_bounce = False
        confirmed_breakdown = False
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'breached_below': float(df['low'].iloc[-1]) < lod,  # Wick went below
            'breached_above': float(df['high'].iloc[-1]) > lod,  # Wick went above
            'closed_above': current_price > lod,
            'closed_below': current_price < lod
        }
        
        # BOUNCE TEST: Price wicks BELOW LOD but closes ABOVE (support holding)
        if current_bar['breached_below'] and current_bar['closed_above']:
            self.bounce_test_bars.append(current_bar)
            # Keep only recent bars
            if len(self.bounce_test_bars) > self.confirmation_candles + 2:
                self.bounce_test_bars.pop(0)
            
            # Check for confirmed bounce (X consecutive tests of support)
            if len(self.bounce_test_bars) >= self.confirmation_candles:
                recent_bars = self.bounce_test_bars[-self.confirmation_candles:]
                all_tested_and_held = all(
                    bar['breached_below'] and bar['closed_above']
                    for bar in recent_bars
                )
                
                # Confirmed if: support tested X times and held each time
                if all_tested_and_held:
                    confirmed_bounce = True
                    self.bounce_test_bars = []  # Reset after confirmation
        elif distance_class not in ['AT_LOD', 'VERY_CLOSE']:
            # Price moved far away, reset bounce tracking
            if len(self.bounce_test_bars) > 0:
                self.bounce_test_bars = []
        
        # BREAKDOWN TEST: Price closes BELOW LOD (support broken)
        if current_bar['closed_below']:
            self.breakdown_bars.append(current_bar)
            # Keep only recent bars
            if len(self.breakdown_bars) > self.confirmation_candles + 2:
                self.breakdown_bars.pop(0)
            
            # Check for confirmed breakdown (X consecutive closes below)
            if len(self.breakdown_bars) >= self.confirmation_candles:
                recent_bars = self.breakdown_bars[-self.confirmation_candles:]
                all_closed_below = all(
                    bar['closed_below']
                    for bar in recent_bars
                )
                
                # Confirmed if: X consecutive bars closed below LOD
                if all_closed_below:
                    confirmed_breakdown = True
                    self.breakdown_bars = []  # Reset after confirmation
        elif current_bar['closed_above']:
            # Price back above LOD, reset breakdown tracking
            if len(self.breakdown_bars) > 0:
                self.breakdown_bars = []
        
        # Determine signal (ENHANCED with retest confirmation)
        if confirmed_bounce:
            # CONFIRMED BOUNCE - support holding (BULLISH)
            signal = 'BULLISH'
        elif confirmed_breakdown:
            # CONFIRMED BREAKDOWN - support broken (BEARISH)
            signal = 'BEARISH'
        elif breakdown_status == 'BREAKDOWN_CONFIRMED' or is_new_lod:
            signal = 'BEARISH'
        elif breakdown_status == 'BREAKING_DOWN':
            signal = 'NEUTRAL'
        elif distance_class == 'AT_LOD' and distance_pct > 0:
            # More selective: Only AT_LOD (not VERY_CLOSE)
            # This is within 0.2% of LOD (9-18 points on BTC)
            signal = 'BULLISH'  # Bounce from LOD
        else:
            signal = 'NEUTRAL'
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_lod:
            is_new_event = True  # New LOD = event
        elif confirmed_bounce or confirmed_breakdown:
            is_new_event = True  # Retest confirmation = event
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for retest confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        # Boost confidence for confirmed retests (highest priority)
        if confirmed_bounce or confirmed_breakdown:
            confidence = min(95, confidence + 20)  # Strong boost for 3-bar confirmation
        
        # Build confluence
        confluence_factors = []
        
        # Retest confirmation confluence (HIGHEST PRIORITY)
        if confirmed_bounce:
            confluence_factors.append('⭐⭐ CONFIRMED BOUNCE FROM LOD - Strong bullish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked below, closed above (support holding!)')
        elif confirmed_breakdown:
            confluence_factors.append('⭐⭐ CONFIRMED BREAKDOWN BELOW LOD - Strong bearish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} bars: closed below LOD (support broken!)')
        
        # Event-specific confluence
        elif is_new_event:
            if is_new_lod:
                confluence_factors.append('⭐ NEW LOD: Fresh low created - bearish breakdown!')
            elif signal == 'BEARISH' and self.prev_signal != 'BEARISH':
                confluence_factors.append('⭐ NEW STATE: LOD breakdown initiated')
            elif signal == 'BULLISH' and self.prev_signal != 'BULLISH':
                confluence_factors.append('⭐ NEW STATE: LOD bounce detected')
        
        if breakdown_status == 'BREAKDOWN_CONFIRMED':
            confluence_factors.append('LOD breakdown confirmed - bearish signal')
        elif breakdown_status == 'BREAKING_DOWN':
            confluence_factors.append('Price breaking below LOD - watch for confirmation')
        elif distance_class in ['AT_LOD', 'VERY_CLOSE']:
            if distance_pct > 0:
                confluence_factors.append('Price testing LOD support - potential bounce')
            else:
                confluence_factors.append('Price at LOD - critical level')
        
        confluence_factors.append(f'LOD: ${lod:.2f}')
        confluence_factors.append(f'Distance from LOD: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking
        self.prev_lod = lod
        self.prev_signal = signal
        
        # Metadata (ENHANCED with retest confirmation)
        metadata = {
            'lod': round(lod, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'breakdown_status': breakdown_status,
            'is_new_lod': is_new_lod,
            'is_breakdown': is_breakdown,
            'is_at_support': distance_class in ['AT_LOD', 'VERY_CLOSE'] and distance_pct > 0,
            'is_breaking_down': breakdown_status in ['BREAKING_DOWN', 'BREAKDOWN_CONFIRMED'],
            'is_new_event': is_new_event,
            'confirmed_bounce': confirmed_bounce,  # NEW: 3-bar support holding
            'confirmed_breakdown': confirmed_breakdown,  # NEW: 3-bar support broken
            'confirmation_candles': self.confirmation_candles
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
    lows = base - np.random.uniform(0, 500, 50)
    closes = lows + np.random.uniform(0, 100, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 50,
        'high': closes + 100,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    lod_block = LOD()
    result = lod_block.analyze(data)
    
    print("=" * 80)
    print("LOD (LOW OF DAY) - TEST RESULTS")
    print("=" * 80)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nLOD Analysis:")
    print(f"  LOD: ${result['metadata']['lod']:.2f}")
    print(f"  Current Price: ${result['metadata']['current_price']:.2f}")
    print(f"  Distance: {result['metadata']['distance_pct']:+.2f}% ({result['metadata']['distance_class']})")
    print(f"  Breakdown Status: {result['metadata']['breakdown_status']}")
    print(f"  At Support: {result['metadata']['is_at_support']}")
    print(f"  Breaking Down: {result['metadata']['is_breaking_down']}")
    print(f"\nConfluence Factors:")
    for factor in result['confluence_factors']:
        print(f"  - {factor}")
    print("=" * 80)
