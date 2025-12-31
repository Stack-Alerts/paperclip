"""
EXPERT MODE: Lookforward Window Sensitivity Analysis

Tests M/W pattern performance with different lookforward windows:
- 5 bars (2.5 hours)
- 10 bars (5 hours)
- 20 bars (10 hours) - current
- 40 bars (20 hours)

Goal: Determine if 20-bar window is inflating win rate

Author: BTC_Engine_v3
Date: December 30, 2025
Reference: EXPERT MODE Bug #2 investigation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass

# Import pattern detector
from src.indicators.pattern_adapter import PatternAdapter

print("="*80)
print("EXPERT MODE: LOOKFORWARD WINDOW SENSITIVITY ANALYSIS")
print("="*80)
print(f"Start time: {datetime.now()}")

# Load data
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
train_size = int(len(df) * 0.7)
df_test = df.iloc[train_size:]

print(f"\n✓ Test: {len(df_test)} bars ({df_test.index[0]} to {df_test.index[-1]})")

# Create bar objects
@dataclass
class SimpleBar:
    ts_event: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: any
    
    def __init__(self, timestamp, open_price, high, low, close, volume):
        self.timestamp = timestamp
        self.ts_event = int(timestamp.timestamp() * 1e9)
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

test_bars = []
for idx, row in df_test.iterrows():
    bar = SimpleBar(idx, row['open'], row['high'], row['low'], row['close'], row['volume'])
    test_bars.append(bar)

print(f"✓ Converted {len(test_bars)} test bars\n")

# Test different lookforward windows
lookforward_tests = [5, 10, 15, 20, 30, 40]

print("="*80)
print("TESTING M-PATTERN WITH DIFFERENT LOOKFORWARD WINDOWS")
print("="*80)

results = []

for lookforward in lookforward_tests:
    print(f"\n{'─'*80}")
    print(f"LOOKFORWARD: {lookforward} bars ({lookforward * 0.5:.1f} hours)")
    print(f"{'─'*80}")
    
    m_adapter = PatternAdapter(pattern_type='m_pattern', lookback=50)
    
    trades = 0
    wins = 0
    losses = 0
    
    for i, bar in enumerate(test_bars):
        m_adapter.add_bar(bar)
        
        if i < m_adapter.min_pattern_bars:
            continue
        
        signal = m_adapter.detect_pattern()
        
        if signal.pattern_type == 'M' and signal.confidence >= 0.70:
            entry_price = bar.close
            target = signal.take_profit_1
            stop = signal.stop_loss
            
            # Look ahead with current window
            hit_target = False
            hit_stop = False
            
            for j in range(i+1, min(i+1+lookforward, len(test_bars))):
                future_bar = test_bars[j]
                
                # For SHORT: Stop hit if price goes ABOVE stop
                if future_bar.high >= stop:
                    hit_stop = True
                    break
                
                # For SHORT: Target hit if price goes BELOW target
                if future_bar.low <= target:
                    hit_target = True
                    break
            
            if hit_target or hit_stop:
                trades += 1
                if hit_target:
                    wins += 1
                else:
                    losses += 1
    
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    print(f"Trades: {trades}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    
    results.append({
        'lookforward': lookforward,
        'hours': lookforward * 0.5,
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate
    })

# Summary
print("\n" + "="*80)
print("SUMMARY: LOOKFORWARD WINDOW SENSITIVITY")
print("="*80)

df_results = pd.DataFrame(results)
print(f"\n{df_results.to_string(index=False)}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

print(f"\n📊 WIN RATE BY LOOKFORWARD:")
for _, row in df_results.iterrows():
    print(f"   {int(row['lookforward']):2d} bars ({row['hours']:4.1f}h): {row['win_rate']:5.1f}%")

# Calculate degradation
baseline_wr = df_results[df_results['lookforward'] == 5]['win_rate'].values[0]
current_wr = df_results[df_results['lookforward'] == 20]['win_rate'].values[0]
degradation = current_wr - baseline_wr

print(f"\n🔍 SENSITIVITY ANALYSIS:")
print(f"   Baseline (5 bars):  {baseline_wr:.1f}%")
print(f"   Current (20 bars):  {current_wr:.1f}%")
print(f"   Inflation:          {degradation:+.1f}%")

if abs(degradation) > 5:
    print(f"\n🚨 WARNING: Lookforward window significantly affects win rate!")
    print(f"   20-bar window may be TOO GENEROUS")
    print(f"   Recommended: Use 5-10 bars for realistic results")
elif abs(degradation) > 2:
    print(f"\n⚠️  CAUTION: Moderate impact from lookforward window")
    print(f"   Consider using shorter window (5-10 bars)")
else:
    print(f"\n✅ GOOD: Lookforward window has minimal impact")
    print(f"   Current 20-bar window is acceptable")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n💡 RECOMMENDATION:")
if abs(degradation) > 5:
    print(f"   Change lookforward from 20 → 5-10 bars")
    print(f"   Expected realistic win rate: ~{baseline_wr:.1f}%")
elif abs(degradation) > 2:
    print(f"   Consider reducing lookforward to 10 bars")
    print(f"   Current 20 bars is acceptable but generous")
else:
    print(f"   Keep current 20-bar lookforward")
    print(f"   No significant inflation detected")
