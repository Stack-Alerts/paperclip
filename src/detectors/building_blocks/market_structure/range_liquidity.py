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
from datetime import datetime
import pandas as pd
import numpy as np
from src.utils.advanced_data_loader import advanced_data


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
    
    def calculate_variable_confidence(self, liquidity_strength: int, distance_pct: float, 
                                     has_orderbook: bool, has_volume_spike: bool = False) -> int:
        """
        FIXED V2: MUCH wider variation based on distance and liquidity
        
        Priority 1 fix: Maximum confidence variation
        - Distance-driven (primary driver when no orderbook)
        - Liquidity strength scaling
        - Volume spike bonus
        """
        # BASE: Scale with liquidity strength (wider range!)
        if has_orderbook:
            # With real data: 55-85 base range
            base_confidence = 55 + int(liquidity_strength * 0.30)
        else:
            # Without orderbook: Start lower, vary more
            base_confidence = 50 + int(liquidity_strength * 0.30)
        
        # DISTANCE: MUCH LARGER adjustments (this is the main variation source!)
        if distance_pct < 1:
            distance_adj = 20  # Extremely close = very high confidence
        elif distance_pct < 3:
            distance_adj = 15  # Very close = high confidence
        elif distance_pct < 6:
            distance_adj = 10  # Close = moderate boost
        elif distance_pct < 10:
            distance_adj = 5   # Moderately close = small boost
        elif distance_pct < 15:
            distance_adj = 0   # Moderate distance = neutral
        elif distance_pct < 25:
            distance_adj = -10 # Far = penalty
        else:
            distance_adj = -20 # Very far = big penalty
        
        base_confidence += distance_adj
        
        # STRENGTH: Additional bonus for strong liquidity (less important without orderbook)
        if liquidity_strength >= 80:
            base_confidence += 5  # Very strong
        elif liquidity_strength >= 60:
            base_confidence += 3  # Strong
        elif liquidity_strength <= 30:
            base_confidence -= 5  # Very weak
        
        # VOLUME SPIKE: Magnet effect bonus (Priority 2)
        if has_volume_spike:
            base_confidence += 7  # Increased from 5
        
        return max(50, min(90, base_confidence))
    

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
        liquidity_strength = 50
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
            except:
                pass
        
        # Detect volume spike (Priority 2 enhancement)
        has_volume_spike = self.detect_volume_spike(df)
        
        # Variable confidence (justified by real data if available!)
        confidence = self.calculate_variable_confidence(liquidity_strength, distance_pct, 
                                                       has_orderbook, has_volume_spike)
        
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
                confluence_factors.append(f'📊 Volume spike detected - MAGNET EFFECT! (+5 confidence)')
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
                confluence_factors.append(f'📊 Volume spike detected - MAGNET EFFECT! (+5 confidence)')
        
        # Metadata
        metadata = {
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
            'lookback_bars': lookback
        }
        
        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': metadata,
            'timestamp': df['timestamp'].iloc[-1],
            'timeframe': self.timeframe,
            'confluence_factors': confluence_factors
        }
