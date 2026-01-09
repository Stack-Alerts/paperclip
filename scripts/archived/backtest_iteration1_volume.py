"""
Backtest Iteration 1: Volume Confirmation

This script validates Iteration 1 improvement:
- Baseline: 51.8% win rate (no filtering)
- Phase 1: 53.8% win rate (divergence strength filter)
- Iteration 1: 57-59% expected (Phase 1 + Volume confirmation)

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: docs/ITERATION_PLAN_V2.md, docs/EXPERT_MODE_BASELINE_ANALYSIS.md
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
from src.detectors.volume_analyzer import VolumeAnalyzer

print("="*80)
print("ITERATION 1: VOLUME CONFIRMATION BACKTEST")
print("="*80)
print(f"Start time: {datetime.now()}")
print("\nTarget: 53.8% → 57-59% win rate")
print("Method: Add volume confirmation to Phase 1 filter")

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
print("3. TRAINING PATTERN STATISTICS")
print("="*80)
zigzag = ZigzagDetector(length=50)
pivots_train = zigzag.find_pivots(df_train, oscillator_data=rsi_train)
highs_train = [p for p in pivots_train if p.pivot_type.name == 'HIGH']
print(f"✓ Found {len(highs_train)} pivot highs in training data")

# Train pattern statistics
encoder = PatternEncoder()
stats = PatternStatistics(min_samples=10)

trained_count = 0
for i in range(3, len(highs_train)):
    # Get 3-pivot sequence
    p1, p2, p3 = highs_train[i-3], highs_train[i-2], highs_train[i-1]
    
    # Encode pattern
    pattern = encoder.encode(p1, p2, p3)
    if pattern is None:
        continue
    
    # Determine outcome (what happened at pivot i?)
    p4 = highs_train[i]
    outcome = 'HH' if p4.price > p3.price else 'LH'
    
    # Calculate metrics
    price_move = abs(p4.price - p3.price)
    prev_move = abs(p3.price - p2.price)
    fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
    bars = p4.index - p3.index
    
    # Update statistics
    stats.update(pattern.index, outcome, fib_ratio, bars, is_high=True)
    trained_count += 1

stats.training_complete = True
print(f"✓ Trained on {trained_count} patterns")

# ============================================================================
# 4. Initialize Volume Analyzer
# ============================================================================
print("\n" + "="*80)
print("4. INITIALIZING VOLUME ANALYZER")
print("="*80)
volume_analyzer = VolumeAnalyzer(lookback=20)
print(f"✓ VolumeAnalyzer initialized (lookback=20 bars)")

# Get volume statistics
vol_stats = volume_analyzer.get_volume_statistics(df_test)
print(f"✓ Test data volume statistics:")
print(f"  - Mean volume: {vol_stats['mean']:,.0f}")
print(f"  - Climax threshold (2.0x): {vol_stats['climax_threshold']:,.0f}")
print(f"  - High threshold (1.5x): {vol_stats['high_threshold']:,.0f}")

# ============================================================================
# 5. Test on Out-of-Sample Data
# ============================================================================
print("\n" + "="*80)
print("5. TESTING ON OUT-OF-SAMPLE DATA")
print("="*80)
pivots_test = zigzag.find_pivots(df_test, oscillator_data=rsi_test)
highs_test = [p for p in pivots_test if p.pivot_type.name == 'HIGH']
print(f"✓ Found {len(highs_test)} pivot highs in test data")

# Track results for each method
results = {
    'base': {'correct': 0, 'total': 0, 'predictions': []},
    'phase1': {'correct': 0, 'total': 0, 'predictions': []},
    'iteration1': {'correct': 0, 'total': 0, 'predictions': []},
}

# Volume state tracking
volume_states = {'CLIMAX': 0, 'HIGH': 0, 'NORMAL': 0, 'LOW': 0}
volume_confirmations = {'bearish_confirmed': 0, 'bearish_rejected': 0, 
                       'bullish_confirmed': 0, 'bullish_rejected': 0}

test_count = 0
for i in range(3, len(highs_test) - 1):  # -1 to have outcome
    # Get 3-pivot sequence
    p1, p2, p3 = highs_test[i-3], highs_test[i-2], highs_test[i-1]
    
    # Encode pattern
    pattern = encoder.encode(p1, p2, p3)
    if pattern is None:
        continue
    
    # Actual outcome
    p4 = highs_test[i]
    actual_outcome = 'LH' if p4.price < p3.price else 'HH'
    
    # Calculate strengths for Phase 1
    price_strength = abs(p3.price - p2.price) / p2.price
    osc_strength = abs(p3.oscillator_value - p2.oscillator_value)
    
    # Get volume state (need to map pivot index to dataframe index)
    # p3.index is the position in df_test
    vol_state, vol_ratio = volume_analyzer.get_volume_state(df_test, p3.index)
    volume_states[vol_state] += 1
    
    # ================================
    # Method 1: Base Prediction
    # ================================
    base_pred = stats.predict(pattern.index, is_high=True)
    
    if base_pred.sample_count >= 10:
        predicted = 'LH' if base_pred.lh_probability > 0.55 else 'HH'
        
        results['base']['total'] += 1
        if predicted == actual_outcome:
            results['base']['correct'] += 1
    
    # ================================
    # Method 2: Phase 1 Filter
    # ================================
    phase1_pred = stats.predict_with_strength(
        pattern.index,
        price_strength,
        osc_strength,
        is_high=True
    )
    
    if phase1_pred is not None and phase1_pred.sample_count >= 10:
        predicted_phase1 = 'LH' if phase1_pred.lh_probability > 0.55 else 'HH'
        
        results['phase1']['total'] += 1
        if predicted_phase1 == actual_outcome:
            results['phase1']['correct'] += 1
        
        # ================================
        # Method 3: Iteration 1 - Volume Confirmation
        # ================================
        
        # Check volume confirmation based on prediction
        if predicted_phase1 == 'LH':
            # Bearish prediction - need HIGH/CLIMAX volume
            vol_confirmed, vol_state, vol_ratio = volume_analyzer.confirm_bearish_reversal(df_test, p3.index)
            if vol_confirmed:
                volume_confirmations['bearish_confirmed'] += 1
            else:
                volume_confirmations['bearish_rejected'] += 1
        else:
            # Bullish prediction - need LOW/NORMAL volume
            vol_confirmed, vol_state, vol_ratio = volume_analyzer.confirm_bullish_reversal(df_test, p3.index)
            if vol_confirmed:
                volume_confirmations['bullish_confirmed'] += 1
            else:
                volume_confirmations['bullish_rejected'] += 1
        
        # Only count if volume confirms
        if vol_confirmed:
            results['iteration1']['total'] += 1
            if predicted_phase1 == actual_outcome:
                results['iteration1']['correct'] += 1
            
            results['iteration1']['predictions'].append({
                'pattern_index': pattern.index,
                'predicted': predicted_phase1,
                'actual': actual_outcome,
                'lh_prob': phase1_pred.lh_probability,
                'vol_state': vol_state,
                'vol_ratio': vol_ratio,
            })
    
    test_count += 1

print(f"✓ Tested {test_count} patterns")

# ============================================================================
# 6. Results Analysis
# ============================================================================
print("\n" + "="*80)
print("ITERATION 1 BACKTEST RESULTS")
print("="*80)

# Base predictions
base_total = results['base']['total']
base_correct = results['base']['correct']
base_win_rate = (base_correct / base_total * 100) if base_total > 0 else 0

print(f"\n📊 BASELINE (No Filtering):")
print(f"   Total predictions: {base_total}")
print(f"   Correct: {base_correct}")
print(f"   Win rate: {base_win_rate:.1f}%")

# Phase 1 predictions
phase1_total = results['phase1']['total']
phase1_correct = results['phase1']['correct']
phase1_win_rate = (phase1_correct / phase1_total * 100) if phase1_total > 0 else 0

print(f"\n📊 PHASE 1 (Divergence Strength Filter):")
print(f"   Total predictions: {phase1_total}")
print(f"   Correct: {phase1_correct}")
print(f"   Win rate: {phase1_win_rate:.1f}%")
print(f"   Improvement from base: +{phase1_win_rate - base_win_rate:.1f}%")

# Iteration 1 predictions
iter1_total = results['iteration1']['total']
iter1_correct = results['iteration1']['correct']
iter1_win_rate = (iter1_correct / iter1_total * 100) if iter1_total > 0 else 0

print(f"\n📊 ITERATION 1 (Phase 1 + Volume Confirmation): ⭐")
print(f"   Total predictions: {iter1_total}")
print(f"   Correct: {iter1_correct}")
print(f"   Win rate: {iter1_win_rate:.1f}%")
print(f"   Filtered: {phase1_total - iter1_total} weak volume signals ({(phase1_total - iter1_total)/phase1_total*100:.1f}%)")
print(f"   Improvement from Phase 1: +{iter1_win_rate - phase1_win_rate:.1f}%")
print(f"   Improvement from Base: +{iter1_win_rate - base_win_rate:.1f}%")

# Volume statistics
print(f"\n📊 VOLUME ANALYSIS:")
print(f"   Volume state distribution:")
for state, count in volume_states.items():
    pct = count / test_count * 100 if test_count > 0 else 0
    print(f"     {state}: {count} ({pct:.1f}%)")

print(f"\n   Volume confirmations:")
print(f"     Bearish confirmed: {volume_confirmations['bearish_confirmed']}")
print(f"     Bearish rejected: {volume_confirmations['bearish_rejected']}")
print(f"     Bullish confirmed: {volume_confirmations['bullish_confirmed']}")
print(f"     Bullish rejected: {volume_confirmations['bullish_rejected']}")

total_confirmed = volume_confirmations['bearish_confirmed'] + volume_confirmations['bullish_confirmed']
total_rejected = volume_confirmations['bearish_rejected'] + volume_confirmations['bullish_rejected']
confirm_rate = total_confirmed / (total_confirmed + total_rejected) * 100 if (total_confirmed + total_rejected) > 0 else 0
print(f"\n   Overall confirmation rate: {confirm_rate:.1f}%")

# ============================================================================
# 7. Iteration 1 Assessment
# ============================================================================
print("\n" + "="*80)
print("ITERATION 1 ASSESSMENT")
print("="*80)

FEE_PCT = 0.5

print(f"\n🎯 TARGET VALIDATION:")
print(f"   Target: 57-59% win rate")
print(f"   Actual: {iter1_win_rate:.1f}%")

if iter1_win_rate >= 59:
    status = "✅ EXCEEDS TARGET"
elif iter1_win_rate >= 57:
    status = "✅ MEETS TARGET"
elif iter1_win_rate >= 55:
    status = "⚠️  CLOSE TO TARGET"
else:
    status = "❌ BELOW TARGET"
print(f"   Status: {status}")

print(f"\n💰 PROFITABILITY ANALYSIS:")
print(f"   Win rate: {iter1_win_rate:.1f}%")
print(f"   After fees ({FEE_PCT}%): {iter1_win_rate - FEE_PCT:.1f}%")
print(f"   Net edge: {iter1_win_rate - 50:.1f}% (before fees)")
print(f"   Net edge: {iter1_win_rate - 50 - FEE_PCT:.1f}% (after fees)")

if iter1_win_rate - FEE_PCT >= 60:
    prof_status = "✅ HIGHLY PROFITABLE"
elif iter1_win_rate - FEE_PCT >= 55:
    prof_status = "✅ PROFITABLE"
elif iter1_win_rate - FEE_PCT >= 50:
    prof_status = "⚠️  MARGINALLY PROFITABLE"
else:
    prof_status = "❌ NOT PROFITABLE"
print(f"   Profit status: {prof_status}")

print(f"\n📈 IMPROVEMENT METRICS:")
improvement_from_phase1 = iter1_win_rate - phase1_win_rate
improvement_from_base = iter1_win_rate - base_win_rate
relative_improvement = improvement_from_base / base_win_rate * 100 if base_win_rate > 0 else 0

print(f"   Absolute improvement (from Phase 1): +{improvement_from_phase1:.1f}%")
print(f"   Absolute improvement (from Base): +{improvement_from_base:.1f}%")
print(f"   Relative improvement: +{relative_improvement:.1f}%")

print(f"\n🎯 VERDICT:")
if iter1_win_rate >= 65:
    print(f"   ✅ EXCELLENT - {iter1_win_rate:.1f}% exceeds target!")
    print(f"   ✅ Ready for deployment consideration")
    print(f"   ✅ Volume confirmation delivers significant edge")
elif iter1_win_rate >= 57:
    print(f"   ✅ SUCCESS - {iter1_win_rate:.1f}% meets Iteration 1 target!")
    print(f"   ✅ Volume confirmation works as expected")
    print(f"   ✅ Proceed to Iteration 2 (more data + pattern simplification)")
elif iter1_win_rate >= 55:
    print(f"   ⚠️  PARTIAL SUCCESS - {iter1_win_rate:.1f}% shows improvement")
    print(f"   ⚠️  Below target but moving in right direction")
    print(f"   ⚠️  Consider adjusting volume thresholds")
elif iter1_win_rate > phase1_win_rate:
    print(f"   ⚠️  MODEST IMPROVEMENT - {iter1_win_rate:.1f}% better than Phase 1")
    print(f"   ⚠️  Volume helps but not enough")
    print(f"   ⚠️  Need additional improvements")
else:
    print(f"   ❌ NO IMPROVEMENT - {iter1_win_rate:.1f}% not better than Phase 1")
    print(f"   ❌ Volume filter may need adjustment")
    print(f"   ❌ Review volume logic")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n✅ Iteration 1 backtest complete!")
print(f"📊 Volume confirmation {'VALIDATED' if iter1_win_rate > phase1_win_rate else 'NEEDS REVIEW'}!")
print(f"🎯 Result: {iter1_win_rate:.1f}% win rate")

if iter1_win_rate >= 57:
    print(f"🚀 Ready for Iteration 2: More Data + Pattern Simplification!")
else:
    print(f"🔧 Review and adjust before next iteration")
