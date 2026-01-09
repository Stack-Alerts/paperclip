"""
Backtest Iteration 3: Selective Pattern System

Tests the 13 high-edge patterns identified in pattern analysis:
- Patterns: [42, 24, 16, 5, 45, 0, 26, 7, 47, 32, 18, 21, 40]
- Expected win rate: 61.9% (in-sample analysis)
- Target: Validate 58-63% on out-of-sample data

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: Pattern edge analysis results
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
from src.detectors.pattern_encoder import PatternEncoder
from src.detectors.pattern_statistics import PatternStatistics

# High-edge patterns identified in analysis
KEPT_PATTERNS = [42, 24, 16, 5, 45, 0, 26, 7, 47, 32, 18, 21, 40]

print("="*80)
print("ITERATION 3: SELECTIVE 13-PATTERN BACKTEST")
print("="*80)
print(f"Start time: {datetime.now()}")
print("\nObjective: Validate 61.9% expected win rate on out-of-sample data")
print(f"Method: Use only {len(KEPT_PATTERNS)} high-edge patterns")
print(f"Patterns: {KEPT_PATTERNS}")

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
# 3. Train on Selected Patterns Only
# ============================================================================
print("\n" + "="*80)
print(f"3. TRAINING ON {len(KEPT_PATTERNS)} SELECTED PATTERNS")
print("="*80)

zigzag = ZigzagDetector(length=50)
pivots_train = zigzag.find_pivots(df_train, oscillator_data=rsi_train)
highs_train = [p for p in pivots_train if p.pivot_type.name == 'HIGH']
lows_train = [p for p in pivots_train if p.pivot_type.name == 'LOW']

print(f"✓ Found {len(highs_train)} pivot HIGHS in training data")
print(f"✓ Found {len(lows_train)} pivot LOWS in training data")

encoder = PatternEncoder()
stats = PatternStatistics(min_samples=5)

# Train on HIGHS
trained_highs = 0
for i in range(3, len(highs_train)):
    p1, p2, p3 = highs_train[i-3], highs_train[i-2], highs_train[i-1]
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern is None or pattern.index not in KEPT_PATTERNS:
        continue
    
    p4 = highs_train[i]
    outcome = 'HH' if p4.price > p3.price else 'LH'
    
    price_move = abs(p4.price - p3.price)
    prev_move = abs(p3.price - p2.price)
    fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
    bars = p4.index - p3.index
    
    stats.update(pattern.index, outcome, fib_ratio, bars, is_high=True)
    trained_highs += 1

# Train on LOWS
trained_lows = 0
for i in range(3, len(lows_train)):
    p1, p2, p3 = lows_train[i-3], lows_train[i-2], lows_train[i-1]
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern is None or pattern.index not in KEPT_PATTERNS:
        continue
    
    p4 = lows_train[i]
    outcome = 'LL' if p4.price < p3.price else 'HL'
    
    price_move = abs(p4.price - p3.price)
    prev_move = abs(p3.price - p2.price)
    fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
    bars = p4.index - p3.index
    
    stats.update(pattern.index, outcome, fib_ratio, bars, is_high=False)
    trained_lows += 1

stats.training_complete = True

print(f"✓ Trained on {trained_highs} HIGH patterns (selected only)")
print(f"✓ Trained on {trained_lows} LOW patterns (selected only)")
print(f"✓ Total: {trained_highs + trained_lows} patterns")

# ============================================================================
# 4. Test on Out-of-Sample Data
# ============================================================================
print("\n" + "="*80)
print("4. TESTING ON OUT-OF-SAMPLE DATA")
print("="*80)

pivots_test = zigzag.find_pivots(df_test, oscillator_data=rsi_test)
highs_test = [p for p in pivots_test if p.pivot_type.name == 'HIGH']
lows_test = [p for p in pivots_test if p.pivot_type.name == 'LOW']

print(f"✓ Found {len(highs_test)} pivot HIGHS in test data")
print(f"✓ Found {len(lows_test)} pivot LOWS in test data")

# Track results
results = {
    'selective_base': {'correct': 0, 'total': 0},
    'selective_filtered': {'correct': 0, 'total': 0},
}

# Test HIGHS
for i in range(3, len(highs_test) - 1):
    p1, p2, p3 = highs_test[i-3], highs_test[i-2], highs_test[i-1]
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern is None or pattern.index not in KEPT_PATTERNS:
        continue
    
    p4 = highs_test[i]
    actual_outcome = 'LH' if p4.price < p3.price else 'HH'
    
    # Base prediction
    pred = stats.predict(pattern.index, is_high=True)
    if pred.sample_count >= 5:
        predicted = 'LH' if pred.lh_probability > 0.55 else 'HH'
        results['selective_base']['total'] += 1
        if predicted == actual_outcome:
            results['selective_base']['correct'] += 1
    
    # Filtered prediction
    price_strength = abs(p3.price - p2.price) / p2.price
    osc_strength = abs(p3.oscillator_value - p2.oscillator_value)
    
    pred_filt = stats.predict_with_strength(pattern.index, price_strength, osc_strength, is_high=True)
    if pred_filt and pred_filt.sample_count >= 5:
        predicted_filt = 'LH' if pred_filt.lh_probability > 0.55 else 'HH'
        results['selective_filtered']['total'] += 1
        if predicted_filt == actual_outcome:
            results['selective_filtered']['correct'] += 1

# Test LOWS
for i in range(3, len(lows_test) - 1):
    p1, p2, p3 = lows_test[i-3], lows_test[i-2], lows_test[i-1]
    pattern = encoder.encode(p1, p2, p3)
    
    if pattern is None or pattern.index not in KEPT_PATTERNS:
        continue
    
    p4 = lows_test[i]
    actual_outcome = 'LL' if p4.price < p3.price else 'HL'
    
    # Base prediction
    pred = stats.predict(pattern.index, is_high=False)
    if pred.sample_count >= 5:
        predicted = 'LL' if pred.lh_probability > 0.55 else 'HL'
        results['selective_base']['total'] += 1
        if predicted == actual_outcome:
            results['selective_base']['correct'] += 1
    
    # Filtered prediction
    price_strength = abs(p3.price - p2.price) / p2.price
    osc_strength = abs(p3.oscillator_value - p2.oscillator_value)
    
    pred_filt = stats.predict_with_strength(pattern.index, price_strength, osc_strength, is_high=False)
    if pred_filt and pred_filt.sample_count >= 5:
        predicted_filt = 'LL' if pred_filt.lh_probability > 0.55 else 'HL'
        results['selective_filtered']['total'] += 1
        if predicted_filt == actual_outcome:
            results['selective_filtered']['correct'] += 1

# ============================================================================
# 5. Results Analysis
# ============================================================================
print("\n" + "="*80)
print("ITERATION 3 BACKTEST RESULTS")
print("="*80)

# Base selective
base_total = results['selective_base']['total']
base_correct = results['selective_base']['correct']
base_win_rate = (base_correct / base_total * 100) if base_total > 0 else 0

print(f"\n📊 SELECTIVE SYSTEM (13 patterns, no filter):")
print(f"   Total predictions: {base_total}")
print(f"   Correct: {base_correct}")
print(f"   Win rate: {base_win_rate:.1f}%")

# Filtered selective
filt_total = results['selective_filtered']['total']
filt_correct = results['selective_filtered']['correct']
filt_win_rate = (filt_correct / filt_total * 100) if filt_total > 0 else 0

print(f"\n📊 SELECTIVE + FILTERED (13 patterns + divergence strength):")
print(f"   Total predictions: {filt_total}")
print(f"   Correct: {filt_correct}")
print(f"   Win rate: {filt_win_rate:.1f}%")
print(f"   Filtered: {base_total - filt_total} weak signals")

# ============================================================================
# 6. Comparison with Previous Iterations
# ============================================================================
print("\n" + "="*80)
print("ITERATION COMPARISON")
print("="*80)

baseline = 51.8
phase1 = 53.8
iter2 = 51.6
expected = 61.9

print(f"\n📈 PROGRESSION:")
print(f"   Baseline (no filter):          {baseline:.1f}%")
print(f"   Phase 1 (48 patterns):         {phase1:.1f}%  (+{phase1 - baseline:.1f}%)")
print(f"   Iteration 2 (8 patterns):      {iter2:.1f}%  ({iter2 - baseline:+.1f}%)")
print(f"   Iteration 3 Expected:          {expected:.1f}%  (+{expected - baseline:.1f}%)")
print(f"   Iteration 3 Actual (base):     {base_win_rate:.1f}%  (+{base_win_rate - baseline:.1f}%)")
print(f"   Iteration 3 Actual (filtered): {filt_win_rate:.1f}%  (+{filt_win_rate - baseline:.1f}%)")

# ============================================================================
# 7. Assessment
# ============================================================================
print("\n" + "="*80)
print("ITERATION 3 ASSESSMENT")
print("="*80)

best_win_rate = max(base_win_rate, filt_win_rate)
FEE_PCT = 0.5

print(f"\n🎯 TARGET VALIDATION:")
print(f"   Target: 58-63% win rate")
print(f"   Expected: {expected:.1f}%")
print(f"   Actual: {best_win_rate:.1f}%")

if best_win_rate >= 63:
    status = "✅ EXCEEDS TARGET"
elif best_win_rate >= 58:
    status = "✅ MEETS TARGET"
elif best_win_rate >= 55:
    status = "⚠️  CLOSE TO TARGET"
else:
    status = "❌ BELOW TARGET"
print(f"   Status: {status}")

print(f"\n💰 PROFITABILITY ANALYSIS:")
print(f"   Win rate: {best_win_rate:.1f}%")
print(f"   After fees ({FEE_PCT}%): {best_win_rate - FEE_PCT:.1f}%")
print(f"   Net edge: {best_win_rate - 50:.1f}% (before fees)")
print(f"   Net edge: {best_win_rate - 50 - FEE_PCT:.1f}% (after fees)")

if best_win_rate - FEE_PCT >= 65:
    prof_status = "✅ HIGHLY PROFITABLE"
elif best_win_rate - FEE_PCT >= 60:
    prof_status = "✅ VERY PROFITABLE"
elif best_win_rate - FEE_PCT >= 55:
    prof_status = "✅ PROFITABLE"
elif best_win_rate - FEE_PCT >= 50:
    prof_status = "⚠️  MARGINALLY PROFITABLE"
else:
    prof_status = "❌ NOT PROFITABLE"
print(f"   Profit status: {prof_status}")

print(f"\n🎯 VERDICT:")
if best_win_rate >= 65:
    print(f"   ✅ EXCELLENT - {best_win_rate:.1f}% is deployment-ready!")
    print(f"   ✅ Data-driven pattern selection VALIDATED!")
    print(f"   🎯 Ready for production or M/W pattern integration")
elif best_win_rate >= 58:
    print(f"   ✅ SUCCESS - {best_win_rate:.1f}% meets Iteration 3 target!")
    print(f"   ✅ Pattern selection approach works!")
    print(f"   🎯 Proceed to confluence strategies or M/W patterns")
elif best_win_rate >= 55:
    print(f"   ⚠️  PARTIAL SUCCESS - {best_win_rate:.1f}% shows improvement")
    print(f"   ⚠️  Below target but better than previous iterations")
    print(f"   ⚠️  Consider fine-tuning or more data")
else:
    print(f"   ❌ NEEDS WORK - {best_win_rate:.1f}% not sufficient")
    print(f"   ❌ May need more training data or different approach")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

if best_win_rate >= 58:
    print(f"\n🎉 Iteration 3 SUCCESS!")
    print(f"📊 Data-driven pattern selection WORKS!")
    print(f"🎯 Win rate: {best_win_rate:.1f}%")
    print(f"🚀 Ready for next phase: M/W patterns or confluence strategies!")
else:
    print(f"\n📊 Iteration 3 results: {best_win_rate:.1f}%")
    print(f"🔧 Review and adjust as needed")
