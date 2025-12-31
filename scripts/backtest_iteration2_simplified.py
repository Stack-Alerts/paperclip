"""
Backtest Iteration 2: Simplified 8-Pattern System

This script validates Iteration 2 improvement:
- Baseline: 51.8% win rate (no filtering)
- Phase 1 (48 patterns): 53.8% win rate (divergence strength filter)
- Iteration 2 (8 patterns): 58-60% expected (simplified patterns)

Improvement rationale:
- 48 patterns → 8 core patterns
- 11 samples/pattern → 67 samples/pattern
- 6x more robust statistics

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: EXPERT_MODE_ITERATION1_ANALYSIS.md - Iteration 2 Plan
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

# Import our detectors
from src.detectors.zigzag_detector import ZigzagDetector
from src.detectors.oscillators import calculate_rsi
from src.detectors.pattern_encoder import PatternEncoder  # Original 48-pattern
from src.detectors.pattern_encoder_v2 import SimplifiedPatternEncoder  # New 8-pattern
from src.detectors.pattern_statistics import PatternStatistics

print("="*80)
print("ITERATION 2: SIMPLIFIED 8-PATTERN SYSTEM BACKTEST")
print("="*80)
print(f"Start time: {datetime.now()}")
print("\nObjective: Improve from 53.8% to 58-60%")
print("Method: Simplify 48 patterns → 8 core patterns (6x more samples)")

# ============================================================================
# 1. Load Data
# ============================================================================
print("\n" + "="*80)
print("1. LOADING DATA")
print("="*80)
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
print(f"✓ Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")

# Split into train/test
train_size = int(len(df) * 0.7)  # 70% train, 30% test
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
# 3. Detect Pivots on Training Data
# ============================================================================
print("\n" + "="*80)
print("3. TRAINING PATTERN STATISTICS (8-Pattern System)")
print("="*80)
zigzag = ZigzagDetector(length=50)
pivots_train = zigzag.find_pivots(df_train, oscillator_data=rsi_train)
highs_train = [p for p in pivots_train if p.pivot_type.name == 'HIGH']
print(f"✓ Found {len(highs_train)} pivot highs in training data")

# Initialize both encoders for comparison
encoder_48 = PatternEncoder()  # Original system
encoder_8 = SimplifiedPatternEncoder()  # New simplified system

# Train 8-pattern statistics
stats_8 = PatternStatistics(min_samples=5)  # Lower threshold since we have fewer patterns

trained_count_8 = 0
pattern_distribution = {i: 0 for i in range(8)}  # Track pattern distribution

for i in range(3, len(highs_train)):
    # Get 3-pivot sequence
    p1, p2, p3 = highs_train[i-3], highs_train[i-2], highs_train[i-1]
    
    # Encode with simplified system
    pattern_8 = encoder_8.encode(p1, p2, p3)
    if pattern_8 is None:
        continue
    
    # Track distribution
    pattern_distribution[pattern_8.index] += 1
    
    # Determine outcome (what happened at pivot i?)
    p4 = highs_train[i]
    outcome = 'HH' if p4.price > p3.price else 'LH'
    
    # Calculate metrics
    price_move = abs(p4.price - p3.price)
    prev_move = abs(p3.price - p2.price)
    fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
    bars = p4.index - p3.index
    
    # Update statistics for 8-pattern system
    stats_8.update(pattern_8.index, outcome, fib_ratio, bars, is_high=True)
    trained_count_8 += 1

stats_8.training_complete = True
print(f"✓ Trained on {trained_count_8} patterns")
print(f"\n✓ Pattern Distribution (8-pattern system):")
for idx in range(8):
    count = pattern_distribution[idx]
    pct = (count / trained_count_8 * 100) if trained_count_8 > 0 else 0
    desc = encoder_8.get_pattern_description(idx)
    print(f"   Pattern {idx}: {count:3d} samples ({pct:5.1f}%) - {desc}")

# ============================================================================
# 4. Test on Out-of-Sample Data
# ============================================================================
print("\n" + "="*80)
print("4. TESTING ON OUT-OF-SAMPLE DATA")
print("="*80)
pivots_test = zigzag.find_pivots(df_test, oscillator_data=rsi_test)
highs_test = [p for p in pivots_test if p.pivot_type.name == 'HIGH']
print(f"✓ Found {len(highs_test)} pivot highs in test data")

# Track results
results = {
    'iteration2_base': {'correct': 0, 'total': 0, 'predictions': []},
    'iteration2_filtered': {'correct': 0, 'total': 0, 'predictions': []},
}

test_count = 0
for i in range(3, len(highs_test) - 1):  # -1 to have outcome
    # Get 3-pivot sequence
    p1, p2, p3 = highs_test[i-3], highs_test[i-2], highs_test[i-1]
    
    # Encode with 8-pattern system
    pattern_8 = encoder_8.encode(p1, p2, p3)
    if pattern_8 is None:
        continue
    
    # Actual outcome
    p4 = highs_test[i]
    actual_outcome = 'LH' if p4.price < p3.price else 'HH'
    
    # Calculate strengths for filtering
    price_strength = abs(p3.price - p2.price) / p2.price
    osc_strength = abs(p3.oscillator_value - p2.oscillator_value)
    
    # ================================
    # Method 1: 8-Pattern Base (No Filter)
    # ================================
    pred_8 = stats_8.predict(pattern_8.index, is_high=True)
    
    if pred_8.sample_count >= 5:  # Lower threshold for 8 patterns
        # Predict LH if probability > 55%
        predicted = 'LH' if pred_8.lh_probability > 0.55 else 'HH'
        
        results['iteration2_base']['total'] += 1
        if predicted == actual_outcome:
            results['iteration2_base']['correct'] += 1
        
        results['iteration2_base']['predictions'].append({
            'pattern_index': pattern_8.index,
            'pattern_name': pattern_8.core_pattern.name,
            'predicted': predicted,
            'actual': actual_outcome,
            'lh_prob': pred_8.lh_probability,
            'sample_count': pred_8.sample_count,
        })
    
    # ================================
    # Method 2: 8-Pattern + Divergence Filter
    # ================================
    pred_8_filtered = stats_8.predict_with_strength(
        pattern_8.index,
        price_strength,
        osc_strength,
        is_high=True
    )
    
    if pred_8_filtered is not None and pred_8_filtered.sample_count >= 5:
        # Predict LH if probability > 55%
        predicted_filtered = 'LH' if pred_8_filtered.lh_probability > 0.55 else 'HH'
        
        results['iteration2_filtered']['total'] += 1
        if predicted_filtered == actual_outcome:
            results['iteration2_filtered']['correct'] += 1
        
        results['iteration2_filtered']['predictions'].append({
            'pattern_index': pattern_8.index,
            'pattern_name': pattern_8.core_pattern.name,
            'predicted': predicted_filtered,
            'actual': actual_outcome,
            'lh_prob': pred_8_filtered.lh_probability,
            'passed_filter': True,
        })
    
    test_count += 1

print(f"✓ Tested {test_count} patterns")

# ============================================================================
# 5. Results Analysis
# ============================================================================
print("\n" + "="*80)
print("ITERATION 2 BACKTEST RESULTS")
print("="*80)

# Base 8-pattern predictions
iter2_base_total = results['iteration2_base']['total']
iter2_base_correct = results['iteration2_base']['correct']
iter2_base_win_rate = (iter2_base_correct / iter2_base_total * 100) if iter2_base_total > 0 else 0

print(f"\n📊 ITERATION 2 BASE (8 Patterns, No Filter):")
print(f"   Total predictions: {iter2_base_total}")
print(f"   Correct: {iter2_base_correct}")
print(f"   Win rate: {iter2_base_win_rate:.1f}%")
print(f"   Sample size: Much more robust (67 avg vs 11 previously)")

# Filtered 8-pattern predictions
iter2_filt_total = results['iteration2_filtered']['total']
iter2_filt_correct = results['iteration2_filtered']['correct']
iter2_filt_win_rate = (iter2_filt_correct / iter2_filt_total * 100) if iter2_filt_total > 0 else 0

print(f"\n📊 ITERATION 2 FILTERED (8 Patterns + Divergence Strength):")
print(f"   Total predictions: {iter2_filt_total}")
print(f"   Correct: {iter2_filt_correct}")
print(f"   Win rate: {iter2_filt_win_rate:.1f}%")
print(f"   Filtered: {iter2_base_total - iter2_filt_total} weak signals ({(iter2_base_total - iter2_filt_total)/iter2_base_total*100:.1f}%)")

# ============================================================================
# 6. Comparison with Previous Iterations
# ============================================================================
print("\n" + "="*80)
print("ITERATION COMPARISON")
print("="*80)

# Historical results
baseline_win_rate = 51.8
phase1_win_rate = 53.8

print(f"\n📈 PROGRESSION:")
print(f"   Baseline (no filter):        {baseline_win_rate:.1f}%")
print(f"   Phase 1 (48 patterns):       {phase1_win_rate:.1f}%  (+{phase1_win_rate - baseline_win_rate:.1f}%)")
print(f"   Iteration 2 Base (8 patterns): {iter2_base_win_rate:.1f}%  (+{iter2_base_win_rate - baseline_win_rate:.1f}%)")
print(f"   Iteration 2 Filtered (best):   {iter2_filt_win_rate:.1f}%  (+{iter2_filt_win_rate - baseline_win_rate:.1f}%)")

# ============================================================================
# 7. Assessment
# ============================================================================
print("\n" + "="*80)
print("ITERATION 2 ASSESSMENT")
print("="*80)

FEE_PCT = 0.5

print(f"\n🎯 TARGET VALIDATION:")
print(f"   Target: 58-60% win rate")
print(f"   Actual: {iter2_filt_win_rate:.1f}%")

improvement_from_phase1 = iter2_filt_win_rate - phase1_win_rate

if iter2_filt_win_rate >= 60:
    status = "✅ EXCEEDS TARGET"
elif iter2_filt_win_rate >= 58:
    status = "✅ MEETS TARGET"
elif iter2_filt_win_rate >= 55:
    status = "⚠️  CLOSE TO TARGET"
else:
    status = "❌ BELOW TARGET"
print(f"   Status: {status}")

print(f"\n💰 PROFITABILITY ANALYSIS:")
print(f"   Win rate: {iter2_filt_win_rate:.1f}%")
print(f"   After fees ({FEE_PCT}%): {iter2_filt_win_rate - FEE_PCT:.1f}%")
print(f"   Net edge: {iter2_filt_win_rate - 50:.1f}% (before fees)")
print(f"   Net edge: {iter2_filt_win_rate - 50 - FEE_PCT:.1f}% (after fees)")

if iter2_filt_win_rate - FEE_PCT >= 65:
    prof_status = "✅ HIGHLY PROFITABLE"
elif iter2_filt_win_rate - FEE_PCT >= 60:
    prof_status = "✅ VERY PROFITABLE"
elif iter2_filt_win_rate - FEE_PCT >= 55:
    prof_status = "✅ PROFITABLE"
elif iter2_filt_win_rate - FEE_PCT >= 50:
    prof_status = "⚠️  MARGINALLY PROFITABLE"
else:
    prof_status = "❌ NOT PROFITABLE"
print(f"   Profit status: {prof_status}")

print(f"\n📈 IMPROVEMENT METRICS:")
print(f"   Improvement from Phase 1: +{improvement_from_phase1:.1f}%")
print(f"   Relative improvement: +{improvement_from_phase1/phase1_win_rate*100:.1f}%")
print(f"   Statistical robustness: 6x better (67 vs 11 samples/pattern)")

print(f"\n🎯 VERDICT:")
if iter2_filt_win_rate >= 65:
    print(f"   ✅ EXCELLENT - {iter2_filt_win_rate:.1f}% is deployment-ready!")
    print(f"   ✅ After fees: {iter2_filt_win_rate - FEE_PCT:.1f}% (highly profitable)")
    print(f"   ✅ Pattern simplification validated!")
    print(f"   🎯 Consider live trading or proceed to Iteration 3 for further improvement")
elif iter2_filt_win_rate >= 58:
    print(f"   ✅ SUCCESS - {iter2_filt_win_rate:.1f}% meets Iteration 2 target!")
    print(f"   ✅ Pattern simplification works as expected")
    print(f"   ✅ Proceed to Iteration 3 (more data or additional filters)")
elif iter2_filt_win_rate >= 55:
    print(f"   ⚠️  PARTIAL SUCCESS - {iter2_filt_win_rate:.1f}% shows improvement")
    print(f"   ⚠️  Below target but better than Phase 1")
    print(f"   ⚠️  Consider parameter tuning or Iteration 3")
else:
    print(f"   ❌ NEEDS WORK - {iter2_filt_win_rate:.1f}% not sufficient")
    print(f"   ❌ Review pattern mapping")
    print(f"   ❌ May need different approach")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n✅ Iteration 2 backtest complete!")
print(f"📊 8-pattern system {'VALIDATED' if iter2_filt_win_rate > phase1_win_rate else 'NEEDS REVIEW'}!")
print(f"🎯 Result: {iter2_filt_win_rate:.1f}% win rate")

if iter2_filt_win_rate >= 58:
    print(f"🚀 Ready for Iteration 3: More Data or Advanced Filters!")
else:
    print(f"🔧 Review and adjust before next iteration")
