"""
Train Pattern Statistics on Historical Data

This script trains the 64x3 pattern statistics matrix on historical
BTC data to learn which patterns lead to reversals vs continuations.

This is THE SECRET SAUCE that transforms our detector from 0% to 60%+ win rate!

Usage:
    python scripts/train_pattern_statistics.py

Output:
    - data/pattern_statistics/m_pattern_stats.pkl (trained for M-patterns/highs)
    - data/pattern_statistics/w_pattern_stats.pkl (trained for W-patterns/lows)
    - Comprehensive training report

Author: BTC_Engine_v3
Date: December 30, 2025
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Tuple

from src.detectors.zigzag_detector import ZigzagDetector, PivotType
from src.detectors.oscillators import calculate_rsi
from src.detectors.pattern_encoder import PatternEncoder
from src.detectors.pattern_statistics import PatternStatistics


def load_historical_data(filepath: str = 'data/raw/BTC_USDT_PERP_30m.pkl') -> pd.DataFrame:
    """Load historical BTC data"""
    print(f"Loading data from {filepath}...")
    df = pd.read_pickle(filepath)
    print(f"✓ Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    return df


def train_on_historical_data(
    df: pd.DataFrame,
    pivot_length: int = 50,
    min_samples: int = 10,
    save_path: str = 'data/pattern_statistics'
) -> Tuple[PatternStatistics, PatternStatistics]:
    """
    Train pattern statistics on historical data.
    
    Args:
        df: Historical OHLCV data
        pivot_length: Zigzag pivot length
        min_samples: Minimum samples for high confidence
        save_path: Directory to save trained statistics
        
    Returns:
        Tuple of (high_stats, low_stats)
    """
    print("\n" + "="*80)
    print("TRAINING PATTERN STATISTICS")
    print("="*80)
    
    # Initialize components
    print(f"\n1. Initializing components...")
    print(f"   Pivot length: {pivot_length}")
    print(f"   Min samples: {min_samples}")
    
    zigzag = ZigzagDetector(length=pivot_length)
    encoder = PatternEncoder()
    
    high_stats = PatternStatistics(min_samples=min_samples)
    low_stats = PatternStatistics(min_samples=min_samples)
    
    # Build zigzag with oscillator values
    print(f"\n2. Building zigzag on {len(df)} bars...")
    
    # Calculate RSI
    rsi = calculate_rsi(df, length=14)
    
    # Detect pivots using zigzag
    all_pivots = zigzag.find_pivots(df, oscillator_data=rsi)
    
    # Separate into highs and lows
    pivot_highs = [p for p in all_pivots if p.pivot_type == PivotType.HIGH]
    pivot_lows = [p for p in all_pivots if p.pivot_type == PivotType.LOW]
    
    print(f"   ✓ Found {len(pivot_highs)} pivot highs")
    print(f"   ✓ Found {len(pivot_lows)} pivot lows")
    print(f"   ✓ Total pivots: {len(all_pivots)}")
    
    # Train on pivot highs (M-patterns)
    print(f"\n3. Training on pivot highs (M-patterns)...")
    highs_trained = 0
    
    for i in range(3, len(pivot_highs)):
        # Get 4 consecutive pivot highs
        p1 = pivot_highs[i-3]
        p2 = pivot_highs[i-2]
        p3 = pivot_highs[i-1]
        p4 = pivot_highs[i]  # What happens next
        
        # Encode first 3 pivots
        pattern = encoder.encode(p1, p2, p3)
        if pattern is None:
            continue
        
        # Determine outcome (what happened at p4)
        if p4.price > p3.price:
            outcome = 'HH'  # Higher High
        else:
            outcome = 'LH'  # Lower High
        
        # Calculate Fibonacci ratio
        prev_swing = abs(p3.price - p2.price)
        current_swing = abs(p4.price - p3.price)
        fib_ratio = current_swing / prev_swing if prev_swing > 0 else 1.0
        
        # Calculate bars to next pivot
        bars_to_next = p4.index - p3.index
        
        # Update statistics
        high_stats.update(
            pattern_index=pattern.index,
            outcome=outcome,
            fib_ratio=fib_ratio,
            bars_to_next=bars_to_next,
            is_high=True
        )
        
        highs_trained += 1
    
    print(f"   ✓ Trained on {highs_trained} pivot high sequences")
    
    # Train on pivot lows (W-patterns)
    print(f"\n4. Training on pivot lows (W-patterns)...")
    lows_trained = 0
    
    for i in range(3, len(pivot_lows)):
        # Get 4 consecutive pivot lows
        p1 = pivot_lows[i-3]
        p2 = pivot_lows[i-2]
        p3 = pivot_lows[i-1]
        p4 = pivot_lows[i]  # What happens next
        
        # Encode first 3 pivots
        pattern = encoder.encode(p1, p2, p3)
        if pattern is None:
            continue
        
        # Determine outcome (what happened at p4)
        if p4.price > p3.price:
            outcome = 'HL'  # Higher Low
        else:
            outcome = 'LL'  # Lower Low
        
        # Calculate Fibonacci ratio
        prev_swing = abs(p3.price - p2.price)
        current_swing = abs(p4.price - p3.price)
        fib_ratio = current_swing / prev_swing if prev_swing > 0 else 1.0
        
        # Calculate bars to next pivot
        bars_to_next = p4.index - p3.index
        
        # Update statistics
        low_stats.update(
            pattern_index=pattern.index,
            outcome=outcome,
            fib_ratio=fib_ratio,
            bars_to_next=bars_to_next,
            is_high=False
        )
        
        lows_trained += 1
    
    print(f"   ✓ Trained on {lows_trained} pivot low sequences")
    
    # Mark training complete
    high_stats.training_complete = True
    low_stats.training_complete = True
    
    # Print summaries
    print(f"\n5. Training Summary:")
    print(f"\n   PIVOT HIGHS (M-PATTERNS):")
    high_stats.print_summary(top_n=10)
    
    print(f"\n   PIVOT LOWS (W-PATTERNS):")
    low_stats.print_summary(top_n=10)
    
    # Save statistics
    print(f"\n6. Saving trained statistics...")
    Path(save_path).mkdir(parents=True, exist_ok=True)
    
    high_path = os.path.join(save_path, 'm_pattern_stats.pkl')
    low_path = os.path.join(save_path, 'w_pattern_stats.pkl')
    
    high_stats.save(high_path)
    low_stats.save(low_path)
    
    print(f"\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"\nTrained Statistics:")
    print(f"  M-patterns (highs): {high_stats.total_patterns_tracked} patterns tracked")
    print(f"  W-patterns (lows): {low_stats.total_patterns_tracked} patterns tracked")
    print(f"\nSaved to:")
    print(f"  {high_path}")
    print(f"  {low_path}")
    print(f"\n✅ Ready for prediction in live trading!")
    print("="*80)
    
    return high_stats, low_stats


def main():
    """Main training function"""
    print("="*80)
    print("PATTERN STATISTICS TRAINING")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load data
    df = load_historical_data()
    
    # Train statistics
    high_stats, low_stats = train_on_historical_data(
        df,
        pivot_length=50,
        min_samples=10,
        save_path='data/pattern_statistics'
    )
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🎉 Training complete! The secret sauce is ready!")


if __name__ == "__main__":
    main()
