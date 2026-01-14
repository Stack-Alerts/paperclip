"""
Volume Analyzer - Institutional-Grade Volume Confirmation

This module provides volume analysis for pivot reversal confirmation.
Based on institutional trading principles:
- High volume at tops = Distribution (smart money selling)
- Low volume at tops = Weak rally (retail exhaustion)
- High volume at bottoms = Accumulation (smart money buying)
- Low volume at bottoms = Weak selloff (no conviction)

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: .clinerules - INSTITUTIONAL_RULES
"""

import pandas as pd
import numpy as np
from typing import Tuple


class VolumeAnalyzer:
    """
    Institutional-grade volume analysis for pivot confirmation
    
    Uses:
    - Volume ratio vs moving average
    - Volume climax detection
    - Context-aware confirmation (bearish vs bullish)
    
    Args:
        lookback (int): Lookback period for average volume calculation
    
    Example:
        >>> analyzer = VolumeAnalyzer(lookback=20)
        >>> confirmed, state, ratio = analyzer.confirm_bearish_reversal(df, pivot_index)
        >>> if confirmed:
        >>>     # High confidence bearish setup
        >>>     place_trade()
    """
    
    def __init__(self, lookback: int = 20):
        """
        Initialize VolumeAnalyzer
        
        Args:
            lookback: Number of bars to use for average volume calculation
                     Default 20 = ~10 hours on 30min timeframe
        """
        self.lookback = lookback
    
    def get_volume_state(self, df: pd.DataFrame, pivot_index: int) -> Tuple[str, float]:
        """
        Classify volume at pivot relative to recent average
        
        Args:
            df: DataFrame with 'volume' column
            pivot_index: Integer index of pivot bar
        
        Returns:
            Tuple of (state, ratio):
                state: 'CLIMAX', 'HIGH', 'NORMAL', or 'LOW'
                ratio: Volume / Average volume
        
        Classification:
            CLIMAX: >2.0x average (very strong signal - institutional activity)
            HIGH: 1.5-2.0x average (good signal - above average interest)
            NORMAL: 0.7-1.5x average (neutral - typical volume)
            LOW: <0.7x average (weak signal - low conviction)
        """
        # Get lookback window (before pivot, not including pivot)
        lookback_start = max(0, pivot_index - self.lookback)
        
        # Calculate average volume over lookback period
        avg_volume = df.iloc[lookback_start:pivot_index]['volume'].mean()
        
        # Get pivot volume
        pivot_volume = df.iloc[pivot_index]['volume']
        
        # Calculate ratio
        ratio = pivot_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Classify
        if ratio > 2.0:
            state = 'CLIMAX'
        elif ratio > 1.5:
            state = 'HIGH'
        elif ratio > 0.7:
            state = 'NORMAL'
        else:
            state = 'LOW'
        
        return state, ratio
    
    def confirm_bearish_reversal(self, df: pd.DataFrame, pivot_index: int) -> Tuple[bool, str, float]:
        """
        Confirm bearish reversal (expecting Lower High)
        
        Theory:
        At a pivot high, we're predicting the price will reverse down (make a Lower High).
        High volume at a top indicates distribution - institutional selling into retail buying.
        This is a bearish confirmation.
        
        Args:
            df: DataFrame with 'volume' column
            pivot_index: Integer index of pivot high
        
        Returns:
            Tuple of (confirmed, vol_state, vol_ratio):
                confirmed: True if volume confirms bearish reversal
                vol_state: 'CLIMAX', 'HIGH', 'NORMAL', or 'LOW'
                vol_ratio: Volume / Average volume
        
        Logic:
            Confirmed if vol_state in ['HIGH', 'CLIMAX']
            - HIGH/CLIMAX = Strong selling pressure
            - NORMAL/LOW = Weak top (less confident)
        
        Example:
            >>> # At pivot high, pattern predicts LH
            >>> confirmed, state, ratio = analyzer.confirm_bearish_reversal(df, pivot_idx)
            >>> if confirmed:
            >>>     # Take short position with high confidence
            >>>     print(f"Bearish confirmed: {state} volume ({ratio:.2f}x)")
        """
        vol_state, ratio = self.get_volume_state(df, pivot_index)
        
        # Confirm if HIGH or CLIMAX volume
        # High volume at top = distribution = bearish
        confirmed = vol_state in ['HIGH', 'CLIMAX']
        
        return confirmed, vol_state, ratio
    
    def confirm_bullish_reversal(self, df: pd.DataFrame, pivot_index: int) -> Tuple[bool, str, float]:
        """
        Confirm bullish reversal (expecting Higher High)
        
        Theory:
        At a pivot high, we're predicting the price will continue up (make a Higher High).
        Low volume at a top indicates weak rally with no institutional selling.
        This suggests the uptrend will continue (bullish confirmation).
        
        Args:
            df: DataFrame with 'volume' column
            pivot_index: Integer index of pivot high
        
        Returns:
            Tuple of (confirmed, vol_state, vol_ratio):
                confirmed: True if volume confirms bullish continuation
                vol_state: 'CLIMAX', 'HIGH', 'NORMAL', or 'LOW'
                vol_ratio: Volume / Average volume
        
        Logic:
            Confirmed if vol_state in ['LOW', 'NORMAL']
            - LOW/NORMAL = No distribution, weak selling
            - HIGH/CLIMAX = Strong selling (bearish, not bullish)
        
        Example:
            >>> # At pivot high, pattern predicts HH
            >>> confirmed, state, ratio = analyzer.confirm_bullish_reversal(df, pivot_idx)
            >>> if confirmed:
            >>>     # Continue long position with confidence
            >>>     print(f"Bullish confirmed: {state} volume ({ratio:.2f}x)")
        """
        vol_state, ratio = self.get_volume_state(df, pivot_index)
        
        # Confirm if LOW or NORMAL volume
        # Low volume at top = no distribution = bullish continuation
        confirmed = vol_state in ['LOW', 'NORMAL']
        
        return confirmed, vol_state, ratio
    
    def get_volume_statistics(self, df: pd.DataFrame) -> dict:
        """
        Get volume statistics for the entire dataset
        
        Args:
            df: DataFrame with 'volume' column
        
        Returns:
            Dictionary with volume statistics:
                - mean: Average volume
                - median: Median volume
                - std: Standard deviation
                - min: Minimum volume
                - max: Maximum volume
                - climax_threshold: 2.0x mean
                - high_threshold: 1.5x mean
        
        Example:
            >>> stats = analyzer.get_volume_statistics(df)
            >>> print(f"Average volume: {stats['mean']:,.0f}")
            >>> print(f"Climax threshold: {stats['climax_threshold']:,.0f}")
        """
        return {
            'mean': df['volume'].mean(),
            'median': df['volume'].median(),
            'std': df['volume'].std(),
            'min': df['volume'].min(),
            'max': df['volume'].max(),
            'climax_threshold': df['volume'].mean() * 2.0,
            'high_threshold': df['volume'].mean() * 1.5,
        }


if __name__ == "__main__":
    """
    Test VolumeAnalyzer with sample data
    """
    print("="*80)
    print("VOLUME ANALYZER TEST")
    print("="*80)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='30min')
    df = pd.DataFrame({
        'volume': np.random.lognormal(mean=10, sigma=0.5, size=100)
    }, index=dates)
    
    # Add some volume spikes
    df.iloc[50, df.columns.get_loc('volume')] *= 3.0  # Climax
    df.iloc[70, df.columns.get_loc('volume')] *= 1.7  # High
    df.iloc[30, df.columns.get_loc('volume')] *= 0.5  # Low
    
    # Initialize analyzer
    analyzer = VolumeAnalyzer(lookback=20)
    
    # Test volume states
    print("\nVolume State Classification:")
    for idx in [30, 50, 70]:
        state, ratio = analyzer.get_volume_state(df, idx)
        print(f"  Index {idx}: {state} ({ratio:.2f}x average)")
    
    # Test bearish confirmation
    print("\nBearish Reversal Confirmation:")
    for idx in [30, 50, 70]:
        confirmed, state, ratio = analyzer.confirm_bearish_reversal(df, idx)
        status = "✅ CONFIRMED" if confirmed else "❌ REJECTED"
        print(f"  Index {idx}: {status} - {state} volume ({ratio:.2f}x)")
    
    # Test bullish confirmation
    print("\nBullish Reversal Confirmation:")
    for idx in [30, 50, 70]:
        confirmed, state, ratio = analyzer.confirm_bullish_reversal(df, idx)
        status = "✅ CONFIRMED" if confirmed else "❌ REJECTED"
        print(f"  Index {idx}: {status} - {state} volume ({ratio:.2f}x)")
    
    # Statistics
    print("\nVolume Statistics:")
    stats = analyzer.get_volume_statistics(df)
    for key, value in stats.items():
        print(f"  {key}: {value:,.2f}")
    
    print("\n" + "="*80)
    print("✅ VolumeAnalyzer test complete!")
    print("="*80)
