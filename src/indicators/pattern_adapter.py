#!/usr/bin/env python3
"""
BTC_Engine_v3 - Pattern Adapter
Day 3: Framework-Agnostic Pattern Adapter

This adapter:
1. Converts NautilusTrader Bar objects → DataFrame format
2. Detects M/W patterns using simplified logic
3. Returns signals compatible with NautilusTrader strategies

NOTE: This is a simplified implementation for Day 3.
Full sophisticated pattern detection will be integrated in Days 4-5.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from nautilus_trader.model.data import Bar
from nautilus_trader.model.objects import Price, Quantity


@dataclass
class PatternSignal:
    """Pattern detection signal"""
    pattern_type: str  # 'M', 'W', 'none'
    direction: str  # 'long', 'short', 'neutral'
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    metadata: Optional[Dict] = None


class PatternAdapter:
    """
    Framework-agnostic adapter for pattern detection
    
    Converts between NautilusTrader and our pattern detectors
    """
    
    def __init__(self, pattern_type: str = 'm_pattern', lookback: int = 50):
        """
        Initialize pattern adapter
        
        Args:
            pattern_type: 'm_pattern' or 'w_pattern'
            lookback: Number of bars to analyze
        """
        self.pattern_type = pattern_type.lower()
        self.lookback = lookback
        self.bar_buffer: List[Bar] = []
        
        # Pattern detection parameters (simplified for Day 3)
        self.pivot_length = 5  # Bars on each side for pivot
        self.min_pattern_bars = 20
        self.peak_tolerance = 0.02  # 2% max asymmetry
        
    def add_bar(self, bar: Bar) -> None:
        """
        Add bar to buffer
        
        Args:
            bar: NautilusTrader Bar object
        """
        self.bar_buffer.append(bar)
        
        # Keep only required lookback
        if len(self.bar_buffer) > self.lookback:
            self.bar_buffer.pop(0)
    
    def bars_to_dataframe(self, bars: List[Bar]) -> pd.DataFrame:
        """
        Convert NautilusTrader bars to DataFrame
        
        Args:
            bars: List of Bar objects
            
        Returns:
            DataFrame with OHLCV data
        """
        data = []
        for bar in bars:
            data.append({
                'timestamp': pd.Timestamp(bar.ts_event, unit='ns'),
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': float(bar.volume),
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def detect_pattern(self, bars: Optional[List[Bar]] = None) -> PatternSignal:
        """
        Detect pattern in bars
        
        Args:
            bars: List of bars (uses buffer if None)
            
        Returns:
            PatternSignal with detection result
        """
        # Use buffer if no bars provided
        if bars is None:
            bars = self.bar_buffer
        
        # Need minimum bars
        if len(bars) < self.min_pattern_bars:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=float(bars[-1].close) if bars else 0.0,
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason': 'insufficient_data'}
            )
        
        # Convert to DataFrame
        df = self.bars_to_dataframe(bars)
        
        # Detect pattern based on type
        if self.pattern_type == 'm_pattern':
            return self._detect_m_pattern(df, bars[-1])
        elif self.pattern_type == 'w_pattern':
            return self._detect_w_pattern(df, bars[-1])
        else:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=float(bars[-1].close),
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason': 'unknown_pattern_type'}
            )
    
    def _detect_m_pattern(self, df: pd.DataFrame, current_bar: Bar) -> PatternSignal:
        """
        Simplified M-pattern detection
        
        M-pattern: Two peaks at similar levels with decline to neckline
        
        Args:
            df: OHLCV DataFrame
            current_bar: Current bar
            
        Returns:
            PatternSignal
        """
        current_price = float(current_bar.close)
        
        # Find recent highs
        highs = df['high'].values
        
        # Simple pivot detection
        pivots_high = []
        for i in range(self.pivot_length, len(highs) - self.pivot_length):
            is_pivot = True
            for j in range(1, self.pivot_length + 1):
                if highs[i] < highs[i-j] or highs[i] < highs[i+j]:
                    is_pivot = False
                    break
            if is_pivot:
                pivots_high.append((i, highs[i]))
        
        # Need at least 2 peaks for M-pattern
        if len(pivots_high) < 2:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason': 'insufficient_pivots', 'pivot_count': len(pivots_high)}
            )
        
        # Check last 2 peaks for M-pattern
        peak1_idx, peak1_price = pivots_high[-2]
        peak2_idx, peak2_price = pivots_high[-1]
        
        # Check peak symmetry (should be similar heights)
        peak_diff = abs(peak1_price - peak2_price) / max(peak1_price, peak2_price)
        if peak_diff > self.peak_tolerance:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason':  'peaks_too_asymmetric', 'peak_diff_pct': peak_diff * 100}
            )
        
        # Find neckline (lowest low between peaks)
        neckline = df['low'].iloc[peak1_idx:peak2_idx+1].min()
        
        # Check if price is near neckline (potential entry)
        neckline_dist = abs(current_price - neckline) / neckline
        
        # M-pattern detected if:
        # 1. Two peaks at similar levels
        # 2. Price declining from second peak
        # 3. Approaching neckline
        
        if current_price < max(peak1_price, peak2_price) * 0.98:  # Below peaks
            # Calculate trading parameters
            pattern_height = max(peak1_price, peak2_price) - neckline
            
            # Stop loss above peaks
            stop_loss = max(peak1_price, peak2_price) * 1.01
            
            # Targets below neckline (using Fibonacci ratios)
            tp1 = neckline - (pattern_height * 0.5)  # 0.5x projection
            tp2 = neckline - (pattern_height * 1.0)  # 1.0x projection
            tp3 = neckline - (pattern_height * 1.618)  # 1.618x projection (golden ratio)
            
            # Confidence based on pattern quality
            base_confidence = 0.65
            
            # Bonus for tight peaks
            if peak_diff < 0.01:  # Within 1%
                base_confidence += 0.10
            
            # Bonus if near neckline
            if neckline_dist < 0.02:  # Within 2%
                base_confidence += 0.10
            
            confidence = min(base_confidence, 0.95)
            
            return PatternSignal(
                pattern_type='M',
                direction='short',
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                metadata={
                    'peak1_price': peak1_price,
                    'peak2_price': peak2_price,
                    'neckline': neckline,
                    'pattern_height': pattern_height,
                    'peak_diff_pct': peak_diff * 100,
                    'pattern_bars': peak2_idx - peak1_idx,
                    'detection_method': 'simplified_pivot',
                    'risk_reward': abs(tp1 - current_price) / abs(stop_loss - current_price)
                }
            )
        
        # No pattern
        return PatternSignal(
            pattern_type='none',
            direction='neutral',
            confidence=0.0,
            entry_price=current_price,
            stop_loss=0.0,
            take_profit_1=0.0,
            metadata={'reason': 'pattern_structure_incomplete'}
        )
    
    def _detect_w_pattern(self, df: pd.DataFrame, current_bar: Bar) -> PatternSignal:
        """
        Simplified W-pattern detection (inverse of M-pattern)
        
        W-pattern: Two troughs at similar levels with rally to neckline
        
        Args:
            df: OHLCV DataFrame
            current_bar: Current bar
            
        Returns:
            PatternSignal
        """
        current_price = float(current_bar.close)
        
        # Find recent lows
        lows = df['low'].values
        
        # Simple pivot detection
        pivots_low = []
        for i in range(self.pivot_length, len(lows) - self.pivot_length):
            is_pivot = True
            for j in range(1, self.pivot_length + 1):
                if lows[i] > lows[i-j] or lows[i] > lows[i+j]:
                    is_pivot = False
                    break
            if is_pivot:
                pivots_low.append((i, lows[i]))
        
        # Need at least 2 troughs for W-pattern
        if len(pivots_low) < 2:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason': 'insufficient_pivots', 'pivot_count': len(pivots_low)}
            )
        
        # Check last 2 troughs for W-pattern
        trough1_idx, trough1_price = pivots_low[-2]
        trough2_idx, trough2_price = pivots_low[-1]
        
        # Check trough symmetry
        trough_diff = abs(trough1_price - trough2_price) / min(trough1_price, trough2_price)
        if trough_diff > self.peak_tolerance:
            return PatternSignal(
                pattern_type='none',
                direction='neutral',
                confidence=0.0,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit_1=0.0,
                metadata={'reason': 'troughs_too_asymmetric', 'trough_diff_pct': trough_diff * 100}
            )
        
        # Find neckline (highest high between troughs)
        neckline = df['high'].iloc[trough1_idx:trough2_idx+1].max()
        
        # W-pattern detected if price rallying from second trough
        if current_price > min(trough1_price, trough2_price) * 1.02:  # Above troughs
            # Calculate trading parameters
            pattern_height = neckline - min(trough1_price, trough2_price)
            
            # Stop loss below troughs
            stop_loss = min(trough1_price, trough2_price) * 0.99
            
            # Targets above neckline
            tp1 = neckline + (pattern_height * 0.5)
            tp2 = neckline + (pattern_height * 1.0)
            tp3 = neckline + (pattern_height * 1.618)
            
            # Confidence
            base_confidence = 0.65
            if trough_diff < 0.01:
                base_confidence += 0.10
            
            confidence = min(base_confidence, 0.95)
            
            return PatternSignal(
                pattern_type='W',
                direction='long',
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                metadata={
                    'trough1_price': trough1_price,
                    'trough2_price': trough2_price,
                    'neckline': neckline,
                    'pattern_height': pattern_height,
                    'trough_diff_pct': trough_diff * 100,
                    'pattern_bars': trough2_idx - trough1_idx,
                    'detection_method': 'simplified_pivot',
                    'risk_reward': abs(tp1 - current_price) / abs(current_price - stop_loss)
                }
            )
        
        # No pattern
        return PatternSignal(
            pattern_type='none',
            direction='neutral',
            confidence=0.0,
            entry_price=current_price,
            stop_loss=0.0,
            take_profit_1=0.0,
            metadata={'reason': 'pattern_structure_incomplete'}
        )


# Example usage
if __name__ == "__main__":
    print("Pattern Adapter initialized")
    print("Use with NautilusTrader strategies")
