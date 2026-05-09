"""
Asia Session 50% Price Building Block
Category: Price Levels
Purpose: Mid-point of Asia session range for support/resistance
"""
"""
Building Block Classification: HYBRID BLOCK
Mode: CONTINUOUS TRACKING + EVENT-DRIVEN SIGNALS
Purpose: Track Asia 50% level + signal on breaches during London/US

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events (THIS BLOCK)
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='asia_session_50_percent',
    category='PRICE_LEVELS',
    class_name='AsiaSession50Percent',
    default_weight=20,
    description='Asia Session 50% - Marks the midpoint of the Asian session range as a key reference level. Price often revisits this level during London/NY sessions. Neutral level used for support/resistance and mean-reversion setups.',
    direction='NEUTRAL',
    valid_signals=[
        # Granular position signals
        'ABOVE_ASIA_50', 'AT_ASIA_50', 'BELOW_ASIA_50',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        # Granular position signals
        'ABOVE_ASIA_50': {
                'base_points': 15,
                'formula': 'scaled',
                'description': 'Above Asia 50% - Price above Asia session midpoint. Bullish bias. Asia highs target. Mean reversion down possible. ICT key level.'
        },
        'AT_ASIA_50': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'At Asia 50% - Price at Asia session equilibrium. Key decision level. High-probability bounce or rejection. Mean reversion target. ICT pivot.'
        },
        'BELOW_ASIA_50': {
                'base_points': 15,
                'formula': 'scaled',
                'description': 'Below Asia 50% - Price below Asia session midpoint. Bearish bias. Asia lows target. Mean reversion up possible. ICT key level.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bullish Asia - Above or at Asia 50%. Long positions favorable. Asia session liquidity supporting price.'
        },
        'BEARISH': {
                'base_points': 20,
                'formula': 'scaled',
                'description': 'Bearish Asia - Below Asia 50%. Short positions favorable. Asia session liquidity resisting price.'
        },
        'NEUTRAL': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Neutral Asia - At equilibrium. No clear bias from Asia session. Wait for direction.'
        },
        
        # Status
        'ERROR': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Analysis error - Cannot calculate Asia session 50%. Check data quality and timestamp availability.'
        },
        'INSUFFICIENT_DATA': {
                'points': 0,
                'ui_visible': False,  # Filter from Strategy Builder UI
                'description': 'Insufficient data - Need Asia session data. Wait for Asia session completion.'
        }
}
)
class AsiaSession50Percent:
    """
    Asia Session 50% Price Level (ENHANCED 2026-01-04)
    
    Calculates the 50% level (midpoint) of the Asia session range.
    Critical for:
    - ICT concepts (Asia session liquidity)
    - Mean reversion trading
    - Session transition setups
    - Equilibrium levels
    
    ENHANCEMENTS (2026-01-04):
    - Fixed ALWAYS NEUTRAL bug (was 0% active, now 92%+)
    - Added event tracking for 50% crosses
    - Variable confidence based on distance and events
    - Previous state tracking
    """
    
    def __init__(self, timeframe: str = '15min', 
                 asia_start_utc: int = 0, asia_end_utc: int = 8, **kwargs):
        """Initialize Asia Session 50% block"""
        self.timeframe = timeframe
        self.asia_start = asia_start_utc
        self.asia_end = asia_end_utc
        
        # INSTITUTIONAL: Track previous state for breach detection
        self.prev_signal = None
        self.prev_asia_50 = None
        self.prev_price_above = None  # Track if price was above/below
        
        # INSTITUTIONAL: Track bounce/rejection confirmation
        self.confirmation_candles = 3  # Default: 3 candles for confirmation
        self.bounce_test_bars = []  # Track bars testing support
        self.rejection_test_bars = []  # Track bars testing resistance
        
        # INSTITUTIONAL: Distance thresholds (BTC-optimized)
        self.btc_distance_thresholds = {
            'at_50': 0.2,      # ~90-180 points
            'very_close': 1.0,  # ~450 points
            'close': 2.5,       # ~1,125 points
            'moderate': 5.0,    # ~2,250 points
            'far': 5.0
        }
    
    def _determine_dual_signals(self, distance_pct: float, distance_class: str,
                                 in_asia_session: bool, in_london_us_session: bool,
                                 confirmed_bounce: bool, confirmed_rejection: bool,
                                 breached_50: bool, crossed_50_up: bool, crossed_50_down: bool) -> tuple:
        """DUAL SIGNAL ARCHITECTURE - Returns (granular_signal, simple_signal)"""
        
        # Granular signal: position relative to Asia 50%
        if distance_class == 'AT_ASIA_50':
            granular = 'AT_ASIA_50'
        elif distance_pct > 0:
            granular = 'ABOVE_ASIA_50'
        else:
            granular = 'BELOW_ASIA_50'
        
        # Simple signal: directional bias
        if in_asia_session:
            simple = 'NEUTRAL'  # No signals during Asia (50% forming)
        elif in_london_us_session:
            if confirmed_bounce:
                simple = 'BULLISH'
            elif confirmed_rejection:
                simple = 'BEARISH'
            elif breached_50:
                simple = 'BULLISH' if crossed_50_up else 'BEARISH'
            elif distance_class == 'AT_ASIA_50':
                simple = 'BULLISH' if distance_pct > 0 else 'BEARISH'
            else:
                simple = 'NEUTRAL'
        else:
            simple = 'NEUTRAL'
        
        return granular, simple
    
    def calculate_asia_50(self, df: pd.DataFrame) -> float:
        """Calculate 50% of Asia session range"""
        if 'timestamp' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
            return None
        
        current_date = df['timestamp'].iloc[-1].date()
        
        # Get today's Asia session data
        asia_data = df[
            (df['timestamp'].dt.date == current_date) &
            (df['timestamp'].dt.hour >= self.asia_start) &
            (df['timestamp'].dt.hour < self.asia_end)
        ]
        
        if len(asia_data) == 0:
            # Try previous day
            import pandas as pd
            prev_date = current_date - pd.Timedelta(days=1)
            asia_data = df[
                (df['timestamp'].dt.date == prev_date) &
                (df['timestamp'].dt.hour >= self.asia_start) &
                (df['timestamp'].dt.hour < self.asia_end)
            ]
        
        if len(asia_data) == 0:
            return None
        
        asia_high = float(asia_data['high'].max())
        asia_low = float(asia_data['low'].min())
        
        return (asia_high + asia_low) / 2
    
    def calculate_distance(self, price: float, asia_50: float) -> float:
        """Calculate percentage distance from Asia 50%"""
        if asia_50 is None:
            return None
        return ((price - asia_50) / asia_50) * 100
    
    def classify_distance(self, distance_pct: float) -> str:
        """Classify distance from Asia 50%"""
        if distance_pct is None:
            return 'NO_ASIA_50'
        
        abs_dist = abs(distance_pct)
        
        if abs_dist < self.btc_distance_thresholds['at_50']:
            return 'AT_ASIA_50'
        elif abs_dist < self.btc_distance_thresholds['very_close']:
            return 'VERY_CLOSE'
        elif abs_dist < self.btc_distance_thresholds['close']:
            return 'CLOSE'
        elif abs_dist < self.btc_distance_thresholds['moderate']:
            return 'MODERATE'
        else:
            return 'FAR'
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Main analysis method"""
        if not all(col in df.columns for col in ['timestamp', 'high', 'low', 'close']):
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
                'metadata': {'error': 'No data provided'},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        asia_50 = self.calculate_asia_50(df)
        
        if asia_50 is None:
            return {
                'signal': 'NO_ASIA_DATA',
                'confidence': 0,
                'metadata': {'error': 'No Asia session data found'},
                'timestamp': df['timestamp'].iloc[-1],
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        current_price = float(df['close'].iloc[-1])
        distance_pct = self.calculate_distance(current_price, asia_50)
        distance_class = self.classify_distance(distance_pct)
        
        # INSTITUTIONAL: Determine current session
        current_hour = df['timestamp'].iloc[-1].hour
        in_asia_session = self.asia_start <= current_hour < self.asia_end
        in_london_us_session = current_hour >= self.asia_end  # After Asia close
        
        # INSTITUTIONAL: Detect breaches (ONLY during London/US sessions!)
        # During Asia session, 50% is still forming - no breach signals
        is_new_event = False
        crossed_50_up = False
        crossed_50_down = False
        breached_50 = False
        confirmed_bounce = False
        confirmed_rejection = False
        
        # Track if price is currently above or below 50%
        price_above = distance_pct > 0
        
        # INSTITUTIONAL: Track bounce/rejection confirmation with RETESTS
        # Bounce: Price can breach BELOW 50% but closes ABOVE (support holds)
        # Rejection: Price can breach ABOVE 50% but closes BELOW (resistance holds)
        if in_london_us_session:
            current_bar = {
                'close': current_price,
                'low': float(df['low'].iloc[-1]),
                'high': float(df['high'].iloc[-1]),
                'distance': distance_pct,
                'above_50': price_above,
                'breached_below': float(df['low'].iloc[-1]) < asia_50,  # Wick went below
                'breached_above': float(df['high'].iloc[-1]) > asia_50,  # Wick went above
                'closed_above': current_price > asia_50,
                'closed_below': current_price < asia_50
            }
            
            # BOUNCE TEST: Price wicks BELOW 50% but closes ABOVE (building support)
            # This shows price testing support and holding
            if current_bar['breached_below'] and current_bar['closed_above']:
                self.bounce_test_bars.append(current_bar)
                # Keep only recent bars (confirmation window)
                if len(self.bounce_test_bars) > self.confirmation_candles + 2:
                    self.bounce_test_bars.pop(0)
                
                # Check for confirmed bounce (X consecutive tests of support)
                if len(self.bounce_test_bars) >= self.confirmation_candles:
                    # Last X candles: all breached below but closed above
                    recent_bars = self.bounce_test_bars[-self.confirmation_candles:]
                    all_tested_and_held = all(
                        bar['breached_below'] and bar['closed_above'] 
                        for bar in recent_bars
                    )
                    
                    # Confirmed if: support tested X times and held each time
                    if all_tested_and_held:
                        confirmed_bounce = True
                        is_new_event = True
                        self.bounce_test_bars = []  # Reset after confirmation
            elif distance_class not in ['AT_ASIA_50', 'VERY_CLOSE']:
                # Price moved far away, reset bounce tracking
                if len(self.bounce_test_bars) > 0:
                    self.bounce_test_bars = []
            
            # REJECTION TEST: Price wicks ABOVE 50% but closes BELOW (resistance holds)
            # This shows price testing resistance and getting rejected
            if current_bar['breached_above'] and current_bar['closed_below']:
                self.rejection_test_bars.append(current_bar)
                # Keep only recent bars
                if len(self.rejection_test_bars) > self.confirmation_candles + 2:
                    self.rejection_test_bars.pop(0)
                
                # Check for confirmed rejection (X consecutive tests of resistance)
                if len(self.rejection_test_bars) >= self.confirmation_candles:
                    recent_bars = self.rejection_test_bars[-self.confirmation_candles:]
                    all_tested_and_rejected = all(
                        bar['breached_above'] and bar['closed_below']
                        for bar in recent_bars
                    )
                    
                    # Confirmed if: resistance tested X times and rejected each time
                    if all_tested_and_rejected:
                        confirmed_rejection = True
                        is_new_event = True
                        self.rejection_test_bars = []  # Reset after confirmation
            elif distance_class not in ['AT_ASIA_50', 'VERY_CLOSE']:
                # Price moved far away, reset rejection tracking
                if len(self.rejection_test_bars) > 0:
                    self.rejection_test_bars = []
        
        if in_london_us_session and self.prev_price_above is not None:
            # Only detect breaches AFTER Asia session closes
            # Asia 50% is now FIXED for the day
            if self.prev_price_above == False and price_above == True:
                # Crossed UP through 50%
                crossed_50_up = True
                breached_50 = True
                is_new_event = True
            elif self.prev_price_above == True and price_above == False:
                # Crossed DOWN through 50%
                crossed_50_down = True
                breached_50 = True
                is_new_event = True
        
        # INSTITUTIONAL: Signal logic (EVENT-DRIVEN - highly selective)
        # NO SIGNALS during Asia session (50% still forming)
        # ONLY signal during London/US sessions (50% is FIXED)
        if in_asia_session:
            # During Asia session - 50% is still forming
            # No signals, just NEUTRAL tracking
            signal = 'NEUTRAL'
            
        elif in_london_us_session:
            # After Asia close - 50% is FIXED for the day
            # Now we can signal on breaches, confirmations, and proximity
            
            if confirmed_bounce:
                # CONFIRMED BOUNCE - price bounced off 50% support (BULLISH)
                signal = 'BULLISH'
                is_new_event = True
                
            elif confirmed_rejection:
                # CONFIRMED REJECTION - price rejected from 50% resistance (BEARISH)
                signal = 'BEARISH'
                is_new_event = True
                
            elif breached_50:
                # BREACH EVENT - crossing through 50%
                if crossed_50_up:
                    signal = 'BULLISH'  # Crossed up - bullish momentum
                else:
                    signal = 'BEARISH'  # Crossed down - bearish momentum
                    
            elif distance_class == 'AT_ASIA_50':
                # AT equilibrium - signal based on position
                if self.prev_signal == 'NEUTRAL':
                    # Just entered AT zone
                    is_new_event = True
                    if distance_pct > 0:
                        signal = 'BULLISH'  # Testing support
                    else:
                        signal = 'BEARISH'  # Testing resistance
                else:
                    # Continue previous signal (not new event)
                    signal = self.prev_signal if self.prev_signal else 'NEUTRAL'
            else:
                # NEUTRAL - away from 50%
                signal = 'NEUTRAL'
                # Detect if exiting active zone
                if self.prev_signal is not None and self.prev_signal != 'NEUTRAL':
                    is_new_event = True  # Exiting zone
        else:
            # Edge case: before Asia session starts
            signal = 'NEUTRAL'
        
        # INSTITUTIONAL: Optimized Variable Confidence (target: 75-85% avg)
        if distance_class == 'AT_ASIA_50':
            base = 80  # At exact equilibrium (reduced from 90)
        elif distance_class == 'VERY_CLOSE':
            base = 75  # Very close (reduced from 85)
        elif distance_class == 'CLOSE':
            base = 65  # Approaching (reduced from 80)
        elif distance_class == 'MODERATE':
            base = 55  # Moderate (reduced from 75)
        else:
            base = 50  # Far/NEUTRAL (reduced from 65)
        
        # Event modifiers (±15%)
        if confirmed_bounce or confirmed_rejection:
            # CONFIRMED EVENT - highest priority (3 candles confirmation)
            base = min(95, base + 20)
        elif breached_50:
            # Major event - price crossed 50% level
            base = min(95, base + 15)
        elif is_new_event:
            # State change event
            base = min(95, base + 10)
        
        confidence = base
        
        # Build confluence
        confluence_factors = []
        
        # Event-specific confluence (INSTITUTIONAL)
        if confirmed_bounce:
            confluence_factors.append('⭐⭐ CONFIRMED BOUNCE OFF ASIA 50% - Strong bullish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked below, closed above (support holding!)')
        elif confirmed_rejection:
            confluence_factors.append('⭐⭐ CONFIRMED REJECTION FROM ASIA 50% - Strong bearish setup!')
            confluence_factors.append(f'✓ {self.confirmation_candles} retests: wicked above, closed below (resistance holding!)')
        elif crossed_50_up:
            confluence_factors.append('⭐ BREACHED ASIA 50% UPWARD - Bullish momentum!')
        elif crossed_50_down:
            confluence_factors.append('⭐ BREACHED ASIA 50% DOWNWARD - Bearish momentum!')
        elif is_new_event:
            if signal != 'NEUTRAL' and self.prev_signal == 'NEUTRAL':
                confluence_factors.append('⭐ ENTERING ASIA 50% ZONE - New setup')
            elif signal == 'NEUTRAL' and self.prev_signal != 'NEUTRAL':
                confluence_factors.append('Exiting Asia 50% zone')
        
        if distance_class in ['AT_ASIA_50', 'VERY_CLOSE']:
            if signal == 'BULLISH':
                confluence_factors.append('Price testing Asia 50% support - bounce setup')
            elif signal == 'BEARISH':
                confluence_factors.append('Price testing Asia 50% resistance - rejection setup')
        
        confluence_factors.append(f'Asia 50%: ${asia_50:.2f}')
        confluence_factors.append(f'Distance: {distance_pct:+.2f}% ({distance_class})')
        
        # Update tracking (INSTITUTIONAL - includes price_above)
        self.prev_signal = signal
        self.prev_asia_50 = asia_50
        self.prev_price_above = price_above
        
        # Determine session name
        if in_asia_session:
            current_session = 'ASIA'
        elif 8 <= current_hour < 16:
            current_session = 'LONDON'
        elif current_hour >= 13:  # US opens at 13:00 UTC
            current_session = 'US' if current_hour >= 16 else 'LONDON_US_OVERLAP'
        else:
            current_session = 'AFTER_HOURS'
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(
            distance_pct, distance_class, in_asia_session, in_london_us_session,
            confirmed_bounce, confirmed_rejection, breached_50, crossed_50_up, crossed_50_down
        )
        
        # Gate granular signal on is_new_event so AT_ASIA_50 only fires on new entry events,
        # not on every bar where price is within 0.3% of the Asia mid.
        # Without this gate the block fired on ~32% of all bars (positional noise).
        signal = granular_signal if is_new_event else 'NEUTRAL'
        # simple_signal retains its own event-driven logic (used for simple mode compatibility)
        
        metadata = {
            'asia_50': round(asia_50, 2),
            'current_price': round(current_price, 2),
            'distance_pct': round(distance_pct, 2),
            'distance_class': distance_class,
            'is_at_equilibrium': distance_class in ['AT_ASIA_50', 'VERY_CLOSE'],
            'asia_session_hours': f'{self.asia_start}:00-{self.asia_end}:00 UTC',
            'current_session': current_session,
            'asia_50_fixed': in_london_us_session,
            'is_new_event': is_new_event,
            'breached_50': breached_50,
            'crossed_50_up': crossed_50_up,
            'crossed_50_down': crossed_50_down,
            'confirmed_bounce': confirmed_bounce,
            'confirmed_rejection': confirmed_rejection,
            'confirmation_candles': self.confirmation_candles,
            'price_above_50': price_above,
            # DUAL SIGNAL ARCHITECTURE
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
        }
        
        return {
            'signal': signal,  # Granular signal gated on is_new_event (primary)
            'signal_simple': simple_signal,  # Simple signal (for strategy builder)
            'confidence': round(confidence, 2),
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
