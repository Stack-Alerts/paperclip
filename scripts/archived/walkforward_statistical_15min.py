"""
Walk-Forward Validation: Statistical System on 15min Timeframe

Tests the 13 high-edge statistical patterns on 15min data:
- Data: BTC_USDT_PERP_15m.pkl
- Period: 2025-04-01 → Present
- NO lookahead bias
- Uses same 13 patterns: [0, 5, 7, 16, 18, 21, 24, 26, 32, 40, 42, 45, 47]

Author: BTC_Engine_v3
Date: December 30, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("WALK-FORWARD VALIDATION: STATISTICAL SYSTEM (15MIN)")
print("="*80)
print(f"Start time: {datetime.now()}\n")
print("Objective: Validate 13-pattern statistical system on 15min")
print("Method: Walk-forward (NO lookahead bias)")
print("="*80)

# Load 15min data
try:
    df = pd.read_pickle('data/raw/BTC_USDT_PERP_15m.pkl')
    print(f"\n✓ Loaded 15min data: {len(df)} bars")
    print(f"  From: {df.index[0]}")
    print(f"  To: {df.index[-1]}")
except FileNotFoundError:
    print(f"\n❌ ERROR: BTC_USDT_PERP_15m.pkl not found")
    sys.exit(1)

# Walk-forward period: 2025-04-01 onwards
walkforward_start = pd.Timestamp('2025-04-01')
df_walkforward = df[df.index >= walkforward_start].copy()

print(f"\n✓ Walk-forward period:")
print(f"  Bars: {len(df_walkforward)}")
print(f"  From: {df_walkforward.index[0]}")
print(f"  To: {df_walkforward.index[-1]}")
print(f"  Duration: {(df_walkforward.index[-1] - df_walkforward.index[0]).days} days")

# High-edge patterns (from statistical analysis)
high_edge_patterns = [0, 5, 7, 16, 18, 21, 24, 26, 32, 40, 42, 45, 47]

print(f"\n✓ Using {len(high_edge_patterns)} high-edge patterns")
print(f"  Pattern IDs: {high_edge_patterns}")

# ============================================================================
# STATISTICAL PATTERN DETECTION (Walk-Forward)
# ============================================================================
print("\n" + "="*80)
print("STATISTICAL PATTERN WALK-FORWARD TEST")
print("="*80)

# Import pattern detection components
from src.detectors.zigzag_detector import ZigzagDetector
from src.detectors.pattern_encoder import PatternEncoder

zigzag = ZigzagDetector(length=50, threshold_percent=2.0)
encoder = PatternEncoder()

stat_trades = []

print(f"\nProcessing {len(df_walkforward)} bars (walk-forward)...")

# Process each bar (walk-forward - only use past data)
for idx in range(len(df_walkforward)):
    current_date = df_walkforward.index[idx]
    
    # Only use data up to current bar (NO LOOKAHEAD)
    historical_data = df_walkforward.iloc[:idx+1].copy()
    
    if len(historical_data) < 100:  # Need minimum history
        continue
    
    # Detect pivots on historical data only
    try:
        pivots_df = zigzag.detect_pivots(historical_data)
    except:
        continue
    
    if len(pivots_df) < 3:  # Need at least 3 pivots
        continue
    
    # Calculate RSI
    delta = historical_data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    historical_data['rsi'] = 100 - (100 / (1 + rs))
    
    # Encode pattern
    try:
        pattern_id = encoder.encode_pattern(pivots_df, historical_data)
    except:
        continue
    
    # Check if it's a high-edge pattern
    if pattern_id in high_edge_patterns:
        # Get last pivot
        last_pivot = pivots_df.iloc[-1]
        current_price = historical_data.iloc[-1]['close']
        
        # Determine trade direction from pivot type
        if last_pivot['type'] == 'low':
            direction = 'LONG'
            target = current_price * 1.015  # 1.5% profit target
            stop = current_price * 0.985    # 1.5% stop loss
        else:
            direction = 'SHORT'
            target = current_price * 0.985
            stop = current_price * 1.015
        
        stat_trades.append({
            'timestamp': current_date,
            'pattern_id': pattern_id,
            'direction': direction,
            'entry': current_price,
            'target': target,
            'stop': stop,
            'last_pivot_type': last_pivot['type']
        })

print(f"\n✓ Statistical signals detected: {len(stat_trades)}")
print(f"  LONG signals: {sum(1 for t in stat_trades if t['direction'] == 'LONG')}")
print(f"  SHORT signals: {sum(1 for t in stat_trades if t['direction'] == 'SHORT')}")

# Pattern distribution
pattern_counts = {}
for trade in stat_trades:
    pid = trade['pattern_id']
    pattern_counts[pid] = pattern_counts.get(pid, 0) + 1

print(f"\n✓ Pattern distribution:")
for pid in sorted(pattern_counts.keys()):
    print(f"  Pattern {pid}: {pattern_counts[pid]} signals")

# Check outcomes (NO LOOKAHEAD)
stat_wins = 0
stat_losses = 0
stat_no_result = 0

for i, trade in enumerate(stat_trades):
    trade_idx = df_walkforward.index.get_loc(trade['timestamp'])
    
    # Look ahead max 20 bars (5 hours on 15min = same as 10 bars on 30min)
    lookforward = 20
    hit_target = False
    hit_stop = False
    
    for j in range(1, min(lookforward + 1, len(df_walkforward) - trade_idx)):
        future_idx = trade_idx + j
        future_bar = df_walkforward.iloc[future_idx]
        
        if trade['direction'] == 'SHORT':
            if future_bar['high'] >= trade['stop']:
                hit_stop = True
                break
            if future_bar['low'] <= trade['target']:
                hit_target = True
                break
        else:  # LONG
            if future_bar['low'] <= trade['stop']:
                hit_stop = True
                break
            if future_bar['high'] >= trade['target']:
                hit_target = True
                break
    
    if hit_target:
        stat_wins += 1
        stat_trades[i]['result'] = 'WIN'
    elif hit_stop:
        stat_losses += 1
        stat_trades[i]['result'] = 'LOSS'
    else:
        stat_no_result += 1
        stat_trades[i]['result'] = 'NO_RESULT'

stat_completed = stat_wins + stat_losses
stat_win_rate = (stat_wins / stat_completed * 100) if stat_completed > 0 else 0

print(f"\n✓ Results:")
print(f"  Completed trades: {stat_completed}")
print(f"  Wins: {stat_wins}")
print(f"  Losses: {stat_losses}")
print(f"  No result (still open): {stat_no_result}")
print(f"  Win Rate: {stat_win_rate:.1f}%")

# ============================================================================
# COMPARISON
# ============================================================================
print("\n" + "="*80)
print("STATISTICAL SYSTEM COMPARISON")
print("="*80)

# Previous results
stat_30min_backtest = 57.3
stat_30min_trades = 168

print(f"\n📊 STATISTICAL SYSTEM ACROSS TESTS:")

print(f"\n   30-Minute Backtest (Original):")
print(f"   ├── Period: Out-of-sample test set")
print(f"   ├── Trades: {stat_30min_trades}")
print(f"   ├── Win Rate: {stat_30min_backtest:.1f}%")
print(f"   └── Status: ✅ VALIDATED")

print(f"\n   15-Minute Walk-Forward (This Test):")
print(f"   ├── Period: 2025-04-01 → 2025-12-16")
print(f"   ├── Trades: {stat_completed}")
print(f"   ├── Win Rate: {stat_win_rate:.1f}%")
print(f"   ├── Difference: {stat_win_rate - stat_30min_backtest:+.1f}%")
print(f"   └── Status: {'✅ VALIDATED' if stat_win_rate >= 52 else '⚠️  MARGINAL' if stat_win_rate >= 50 else '❌ FAILED'}")

print(f"\n💡 ANALYSIS:")
if stat_win_rate >= 55:
    print(f"   ✅ EXCELLENT performance on 15min walk-forward")
    print(f"   ✅ System works on faster timeframe")
    print(f"   ✅ Ready for deployment on 15min")
elif stat_win_rate >= 52:
    print(f"   ✅ GOOD performance on 15min walk-forward")
    print(f"   ✅ Consistent with 30min backtest")
    print(f"   ✅ Can deploy on 15min or 30min")
elif stat_win_rate >= 50:
    print(f"   ⚠️  MARGINAL performance")
    print(f"   ⚠️  Prefer 30min timeframe")
    print(f"   ⚠️  Need more validation")
else:
    print(f"   ❌ POOR performance on 15min")
    print(f"   ❌ Stick with 30min only")

# ============================================================================
# FINAL COMBINED RESULTS
# ============================================================================
print("\n" + "="*80)
print("COMPLETE SYSTEM VALIDATION SUMMARY")
print("="*80)

mw_30min_wf = 68.6
mw_15min_wf = 67.7

print(f"\n📊 ALL SYSTEMS - ALL TIMEFRAMES:")

print(f"\n   M/W Pattern System:")
print(f"   ├── 30min walk-forward: {mw_30min_wf:.1f}% ✅")
print(f"   ├── 15min walk-forward: {mw_15min_wf:.1f}% ✅")
print(f"   ├── Variance: {abs(mw_30min_wf - mw_15min_wf):.1f}%")
print(f"   └── Status: TIMEFRAME-ROBUST ✅")

print(f"\n   Statistical System:")
print(f"   ├── 30min backtest: {stat_30min_backtest:.1f}% ✅")
print(f"   ├── 15min walk-forward: {stat_win_rate:.1f}% {' ✅' if stat_win_rate >= 52 else '⚠️'}")
print(f"   ├── Difference: {abs(stat_30min_backtest - stat_win_rate):.1f}%")
print(f"   └── Status: {'VALIDATED ✅' if stat_win_rate >= 52 else 'MARGINAL ⚠️' if stat_win_rate >= 50 else 'FAILED ❌'}")

print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)

print(f"\n🎯 COMPLETE VALIDATION STATUS:")

if mw_30min_wf >= 65 and mw_15min_wf >= 65:
    print(f"   ✅ M/W System: VALIDATED across timeframes")
    print(f"   ✅ Ready for deployment on 15min OR 30min")

if stat_win_rate >= 52:
    print(f"   ✅ Statistical System: VALIDATED on 15min")
    print(f"   ✅ Can deploy on multiple timeframes")
elif stat_win_rate >= 50:
    print(f"   ⚠️  Statistical System: MARGINAL on 15min")
    print(f"   ⚠️  Prefer 30min for statistical trades")

print(f"\n💡 FINAL DEPLOYMENT RECOMMENDATION:")
print(f"   M/W System: Deploy on 15min OR 30min (both validated)")
print(f"   Statistical System: {'Deploy on 15min or 30min' if stat_win_rate >= 52 else 'Deploy on 30min only'}")
print(f"   Confluence: Combine both systems for higher quality trades")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n✅ Statistical 15min walk-forward validation complete!")
print(f"🎯 Both systems now tested across multiple timeframes")
print(f"📊 Ready for deployment decision")
