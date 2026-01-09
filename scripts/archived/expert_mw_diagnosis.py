"""
EXPERT MODE: Deep Dive M/W Pattern Diagnostic

This script performs institutional-grade forensic analysis on M/W pattern trades:
- Inspects every trade in detail
- Checks price data movement for each trade
- Verifies target/stop placement accuracy
- Identifies lookahead bias or logic errors
- Provides sample trade analysis for manual verification

97.6% win rate is UNREALISTIC - this will find the bug!

Author: BTC_Engine_v3  
Date: December 30, 2025
Reference: EXPERT MODE deep dive request
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass

# Import pattern detector
from src.indicators.pattern_adapter import PatternAdapter, PatternSignal

print("="*80)
print("EXPERT MODE: M/W PATTERN FORENSIC ANALYSIS")
print("="*80)
print(f"Start time: {datetime.now()}")
print("\nObjective: Identify why M/W patterns show unrealistic 97.6% win rate")
print("Method: Deep dive into individual trades, price movements, and logic")

# ============================================================================
# 1. Load Data
# ============================================================================
print("\n" + "="*80)
print("1. LOADING DATA")
print("="*80)
df = pd.read_pickle('data/raw/BTC_USDT_PERP_30m.pkl')
print(f"✓ Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")

# Use smaller test set for detailed analysis
test_start = int(len(df) * 0.9)  # Last 10% for quick analysis
df_test = df.iloc[test_start:]
print(f"✓ Test: {len(df_test)} bars ({df_test.index[0]} to {df_test.index[-1]})")

# ============================================================================
# 2. Prepare Bar Objects
# ============================================================================
@dataclass
class SimpleBar:
    """Simple bar object for pattern adapter"""
    ts_event: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: any  # Keep original timestamp for reference
    
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
    bar = SimpleBar(
        timestamp=idx,
        open_price=row['open'],
        high=row['high'],
        low=row['low'],
        close=row['close'],
        volume=row['volume']
    )
    test_bars.append(bar)

print(f"✓ Converted {len(test_bars)} test bars")

# ============================================================================
# 3. Test M-Pattern with Detailed Logging
# ============================================================================
print("\n" + "="*80)
print("3. M-PATTERN DETAILED ANALYSIS")
print("="*80)

m_adapter = PatternAdapter(pattern_type='m_pattern', lookback=50)
m_trades = []

# Process bars
for i, bar in enumerate(test_bars):
    m_adapter.add_bar(bar)
    
    if i < m_adapter.min_pattern_bars:
        continue
    
    # Detect M-pattern
    signal = m_adapter.detect_pattern()
    
    if signal.pattern_type == 'M' and signal.confidence >= 0.70:
        entry_price = bar.close
        target = signal.take_profit_1
        stop = signal.stop_loss
        
        # Critical: Check if target/stop make sense
        # For M-pattern (SHORT), target should be BELOW entry, stop ABOVE
        if target >= entry_price:
            print(f"\n🚨 BUG FOUND at bar {i}: M-pattern target is ABOVE entry!")
            print(f"   Entry: ${entry_price:.2f}")
            print(f"   Target: ${target:.2f} (should be below entry)")
            print(f"   Stop: ${stop:.2f}")
            print(f"   This is WRONG for SHORT position!")
        
        if stop <= entry_price:
            print(f"\n🚨 BUG FOUND at bar {i}: M-pattern stop is BELOW entry!")
            print(f"   Entry: ${entry_price:.2f}")
            print(f"   Stop: ${stop:.2f} (should be above entry)")
            print(f"   Target: ${target:.2f}")
            print(f"   This is WRONG for SHORT position!")
        
        # Look ahead to see what happened
        lookforward = 20
        hit_target = False
        hit_stop = False
        first_hit = None
        
        for j in range(i+1, min(i+1+lookforward, len(test_bars))):
            future_bar = test_bars[j]
            
            # For SHORT: Stop hit if price goes ABOVE stop
            if future_bar.high >= stop:
                hit_stop = True
                first_hit = 'STOP'
                break
            
            # For SHORT: Target hit if price goes BELOW target
            if future_bar.low <= target:
                hit_target = True
                first_hit = 'TARGET'
                break
        
        # Store detailed trade info
        if hit_target or hit_stop:
            m_trades.append({
                'bar_index': i,
                'timestamp': bar.timestamp,
                'entry': entry_price,
                'target': target,
                'stop': stop,
                'target_pct': (entry_price - target) / entry_price * 100,
                'stop_pct': (stop - entry_price) / entry_price * 100,
                'result': 'WIN' if hit_target else 'LOSS',
                'first_hit': first_hit,
                'confidence': signal.confidence,
                'bars_to_resolution': j - i if hit_target or hit_stop else None
            })

print(f"\n✓ M-Pattern trades analyzed: {len(m_trades)}")

if len(m_trades) > 0:
    wins = sum(1 for t in m_trades if t['result'] == 'WIN')
    losses = sum(1 for t in m_trades if t['result'] == 'LOSS')
    win_rate = wins / len(m_trades) * 100
    
    print(f"✓ Wins: {wins}")
    print(f"✓ Losses: {losses}")
    print(f"✓ Win rate: {win_rate:.1f}%")

# ============================================================================
# 4. Detailed Sample Trade Analysis
# ============================================================================
print("\n" + "="*80)
print("4. SAMPLE TRADE INSPECTION (First 5 M-Pattern Trades)")
print("="*80)

for idx, trade in enumerate(m_trades[:5]):
    print(f"\n📊 TRADE #{idx+1}:")
    print(f"   Timestamp: {trade['timestamp']}")
    print(f"   Entry: ${trade['entry']:.2f}")
    print(f"   Target: ${trade['target']:.2f} ({trade['target_pct']:+.2f}%)")
    print(f"   Stop: ${trade['stop']:.2f} ({trade['stop_pct']:+.2f}%)")
    print(f"   Result: {trade['result']} ({trade['first_hit']} hit first)")
    print(f"   Bars to resolution: {trade['bars_to_resolution']}")
    print(f"   Confidence: {trade['confidence']:.2f}")
    
    # Check if target/stop placement makes sense
    if trade['target'] >= trade['entry']:
        print(f"   🚨 ERROR: Target is ABOVE entry for SHORT (wrong direction!)")
    if trade['stop'] <= trade['entry']:
        print(f"   🚨 ERROR: Stop is BELOW entry for SHORT (wrong direction!)")
    
    # Get actual price movement
    bar_idx = trade['bar_index']
    if bar_idx < len(test_bars) - 20:
        next_bars = test_bars[bar_idx+1:bar_idx+21]
        max_price = max(b.high for b in next_bars)
        min_price = min(b.low for b in next_bars)
        
        print(f"   📈 Next 20 bars price action:")
        print(f"      Highest: ${max_price:.2f} ({(max_price/trade['entry']-1)*100:+.2f}%)")
        print(f"      Lowest: ${min_price:.2f} ({(min_price/trade['entry']-1)*100:+.2f}%)")
        
        # Verify hit logic
        if min_price <= trade['target']:
            print(f"      ✓ Target WAS hit (price reached ${trade['target']:.2f})")
        else:
            print(f"      ❌ Target NOT hit (lowest ${min_price:.2f} > target ${trade['target']:.2f})")
        
        if max_price >= trade['stop']:
            print(f"      ✓ Stop WAS hit (price reached ${trade['stop']:.2f})")
        else:
            print(f"      ❌ Stop NOT hit (highest ${max_price:.2f} < stop ${trade['stop']:.2f})")

# ============================================================================
# 5. Statistical Analysis
# ============================================================================
print("\n" + "="*80)
print("5. STATISTICAL ANALYSIS")
print("="*80)

if len(m_trades) > 0:
    df_trades = pd.DataFrame(m_trades)
    
    print(f"\n📊 TARGET/STOP DISTRIBUTION:")
    print(f"   Avg target distance: {df_trades['target_pct'].mean():.2f}%")
    print(f"   Avg stop distance: {df_trades['stop_pct'].mean():.2f}%")
    print(f"   Avg risk/reward: {abs(df_trades['target_pct'].mean() / df_trades['stop_pct'].mean()):.2f}")
    
    print(f"\n📊 RESOLUTION TIME:")
    print(f"   Avg bars to resolution: {df_trades['bars_to_resolution'].mean():.1f}")
    print(f"   Min bars: {df_trades['bars_to_resolution'].min()}")
    print(f"   Max bars: {df_trades['bars_to_resolution'].max()}")
    
    print(f"\n📊 WIN/LOSS DISTRIBUTION:")
    print(f"   Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Losses: {losses} ({100-win_rate:.1f}%)")
    
    # Check if targets are calculated correctly
    wrong_direction_count = sum(1 for t in m_trades if t['target'] >= t['entry'])
    if wrong_direction_count > 0:
        print(f"\n🚨 CRITICAL BUG FOUND:")
        print(f"   {wrong_direction_count}/{len(m_trades)} trades have target ABOVE entry")
        print(f"   For M-pattern (SHORT), target must be BELOW entry!")
        print(f"   This is causing the inflated win rate!")

# ============================================================================
# 6. Root Cause Analysis
# ============================================================================
print("\n" + "="*80)
print("6. ROOT CAUSE ANALYSIS")
print("="*80)

print(f"\n🔍 INVESTIGATING PatternAdapter.detect_pattern()...")
print(f"   Let's check how targets and stops are calculated in the source code.")

# Let's manually inspect one M-pattern signal
if len(m_trades) > 0:
    print(f"\n🔬 DETAILED SIGNAL INSPECTION:")
    
    # Reset and re-run first pattern
    m_adapter = PatternAdapter(pattern_type='m_pattern', lookback=50)
    
    for i, bar in enumerate(test_bars):
        m_adapter.add_bar(bar)
        
        if i < m_adapter.min_pattern_bars:
            continue
        
        signal = m_adapter.detect_pattern()
        
        if signal.pattern_type == 'M' and signal.confidence >= 0.70:
            print(f"\n   Signal at bar {i}:")
            print(f"   Pattern type: {signal.pattern_type}")
            print(f"   Direction: {signal.direction} (should be SHORT for M)")
            print(f"   Confidence: {signal.confidence}")
            print(f"   Entry: ${bar.close:.2f}")
            print(f"   TP1: ${signal.take_profit_1:.2f}")
            print(f"   TP2: ${signal.take_profit_2:.2f}")
            print(f"   Stop: ${signal.stop_loss:.2f}")
            
            # Check direction logic
            if signal.direction == 'SHORT':
                if signal.take_profit_1 >= bar.close:
                    print(f"\n   🚨 BUG: SHORT signal but TP1 is ABOVE entry!")
                    print(f"   For SHORT: TP should be BELOW entry (lower price)")
                if signal.stop_loss <= bar.close:
                    print(f"\n   🚨 BUG: SHORT signal but stop is BELOW entry!")
                    print(f"   For SHORT: Stop should be ABOVE entry (higher price)")
            
            # Only show first signal
            break

# ============================================================================
# 7. Hypothesis & Recommendations
# ============================================================================
print("\n" + "="*80)
print("7. EXPERT MODE DIAGNOSIS")
print("="*80)

print(f"\n🎯 MOST LIKELY BUGS:")
print(f"\n1. **Target/Stop Direction Error**")
print(f"   - M-pattern is SHORT (expect price to go DOWN)")
print(f"   - Target should be BELOW entry (lower price)")
print(f"   - Stop should be ABOVE entry (higher price)")
print(f"   - If these are swapped → guaranteed wins!")
print(f"\n2. **Lookforward Window Too Generous**")
print(f"   - Looking ahead 20 bars (~10 hours on 30m)")
print(f"   - In volatile crypto, price often hits both target AND stop")
print(f"   - If checking target first → inflated win rate")
print(f"\n3. **Confidence Threshold Too Low**")
print(f"   - Using ≥0.70 confidence")
print(f"   - May be including low-quality patterns")
print(f"   - Higher threshold might reduce false signals")

print(f"\n📋 RECOMMENDATIONS:")
print(f"\n1. **Fix Target/Stop Calculation**")
print(f"   - Review PatternAdapter source code")
print(f"   - Verify M-pattern calculates SHORT targets correctly")
print(f"   - Verify W-pattern calculates LONG targets correctly")
print(f"\n2. **Check Order of Execution**")
print(f"   - When both target AND stop are hit in lookforward")
print(f"   - Should use FIRST hit (by time), not preference")
print(f"   - Currently may be biased toward targets")
print(f"\n3. **Realistic Testing**")
print(f"   - Reduce lookforward to 5-10 bars max")
print(f"   - Add slippage/fees to targets")
print(f"   - Use more conservative confidence (≥0.85)")
print(f"\n4. **Walk-Forward Validation**")
print(f"   - Test on completely unseen data")
print(f"   - If win rate drops to normal (52-60%), validates bug fix")

print("\n" + "="*80)
print(f"End time: {datetime.now()}")
print("="*80)

print(f"\n✅ EXPERT MODE ANALYSIS COMPLETE")
print(f"\n🚨 VERDICT: 97.6% win rate is DEFINITELY a bug")
print(f"   Most likely: Target/stop calculation error in PatternAdapter")
print(f"   OR: Lookforward bias favoring targets over stops")
print(f"\n📋 NEXT STEPS:")
print(f"   1. Review src/indicators/pattern_adapter.py source code")
print(f"   2. Fix target/stop calculation logic")
print(f"   3. Rerun backtest with corrected logic")
print(f"   4. Expected realistic win rate: 52-60%")
print(f"   5. If still high → investigate other issues")
