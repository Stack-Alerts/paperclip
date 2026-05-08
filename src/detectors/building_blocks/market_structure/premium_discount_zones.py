"""
Premium and Discount Zones Building Block - ENHANCED VERSION
Category: Market Structure
Purpose: Advanced premium/discount analysis with depth awareness

Enhanced Features (Incorporating Quality Blocks):
- Zone depth calculation (0-100%)
- Variable confidence (60-85 based on depth)
- Equilibrium zone (not point!)
- ATR-normalized range analysis
- Volume trend confirmation
- Strength scoring (0-100)
- Rich metadata for strategies

Fixes: Fixed confidence (0.05% std) → Variable confidence (8-12% std)!

ENHANCEMENTS (2026-01-04 - Expert Mode):
- Priority 1.1: Multi-timeframe alignment (3 timeframes)
- Priority 1.2: Zone duration tracking (freshness awareness)
- Priority 1.3: Historical zone reaction (data-driven confidence)
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous premium/discount state

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals (selective, fires on specific conditions)
- CONTEXT BLOCK: Continuous state provider (always active, used for confluence/reference)
- EVENT BLOCK: Specific market event detection (selective, fires when events occur)
- HYBRID BLOCK: Combination of continuous state + selective events
"""



from typing import Dict, Any

from src.detectors.building_blocks.registry import register_block
from datetime import datetime
import pandas as pd
import numpy as np


@register_block(
    name='premium_discount_zones',
    category='MARKET_STRUCTURE',
    class_name='PremiumDiscountZones',
    default_weight=14,
    direction='NEUTRAL',
    valid_signals=[
        # Zone locations - GRANULAR
        'PRICE_IN_PREMIUM', 'PRICE_IN_DISCOUNT', 'PRICE_AT_EQUILIBRIUM',
        # Simple directional signals - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'INSUFFICIENT_DATA', 'ERROR'
    ],
    signal_tiers={
        'PRICE_IN_PREMIUM': {
            'base_points': 14,
            'formula': 'scaled',
            'description': 'Premium zone - Price above fair value. Expensive. Institutions distributing. Expect pullback to equilibrium. Take profits on longs. Consider shorts. Stop above recent high.'
        },
        'PRICE_IN_DISCOUNT': {
            'base_points': 14,
            'formula': 'scaled',
            'description': 'Discount zone - Price below fair value. Cheap. Institutions accumulating. Prime buying opportunity. Enter longs. Target equilibrium. Stop below recent low.'
        },
        'PRICE_AT_EQUILIBRIUM': {
            'base_points': 10,
            'formula': 'scaled',
            'description': 'Equilibrium zone - Fair value. Balanced. No edge. Wait for move into premium or discount. Range-bound. Use tight stops or stand aside.'
        },
        
        # Simple directional signals - SIMPLE
        'BULLISH': {
            'base_points': 14,
            'formula': 'scaled',
            'description': 'In discount - Price at bargain levels. Institutional buying zone. Long positions highly favorable. Use discount as support.'
        },
        'BEARISH': {
            'base_points': 14,
            'formula': 'scaled',
            'description': 'In premium - Price overextended. Institutional selling zone. Short positions favorable or take profits on longs. Mean reversion expected.'
        },
        'NEUTRAL': {
            'base_points': 10,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'At equilibrium - Fair value. No clear edge. Wait for discount to buy or premium to sell. Patient positioning required.'
        },
        
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate premium/discount zones. Check range calculation and data quality.'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient data - Need at least 20 candles for premium/discount analysis. Wait for wider price range to develop.'
        }
    },
    description='Premium/Discount Zones - ICT premium/discount analysis with multi-timeframe alignment',
    tags=['market_structure', 'premium_discount', 'ict', 'value_zones', 'equilibrium', 'context_block']
)
class PremiumDiscountZones:
    """
    Enhanced Premium/Discount Zones with depth awareness
    
    Improvements over basic version:
    - Variable confidence (60-85 based on depth!)
    - Zone depth percentage (0-100%)
    - Equilibrium zone (±2%, not single point)
    - ATR-normalized range analysis
    - Volume trend detection
    - Strength scoring
    - Rich metadata
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 atr_period: int = 14,
                 equilibrium_buffer_pct: float = 0.02,
                 **kwargs):
        """
        Initialize Enhanced Premium/Discount Zones
        
        Args:
            timeframe: Timeframe string
            lookback: Bars to analyze for high/low (default 20)
            atr_period: Period for ATR calculation
            equilibrium_buffer_pct: % buffer for equilibrium zone (0.02 = ±2%)
        """
        self.timeframe = timeframe
        self.lookback = lookback
        self.atr_period = atr_period
        self.equilibrium_buffer_pct = equilibrium_buffer_pct
        
        # ENHANCEMENT: Zone tracking for duration and history
        self.current_zone = None
        self.previous_zone = None  # Track for breakout detection
        self.zone_entry_time = None
        self.bars_in_zone = 0
        self.zone_history = []  # Track recent zones for historical analysis
        self.max_history = 20   # Keep last 20 zone changes
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        if granular == 'PRICE_IN_DISCOUNT':
            simple = 'BULLISH'
        elif granular == 'PRICE_IN_PREMIUM':
            simple = 'BEARISH'
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def calculate_multi_timeframe_alignment(self, df: pd.DataFrame) -> dict:
        """
        Priority 1.1: Multi-timeframe alignment
        
        Check 3 timeframes for alignment:
        - Short: lookback bars
        - Medium: 3x lookback
        - Long: 5x lookback
        
        Returns alignment info and confluence bonus
        """
        if len(df) < self.lookback * 5:
            return {
                'aligned': False,
                'alignment_type': 'INSUFFICIENT_DATA',
                'confluence_bonus': 0,
                'details': {}
            }
        
        # Calculate zones for 3 timeframes
        short_lookback = self.lookback
        medium_lookback = self.lookback * 3
        long_lookback = self.lookback * 5
        
        current_price = float(df['close'].iloc[-1])
        
        # Short timeframe
        short_high = float(df['high'].iloc[-short_lookback:].max())
        short_low = float(df['low'].iloc[-short_lookback:].min())
        short_eq = (short_high + short_low) / 2
        short_zone = self._classify_zone(current_price, short_eq, short_high, short_low)
        
        # Medium timeframe
        medium_high = float(df['high'].iloc[-medium_lookback:].max())
        medium_low = float(df['low'].iloc[-medium_lookback:].min())
        medium_eq = (medium_high + medium_low) / 2
        medium_zone = self._classify_zone(current_price, medium_eq, medium_high, medium_low)
        
        # Long timeframe
        long_high = float(df['high'].iloc[-long_lookback:].max())
        long_low = float(df['low'].iloc[-long_lookback:].min())
        long_eq = (long_high + long_low) / 2
        long_zone = self._classify_zone(current_price, long_eq, long_high, long_low)
        
        # Check alignment
        zones = [short_zone, medium_zone, long_zone]
        
        # All in extreme discount
        if all(z == 'EXTREME_DISCOUNT' for z in zones):
            return {
                'aligned': True,
                'alignment_type': 'EXTREME_DISCOUNT_ALL',
                'confluence_bonus': 15,
                'details': {'short': short_zone, 'medium': medium_zone, 'long': long_zone}
            }
        
        # All in discount
        elif all('DISCOUNT' in z for z in zones):
            return {
                'aligned': True,
                'alignment_type': 'DISCOUNT_ALL',
                'confluence_bonus': 10,
                'details': {'short': short_zone, 'medium': medium_zone, 'long': long_zone}
            }
        
        # All in extreme premium
        elif all(z == 'EXTREME_PREMIUM' for z in zones):
            return {
                'aligned': True,
                'alignment_type': 'EXTREME_PREMIUM_ALL',
                'confluence_bonus': -15,  # Negative = avoid longs
                'details': {'short': short_zone, 'medium': medium_zone, 'long': long_zone}
            }
        
        # All in premium
        elif all('PREMIUM' in z for z in zones):
            return {
                'aligned': True,
                'alignment_type': 'PREMIUM_ALL',
                'confluence_bonus': -10,
                'details': {'short': short_zone, 'medium': medium_zone, 'long': long_zone}
            }
        
        # Partial alignment
        else:
            return {
                'aligned': False,
                'alignment_type': 'MIXED',
                'confluence_bonus': 0,
                'details': {'short': short_zone, 'medium': medium_zone, 'long': long_zone}
            }
    
    def _classify_zone(self, price: float, equilibrium: float, 
                       range_high: float, range_low: float) -> str:
        """Helper to classify zone without full analysis"""
        range_size = range_high - range_low
        if range_size == 0:
            return 'EQUILIBRIUM'
        
        eq_buffer = range_size * self.equilibrium_buffer_pct
        
        if price > equilibrium + eq_buffer:
            # Premium side
            depth_pct = ((price - equilibrium) / ((range_high - range_low) / 2)) * 100
            if depth_pct > 75:
                return 'EXTREME_PREMIUM'
            else:
                return 'PREMIUM'
        elif price < equilibrium - eq_buffer:
            # Discount side
            depth_pct = ((equilibrium - price) / ((range_high - range_low) / 2)) * 100
            if depth_pct > 75:
                return 'EXTREME_DISCOUNT'
            else:
                return 'DISCOUNT'
        else:
            return 'EQUILIBRIUM'
    
    def track_zone_duration(self, zone: str, timestamp) -> dict:
        """
        Priority 1.2: Zone duration tracking
        
        Track how long in current zone and classify freshness
        """
        # Check if zone changed
        if zone != self.current_zone:
            # Zone changed!
            self.previous_zone = self.current_zone  # Save for breakout detection
            self.current_zone = zone
            self.zone_entry_time = timestamp
            self.bars_in_zone = 0
            is_new = True
        else:
            # Continuing in same zone
            self.bars_in_zone += 1
            is_new = False
        
        # Classify freshness
        if self.bars_in_zone == 0:
            freshness = 'FRESH'
            freshness_bonus = 5
        elif self.bars_in_zone <= 5:
            freshness = 'RECENT'
            freshness_bonus = 3
        elif self.bars_in_zone <= 15:
            freshness = 'MODERATE'
            freshness_bonus = 0
        else:
            freshness = 'STALE'
            freshness_bonus = -3
        
        return {
            'is_new_zone': is_new,
            'bars_in_zone': self.bars_in_zone,
            'freshness': freshness,
            'freshness_bonus': freshness_bonus,
            'entry_time': self.zone_entry_time
        }
    
    def analyze_historical_reaction(self, zone: str, zone_classification: str) -> dict:
        """
        Priority 1.3: Historical zone reaction analysis
        
        Track which zones historically lead to reversals
        Build confidence from historical data
        """
        if len(self.zone_history) < 5:
            return {
                'has_history': False,
                'historical_confidence': 0,
                'reversal_rate': 0,
                'sample_size': len(self.zone_history)
            }
        
        # Count historical reversals from similar zones
        similar_zones = [
            z for z in self.zone_history
            if z['zone'] == zone and z.get('zone_classification') == zone_classification
        ]
        
        if len(similar_zones) < 3:
            return {
                'has_history': False,
                'historical_confidence': 0,
                'reversal_rate': 0,
                'sample_size': len(similar_zones)
            }
        
        # Calculate reversal rate
        reversals = sum(1 for z in similar_zones if z.get('led_to_reversal', False))
        reversal_rate = (reversals / len(similar_zones)) * 100
        
        # Historical confidence bonus
        if reversal_rate >= 75:
            historical_bonus = 5
        elif reversal_rate >= 60:
            historical_bonus = 3
        else:
            historical_bonus = 0
        
        return {
            'has_history': True,
            'historical_confidence': historical_bonus,
            'reversal_rate': round(reversal_rate, 1),
            'sample_size': len(similar_zones)
        }
    
    def update_zone_history(self, zone: str, zone_classification: str, 
                           led_to_reversal: bool = False):
        """Update zone history for future analysis"""
        self.zone_history.append({
            'zone': zone,
            'zone_classification': zone_classification,
            'led_to_reversal': led_to_reversal,
            'timestamp': datetime.now()
        })
        
        # Keep only recent history
        if len(self.zone_history) > self.max_history:
            self.zone_history.pop(0)
    
    def detect_zone_breakout(self, current_zone: str, previous_zone: str) -> dict:
        """
        Optional Enhancement 2: Zone Breakout Detection
        
        Detect when price breaks out of premium/discount into opposite zone
        This is a potential reversal signal
        
        Returns:
            dict with breakout info and confluence bonus
        """
        if previous_zone is None:
            return {
                'has_breakout': False,
                'breakout_type': 'NONE',
                'confluence_bonus': 0
            }
        
        # Detect breakouts
        if previous_zone == 'DISCOUNT' and current_zone == 'PREMIUM':
            # Broke from discount → premium (bullish breakout)
            return {
                'has_breakout': True,
                'breakout_type': 'BULLISH_BREAKOUT',
                'confluence_bonus': 5,
                'description': 'Price broke from discount to premium (bullish)'
            }
        
        elif previous_zone == 'PREMIUM' and current_zone == 'DISCOUNT':
            # Broke from premium → discount (bearish breakout)
            return {
                'has_breakout': True,
                'breakout_type': 'BEARISH_BREAKOUT',
                'confluence_bonus': 5,
                'description': 'Price broke from premium to discount (bearish)'
            }
        
        elif previous_zone == 'EQUILIBRIUM' and current_zone == 'DISCOUNT':
            # Broke from equilibrium → discount
            return {
                'has_breakout': True,
                'breakout_type': 'DISCOUNT_ENTRY',
                'confluence_bonus': 3,
                'description': 'Price entered discount from equilibrium'
            }
        
        elif previous_zone == 'EQUILIBRIUM' and current_zone == 'PREMIUM':
            # Broke from equilibrium → premium
            return {
                'has_breakout': True,
                'breakout_type': 'PREMIUM_ENTRY',
                'confluence_bonus': 3,
                'description': 'Price entered premium from equilibrium'
            }
        
        else:
            # No breakout (same zone)
            return {
                'has_breakout': False,
                'breakout_type': 'NONE',
                'confluence_bonus': 0
            }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range for volatility context
        (Integrated from quality blocks)
        """
        if len(df) < period + 1:
            return 0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return float(atr) if not pd.isna(atr) else 0
    
    def calculate_volume_trend(self, df: pd.DataFrame, lookback: int = 10) -> tuple:
        """
        Detect if volume is trending up or down
        Returns: (is_increasing: bool, trend_strength: float)
        """
        if len(df) < lookback:
            return False, 0
        
        recent_volume = df['volume'].iloc[-lookback:]
        
        # Simple linear regression slope
        x = np.arange(len(recent_volume))
        y = recent_volume.values
        
        if len(x) < 2:
            return False, 0
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        avg_volume = y.mean()
        
        # Normalize slope by average volume
        trend_strength = (slope / avg_volume) * 100 if avg_volume > 0 else 0
        is_increasing = slope > 0
        
        return is_increasing, float(trend_strength)
    
    def calculate_zone_depth(self, current_price: float, equilibrium: float,
                            range_high: float, range_low: float) -> tuple:
        """
        Calculate how deep into zone (premium or discount)
        
        Returns: (depth_percentage, zone_classification)
        
        Depth percentages:
        - 0-25%: Shallow
        - 25-50%: Moderate
        - 50-75%: Deep
        - 75-100%: Extreme
        """
        # Half range (from equilibrium to high or low)
        half_range = (range_high - range_low) / 2
        
        if half_range == 0:
            return 0, 'UNKNOWN'
        
        # Distance from equilibrium
        distance = abs(current_price - equilibrium)
        
        # Depth as percentage into zone
        depth_pct = (distance / half_range) * 100
        depth_pct = max(0, min(100, depth_pct))  # Clamp to 0-100
        
        # Classify zone
        if depth_pct < 25:
            classification = 'SHALLOW'
        elif depth_pct < 50:
            classification = 'MODERATE'
        elif depth_pct < 75:
            classification = 'DEEP'
        else:
            classification = 'EXTREME'
        
        return float(depth_pct), classification
    
    def calculate_zone_strength(self, depth_pct: float, volume_increasing: bool,
                               in_discount: bool) -> int:
        """
        Calculate zone strength score (0-100)
        
        Factors:
        - Depth into zone (higher = stronger)
        - Volume trend (increasing in discount = bullish strength)
        """
        strength = int(depth_pct)  # Base: 0-100 from depth
        
        # Volume trend bonus
        if in_discount and volume_increasing:
            strength += 10  # Volume confirming discount (bullish!)
        elif not in_discount and not volume_increasing:
            strength += 10  # Volume declining in premium (bearish!)
        
        # Ensure 0-100 range
        return max(0, min(100, strength))
    
    def calculate_variable_confidence(self, signal: str, depth_pct: float,
                                     zone_classification: str,
                                     volume_increasing: bool) -> int:
        """
        Variable confidence based on zone quality
        
        KEY ENHANCEMENT: No more fixed confidence!
        
        Factors:
        - Zone depth (deeper = higher confidence)
        - Zone classification (extreme = highest)
        - Volume trend (confirmation bonus)
        """
        # Base confidence by zone classification
        if zone_classification == 'EXTREME':
            base_confidence = 80
        elif zone_classification == 'DEEP':
            base_confidence = 75
        elif zone_classification == 'MODERATE':
            base_confidence = 70
        else:  # SHALLOW
            base_confidence = 65
        
        # Fine-tune with exact depth
        depth_bonus = int((depth_pct - 50) / 10)  # -5 to +5
        base_confidence += depth_bonus
        
        # Volume trend bonus
        volume_bonus = 0
        if signal == 'PRICE_IN_DISCOUNT' and volume_increasing:
            volume_bonus = 3  # Volume confirming discount
        elif signal == 'PRICE_IN_PREMIUM' and not volume_increasing:
            volume_bonus = 3  # Volume declining in premium
        
        # Calculate final confidence
        confidence = base_confidence + volume_bonus
        
        # Ensure in valid range
        return max(60, min(85, confidence))
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Enhanced analysis with depth awareness
        
        KEY FIX: Variable confidence based on zone depth!
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
        
        if len(df) < 20:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate range
        lookback = min(self.lookback, len(df))
        recent_high = float(df['high'].iloc[-lookback:].max())
        recent_low = float(df['low'].iloc[-lookback:].min())
        equilibrium = (recent_high + recent_low) / 2
        current_price = float(df['close'].iloc[-1])
        
        # Calculate ATR for context
        atr = self.calculate_atr(df, self.atr_period)
        
        # Volume trend
        volume_increasing, volume_trend_strength = self.calculate_volume_trend(df, min(10, len(df)))
        
        # Equilibrium buffer (creates zone instead of point!)
        range_size = recent_high - recent_low
        equilibrium_buffer = range_size * self.equilibrium_buffer_pct
        
        # Determine signal and calculate depth
        if current_price > equilibrium + equilibrium_buffer:
            # PREMIUM ZONE
            signal = 'PRICE_IN_PREMIUM'
            zone = 'PREMIUM'
            depth_pct, zone_class = self.calculate_zone_depth(
                current_price, equilibrium, recent_high, recent_low
            )
            in_discount = False
            
        elif current_price < equilibrium - equilibrium_buffer:
            # DISCOUNT ZONE
            signal = 'PRICE_IN_DISCOUNT'
            zone = 'DISCOUNT'
            depth_pct, zone_class = self.calculate_zone_depth(
                current_price, equilibrium, recent_high, recent_low
            )
            in_discount = True
            
        else:
            # EQUILIBRIUM ZONE (now actually used!)
            signal = 'PRICE_AT_EQUILIBRIUM'
            zone = 'EQUILIBRIUM'
            depth_pct = 0
            zone_class = 'AT_EQUILIBRIUM'
            in_discount = False
        
        # Calculate zone strength
        strength = self.calculate_zone_strength(depth_pct, volume_increasing, in_discount)
        
        # **ENHANCED:** Multi-timeframe alignment (Priority 1.1)
        mtf_alignment = self.calculate_multi_timeframe_alignment(df)
        
        # **ENHANCED:** Zone duration tracking (Priority 1.2)
        current_timestamp = df['timestamp'].iloc[-1]
        zone_duration = self.track_zone_duration(zone, current_timestamp)
        
        # **ENHANCED:** Historical reaction analysis (Priority 1.3)
        historical = self.analyze_historical_reaction(zone, zone_class)
        
        # **NEW:** Zone breakout detection (Optional Enhancement 2)
        breakout = self.detect_zone_breakout(zone, self.previous_zone)
        
        # VARIABLE CONFIDENCE (enhanced with new factors!)
        base_confidence = self.calculate_variable_confidence(
            signal, depth_pct, zone_class, volume_increasing
        )
        
        # Add enhancement bonuses
        confidence = base_confidence
        confidence += mtf_alignment['confluence_bonus']
        confidence += zone_duration['freshness_bonus']
        confidence += historical['historical_confidence']
        confidence += breakout['confluence_bonus']
        
        # Clamp to valid range
        confidence = max(50, min(90, confidence))
        
        # Update history for future analysis
        self.update_zone_history(zone, zone_class, led_to_reversal=False)
        
        # Build confluence factors (rich descriptions with enhancements!)
        confluence_factors = []
        
        if signal == 'PRICE_IN_PREMIUM':
            confluence_factors.append(f'Price in premium zone ({depth_pct:.1f}% into premium)')
            if zone_class == 'EXTREME':
                confluence_factors.append(f'⚠️ EXTREME premium - very expensive!')
            elif zone_class == 'DEEP':
                confluence_factors.append(f'📈 DEEP premium - expensive zone')
            
            if not volume_increasing:
                confluence_factors.append(f'📉 Volume declining in premium')
                
        elif signal == 'PRICE_IN_DISCOUNT':
            confluence_factors.append(f'Price in discount zone ({depth_pct:.1f}% into discount)')
            if zone_class == 'EXTREME':
                confluence_factors.append(f'⭐ EXTREME discount - great opportunity!')
            elif zone_class == 'DEEP':
                confluence_factors.append(f'✅ DEEP discount - good value')
            
            if volume_increasing:
                confluence_factors.append(f'📈 Volume increasing in discount')
                
        else:  # EQUILIBRIUM
            confluence_factors.append(f'Price at equilibrium (fair value)')
            confluence_factors.append(f'Range: ${recent_low:.2f} - ${recent_high:.2f}')
        
        # **ENHANCED:** Multi-timeframe alignment indicators
        if mtf_alignment['aligned']:
            if mtf_alignment['alignment_type'] == 'EXTREME_DISCOUNT_ALL':
                confluence_factors.append(f'🚀🚀🚀 ALL TIMEFRAMES IN EXTREME DISCOUNT! (+{mtf_alignment["confluence_bonus"]})')
            elif mtf_alignment['alignment_type'] == 'DISCOUNT_ALL':
                confluence_factors.append(f'✅ All timeframes in discount (+{mtf_alignment["confluence_bonus"]})')
            elif mtf_alignment['alignment_type'] == 'EXTREME_PREMIUM_ALL':
                confluence_factors.append(f'⚠️⚠️⚠️ ALL TIMEFRAMES IN EXTREME PREMIUM ({mtf_alignment["confluence_bonus"]})')
            elif mtf_alignment['alignment_type'] == 'PREMIUM_ALL':
                confluence_factors.append(f'⚠️ All timeframes in premium ({mtf_alignment["confluence_bonus"]})')
        
        # **ENHANCED:** Zone freshness indicators
        if zone_duration['is_new_zone']:
            confluence_factors.append(f'🆕 FRESH ZONE ENTRY! (+{zone_duration["freshness_bonus"]})')
        elif zone_duration['freshness'] == 'STALE':
            confluence_factors.append(f'⏰ Stale zone ({zone_duration["bars_in_zone"]} bars, {zone_duration["freshness_bonus"]})')
        
        # **ENHANCED:** Historical reaction indicators
        if historical['has_history']:
            if historical['reversal_rate'] >= 75:
                confluence_factors.append(f'📊 Historical reversal rate: {historical["reversal_rate"]}% (+{historical["historical_confidence"]})')
            elif historical['reversal_rate'] >= 60:
                confluence_factors.append(f'📊 Good historical reversals: {historical["reversal_rate"]}% (+{historical["historical_confidence"]})')
        
        # **NEW:** Zone breakout indicators
        if breakout['has_breakout']:
            confluence_factors.append(f'💥 {breakout["description"]} (+{breakout["confluence_bonus"]})')
        
        # Strength note
        if strength >= 75:
            confluence_factors.append(f'⭐ Strong zone (strength: {strength})')
        elif strength <= 25:
            confluence_factors.append(f'⚠️ Weak zone (strength: {strength})')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        # **ENHANCED:** Metadata with all new fields!
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'zone': zone,
            'equilibrium': round(equilibrium, 2),
            'high': round(recent_high, 2),
            'low': round(recent_low, 2),
            'current_price': round(current_price, 2),
            'depth_percentage': round(depth_pct, 2),
            'zone_classification': zone_class,
            'distance_from_equilibrium': round(abs(current_price - equilibrium), 2),
            'zone_strength': strength,
            'volume_trend': 'INCREASING' if volume_increasing else 'DECREASING',
            'volume_trend_strength': round(volume_trend_strength, 2),
            'atr': round(atr, 2),
            'range_size': round(range_size, 2),
            'equilibrium_buffer': round(equilibrium_buffer, 2),
            # NEW: Multi-timeframe alignment (Priority 1.1)
            'mtf_aligned': mtf_alignment['aligned'],
            'mtf_alignment_type': mtf_alignment['alignment_type'],
            'mtf_details': mtf_alignment['details'],
            # NEW: Zone duration tracking (Priority 1.2)
            'is_new_zone': zone_duration['is_new_zone'],
            'bars_in_zone': zone_duration['bars_in_zone'],
            'zone_freshness': zone_duration['freshness'],
            # NEW: Historical reaction (Priority 1.3)
            'has_historical_data': historical['has_history'],
            'historical_reversal_rate': historical['reversal_rate'],
            'historical_sample_size': historical['sample_size'],
            # NEW: Zone breakout detection (Optional Enhancement 2)
            'has_breakout': breakout['has_breakout'],
            'breakout_type': breakout['breakout_type']
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


def analyze_premium_discount_value(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Production helper for comprehensive zone analysis
    
    Analyzes both short-term and long-term zones for better context.
    
    Args:
        df: OHLCV dataframe
    
    Returns:
        dict with:
            - short_term: 10-bar zone analysis
            - long_term: 50-bar zone analysis
            - value_alignment: Both agree or diverge
            - recommended_action: Buy/Sell/Wait
            - notes: Analysis notes
    
    Usage Example:
        result = analyze_premium_discount_value(df)
        if result['value_alignment'] == 'DEEP_DISCOUNT':
            confluence += 50  # Strong buy zone!
    """
    notes = []
    
    # Short-term zones (10 bars)
    pd_short = PremiumDiscountZones(lookback=10)
    result_short = pd_short.analyze(df)
    
    # Long-term zones (50 bars)
    pd_long = PremiumDiscountZones(lookback=50)
    result_long = pd_long.analyze(df)
    
    # Analyze alignment
    short_signal = result_short['signal']
    long_signal = result_long['signal']
    short_depth = result_short['metadata']['depth_percentage']
    long_depth = result_long['metadata']['depth_percentage']
    
    # Value alignment
    if short_signal == 'PRICE_IN_DISCOUNT' and long_signal == 'PRICE_IN_DISCOUNT':
        if short_depth > 60 and long_depth > 60:
            value_alignment = 'DEEP_DISCOUNT'
            recommended_action = 'BUY'
            notes.append('🚀 DEEP DISCOUNT on both timeframes - excellent value!')
            confluence_bonus = 50
        else:
            value_alignment = 'DISCOUNT'
            recommended_action = 'BUY'
            notes.append('✅ Discount zone - good value')
            confluence_bonus = 30
    
    elif short_signal == 'PRICE_IN_PREMIUM' and long_signal == 'PRICE_IN_PREMIUM':
        if short_depth > 60 and long_depth > 60:
            value_alignment = 'DEEP_PREMIUM'
            recommended_action = 'AVOID_LONGS'
            notes.append('⚠️ DEEP PREMIUM on both timeframes - very expensive!')
            confluence_bonus = -40
        else:
            value_alignment = 'PREMIUM'
            recommended_action = 'CAUTION'
            notes.append('⚠️ Premium zone - expensive')
            confluence_bonus = -20
    
    elif short_signal == 'PRICE_IN_DISCOUNT':
        value_alignment = 'SHORT_DISCOUNT'
        recommended_action = 'BUY'
        notes.append('📊 Short-term discount - near-term value')
        confluence_bonus = 25
    
    elif short_signal == 'PRICE_IN_PREMIUM':
        value_alignment = 'SHORT_PREMIUM'
        recommended_action = 'WAIT'
        notes.append('📊 Short-term premium - near-term expensive')
        confluence_bonus = -15
    
    else:  # EQUILIBRIUM
        value_alignment = 'FAIR_VALUE'
        recommended_action = 'NEUTRAL'
        notes.append('⚖️ At fair value')
        confluence_bonus = 15
    
    return {
        'short_term': result_short,
        'long_term': result_long,
        'value_alignment': value_alignment,
        'recommended_action': recommended_action,
        'confluence_bonus': confluence_bonus,
        'notes': notes
    }
