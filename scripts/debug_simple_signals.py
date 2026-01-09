"""
Simple debug - check if building blocks are finding ANY signals
Uses ONLY local data/raw/ pickle file (no downloads)
"""
import sys
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

import pandas as pd
from datetime import datetime, timedelta

# Import building blocks directly
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence
from src.detectors.building_blocks.price_levels.hod import HOD
from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50Percent
from src.detectors.building_blocks.sessions.session_time import SessionTime
from src.detectors.building_blocks.institutional.vwap import VWAP

# Load data DIRECTLY from pickle (no data manager)
print("📂 Loading data from local pickle file...")
df = pd.read_pickle('/home/sirrus/projects/BTC_Engine_v3/data/raw/BTC_USDT_PERP_15m.pkl')

# Reset index to get timestamp as column
df = df.reset_index()
print(f"✅ Loaded {len(df):,} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")

# Get last 180 days for testing (same as optimizer)
end_date = df['timestamp'].max()
start_date = end_date - timedelta(days=180)
df_test = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)

print(f"📊 Test period: {len(df_test):,} bars from {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")

if len(df_test) < 100:
    print("❌ NOT ENOUGH TEST DATA!")
    sys.exit(1)

# Initialize building blocks
print("\n⚙️  Initializing building blocks...")
detectors = {
    'double_top': DoubleTopPattern(timeframe='15min'),
    'rsi_divergence': RSIDivergence(timeframe='15min'),
    'hod': HOD(timeframe='15min'),
    'asia_50': AsiaSession50Percent(timeframe='15min'),
    'session_time': SessionTime(timeframe='15min'),
    'vwap': VWAP(timeframe='15min'),
}

print(f"✅ Initialized {len(detectors)} building blocks")

# Sample every 500 bars to check signals
print("\n🔍 Scanning for signals (sampling every 500 bars)...")
signal_counts = {name: {} for name in detectors.keys()}
sample_count = 0

for i in range(1000, len(df_test), 500):
    sample_count += 1
    history = df_test.iloc[:i+1]
    
    for block_name, detector in detectors.items():
        try:
            result = detector.analyze(history)
            signal = result.get('signal', 'NO_SIGNAL')
            
            if signal not in signal_counts[block_name]:
                signal_counts[block_name][signal] = 0
            signal_counts[block_name][signal] += 1
            
            # Print interesting signals
            if signal not in ['NO_SIGNAL', 'NO_PATTERN', 'ERROR', 'NEUTRAL'] and signal_counts[block_name][signal] == 1:
                conf = result.get('confidence', 0)
                print(f"   ✓ {block_name}: {signal} @ {conf}% (bar {i}, {history.iloc[-1]['timestamp']})")
            
        except Exception as e:
            print(f"   ❌ Error in {block_name}: {e}")

print(f"\n{'='*80}")
print("📊 SIGNAL SUMMARY")
print(f"{'='*80}")
print(f"Samples taken: {sample_count}")

for block_name, signals in signal_counts.items():
    print(f"\n{block_name}:")
    for signal, count in sorted(signals.items(), key=lambda x: x[1], reverse=True):
        pct = (count / sample_count * 100) if sample_count > 0 else 0
        print(f"  {signal}: {count} ({pct:.1f}%)")

# Check for meaningful signals
print(f"\n{'='*80}")
print("📈 ANALYSIS")
print(f"{'='*80}")

meaningful_signals = 0
meaningful_blocks = []

for block_name, signals in signal_counts.items():
    block_meaningful = 0
    for signal, count in signals.items():
        if signal not in ['NO_SIGNAL', 'NO_PATTERN', 'ERROR', 'NEUTRAL']:
            meaningful_signals += count
            block_meaningful += count
    
    if block_meaningful > 0:
        meaningful_blocks.append(f"{block_name} ({block_meaningful} signals)")
        print(f"✓ {block_name}: {block_meaningful} meaningful signals")

if meaningful_signals == 0:
    print("\n❌ NO MEANINGFUL SIGNALS FOUND!")
    print("   Building blocks are not detecting any patterns/conditions.")
    print("   This explains why confluence is always 0 and no trades occur.")
else:
    print(f"\n✓ Found {meaningful_signals} meaningful signals across {len(meaningful_blocks)} blocks")
    print(f"  Active blocks: {', '.join(meaningful_blocks)}")
    print("\n💡 Signals ARE being detected!")
    print("   The 0 trades issue must be:")
    print("   - Confluence threshold too high")
    print("   - R:R requirements impossible")
    print("   - Or entry logic filtering everything out")