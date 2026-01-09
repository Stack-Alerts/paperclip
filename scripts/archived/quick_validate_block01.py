"""Quick validation of Block #1 after fix"""
import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from detectors.building_blocks.moving_averages.ema_50_vector import EMA50Vector

# Load real data
df = pd.read_csv('data/raw/BTC_USDT_PERP_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Test last 1000 bars
test_df = df.tail(1000).copy()

ema50 = EMA50Vector(timeframe='15min')
signals = []
lookback = 100

for i in range(lookback, len(test_df)):
    window = test_df.iloc[i-lookback:i+1].copy()
    result = ema50.analyze(window)
    
    if result['signal'] in ['BULLISH', 'BEARISH']:
        signals.append({
            'timestamp': result['timestamp'],
            'signal': result['signal'],
            'confidence': result['confidence'],
            'vector_break': result['metadata']['vector_break']
        })

print("="*60)
print("BLOCK #1 (50 EMA VECTOR) - POST-FIX VALIDATION")
print("="*60)
print(f"Data period: Last 1000 bars")
print(f"Total signals: {len(signals)} (was 636 before fix)")
print(f"\nSignal breakdown:")
if signals:
    df_signals = pd.DataFrame(signals)
    print(df_signals['signal'].value_counts())
    print(f"\nAverage confidence: {df_signals['confidence'].mean():.2f}%")
    print(f"\nFirst 5 signals:")
    print(df_signals.head())
    
    # Calculate improvement
    before = 636
    after = len(signals)
    reduction = ((before - after) / before) * 100
    print(f"\n📊 IMPROVEMENT:")
    print(f"  Before fix: {before} signals")
    print(f"  After fix: {after} signals") 
    print(f"  Reduction: {reduction:.1f}%")
    
    if after < 100:
        print(f"\n✅ STATUS: INSTITUTIONAL GRADE (quality over quantity)")
    elif after < 200:
        print(f"\n⚠️  STATUS: GOOD (consider minor tuning)")
    else:
        print(f"\n⚠️  STATUS: NEEDS MORE TUNING (still too many signals)")
else:
    print("\n⚠️  WARNING: No signals generated")
print("="*60)
