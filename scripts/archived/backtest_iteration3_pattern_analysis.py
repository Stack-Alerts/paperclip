"""
Backtest Iteration 3: Data-Driven Pattern Analysis

This script analyzes ALL 48 patterns to identify which have real edge:
- Analyzes BOTH pivot HIGHS and LOWS (complete analysis)
- Measures win rate for each pattern individually
- Identifies patterns with >55% win rate
- Recommends which patterns to keep

Expected outcome:
- Identify 12-18 high-edge patterns
- Win rate: 58-63% when using only selected patterns
- Statistical robustness: 30-45 samples per pattern

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: EXPERT_MODE_ITERATION2_ANALYSIS.md - Iteration 3 Plan
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Import our detectors
from src.detectors.zigzag_detector import ZigzagDetector
from src.detectors.oscillators import calculate_rsi
from src.detectors.pattern_encoder import PatternEncoder
from src.detectors.pattern_statistics import PatternStatistics

print("="*80)
print("ITERATION 3: COMPREHENSIVE 48-PATTERN EDGE ANALYSIS")
print("="*80)
print(f"Start time: {datetime.now()}")
print("\nObjective: Identify which patterns have REAL edge")
print("Method: Analyze ALL 48 patterns (HIGHS + LOWS) and measure individual win rates")
print("Goal: Find 12-18 patterns with >55% win rate")

# ============================================================================
# 1. Load Data
# ============================================================================
print("\n" + "="*80)
print("1. LOADING DATA")
print("="*80)
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
print(f"✓ Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")

# Split into train/test
train_size = int(len(df) * 0.7)
df_train = df.iloc[:train_size]
df_test = df.iloc[train_size:]

print(f"✓ Train: {len(df_train)} bars ({df_train.index[0]} to {df_train.index[-1]})")
print(f"✓ Test:  {len(df_test)} bars ({df_test.index[0]} to {df_test.index[-1]})")

# ============================================================================
# 2. Calculate RSI
# ============================================================================
print("\n" + "="*80)
print("2. CALCULATING INDICATORS")
print("="*80)
rsi = calculate_rsi(df, length=14)
rsi_train = rsi.iloc[:train_size]
rsi_test = rsi.iloc[train_size:]
print(f"✓ RSI calculated (length=14)")

# ============================================================================
# 3. Detect Pivots - COMPLETE ANALYSIS (HIGHS + LOWS)
# ============================================================================
print("\n" + "="*80)
print("3. COMPREHENSIVE PIVOT ANALYSIS (HIGHS + LOWS)")
print("="*80)
zigzag = ZigzagDetector(length=50)
pivots_train = zigzag.find_pivots(df_train, oscillator_data=rsi_train)

highs_train = [p for p in pivots_train if p.pivot_type.name == 'HIGH']
lows_train = [p for p in pivots_train if p.pivot_type.name == 'LOW']

print(f"✓ Found {len(highs_train)} pivot HIGHS in training data")
print(f"✓ Found {len(lows_train)} pivot LOWS in training data")
print(f"✓ Total training pivots: {len(pivots_train)}")

# ============================================================================
# 4. Train Pattern Statistics - ALL 48 PATTERNS (HIGHS + LOWS)
# ============================================================================
print("\n" + "="*80)
print("4. TRAINING ALL 48 PATTERNS")
print("="*80)

encoder = PatternEncoder()

# Pattern statistics for detailed tracking
pattern_outcomes = defaultdict(lambda: {'HH': 0, 'LH': 0, 'HL': 0, 'LL': 0, 'total': 0})

def analyze_pivot_sequence(pivots, is_high=True):
    """Analyze a sequence of pivots and track pattern outcomes"""
    trained = 0
    
    for i in range(3, len(pivots)):
        # Get 3-pivot sequence
        p1, p2, p3 = pivots[i-3], pivots[i-2], pivots[i-1]
        
        # Encode pattern
        pattern = encoder.encode(p1, p2, p3)
        if pattern is None:
            continue
        
        # Determine outcome (what happened at pivot i?)
        p4 = pivots[i]
        
        if is_high:
            outcome = 'HH' if p4.price > p3.price else 'LH'
        else:
            outcome = 'LL' if p4.price < p3.price else 'HL'
        
        # Track outcome
        pattern_outcomes[pattern.index][outcome] += 1
        pattern_outcomes[pattern.index]['total'] += 1
        trained += 1
    
    return trained

# Analyze HIGHS
trained_highs = analyze_pivot_sequence(highs_train, is_high=True)
print(f"✓ Analyzed {trained_highs} HIGH pivot patterns")

# Analyze LOWS  
trained_lows = analyze_pivot_sequence(lows_train, is_high=False)
print(f"✓ Analyzed {trained_lows} LOW pivot patterns")

total_trained = trained_highs + trained_lows
print(f"✓ Total patterns analyzed: {total_trained}")

# ============================================================================
# 5. Analyze Edge for Each Pattern
# ============================================================================
print("\n" + "="*80)
print("5. PATTERN EDGE ANALYSIS (ALL 48 PATTERNS)")
print("="*80)

# Calculate win rate for each pattern
pattern_analysis = []

for pattern_idx in range(48):
    if pattern_idx not in pattern_outcomes:
        # No samples
        pattern_analysis.append({
            'pattern': pattern_idx,
            'samples': 0,
            'win_rate': 0.0,
            'edge': 0.0,
            'description': encoder.get_pattern_description(pattern_idx),
            'keep': False
        })
        continue
    
    stats = pattern_outcomes[pattern_idx]
    total = stats['total']
    
    if total == 0:
        continue
    
    # For pattern analysis, we care about predicting correctly
    # For HIGHS: Predict LH (bearish) when pattern suggests bearish
    # For LOWS: Predict HL (bullish) when pattern suggests bullish
    
    # Simplified: Count "correct" predictions
    # This needs context of what each pattern predicts
    # For now, use the dominant outcome as the prediction
    
    hh = stats.get('HH', 0)
    lh = stats.get('LH', 0)
    hl = stats.get('HL', 0)
    ll = stats.get('LL', 0)
    
    # For highs: LH or HH?
    high_outcomes = hh + lh
    if high_outcomes > 0:
        lh_rate = lh / high_outcomes
    else:
        lh_rate = 0.5
    
    # For lows: HL or LL?
    low_outcomes = hl + ll
    if low_outcomes > 0:
        hl_rate = hl / low_outcomes
    else:
        hl_rate = 0.5
    
    # Combined win rate: average of high and low prediction rates
    # Predict the dominant outcome
    if high_outcomes > 0 and low_outcomes > 0:
        win_rate = (max(lh_rate, 1-lh_rate) + max(hl_rate, 1-hl_rate)) / 2
    elif high_outcomes > 0:
        win_rate = max(lh_rate, 1-lh_rate)
    elif low_outcomes > 0:
        win_rate = max(hl_rate, 1-hl_rate)
    else:
        win_rate = 0.5
    
    edge = (win_rate - 0.5) * 100  # Edge above random
    
    # Keep if win rate > 55% and sufficient samples
    keep = win_rate > 0.55 and total >= 5
    
    pattern_analysis.append({
        'pattern': pattern_idx,
        'samples': total,
        'win_rate': win_rate * 100,
        'edge': edge,
        'lh_rate': lh_rate * 100 if high_outcomes > 0 else None,
        'hl_rate': hl_rate * 100 if low_outcomes > 0 else None,
        'description': encoder.get_pattern_description(pattern_idx),
        'keep': keep
    })

# Sort by edge (descending)
pattern_analysis.sort(key=lambda x: x['edge'], reverse=True)

# ============================================================================
# 6. Display Results
# ============================================================================
print("\n" + "="*80)
print("PATTERN EDGE RANKING (by edge above random)")
print("="*80)
print(f"\n{'Rank':<5} {'Pat':<4} {'Samples':<8} {'Win%':<7} {'Edge%':<7} {'Keep?':<6} Description")
print("-" * 120)

kept_patterns = []
discarded_patterns = []

for rank, p in enumerate(pattern_analysis, 1):
    if p['samples'] == 0:
        continue
    
    keep_marker = "✅ KEEP" if p['keep'] else "❌ DROP"
    
    print(f"{rank:<5} {p['pattern']:<4} {p['samples']:<8} {p['win_rate']:<7.1f} {p['edge']:<7.1f} {keep_marker:<6} {p['description'][:70]}")
    
    if p['keep']:
        kept_patterns.append(p)
    else:
        discarded_patterns.append(p)

# ============================================================================
# 7. Summary Statistics
# ============================================================================
print("\n" + "="*80)
print("PATTERN SELECTION SUMMARY")
print("="*80)

total_patterns_with_data = len([p for p in pattern_analysis if p['samples'] > 0])
kept_count = len(kept_patterns)
discarded_count = len(discarded_patterns)

print(f"\n📊 PATTERN DISTRIBUTION:")
print(f"   Total patterns (48): {48}")
print(f"   Patterns with data: {total_patterns_with_data}")
print(f"   Patterns to KEEP: {kept_count} (>{55}% win rate)")
print(f"   Patterns to DISCARD: {discarded_count} (<55% win rate)")
print(f"   Patterns with no data: {48 - total_patterns_with_data}")

if kept_count > 0:
    total_kept_samples = sum(p['samples'] for p in kept_patterns)
    avg_samples_per_kept = total_kept_samples / kept_count
    avg_win_rate_kept = sum(p['win_rate'] for p in kept_patterns) / kept_count
    avg_edge_kept = sum(p['edge'] for p in kept_patterns) / kept_count
    
    print(f"\n📈 KEPT PATTERNS STATISTICS:")
    print(f"   Total samples: {total_kept_samples}")
    print(f"   Avg samples/pattern: {avg_samples_per_kept:.1f}")
    print(f"   Avg win rate: {avg_win_rate_kept:.1f}%")
    print(f"   Avg edge: {avg_edge_kept:.1f}%")
    print(f"   Statistical robustness: {'HIGH' if avg_samples_per_kept >= 30 else 'MEDIUM' if avg_samples_per_kept >= 20 else 'LOW'}")

# ============================================================================
# 8. Pattern Recommendations
# ============================================================================
print("\n" + "="*80)
print("RECOMMENDED PATTERNS TO KEEP")
print("="*80)

if kept_count >= 12:
    print(f"\n✅ SUCCESS: Found {kept_count} high-edge patterns!")
    print(f"   Target: 12-18 patterns")
    print(f"   Actual: {kept_count} patterns")
    print(f"   Status: ✅ MEETS TARGET")
elif kept_count >= 8:
    print(f"\n⚠️  PARTIAL SUCCESS: Found {kept_count} high-edge patterns")
    print(f"   Target: 12-18 patterns")
    print(f"   Actual: {kept_count} patterns")
    print(f"   Status: ⚠️  BELOW TARGET but usable")
else:
    print(f"\n❌ INSUFFICIENT: Only found {kept_count} high-edge patterns")
    print(f"   Target: 12-18 patterns")
    print(f"   Actual: {kept_count} patterns")
    print(f"   Status: ❌ TOO FEW")

print(f"\n🎯 KEPT PATTERNS (indices):")
kept_indices = [p['pattern'] for p in kept_patterns]
print(f"   {kept_indices}")

print(f"\n📋 NEXT STEPS:")
if kept_count >= 8:
    print(f"   1. Create selective encoder using these {kept_count} patterns")
    print(f"   2. Re-train statistics on selected patterns only")
    print(f"   3. Backtest with {kept_count}-pattern system")
    print(f"   4. Expected win rate: {avg_win_rate_kept:.1f}% (vs 51.6% in Iteration 2)")
    print(f"   5. Expected improvement: +{avg_win_rate_kept - 51.6:.1f}%")
else:
    print(f"   1. Review why so few patterns have edge")
    print(f"   2. Consider lowering threshold to 53-54%")
    print(f"   3. Or add more training data")
    print(f"   4. Or try hierarchical approach")

# ============================================================================
# 9. Save Results
# ============================================================================
print("\n" + "="*80)
print("SAVING ANALYSIS RESULTS")
print("="*80)

# Save to CSV
df_analysis = pd.DataFrame(pattern_analysis)
df_analysis.to_csv('data/pattern_edge_analysis.csv', index=False)
print(f"✓ Saved pattern analysis to: data/pattern_edge_analysis.csv")

# Save kept patterns list
with open('data/kept_patterns.txt', 'w') as f:
    f.write(f"# High-Edge Patterns (>55% win rate)\n")
    f.write(f"# Generated: {datetime.now()}\n")
    f.write(f"# Total patterns: {kept_count}\n\n")
    for p in kept_patterns:
        f.write(f"Pattern {p['pattern']}: {p['win_rate']:.1f}% ({p['samples']} samples) - {p['description']}\n")
print(f"✓ Saved kept patterns to: data/kept_patterns.txt")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n✅ Pattern edge analysis complete!")
print(f"📊 {kept_count} high-edge patterns identified")
print(f"🎯 Average win rate of kept patterns: {avg_win_rate_kept if kept_count > 0 else 'N/A'}%")

if kept_count >= 12:
    print(f"\n🚀 Ready to proceed with Iteration 3 backtest!")
    print(f"   Expected win rate: {avg_win_rate_kept:.1f}%")
elif kept_count >= 8:
    print(f"\n⚠️  Can proceed but with caution (fewer patterns than target)")
else:
    print(f"\n❌ Need to adjust approach before proceeding")
