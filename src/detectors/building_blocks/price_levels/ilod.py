"""
ILOD (Intraday Low of Day) Building Block
Category: Price Levels
Purpose: TODAY's lowest price for intraday support/resistance

This block tracks the lowest price reached SO FAR during the current trading day.
Differs from LOD which tracks YESTERDAY's low.
"""

from typing import Dict, Any
from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='ilod',
    category='PRICE_LEVELS',
    class_name='ILOD',
    default_weight=20,
    valid_signals=[
        # Granular event signals
        'BEARISH_BREAK',      # Broke below previous ILOD
        'BULLISH_BOUNCE',     # Bounced at ILOD
        'AT_ILOD',           # Price at ILOD
        'ABOVE_ILOD',        # Price above ILOD
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR'
    ],
    signal_tiers={
        'BEARISH_BREAK': {
            'base_points': 22,
            'formula': 'scaled',
            'description': 'Bearish ILOD break - Price broke below previous intraday low. New ILOD made. Bearish momentum signal. Enter shorts on breakdown. Stop above previous ILOD. Target next support.'
        },
        'BULLISH_BOUNCE': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish ILOD bounce - Price bounced at intraday low. Failed breakdown. Reversal signal. Enter longs on bounce. Stop below ILOD. Target resistance levels.'
        },
        'AT_ILOD': {
            'max_points': 15,
            'formula': 'scaled',
            'description': 'At ILOD - Price testing intraday low. Consolidation at support. Watch for breakdown or bounce. Wait for confirmation before entry. Key decision point.'
        },
        'ABOVE_ILOD': {
            'max_points': 10,
            'formula': 'scaled',
            'description': 'Above ILOD - Price above intraday low. Normal state. ILOD acting as support. Watch for move back toward ILOD or continuation higher.'
        },
        'NEUTRAL': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Neutral ILOD - No clear signal from intraday low. Price not near ILOD. Wait for price to approach support or establish new range.'
        },
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate ILOD signals. Check data quality, timestamp availability, and sufficient bar history.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bullish ILOD - Bounce at intraday low confirmed. Strong bullish reversal signal. Long positions favored. Support holding. High probability rally.'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Bearish ILOD - Intraday low breakdown confirmed. Bearish momentum signal. Short positions favored. Support broken. High probability continuation.'
        }
    }
)
class ILOD:
    """
    ILOD - Intraday Low of Day
    
    Tracks TODAY's lowest price reached so far.
    
    Key Differences from LOD:
    - LOD = Yesterday's low (static reference)
    - ILOD = Today's low (dynamic, updates intraday)
    
    Use Cases:
    - Intraday breakdown trading
    - Day trading support levels
    - Scalping range boundaries
    - Real-time support tracking
    
    Signals:
    - BEARISH_BREAK: New ILOD made (breakdown)
    - BULLISH_BOUNCE: Bounced at ILOD (reversal)
    - AT_ILOD: Price testing ILOD
    - ABOVE_ILOD: Price above today's low
    """
    
    def __init__(self, timeframe: str = '15min', **kwargs):
        self.timeframe = timeframe
        self.prev_ilod = None
        self.proximity_threshold = 0.15  # 0.15% = ~$67 on $45k BTC
    
    def _determine_dual_signals(self, distance_pct: float, is_new_ilod: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        if is_new_ilod:
            # Breaking to new ILOD
            granular = 'BEARISH_BREAK'
            simple = 'BEARISH'
        elif abs(distance_pct) < self.proximity_threshold and distance_pct > 0:
            # At ILOD with bounce
            granular = 'BULLISH_BOUNCE'
            simple = 'BULLISH'
        elif abs(distance_pct) < self.proximity_threshold:
            # At ILOD (testing)
            granular = 'AT_ILOD'
            simple = 'NEUTRAL'
        elif distance_pct > 0.5:
            # Above ILOD (normal state)
            granular = 'ABOVE_ILOD'
            simple = 'NEUTRAL'
        else:
            # Fallback
            granular = 'NEUTRAL'
            simple = 'NEUTRAL'
        
        return granular, simple
        
    def calculate_ilod(self, df: pd.DataFrame) -> float:
        """Calculate INTRADAY Low of Day (today's low so far)"""
        if 'timestamp' not in df.columns or 'low' not in df.columns:
            return None
        
        current_time = df['timestamp'].iloc[-1]
        current_date = current_time.date()
        
        # Filter for today's data only
        today_data = df[df['timestamp'].dt.date == current_date]
        
        if len(today_data) == 0:
            return None
        
        # Return lowest low SO FAR today (dynamic, updates as day progresses)
        return float(today_data['low'].min())
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Analyze ILOD level and price relationship"""
        
        # Validation
        if not all(col in df.columns for col in ['timestamp', 'low', 'close']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing required columns'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe
            }
        
        if len(df) < 5:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Insufficient data'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        # Calculate ILOD from bars BEFORE current bar to detect breaks
        ilod_prev = self.calculate_ilod(df.iloc[:-1])
        
        # Calculate ILOD including current bar
        ilod_current = self.calculate_ilod(df)
        
        # Use previous ILOD for comparison, current for tracking
        ilod = ilod_prev if ilod_prev is not None else ilod_current
        
        if ilod is None:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Could not calculate ILOD'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe
            }
        
        current_price = float(df['close'].iloc[-1])
        current_low = float(df['low'].iloc[-1])
        distance_pct = ((current_price - ilod) / ilod) * 100
        
        # Detect events: new ILOD if current bar's low breaks previous ILOD
        is_new_ilod = current_low < ilod
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(distance_pct, is_new_ilod)
        signal = granular_signal
        
        # Determine confidence
        if signal == 'BEARISH_BREAK':
            confidence = 85
        elif signal == 'BULLISH_BOUNCE':
            confidence = 80
        elif signal == 'AT_ILOD':
            confidence = 70
        elif signal == 'ABOVE_ILOD':
            confidence = 60
        else:
            confidence = 50
        
        # Update tracking
        self.prev_ilod = ilod
        
        return {
            'signal': signal,  # Granular signal (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': confidence,
            'metadata': {
                'ilod': round(ilod, 2),
                'current_price': round(current_price, 2),
                'distance_pct': round(distance_pct, 2),
                'is_new_ilod': is_new_ilod,
                'description': f"Today's low: ${ilod:.2f}, Price: ${current_price:.2f} ({distance_pct:+.2f}%)",
                'signal_simple': simple_signal,
                'signal_granular': granular_signal,
            },
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe
        }


if __name__ == "__main__":
    # Test
    print("="*80)
    print("ILOD (INTRADAY LOW OF DAY) TEST")
    print("="*80)
    
    dates = pd.date_range(start='2024-01-01 09:00', periods=50, freq='15min')
    np.random.seed(42)
    
    # Simulate intraday price action
    lows = 45000 - np.cumsum(np.random.uniform(-50, 100, 50))
    closes = lows + np.random.uniform(0, 50, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'low': lows,
        'close': closes,
        'open': closes + 20,
        'high': closes + 50,
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    ilod = ILOD()
    result = ilod.analyze(data)
    
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Description: {result['metadata']['description']}")
    print(f"Is New ILOD: {result['metadata']['is_new_ilod']}")
    print("="*80)
