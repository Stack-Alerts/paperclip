"""
Dynamic SL Calculator - Building Block Integration
==================================================

Calculates stop loss levels using institutional-grade building blocks
instead of arbitrary fixed percentages or ATR multiples.

CRITICAL INSIGHT:
- Current: Fixed 1.5% SL → Avg Loss $353
- Problem: Not aligned with market structure
- Solution: SL at invalidation points (swing highs, supply zones, fib extensions)
- Expected: Tighter SLs → Avg Loss $250 (29% reduction)

Supports:
- Swing Highs/Lows (structure invalidation)
- Supply/Demand Zones (institutional levels)
- Fibonacci Extensions (pattern targets)
- Structure Breaks (pattern invalidation)
- ATR Dynamic (volatility-based but capped)
- Hybrid mode (tightest valid SL)

Author: Institutional Research
Date: 2026-01-10
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class SLLevel:
    """Container for SL level information"""
    sl: float
    method: str  # 'SWING_HIGH', 'SUPPLY_ZONE', 'FIBONACCI', etc.
    confidence: float  # 0-100
    metadata: dict
    invalidation_reason: str  # Why this SL level invalidates the setup


class DynamicSLCalculator:
    """
    Calculate stop loss using building blocks
    
    PHILOSOPHY:
    - SL should be at pattern INVALIDATION point
    - Not arbitrary distance from entry
    - Tightest valid SL = best risk:reward
    - Use market structure, not random percentages
    
    METHODS:
    1. SWING_POINTS: Last swing high above entry (SHORT) / low below (LONG)
    2. SUPPLY_DEMAND: Nearest supply zone above (SHORT) / demand below (LONG)
    3. FIBONACCI_EXT: 161.8% extension of last swing
    4. STRUCTURE_BREAK: Level where pattern structure breaks
    5. ATR_DYNAMIC: ATR-based but capped at structure
    6. HYBRID: Selects tightest valid SL from all methods
    """
    
    def __init__(self, sl_mode: str = 'HYBRID'):
        """
        Initialize Dynamic SL Calculator
        
        Args:
            sl_mode: 'SWING_POINTS', 'SUPPLY_DEMAND', 'FIBONACCI_EXT',
                     'STRUCTURE_BREAK', 'ATR_DYNAMIC', 'HYBRID'
        """
        self.sl_mode = sl_mode
        self.sl_blocks = {}
        self._initialize_blocks()
    
    def _initialize_blocks(self):
        """Initialize SL building blocks based on mode"""
        
        if self.sl_mode in ['SWING_POINTS', 'HYBRID', 'STRUCTURE_BREAK']:
            from src.detectors.building_blocks.market_structure.swing_points import SwingPoints
            self.sl_blocks['swing_points'] = SwingPoints(timeframe='15min')
        
        if self.sl_mode in ['SUPPLY_DEMAND', 'HYBRID']:
            from src.detectors.building_blocks.supply_demand.supply_demand_zones import SupplyDemandZones
            self.sl_blocks['supply_demand'] = SupplyDemandZones(timeframe='15min')
        
        if self.sl_mode in ['FIBONACCI_EXT', 'HYBRID']:
            from src.detectors.building_blocks.fibonacci.fibonacci_retracements import FibonacciRetracements
            self.sl_blocks['fibonacci'] = FibonacciRetracements(timeframe='15min')
    
    def calculate_sl_level(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float = 1.5,  # Absolute max (failsafe)
        fallback_atr_mult: float = 2.0
    ) -> SLLevel:
        """
        Calculate optimal SL using building blocks
        
        Args:
            df: Price dataframe
            entry_price: Entry price
            entry_bar: Bar index of entry
            side: 'SHORT' or 'LONG'
            max_sl_pct: Maximum SL distance as % (failsafe, default 1.5%)
            fallback_atr_mult: ATR multiplier for fallback (default 2.0)
        
        Returns:
            SLLevel object with SL price and metadata
        """
        
        # Try to calculate using blocks
        if self.sl_mode == 'SWING_POINTS':
            result = self._calculate_swing_sl(df, entry_price, entry_bar, side, max_sl_pct)
        
        elif self.sl_mode == 'SUPPLY_DEMAND':
            result = self._calculate_supply_demand_sl(df, entry_price, entry_bar, side, max_sl_pct)
        
        elif self.sl_mode == 'FIBONACCI_EXT':
            result = self._calculate_fibonacci_sl(df, entry_price, entry_bar, side, max_sl_pct)
        
        elif self.sl_mode == 'STRUCTURE_BREAK':
            result = self._calculate_structure_sl(df, entry_price, entry_bar, side, max_sl_pct)
        
        elif self.sl_mode == 'ATR_DYNAMIC':
            result = self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, fallback_atr_mult)
        
        elif self.sl_mode == 'HYBRID':
            result = self._calculate_hybrid_sl(df, entry_price, entry_bar, side, max_sl_pct, fallback_atr_mult)
        
        else:
            # Fallback to ATR
            result = self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, fallback_atr_mult)
        
        return result
    
    def _calculate_swing_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float
    ) -> SLLevel:
        """Calculate SL based on last swing high/low"""
        
        df_slice = df.iloc[:entry_bar+1].copy()
        
        try:
            swing_result = self.sl_blocks['swing_points'].analyze(df_slice)
        except Exception as e:
            # Fallback to ATR
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        if swing_result['signal'] in ['ERROR', 'INSUFFICIENT_DATA']:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        metadata = swing_result['metadata']
        confidence = swing_result['confidence']
        
        if side == 'SHORT':
            # SL above entry: Use last swing high
            last_swing_high = metadata.get('last_swing_high', entry_price * 1.015)
            
            # Ensure SL is actually ABOVE entry
            if last_swing_high <= entry_price:
                last_swing_high = entry_price * 1.008  # Emergency fallback
            
            # Cap at max_sl_pct
            max_sl = entry_price * (1 + max_sl_pct / 100)
            sl = min(last_swing_high, max_sl)
            
            invalidation = "Price breaks above last swing high (structure invalidated)"
        
        else:  # LONG
            # SL below entry: Use last swing low
            last_swing_low = metadata.get('last_swing_low', entry_price * 0.985)
            
            # Ensure SL is actually BELOW entry
            if last_swing_low >= entry_price:
                last_swing_low = entry_price * 0.992  # Emergency fallback
            
            # Cap at max_sl_pct
            min_sl = entry_price * (1 - max_sl_pct / 100)
            sl = max(last_swing_low, min_sl)
            
            invalidation = "Price breaks below last swing low (structure invalidated)"
        
        return SLLevel(
            sl=sl,
            method='SWING_HIGH' if side == 'SHORT' else 'SWING_LOW',
            confidence=confidence,
            metadata=metadata,
            invalidation_reason=invalidation
        )
    
    def _calculate_supply_demand_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float
    ) -> SLLevel:
        """Calculate SL based on supply/demand zones"""
        
        df_slice = df.iloc[:entry_bar+1].copy()
        
        try:
            sd_result = self.sl_blocks['supply_demand'].analyze(df_slice)
        except Exception as e:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        if sd_result['signal'] == 'ERROR':
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        metadata = sd_result['metadata']
        confidence = sd_result['confidence']
        
        if side == 'SHORT':
            # SL above entry: Use supply zone high
            # Supply zones are resistance, we want to exit if price breaks above
            supply_high = metadata.get('zone_high', entry_price * 1.012)
            
            # Validate
            if supply_high <= entry_price:
                supply_high = entry_price * 1.01
            
            # Cap at max
            max_sl = entry_price * (1 + max_sl_pct / 100)
            sl = min(supply_high, max_sl)
            
            invalidation = "Price breaks into supply zone (resistance broken)"
        
        else:  # LONG
            # SL below entry: Use demand zone low
            demand_low = metadata.get('zone_low', entry_price * 0.988)
            
            # Validate
            if demand_low >= entry_price:
                demand_low = entry_price * 0.99
            
            # Cap at max
            min_sl = entry_price * (1 - max_sl_pct / 100)
            sl = max(demand_low, min_sl)
            
            invalidation = "Price breaks below demand zone (support broken)"
        
        return SLLevel(
            sl=sl,
            method='SUPPLY_ZONE' if side == 'SHORT' else 'DEMAND_ZONE',
            confidence=confidence,
            metadata=metadata,
            invalidation_reason=invalidation
        )
    
    def _calculate_fibonacci_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float
    ) -> SLLevel:
        """Calculate SL based on Fibonacci extensions"""
        
        df_slice = df.iloc[:entry_bar+1].copy()
        
        try:
            fib_result = self.sl_blocks['fibonacci'].analyze(df_slice)
        except Exception as e:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        if fib_result['signal'] in ['ERROR', 'INSUFFICIENT_DATA']:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        metadata = fib_result['metadata']
        confidence = fib_result['confidence']
        fib_levels = metadata.get('fib_levels', {})
        
        if side == 'SHORT':
            # For SHORT: SL at 161.8% extension (above 100% high)
            # Pattern invalidates if price extends too far above the swing
            fib_161 = fib_levels.get('fib_161', entry_price * 1.01)
            
            # Ensure above entry
            if fib_161 <= entry_price:
                fib_161 = entry_price * 1.006
            
            # Cap at max
            max_sl = entry_price * (1 + max_sl_pct / 100)
            sl = min(fib_161, max_sl)
            
            invalidation = "Price extends to 161.8% fib (pattern invalidated)"
        
        else:  # LONG
            # For LONG: SL at 161.8% extension (below 100% low)
            fib_161 = fib_levels.get('fib_161', entry_price * 0.99)
            
            # Ensure below entry
            if fib_161 >= entry_price:
                fib_161 = entry_price * 0.994
            
            # Cap at max
            min_sl = entry_price * (1 - max_sl_pct / 100)
            sl = max(fib_161, min_sl)
            
            invalidation = "Price extends to 161.8% fib (pattern invalidated)"
        
        return SLLevel(
            sl=sl,
            method='FIBONACCI_161',
            confidence=confidence,
            metadata=metadata,
            invalidation_reason=invalidation
        )
    
    def _calculate_structure_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float
    ) -> SLLevel:
        """Calculate SL at structure break point (pattern invalidation)"""
        
        # Use swing points to determine structure
        df_slice = df.iloc[:entry_bar+1].copy()
        
        try:
            swing_result = self.sl_blocks['swing_points'].analyze(df_slice)
        except Exception as e:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        if swing_result['signal'] in ['ERROR', 'INSUFFICIENT_DATA']:
            return self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, 2.0)
        
        metadata = swing_result['metadata']
        confidence = swing_result['confidence']
        recent_swings = metadata.get('recent_swings', [])
        
        if side == 'SHORT':
            # Structure breaks if we take out the last swing high
            # BUT we want a bit of buffer beyond it for confirmation
            last_high = metadata.get('last_swing_high', entry_price * 1.012)
            
            # Add small buffer (0.2%) for structure break confirmation
            structure_break = last_high * 1.002
            
            # Validate
            if structure_break <= entry_price:
                structure_break = entry_price * 1.008
            
            # Cap
            max_sl = entry_price * (1 + max_sl_pct / 100)
            sl = min(structure_break, max_sl)
            
            invalidation = "Structure broken (swing high taken out + confirmation)"
        
        else:  # LONG
            last_low = metadata.get('last_swing_low', entry_price * 0.988)
            
            # Add buffer
            structure_break = last_low * 0.998
            
            # Validate
            if structure_break >= entry_price:
                structure_break = entry_price * 0.992
            
            # Cap
            min_sl = entry_price * (1 - max_sl_pct / 100)
            sl = max(structure_break, min_sl)
            
            invalidation = "Structure broken (swing low taken out + confirmation)"
        
        return SLLevel(
            sl=sl,
            method='STRUCTURE_BREAK',
            confidence=confidence,
            metadata=metadata,
            invalidation_reason=invalidation
        )
    
    def _calculate_atr_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float,
        atr_mult: float
    ) -> SLLevel:
        """Fallback: Calculate SL using ATR (but still capped)"""
        
        df_slice = df.iloc[:entry_bar+1].copy()
        
        # Calculate ATR (14-period)
        high = df_slice['high']
        low = df_slice['low']
        close = df_slice['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
        # Handle NaN
        if pd.isna(atr) or atr == 0:
            atr = entry_price * 0.015  # Fallback to 1.5% of price
        
        # Calculate SL distance
        sl_distance = atr * atr_mult
        
        # Cap at max_sl_pct
        max_distance = entry_price * (max_sl_pct / 100)
        sl_distance = min(sl_distance, max_distance)
        
        if side == 'SHORT':
            sl = entry_price + sl_distance
            invalidation = f"ATR-based stop ({atr_mult}x ATR = {sl_distance:.2f})"
        else:
            sl = entry_price - sl_distance
            invalidation = f"ATR-based stop ({atr_mult}x ATR = {sl_distance:.2f})"
        
        return SLLevel(
            sl=sl,
            method='ATR_DYNAMIC',
            confidence=70.0,  # Medium confidence for ATR
            metadata={'atr': atr, 'atr_mult': atr_mult},
            invalidation_reason=invalidation
        )
    
    def _calculate_hybrid_sl(
        self,
        df: pd.DataFrame,
        entry_price: float,
        entry_bar: int,
        side: str,
        max_sl_pct: float,
        fallback_atr_mult: float
    ) -> SLLevel:
        """
        HYBRID: Try all methods, select TIGHTEST valid SL
        
        Philosophy:
        - Tighter SL = Better R:R
        - But must be at valid invalidation point
        - Choose method with highest confidence AND tightest SL
        """
        
        candidates = []
        
        # Try all methods
        methods = [
            ('swing', self._calculate_swing_sl),
            ('supply_demand', self._calculate_supply_demand_sl),
            ('fibonacci', self._calculate_fibonacci_sl),
            ('structure', self._calculate_structure_sl),
        ]
        
        for method_name, method_func in methods:
            try:
                sl_level = method_func(df, entry_price, entry_bar, side, max_sl_pct)
                candidates.append(sl_level)
            except:
                continue
        
        # Always include ATR as fallback
        try:
            atr_sl = self._calculate_atr_sl(df, entry_price, entry_bar, side, max_sl_pct, fallback_atr_mult)
            candidates.append(atr_sl)
        except:
            pass
        
        if not candidates:
            # Emergency fallback
            if side == 'SHORT':
                sl = entry_price * 1.015
            else:
                sl = entry_price * 0.985
            
            return SLLevel(
                sl=sl,
                method='EMERGENCY_FALLBACK',
                confidence=50.0,
                metadata={},
                invalidation_reason="Emergency fallback (1.5% fixed)"
            )
        
        # Select TIGHTEST SL (best R:R)
        if side == 'SHORT':
            # For SHORT: Tightest = closest to entry (lowest value above entry)
            # Sort by SL ascending, then by confidence descending
            candidates.sort(key=lambda x: (x.sl, -x.confidence))
            best = candidates[0]
        else:  # LONG
            # For LONG: Tightest = closest to entry (highest value below entry)
            # Sort by SL descending, then by confidence descending
            candidates.sort(key=lambda x: (-x.sl, -x.confidence))
            best = candidates[0]
        
        # Mark as HYBRID
        best.method = f'HYBRID_{best.method}'
        
        return best


def calculate_sl_distance_pct(entry_price: float, sl_price: float, side: str) -> float:
    """
    Calculate SL distance as percentage
    
    Args:
        entry_price: Entry price
        sl_price: Stop loss price
        side: 'SHORT' or 'LONG'
    
    Returns:
        SL distance as percentage
    """
    distance = abs(sl_price - entry_price) / entry_price * 100
    return distance
