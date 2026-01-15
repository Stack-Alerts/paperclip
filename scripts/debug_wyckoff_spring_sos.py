"""
Debug Wyckoff Spring/SOS Detection
====================================

Research why SPRING and SOS signals never emit in 180 days
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detectors.building_blocks.wyckoff.wyckoff_accumulation import WyckoffAccumulation
import pandas as pd
from datetime import datetime, timedelta

# Load data from parquet (same as test scripts)
data_path = Path(__file__).parent.parent / 'data' / 'market_data' / 'binance_btcusdt_15m.parquet'
df_all = pd.read_parquet(data_path)

# Get last 180 days
end_date = df_all['timestamp'].max()
start_date = end_date - timedelta(days=180)
df = df_all[df_all['timestamp'] >= start_date].copy()

print("="*80)
print("WYCKOFF SPRING/SOS DEBUG")
print("="*80)
print(f"Loaded {len(df)} 15min bars")

# Resample to 2HR (what Wyckoff does internally)
df_indexed = df.set_index('timestamp')
df_2hr = df_indexed.resample('2H').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna().reset_index()

print(f"Resampled to {len(df_2hr)} 2HR bars")
print()

# Initialize Wyckoff
wyckoff = WyckoffAccumulation(timeframe='2hr')

# Track phases and events
spring_count = 0
sos_count = 0
phase_b_count = 0
phase_a_count = 0

# Scan all bars
for i in range(wyckoff.range_lookback, len(df_2hr)):
    window = df_2hr.iloc[:i+1]
    result = wyckoff.analyze(window)
    
    signal = result['signal']
    
    if signal == 'SPRING_DETECTED':
        spring_count += 1
        print(f"🌱 SPRING #{spring_count} at bar {i} ({window['timestamp'].iloc[-1]})")
        print(f"   Support: {result['metadata']['support_level']:.2f}")
        print(f"   Confidence: {result['confidence']}%")
        print()
    
    elif signal == 'SOS_BREAKOUT':
        sos_count += 1
        print(f"📈 SOS #{sos_count} at bar {i} ({window['timestamp'].iloc[-1]})")
        print(f"   Resistance: {result['metadata']['resistance_level']:.2f}")
        print(f"   Confidence: {result['confidence']}%")
        print()
    
    elif signal == 'ACCUMULATION_PHASE_B':
        phase_b_count += 1
    
    elif signal == 'ACCUMULATION_PHASE_A':
        phase_a_count += 1

print("="*80)
print("FINAL COUNTS")
print("="*80)
print(f"SPRING_DETECTED: {spring_count}")
print(f"SOS_BREAKOUT: {sos_count}")
print(f"ACCUMULATION_PHASE_B: {phase_b_count}")
print(f"ACCUMULATION_PHASE_A: {phase_a_count}")
print()

if spring_count == 0 and sos_count == 0:
    print("⚠️  PROBLEM: No Spring or SOS detected in 180 days!")
    print("   This indicates detection logic is too strict or broken")
else:
    print("✅ Spring and SOS signals are working!")
