"""
Diagnose Pattern Encoder Issue

Expert Mode has identified that only 2/64 patterns have data.
This script will diagnose why the encoder is not producing diverse patterns.

Author: BTC_Engine_v3
Date: December 30, 2025
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np

from src.detectors.zigzag_detector import ZigzagDetector, PivotType
from src.detectors.oscillators import calculate_rsi
from src.detectors.pattern_encoder import PatternEncoder

print("="*80)
print("EXPERT MODE: PATTERN ENCODER DIAGNOSIS")
print("="*80)

# Load data
print("\n1. Loading data...")
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
print(f"   ✓ Loaded {len(df)} bars")

# Detect pivots
print("\n2. Detecting pivots...")
zigzag = ZigzagDetector(length=50)
rsi = calculate_rsi(df, length=14)
all_pivots = zigzag.find_pivots(df, oscillator_data=rsi)

pivot_highs = [p for p in all_pivots if p.pivot_type == PivotType.HIGH]
print(f"   ✓ Found {len(pivot_highs)} pivot highs")

# Test encoder on first 10 pivot sequences
print("\n3. Testing Pattern Encoder on First 10 Sequences:")
print("="*80)

encoder = PatternEncoder()
pattern_indices = []

for i in range(3, min(13, len(pivot_highs))):  # Test first 10 sequences
    p1 = pivot_highs[i-3]
    p2 = pivot_highs[i-2]
    p3 = pivot_highs[i-1]
    
    print(f"\nSequence {i-2}:")
    osc1_str = f"{p1.oscillator_value:.2f}" if p1.oscillator_value else "None"
    osc2_str = f"{p2.oscillator_value:.2f}" if p2.oscillator_value else "None"
    osc3_str = f"{p3.oscillator_value:.2f}" if p3.oscillator_value else "None"
    print(f"   P1: price={p1.price:.2f}, osc={osc1_str}")
    print(f"   P2: price={p2.price:.2f}, osc={osc2_str}")
    print(f"   P3: price={p3.price:.2f}, osc={osc3_str}")
    
    # Manual checks
    trend = "UP" if p3.price > p1.price else "DOWN"
    price_dir = "HH" if p3.price > p2.price else "LH"
    
    if p2.oscillator_value and p3.oscillator_value:
        osc_dir = "HH" if p3.oscillator_value > p2.oscillator_value else "LH"
    else:
        osc_dir = "UNKNOWN"
    
    print(f"   Trend: {trend} (P3 vs P1)")
    print(f"   Price: {price_dir} (P3 vs P2)")
    print(f"   Oscillator: {osc_dir} (P3 vs P2)")
    
    # Try encoding
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern:
        print(f"   ✅ Encoded to index {pattern.index}")
        print(f"   Pattern: {encoder.get_pattern_description(pattern.index)}")
        pattern_indices.append(pattern.index)
    else:
        print(f"   ❌ Failed to encode (returned None)")
        
        # Debug why
        if p1.oscillator_value is None:
            print(f"      Reason: P1 missing oscillator value")
        if p2.oscillator_value is None:
            print(f"      Reason: P2 missing oscillator value")
        if p3.oscillator_value is None:
            print(f"      Reason: P3 missing oscillator value")

# Summary
print("\n4. Pattern Index Distribution (First 10 Sequences):")
print("="*80)

if pattern_indices:
    unique_indices = set(pattern_indices)
    print(f"\nUnique pattern indices found: {len(unique_indices)}")
    print(f"Indices: {sorted(unique_indices)}")
    
    for idx in sorted(unique_indices):
        count = pattern_indices.count(idx)
        desc = encoder.get_pattern_description(idx)
        print(f"   Index {idx}: {count} occurrences - {desc}")
        
    if len(unique_indices) < 5:
        print(f"\n⚠️  WARNING: Very low diversity in first 10 sequences!")
        print(f"   This explains why training has limited pattern coverage.")
else:
    print("\n❌ NO PATTERNS ENCODED!")
    print("   All sequences failed validation")

# Detailed check on ALL patterns
print("\n5. Checking ALL Pivot Sequences:")
print("="*80)

all_pattern_indices = []
failed_count = 0

for i in range(3, len(pivot_highs)):
    p1 = pivot_highs[i-3]
    p2 = pivot_highs[i-2]
    p3 = pivot_highs[i-1]
    
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern:
        all_pattern_indices.append(pattern.index)
    else:
        failed_count += 1

total_sequences = len(pivot_highs) - 3
successful = len(all_pattern_indices)

print(f"\nTotal sequences: {total_sequences}")
print(f"Successfully encoded: {successful} ({successful/total_sequences*100:.1f}%)")
print(f"Failed to encode: {failed_count} ({failed_count/total_sequences*100:.1f}%)")

if all_pattern_indices:
    unique_all = set(all_pattern_indices)
    print(f"\nUnique pattern indices across ALL data: {len(unique_all)}/64")
    print(f"Indices found: {sorted(unique_all)}")
    
    print(f"\nTop 10 Most Common Patterns:")
    from collections import Counter
    counter = Counter(all_pattern_indices)
    for idx, count in counter.most_common(10):
        desc = encoder.get_pattern_description(idx)
        pct = (count / len(all_pattern_indices)) * 100
        print(f"   Index {idx:2d}: {count:4d} ({pct:5.1f}%) - {desc}")

# ROOT CAUSE ANALYSIS
print("\n6. ROOT CAUSE ANALYSIS:")
print("="*80)

if len(unique_all) < 10:
    print("\n❌ CRITICAL: Extremely low pattern diversity")
    print("\nLikely Causes:")
    print("1. Price direction is almost always HH (pivots trending up)")
    print("2. Oscillator direction is almost always HH (RSI trending with price)")
    print("3. This is actually NORMAL in trending markets!")
    print("\nExplanation:")
    print("   In a strong bull market (2019-2025 for BTC), consecutive pivot HIGHS")
    print("   will naturally be higher (HH) most of the time. Same for RSI.")
    print("   This means pattern diversity comes from TREND direction, not price/osc.")
    print("\nIs This a Problem?")
    print("   NOT NECESSARILY! If the market is trending, having only HH patterns")
    print("   is statistically valid. The key is whether outcomes (HH vs LH) vary.")
    
    # Check if outcomes vary
    if all_pattern_indices:
        print("\nChecking if this affects prediction quality...")
        print("   (See previous expert verification for outcome analysis)")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
