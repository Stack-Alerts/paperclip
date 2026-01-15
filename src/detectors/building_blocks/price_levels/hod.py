"""
HOD (High of Day) Building Block - UPDATED 2026-01-09
Category: Price Levels
Purpose: YESTERDAY'S high price level for support/resistance

IMPORTANT: This block now tracks YESTERDAY's high, not today's.
For today's high, use IHOD (Intraday High of Day).

Changes (2026-01-09):
- HOD = Yesterday's high (static daily reference)
- IHOD = Today's high (dynamic, updates intraday)
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime, time
import pandas as pd
import numpy as np


@register_block(
    name='hod',
    category='PRICE_LEVELS',
    class_name='HOD',
    default_weight=20,
    valid_signals=['BEARISH', 'BULLISH', 'NEUTRAL', 'HOD_REJECTION', 'AT_HOD', 'BELOW_HOD', 'ABOVE_HOD', 'ERROR'],
    signal_tiers={
        'ERROR': {
                'points': 0,
                'description': 'Analysis error - Cannot calculate HOD. Check data quality and timestamp availability.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish HOD - Price rejected from or below yesterday\'s high. Short positions favorable. Resistance holding.'
        },
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish HOD - Price broke above yesterday\'s high. Long positions favorable. Breakout confirmed. New highs forming.'
        },
        'NEUTRAL': {
                'max_points': 10,
                'formula': 'scaled',
                'description': 'Neutral HOD - Price near yesterday\'s high equilibrium. Wait for breakout or rejection confirmation.'
        },
        'HOD_REJECTION': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'HOD rejection - Price rejected from yesterday\'s high. Confirmed reversal pattern. Enter shorts. Resistance confirmed.'
        },
        'AT_HOD': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'At HOD - Price testing yesterday\'s high. Key decision level. Watch for breakout or rejection. High probability setup.'
        },
        'BELOW_HOD': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Below HOD - Price below yesterday\'s high. HOD acting as resistance. Wait for breakout or support bounces.'
        },
        'ABOVE_HOD': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Above HOD - Price broke above yesterday\'s high. Bullish breakthrough confirmed. New highs. Trend continuation.'
        }
}
)
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
        
        # REVERSAL CONFIRMATION: Track price action after testing HOD
        self.reversal_candles = 5  # Monitor 5 candles after test for reversal pattern
        self.last_hod_test_bar = None  # Bar that tested HOD
        self.bars_since_test = []  # Track bars after HOD test for reversal detection
        
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
        Calculate YESTERDAY's High of Day
        
        UPDATED 2026-01-09: Now calculates YESTERDAY's high (static reference)
        For today's high, use IHOD building block.
        
        Args:
            df: DataFrame with timestamp and high columns
            
        Returns:
            Yesterday's HOD value (static for the day)
        """
        if 'timestamp' not in df.columns or 'high' not in df.columns:
            return None
        
        # Get current bar's date
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Calculate yesterday's date
        from datetime import timedelta
        yesterday_date = current_date - timedelta(days=1)
        
        # Filter for YESTERDAY's data only
        yesterday_data = df[df['timestamp'].dt.date == yesterday_date]
        
        if len(yesterday_data) == 0:
            # No yesterday data available - try to get most recent previous day
            available_dates = df['timestamp'].dt.date.unique()
            available_dates = sorted([d for d in available_dates if d < current_date])
            
            if len(available_dates) == 0:
                return None
            
            # Use most recent previous day
            prev_date = available_dates[-1]
            yesterday_data = df[df['timestamp'].dt.date == prev_date]
            
            if len(yesterday_data) == 0:
                return None
        
        # Return YESTERDAY's highest high (static for the day)
        return float(yesterday_data['high'].max())
    
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
    
    def _determine_dual_signals(self, current_price: float, hod: float,
                                 distance_pct: float, distance_class: str,
                                 breakout_status: str, reversal_rejection: bool,
                                 reversal_breakthrough: bool) -> tuple:
        """
        DUAL SIGNAL ARCHITECTURE - Returns both granular and simple signals
        
        For strategy builder:
        - Simple mode uses simple_signal: BULLISH, BEARISH, NEUTRAL
        - Advanced mode uses granular_signal: ABOVE_HOD, AT_HOD, BELOW_HOD, HOD_REJECTION
        - Combined mode uses both with confluence logic
        
        Returns: (granular_signal, simple_signal)
        """
        
        # Determine granular signal based on price relationship to HOD
        if reversal_breakthrough:
            granular = 'ABOVE_HOD'
            simple = 'BULLISH'
        elif reversal_rejection:
            granular = 'HOD_REJECTION'
            simple = 'BEARISH'
        elif breakout_status == 'BREAKOUT_CONFIRMED' and current_price > hod:
            granular = 'ABOVE_HOD'
            simple = 'BULLISH'
        elif distance_class == 'AT_HOD' and abs(distance_pct) < 0.3:
            granular = 'AT_HOD'
            simple = 'NEUTRAL' if distance_pct >= 0 else 'BEARISH'
        elif distance_class == 'AT_HOD' and distance_pct < 0:
            granular = 'HOD_REJECTION'
            simple = 'BEARISH'
        elif current_price > hod and distance_class != 'FAR':
            granular = 'ABOVE_HOD'
            simple = 'BULLISH'
        elif current_price < hod:
            granular = 'BELOW_HOD'
            simple = 'BEARISH' if distance_class == 'FAR' else 'NEUTRAL'
        else:
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
    
    def calculate_variable_confidence(self, signal: str, distance_class: str, is_new_event: bool) -> float:
        """
        OPTIMIZED: Variable confidence targeting 75-85% average with better variation
        """
        # Base confidence by signal (works for both granular and simple)
        if signal in ['ABOVE_HOD', 'BULLISH']:
            base = 75
        elif signal in ['HOD_REJECTION', 'BEARISH']:
            base = 65
        elif signal == 'AT_HOD':
            base = 70  # Testing key level
        elif signal == 'BELOW_HOD':
            base = 60  # Below resistance
        else:  # NEUTRAL
            base = 55
        
        # Adjust by distance (±10% for variation)
        if distance_class in ['AT_HOD', 'VERY_CLOSE']:
            base = min(95, base + 10)
        elif distance_class == 'FAR':
            base = max(50, base - 10)
        
        # Fresh event boost (+10% for new events)
        if is_new_event:
            base = min(95, base + 10)
        
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
        
        # REVERSAL CONFIRMATION: Detect reversal patterns after testing HOD
        reversal_rejection = False  # Bearish reversal after testing HOD
        reversal_breakthrough = False  # Bullish continuation after breaking HOD
        
        current_bar = {
            'close': current_price,
            'low': float(df['low'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'distance': distance_pct,
            'tested_hod': distance_class in ['AT_HOD', 'VERY_CLOSE', 'CLOSE'] and distance_pct < 0
        }
        
        # Check if current bar is testing HOD (came close but didn't break)
        if current_bar['tested_hod'] and not is_new_hod:
            # Mark this as a test bar and start monitoring
            self.last_hod_test_bar = current_bar
            self.bars_since_test = []
        
        # If we're monitoring after a HOD test, track subsequent bars
        if self.last_hod_test_bar is not None:
            self.bars_since_test.append(current_bar)
            
            # Keep only the configured number of bars
            if len(self.bars_since_test) > self.reversal_candles:
                self.bars_since_test.pop(0)
            
            # Check for BEARISH REVERSAL: Lower highs and lower lows after testing HOD
            if len(self.bars_since_test) >= self.reversal_candles:
                # Get last N bars for pattern analysis
                recent = self.bars_since_test[-self.reversal_candles:]
                
                # Check for consistent lower highs and lower lows (bearish reversal)
                lower_highs = all(
                    recent[i]['high'] < recent[i-1]['high']
                    for i in range(1, len(recent))
                )
                lower_lows = all(
                    recent[i]['low'] < recent[i-1]['low']
                    for i in range(1, len(recent))
                )
                
                # Confirmed reversal: consistent downtrend after testing HOD
                if lower_highs and lower_lows:
                    reversal_rejection = True
                    self.last_hod_test_bar = None  # Reset
                    self.bars_since_test = []
            
            # Reset if price makes new HOD or moves far away
            if is_new_hod or distance_class == 'FAR':
                self.last_hod_test_bar = None
                self.bars_since_test = []
        
        # Check for BULLISH BREAKTHROUGH: Higher highs and higher lows after breaking HOD
        if is_new_hod:
            # New HOD made, start monitoring for continuation
            self.bars_since_test = [current_bar]
        
        # Monitor continuation after breakthrough
        if is_new_hod or (self.prev_hod is not None and hod > self.prev_hod):
            if len(self.bars_since_test) > 0 and len(self.bars_since_test) < self.reversal_candles:
                self.bars_since_test.append(current_bar)
                
                # Check for consistent higher highs and higher lows (bullish continuation)
                if len(self.bars_since_test) >= self.reversal_candles:
                    recent = self.bars_since_test[-self.reversal_candles:]
                    
                    higher_highs = all(
                        recent[i]['high'] > recent[i-1]['high']
                        for i in range(1, len(recent))
                    )
                    higher_lows = all(
                        recent[i]['low'] > recent[i-1]['low']
                        for i in range(1, len(recent))
                    )
                    
                    # Confirmed breakthrough with strong continuation
                    if higher_highs and higher_lows:
                        reversal_breakthrough = True
        
        # DUAL SIGNAL ARCHITECTURE: Determine both granular and simple signals
        granular_signal, simple_signal = self._determine_dual_signals(
            current_price, hod, distance_pct, distance_class,
            breakout_status, reversal_rejection, reversal_breakthrough
        )
        
        # Use granular signal as primary
        signal = granular_signal
        
        # ENHANCEMENT 2: Event tracking
        is_new_event = False
        if self.prev_signal is not None and signal != self.prev_signal:
            is_new_event = True
        elif is_new_hod:
            is_new_event = True  # New HOD = event
        elif reversal_rejection or reversal_breakthrough:
            is_new_event = True  # Reversal confirmation = event
        
        # ENHANCEMENT 3: Variable confidence (BOOSTED for reversal confirmation)
        confidence = self.calculate_variable_confidence(signal, distance_class, is_new_event)
        
        # Boost confidence for confirmed reversals (highest priority)
        if reversal_rejection or reversal_breakthrough:
            confidence = min(95, confidence + 25)  # Strong boost for reversal pattern
        
        # Build confluence
        confluence_factors = []
        
        # Reversal confirmation confluence (HIGHEST PRIORITY)
        if reversal_rejection:
            confluence_factors.append('⭐⭐⭐ BEARISH REVERSAL CONFIRMED AT HOD!')
            confluence_factors.append(f'✓ Tested HOD then {self.reversal_candles} bars of lower highs + lower lows')
            confluence_factors.append('✓ Strong reversal pattern - resistance holding with downtrend forming')
        elif reversal_breakthrough:
            confluence_factors.append('⭐⭐⭐ BULLISH BREAKTHROUGH CONFIRMED AT HOD!')
            confluence_factors.append(f'✓ Broke HOD then {self.reversal_candles} bars of higher highs + higher lows')
            confluence_factors.append('✓ Strong continuation pattern - new uptrend established')
        
        # Event-specific confluence
        elif is_new_event:
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
        
        # Metadata (ENHANCED with retest confirmation + DUAL SIGNALS)
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
            'is_new_event': is_new_event,
            'reversal_rejection': reversal_rejection,
            'reversal_breakthrough': reversal_breakthrough,
            'reversal_candles': self.reversal_candles,
            'bars_monitored': len(self.bars_since_test),
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,  # For simple mode strategies
            'signal_granular': granular_signal,  # For advanced mode strategies
        }
        
        return {
            'signal': signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
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
