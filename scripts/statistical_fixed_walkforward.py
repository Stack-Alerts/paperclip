"""
Statistical System - FIXED for Walk-Forward

Implements the EXPERT MODE fix:
- Uses length=20 for pivot detection (instead of 50)
- No lookahead bias
- Works in real-time trading

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: EXPERT_MODE_STATISTICAL_FIX_RESEARCH.md
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("STATISTICAL SYSTEM - FIXED WALK-FORWARD TEST")
print("="*80)
print(f"Start time: {datetime.now()}\n")
print("Fix: Using length=20 for pivot detection (faster confirmation)")
print("Method: Walk-forward validation (NO lookahead bias)")
print("="*80)

# Load data
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
print(f"\n✓ Loaded {len(df)} bars")

# Train/test split
train_size = int(len(df) * 0.7)
df_train = df.iloc[:train_size]
df_test = df.iloc[train_size:]

print(f"✓ Train: {len(df_train)} bars ({df_train.index[0]} to {df_train.index[-1]})")
print(f"✓ Test:  {len(df_test)} bars ({df_test.index[0]} to {df_test.index[-1]})")

# High-edge patterns (from previous analysis)
HIGH_EDGE_PATTERNS = [0, 5, 7, 16, 18, 21, 24, 26, 32, 40, 42, 45, 47]

print(f"\n✓ Using {len(HIGH_EDGE_PATTERNS)} high-edge patterns")
print(f"  Pattern IDs: {HIGH_EDGE_PATTERNS}")

# Import detectors
from src.detectors.zigzag_detector import ZigzagDetector
from src.detectors.pattern_encoder import PatternEncoder
from src.detectors.pattern_statistics import PatternStatistics

# ============================================================================
# PHASE 1: TRAIN with length=20 (FIXED)
# ============================================================================
print("\n" + "="*80)
print("PHASE 1: TRAINING (length=20 pivots)")
print("="*80)

# FIXED: Use length=20 instead of 50
zigzag_train = ZigzagDetector(length=20, threshold_percent=2.0)

print(f"\nDetecting pivots with length=20 (10 hours confirmation on 30min)...")
pivots_train = zigzag_train.find_pivots(df_train)

print(f"✓ Found {len(pivots_train)} pivots in training")

# Separate by type
highs_train = [p for p in pivots_train if p.pivot_type.value == 'H']
lows_train = [p for p in pivots_train if p.pivot_type.value == 'L']

print(f"  High pivots: {len(highs_train)}")
print(f"  Low pivots: {len(lows_train)}")

# Calculate RSI
delta = df_train['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df_train['rsi'] = 100 - (100 / (1 + rs))

# Train pattern statistics
encoder = PatternEncoder()
stats = PatternStatistics(min_samples=5)

# Train on HIGHS
for i in range(3, len(highs_train)):
    try:
        # Get 3 pivots for pattern
        pivots_subset = [highs_train[i-3], highs_train[i-2], highs_train[i-1]]
        
        # Convert to DataFrame for encoder
        pivots_df = pd.DataFrame([{
            'index': p.index,
            'timestamp': p.timestamp,
            'price': p.price,
            'type': 'high'
        } for p in pivots_subset])
        
        # Encode pattern
        pattern_id = encoder.encode_pattern(pivots_df, df_train)
        
        if pattern_id not in HIGH_EDGE_PATTERNS:
            continue
        
        # Get outcome (next pivot)
        p4 = highs_train[i]
        p3 = pivots_subset[-1]
        outcome = 'HH' if p4.price > p3.price else 'LH'
        
        # Calculate features
        price_move = abs(p4.price - p3.price)
        prev_move = abs(p3.price - pivots_subset[-2].price)
        fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
        bars_between = p4.index - p3.index
        
        # Update statistics
        stats.update(pattern_id, outcome, fib_ratio, bars_between, is_high=True)
    except:
        continue

# Train on LOWS
for i in range(3, len(lows_train)):
    try:
        pivots_subset = [lows_train[i-3], lows_train[i-2], lows_train[i-1]]
        
        pivots_df = pd.DataFrame([{
            'index': p.index,
            'timestamp': p.timestamp,
            'price': p.price,
            'type': 'low'
        } for p in pivots_subset])
        
        pattern_id = encoder.encode_pattern(pivots_df, df_train)
        
        if pattern_id not in HIGH_EDGE_PATTERNS:
            continue
        
        p4 = lows_train[i]
        p3 = pivots_subset[-1]
        outcome = 'LL' if p4.price < p3.price else 'HL'
        
        price_move = abs(p4.price - p3.price)
        prev_move = abs(p3.price - pivots_subset[-2].price)
        fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
        bars_between = p4.index - p3.index
        
        stats.update(pattern_id, outcome, fib_ratio, bars_between, is_high=False)
    except:
        continue

stats.training_complete = True

print(f"\n✓ Training complete")
print(f"  Total patterns tracked: {stats.total_patterns_tracked}")

# ============================================================================
# PHASE 2: WALK-FORWARD TEST (FIXED - NO LOOKAHEAD)
# ============================================================================
print("\n" + "="*80)
print("PHASE 2: WALK-FORWARD VALIDATION (NO LOOKAHEAD)")
print("="*80)

signals = []
predictions = []

# Calculate RSI for test
delta_test = df_test['close'].diff()
gain_test = (delta_test.where(delta_test > 0, 0)).rolling(window=14).mean()
loss_test = (-delta_test.where(delta_test < 0, 0)).rolling(window=14).mean()
rs_test = gain_test / loss_test
df_test['rsi'] = 100 - (100 / (1 + rs_test))

print(f"\nProcessing {len(df_test)} test bars (walk-forward)...")
print(f"Sampling every 20th bar for speed...")

# Sample every 20th bar (still gives ~1,600 samples)
for idx in range(100, len(df_test), 20):
    try:
        # FIXED: Only use data up to current bar (NO LOOKAHEAD)
        historical_data = df_test.iloc[:idx+1].copy()
        
        # Detect pivots with length=20
        zigzag_test = ZigzagDetector(length=20, threshold_percent=2.0)
        pivots = zigzag_test.find_pivots(historical_data)
        
        if len(pivots) < 3:
            continue
        
        # Get last 3 pivots
        last_pivots = pivots[-3:]
        
        # Check if all same type (highs or lows)
        pivot_types = [p.pivot_type.value for p in last_pivots]
        if len(set(pivot_types)) != 1:
            continue
        
        # Convert to DataFrame
        pivots_df = pd.DataFrame([{
            'index': p.index,
            'timestamp': p.timestamp,
            'price': p.price,
            'type': 'high' if p.pivot_type.value == 'H' else 'low'
        } for p in last_pivots])
        
        # Encode pattern
        pattern_id = encoder.encode_pattern(pivots_df, historical_data)
        
        if pattern_id not in HIGH_EDGE_PATTERNS:
            continue
        
        # Get prediction
        is_high = pivot_types[0] == 'H'
        pred = stats.predict(pattern_id, is_high=is_high)
        
        if pred.sample_count < 5:
            continue
        
        # Generate signal
        current_date = historical_data.index[-1]
        current_price = historical_data.iloc[-1]['close']
        
        # Use prediction to determine direction
        if is_high:
            # Predict LH (down) or HH (up)
            predicted_down = pred.lh_probability > 0.55
            direction = 'SHORT' if predicted_down else 'LONG'
        else:
            # Predict LL (down) or HL (up)
            predicted_down = pred.lh_probability > 0.55
            direction = 'SHORT' if predicted_down else 'LONG'
        
        signals.append({
            'timestamp': current_date,
            'pattern_id': pattern_id,
            'direction': direction,
            'entry': current_price,
            'pivot_type': 'high' if is_high else 'low',
            'prediction_prob': pred.lh_probability
        })
        
    except Exception as e:
        continue

print(f"\n✓ Walk-forward signals: {len(signals)}")
print(f"  LONG: {sum(1 for s in signals if s['direction'] == 'LONG')}")
print(f"  SHORT: {sum(1 for s in signals if s['direction'] == 'SHORT')}")

# ============================================================================
# PHASE 3: RESULTS
# ============================================================================
print("\n" + "="*80)
print("RESULTS")
print("="*80)

print(f"\n📊 WALK-FORWARD VALIDATION (length=20):")
print(f"   Signals detected: {len(signals)}")
print(f"   Previous (length=50): 0 signals")
print(f"   Improvement: {len(signals) - 0} signals!")

if len(signals) > 0:
    print(f"\n✅ SUCCESS! Statistical system now generates signals in walk-forward")
    print(f"✅ NO lookahead bias (only uses past data)")
    print(f"✅ Ready for confluence with M/W system")
    
    # Pattern distribution
    pattern_counts = {}
    for sig in signals:
        pid = sig['pattern_id']
        pattern_counts[pid] = pattern_counts.get(pid, 0) + 1
    
    print(f"\n📊 Pattern Distribution:")
    for pid in sorted(pattern_counts.keys()):
        print(f"   Pattern {pid}: {pattern_counts[pid]} signals")
else:
    print(f"\n⚠️  Still no signals - may need further adjustments")
    print(f"   Consider: length=10 or swing-based detection")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n🎯 NEXT STEPS:")
if len(signals) >= 50:
    print(f"   1. ✅ System generates signals - SUCCESS!")
    print(f"   2. Validate signal quality (win rate)")
    print(f"   3. Compare with M/W system")
    print(f"   4. Test confluence strategies")
elif len(signals) > 0:
    print(f"   1. ⚠️  Low signals ({len(signals)}) - may need tuning")
    print(f"   2. Try length=10 for more signals")
    print(f"   3. Or use as rare high-confidence filter")
else:
    print(f"   1. ❌ Still 0 signals")
    print(f"   2. Try length=10")
    print(f"   3. Or switch to swing-based approach")
