"""
Range Liquidity Building Block - Advanced with Real Orderbook Data
Category: Market Structure
Purpose: Institutional-grade liquidity detection with real orderbook depth

ENHANCED VERSION: Uses REAL orderbook data when available!
- Basic mode: Simple OHLCV proximity (fallback)
- Advanced mode: Real orderbook depth (when data provided)

This maintains backward compatibility while adding game-changing capabilities!
"""
"""
Building Block Classification: CONTEXT BLOCK
Mode: CONTINUOUS
Purpose: Continuous range state tracking

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
from src.utils.advanced_data_loader import advanced_data


@register_block(
    name='range_liquidity',
    category='MARKET_STRUCTURE',
    class_name='RangeLiquidity',
    default_weight=15,
    valid_signals=[
        # Range positions - GRANULAR
        'NEAR_BUY_SIDE_LIQUIDITY', 'NEAR_SELL_SIDE_LIQUIDITY',
        # Simple directional - SIMPLE
        'BULLISH', 'BEARISH', 'NEUTRAL',
        # Status
        'ERROR', 'INSUFFICIENT_DATA'
    ],
    signal_tiers={
        'NEAR_BUY_SIDE_LIQUIDITY': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Near buy-side liquidity - Approaching range high. Long stop clusters above. Expect rejection or sweep. Consider shorts. Take profits on longs. Stop above range high.'
        },
        'NEAR_SELL_SIDE_LIQUIDITY': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Near sell-side liquidity - Approaching range low. Short stop clusters below. Expect bounce or sweep. Consider longs. Take profits on shorts. Stop below range low.'
        },
        
        # Simple directional - SIMPLE
        'BULLISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Near sell-side liquidity - Price at range support. Long stop clusters provide magnet. Enter longs. Target range high. Stop below range low.'
        },
        'BEARISH': {
            'base_points': 20,
            'formula': 'scaled',
            'description': 'Near buy-side liquidity - Price at range resistance. Short stop clusters provide magnet. Enter shorts. Target range low. Stop above range high.'
        },
        'NEUTRAL': {
            'base_points': 10,
            'formula': 'scaled',
            'ui_visible': False,  # Filter from Strategy Builder UI

            'description': 'Mid-range - Between liquidity zones. No clear magnet. Range-bound. Wait for approach to buy or sell-side before entering.'
        },
        
        'ERROR': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Analysis error - Cannot calculate range liquidity. Check range calculation and data quality.'
        },
        'INSUFFICIENT_DATA': {
            'points': 0,
            'ui_visible': False,  # Filter from Strategy Builder UI
            'description': 'Insufficient data - Need at least 20 candles for range liquidity analysis. Wait for wider price range to develop.'
        }
    },
    description='Range Liquidity - Detects proximity to buy/sell-side liquidity with optional orderbook depth analysis',
    tags=['market_structure', 'liquidity', 'range', 'orderbook', 'depth', 'context_block']
)
class RangeLiquidity:
    """
    Range Liquidity with optional real orderbook integration
    
    Modes:
    - Without orderbook: Simple proximity detection (backward compatible)
    - With orderbook: Institutional-grade depth analysis (game changer!)
    """
    
    def __init__(self, timeframe: str = '15min',
                 lookback: int = 20,
                 orderbook_levels: int = 10,
                 **kwargs):
        """
        Initialize Range Liquidity
        
        Args:
            timeframe: Timeframe string
            lookback: Bars for range calculation
            orderbook_levels: How many orderbook levels to analyze if data provided (max 20)
        """
        self.timeframe = timeframe
        self.lookback = lookback
        self.orderbook_levels = min(orderbook_levels, 20)
    
    def _determine_dual_signals(self, granular_signal: str) -> tuple:
        """DUAL SIGNAL ARCHITECTURE"""
        granular = granular_signal
        # Map liquidity proximity to directional bias
        if granular == 'NEAR_SELL_SIDE_LIQUIDITY':
            simple = 'BULLISH'  # Near support - bullish bias
        elif granular == 'NEAR_BUY_SIDE_LIQUIDITY':
            simple = 'BEARISH'  # Near resistance - bearish bias
        else:
            simple = 'NEUTRAL'
        return granular, simple
    
    def load_orderbook_snapshot(self, timestamp: pd.Timestamp, orderbook_file: str) -> pd.Series:
        """Load closest orderbook snapshot to given timestamp"""
        try:
            df_ob = pd.read_parquet(orderbook_file)
            df_ob['origin_time'] = pd.to_datetime(df_ob['origin_time'])
            
            time_diff = abs(df_ob['origin_time'] - timestamp)
            closest_idx = time_diff.idxmin()
            
            if time_diff.iloc[closest_idx] > pd.Timedelta(minutes=1):
                return None
            
            return df_ob.iloc[closest_idx]
        except:
            return None
    
    def calculate_orderbook_depth(self, orderbook_snapshot: pd.Series,
                                   target_price: float, side: str = 'bid') -> tuple:
        """Calculate real liquidity depth near target price"""
        if orderbook_snapshot is None:
            return 0, 0, 0
        
        total_depth = 0
        weighted_depth = 0
        levels_within = 0
        tolerance = target_price * 0.02
        
        for i in range(self.orderbook_levels):
            price_col = f'{side}_{i}_price'
            size_col = f'{side}_{i}_size'
            
            if price_col not in orderbook_snapshot.index:
                continue
            
            level_price = orderbook_snapshot[price_col]
            level_size = orderbook_snapshot[size_col]
            
            if abs(level_price - target_price) <= tolerance:
                total_depth += level_size
                distance = abs(level_price - target_price)
                weight = 1.0 - (distance / tolerance)
                weighted_depth += level_size * weight
                levels_within += 1
        
        return float(total_depth), float(weighted_depth), levels_within
    
    def estimate_liquidity_strength_from_price_action(self, df: pd.DataFrame, 
                                                       target_price: float) -> int:
        """
        Estimate liquidity strength WITHOUT orderbook (variation source!)
        
        Uses price action signals:
        - Volume profile near target
        - Number of touches
        - Rejection strength
        """
        if len(df) < 20:
            return 50
        
        # Base: 30-70 range (creates variation!)
        base_strength = 50
        
        # Factor 1: Volume near target (last 20 bars)
        recent_highs = df['high'].iloc[-20:]
        recent_lows = df['low'].iloc[-20:]
        recent_volumes = df['volume'].iloc[-20:]
        
        # How often touched near target?
        tolerance = target_price * 0.015  # 1.5%
        touches = 0
        touch_volumes = []
        
        for i in range(len(recent_highs)):
            if abs(recent_highs.iloc[i] - target_price) < tolerance or \
               abs(recent_lows.iloc[i] - target_price) < tolerance:
                touches += 1
                touch_volumes.append(recent_volumes.iloc[i])
        
        # Touch bonus: more touches = stronger level
        touch_bonus = min(20, touches * 4)  # 0-20
        
        # Volume bonus: high volume at touches = stronger
        if touch_volumes:
            avg_touch_vol = sum(touch_volumes) / len(touch_volumes)
            avg_overall_vol = recent_volumes.mean()
            if avg_overall_vol > 0:
                vol_ratio = avg_touch_vol / avg_overall_vol
                vol_bonus = int((vol_ratio - 1.0) * 15)  # -15 to +15
                vol_bonus = max(-15, min(15, vol_bonus))
            else:
                vol_bonus = 0
        else:
            vol_bonus = 0
        
        strength = base_strength + touch_bonus + vol_bonus
        return max(30, min(70, strength))
    
    def calculate_liquidity_strength(self, total_depth: float, weighted_depth: float, levels: int) -> int:
        """Calculate liquidity strength from real orderbook data (0-100)"""
        if total_depth == 0:
            return 50
        
        normalized_depth = min(100, (total_depth / 10) * 50)
        
        if total_depth > 0:
            weight_ratio = weighted_depth / total_depth
            weight_bonus = weight_ratio * 20
        else:
            weight_bonus = 0
        
        level_bonus = min(30, levels * 3)
        strength = int(normalized_depth + weight_bonus + level_bonus)
        return max(0, min(100, strength))
    
    def detect_volume_spike(self, df: pd.DataFrame, threshold: float = 1.5) -> bool:
        """
        Priority 2: Detect if volume spiking near liquidity (magnet effect!)
        
        Returns True if recent volume significantly above baseline
        """
        if len(df) < 20:
            return False
        
        recent_vol = df['volume'].iloc[-5:].mean()
        baseline_vol = df['volume'].iloc[-20:-5].mean()
        
        if baseline_vol > 0:
            spike_ratio = recent_vol / baseline_vol
            return spike_ratio > threshold
        
        return False
    
    def calculate_range_volatility(self, df: pd.DataFrame, lookback: int = 20) -> float:
        """Calculate range volatility (expansion/contraction)"""
        if len(df) < lookback * 2:
            return 1.0
        
        # Recent range size vs historical
        recent_range = df['high'].iloc[-lookback:].max() - df['low'].iloc[-lookback:].min()
        historical_range = df['high'].iloc[-lookback*2:-lookback].max() - df['low'].iloc[-lookback*2:-lookback].min()
        
        if historical_range > 0:
            volatility_ratio = recent_range / historical_range
            return float(volatility_ratio)
        return 1.0
    
    def calculate_momentum_toward_target(self, df: pd.DataFrame, target_price: float) -> float:
        """Calculate price momentum toward target (-1 to +1)"""
        if len(df) < 10:
            return 0.0
        
        current_price = float(df['close'].iloc[-1])
        past_price = float(df['close'].iloc[-10])
        
        # Direction toward target
        if target_price > current_price:
            # Target above, moving up is positive
            momentum = (current_price - past_price) / past_price
        else:
            # Target below, moving down is positive
            momentum = (past_price - current_price) / past_price
        
        return float(max(-0.10, min(0.10, momentum)))  # Clamp to ±10%
    
    def calculate_variable_confidence(self, liquidity_strength: int, distance_pct: float, 
                                     has_orderbook: bool, has_volume_spike: bool = False,
                                     range_volatility: float = 1.0, momentum: float = 0.0) -> int:
        """
        V5: MULTI-DIMENSIONAL confidence (A-grade target!)
        
        Dimensions:
        1. Distance (primary)
        2. Range volatility (high variation!)
        3. Momentum toward target (high variation!)
        4. Liquidity strength
        5. Volume spike
        """
        # BASE: Distance mapping (55-85 range)
        if distance_pct < 2:
            base = 85
        elif distance_pct < 5:
            base = 80
        elif distance_pct < 10:
            base = 75
        elif distance_pct < 15:
            base = 70
        elif distance_pct < 20:
            base = 65
        elif distance_pct < 30:
            base = 60
        else:
            base = 55
        
        # RANGE VOLATILITY: Expanding range = uncertain targets
        # This creates MAJOR variation!
        if range_volatility > 1.5:
            vol_adj = -15  # Expanding rapidly = low confidence
        elif range_volatility > 1.2:
            vol_adj = -10  # Expanding = lower confidence
        elif range_volatility > 0.8:
            vol_adj = 0    # Stable
        elif range_volatility > 0.6:
            vol_adj = 5    # Contracting = targets reliable
        else:
            vol_adj = 10   # Contracting rapidly = very reliable
        
        # MOMENTUM: Moving toward target = higher confidence
        # Momentum: -10% to +10%, scale to -10 to +10 points
        momentum_adj = int(momentum * 100)  # -10 to +10
        
        # STRENGTH: Liquidity quality (smaller adjustment)
        if has_orderbook:
            if liquidity_strength >= 80:
                strength_adj = 5
            elif liquidity_strength >= 60:
                strength_adj = 3
            elif liquidity_strength <= 30:
                strength_adj = -5
            else:
                strength_adj = 0
        else:
            strength_adj = int((liquidity_strength - 50) * 0.15)
        
        # VOLUME SPIKE
        spike_adj = 7 if has_volume_spike else 0
        
        # TOTAL
        confidence = base + vol_adj + momentum_adj + strength_adj + spike_adj
        
        return max(50, min(90, confidence))
    

    def check_liquidation_magnets(self, range_high: float, range_low: float, df: pd.DataFrame) -> Dict:
        """Check for liquidation clusters acting as magnets"""
        try:
            levels = advanced_data.get_liquidation_levels(df, lookback_bars=100)
            
            magnets_above = []
            magnets_below = []
            
            for cluster in levels['above']:
                if cluster['price'] > range_high:
                    magnets_above.append(cluster)
            
            for cluster in levels['below']:
                if cluster['price'] < range_low:
                    magnets_below.append(cluster)
            
            has_magnets = len(magnets_above) > 0 or len(magnets_below) > 0
            
            if has_magnets:
                return {
                    'has_magnets': True,
                    'magnets_above': len(magnets_above),
                    'magnets_below': len(magnets_below),
                    'confidence_boost': 10 if has_magnets else 0
                }
            return {'has_magnets': False, 'confidence_boost': 0}
        except:
            return {'has_magnets': False, 'confidence_boost': 0}

    def analyze(self, df: pd.DataFrame, orderbook_file: str = None, **kwargs) -> Dict[str, Any]:
        """
        Analyze liquidity with optional real orderbook data
        
        Args:
            df: OHLCV dataframe
            orderbook_file: Path to orderbook parquet (optional - enables advanced mode!)
        """
        # Validation
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']):
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'metadata': {'error': 'Missing columns', 'has_orderbook_data': False, 'liquidity_strength': 0,
                            'total_depth_btc': None, 'weighted_depth_btc': None, 'orderbook_levels': None},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        if len(df) < self.lookback:
            return {
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'metadata': {'has_orderbook_data': False, 'liquidity_strength': 0,
                            'total_depth_btc': None, 'weighted_depth_btc': None, 'orderbook_levels': None},
                'timestamp': datetime.now(),
                'timeframe': self.timeframe,
                'confluence_factors': []
            }
        
        # Calculate range
        lookback = min(self.lookback, len(df))
        range_high = float(df['high'].iloc[-lookback:].max())
        range_low = float(df['low'].iloc[-lookback:].min())
        current_price = float(df['close'].iloc[-1])
        current_time = pd.to_datetime(df['timestamp'].iloc[-1])
        
        # Distances
        distance_to_high = ((range_high - current_price) / current_price) * 100
        distance_to_low = ((current_price - range_low) / current_price) * 100
        
        # Determine direction
        if distance_to_high < distance_to_low:
            signal = 'NEAR_BUY_SIDE_LIQUIDITY'
            target_liquidity = range_high
            distance_pct = distance_to_high
            orderbook_side = 'ask'
        else:
            signal = 'NEAR_SELL_SIDE_LIQUIDITY'
            target_liquidity = range_low
            distance_pct = distance_to_low
            orderbook_side = 'bid'
        
        # Try orderbook data (ADVANCED MODE!)
        has_orderbook = False
        total_depth = 0
        weighted_depth = 0
        levels_within = 0
        
        if orderbook_file:
            try:
                orderbook_snapshot = self.load_orderbook_snapshot(current_time, orderbook_file)
                if orderbook_snapshot is not None:
                    total_depth, weighted_depth, levels_within = self.calculate_orderbook_depth(
                        orderbook_snapshot, target_liquidity, orderbook_side
                    )
                    liquidity_strength = self.calculate_liquidity_strength(total_depth, weighted_depth, levels_within)
                    has_orderbook = True
                else:
                    # No orderbook: estimate from price action (VARIATION SOURCE!)
                    liquidity_strength = self.estimate_liquidity_strength_from_price_action(df, target_liquidity)
            except:
                # Fallback: estimate from price action
                liquidity_strength = self.estimate_liquidity_strength_from_price_action(df, target_liquidity)
        else:
            # No orderbook: estimate from price action (VARIATION SOURCE!)
            liquidity_strength = self.estimate_liquidity_strength_from_price_action(df, target_liquidity)
        
        # V5: Calculate range volatility (MAJOR variation source!)
        range_volatility = self.calculate_range_volatility(df, lookback)
        
        # V5: Calculate momentum toward target (MAJOR variation source!)
        momentum = self.calculate_momentum_toward_target(df, target_liquidity)
        
        # Detect volume spike (Priority 2 enhancement)
        has_volume_spike = self.detect_volume_spike(df)
        
        # V5: Multi-dimensional confidence!
        confidence = self.calculate_variable_confidence(
            liquidity_strength, distance_pct, has_orderbook, has_volume_spike,
            range_volatility, momentum
        )
        
        # Confluence factors
        confluence_factors = []
        
        if signal == 'NEAR_BUY_SIDE_LIQUIDITY':
            confluence_factors.append(f'Approaching buy-side liquidity at ${target_liquidity:.2f} ({distance_pct:.1f}% away)')
            if has_orderbook:
                confluence_factors.append(f'⭐ REAL orderbook: {total_depth:.2f} BTC depth across {levels_within} levels')
                if liquidity_strength >= 70:
                    confluence_factors.append(f'💪 Strong resistance (strength: {liquidity_strength})')
            else:
                confluence_factors.append(f'📊 Estimated liquidity (no orderbook data)')
            
            # Volume spike indicator (Priority 2)
            if has_volume_spike:
                confluence_factors.append(f'📊 Volume spike detected - MAGNET EFFECT! (+7 confidence)')
            
            # V5: Range volatility indicator
            if range_volatility > 1.5:
                confluence_factors.append(f'📉 Range expanding rapidly - uncertain targets (-15 confidence)')
            elif range_volatility < 0.6:
                confluence_factors.append(f'📈 Range contracting - reliable targets (+10 confidence)')
            
            # V5: Momentum indicator
            if momentum > 0.05:
                confluence_factors.append(f'🎯 Strong momentum toward target (+{int(momentum*100)} confidence)')
            elif momentum < -0.05:
                confluence_factors.append(f'⚠️ Momentum away from target ({int(momentum*100)} confidence)')
        
        else:
            confluence_factors.append(f'Approaching sell-side liquidity at ${target_liquidity:.2f} ({distance_pct:.1f}% away)')
            if has_orderbook:
                confluence_factors.append(f'⭐ REAL orderbook: {total_depth:.2f} BTC depth across {levels_within} levels')
                if liquidity_strength >= 70:
                    confluence_factors.append(f'💪 Strong support (strength: {liquidity_strength})')
            else:
                confluence_factors.append(f'📊 Estimated liquidity (no orderbook data)')
            
            # Volume spike indicator (Priority 2)
            if has_volume_spike:
                confluence_factors.append(f'📊 Volume spike detected - MAGNET EFFECT! (+7 confidence)')
            
            # V5: Range volatility indicator
            if range_volatility > 1.5:
                confluence_factors.append(f'📉 Range expanding rapidly - uncertain targets (-15 confidence)')
            elif range_volatility < 0.6:
                confluence_factors.append(f'📈 Range contracting - reliable targets (+10 confidence)')
            
            # V5: Momentum indicator
            if momentum > 0.05:
                confluence_factors.append(f'🎯 Strong momentum toward target (+{int(momentum*100)} confidence)')
            elif momentum < -0.05:
                confluence_factors.append(f'⚠️ Momentum away from target ({int(momentum*100)} confidence)')
        
        # DUAL SIGNAL ARCHITECTURE
        granular_signal, simple_signal = self._determine_dual_signals(signal)
        
        # Metadata
        metadata = {
            'signal_simple': simple_signal,
            'signal_granular': granular_signal,
            'buy_side': round(range_high, 2),
            'sell_side': round(range_low, 2),
            'target_liquidity': round(target_liquidity, 2),
            'current_price': round(current_price, 2),
            'distance_percentage': round(distance_pct, 2),
            'has_orderbook_data': has_orderbook,
            'liquidity_strength': liquidity_strength,
            'total_depth_btc': round(total_depth, 4) if has_orderbook else None,
            'weighted_depth_btc': round(weighted_depth, 4) if has_orderbook else None,
            'orderbook_levels': levels_within if has_orderbook else None,
            'has_volume_spike': has_volume_spike,
            'range_volatility': round(range_volatility, 2),
            'momentum_toward_target': round(momentum, 4),
            'lookback_bars': lookback
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
