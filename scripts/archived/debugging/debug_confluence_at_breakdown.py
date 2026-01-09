"""
Check confluence score at the exact moment double_top BEARISH_BREAKDOWN fires
"""
import sys
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

import pandas as pd
from datetime import timedelta
from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator

# Import building blocks
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence
from src.detectors.building_blocks.price_levels.hod import HOD
from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50Percent
from src.detectors.building_blocks.sessions.session_time import SessionTime
from src.detectors.building_blocks.institutional.vwap import VWAP

# Load data
print("📂 Loading data...")
df = pd.read_pickle('/home/sirrus/projects/BTC_Engine_v3/data/raw/BTC_USDT_PERP_15m.pkl')
df = df.reset_index()

# Get last 180 days
end_date = df['timestamp'].max()
start_date = end_date - timedelta(days=180)
df_test = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)

print(f"✅ Loaded {len(df_test):,} test bars")

# Initialize blocks
detectors = {
    'double_top': DoubleTopPattern(timeframe='15min'),
    'rsi_divergence': RSIDivergence(timeframe='15min'),
    'hod': HOD(timeframe='15min'),
    'asia_50': AsiaSession50Percent(timeframe='15min'),
    'session_time': SessionTime(timeframe='15min'),
    'vwap': VWAP(timeframe='15min'),
}

# Strategy config (from optimizer)
block_configs = {
    'double_top': {'weight': 35, 'enabled': True},
    'rsi_divergence': {'weight': 30, 'enabled': True},
    'hod': {'weight': 15, 'enabled': True},
    'asia_50': {'weight': 12, 'enabled': True},
    'session_time': {'weight': 10, 'enabled': True},
    'vwap': {'weight': 10, 'enabled': True},
}

print("\n🔍 Scanning for BEARISH_BREAKDOWN moments...")
breakdown_count = 0

for i in range(1000, len(df_test)):
    history = df_test.iloc[:i+1]
    
    # Check double_top first
    dt_result = detectors['double_top'].analyze(history)
    
    if dt_result.get('signal') == 'BEARISH_BREAKDOWN':
        breakdown_count += 1
        
        # Run all blocks at this moment
        block_results = {}
        for block_name, detector in detectors.items():
            block_results[block_name] = detector.analyze(history)
        
        # Calculate confluence
        confluence, signals = ConfluenceCalculator.calculate_confluence(block_results, block_configs)
        
        bar_time = history.iloc[-1]['timestamp']
        bar_price = history.iloc[-1]['close']
        
        print(f"\n{'='*80}")
        print(f"🎯 BEARISH_BREAKDOWN #{breakdown_count} at bar {i}")
        print(f"{'='*80}")
        print(f"Time: {bar_time}")
        print(f"Price: ${bar_price:,.2f}")
        print(f"Confluence: {confluence} points")
        print(f"\nSignals at this moment:")
        for sig in signals:
            print(f"  {sig}")
        
        if confluence >= 70:
            print(f"\n✅ WOULD TRADE (confluence {confluence} >= 70)")
        elif confluence >= 60:
            print(f"\n⚠️  CLOSE (confluence {confluence}, needs 60+)")
        elif confluence >= 50:
            print(f"\n⚠️  MODERATE (confluence {confluence}, needs 50+)")
        elif confluence >= 40:
            print(f"\n⚠️  LOW (confluence {confluence}, needs 40+)")
        else:
            print(f"\n❌ NO TRADE (confluence {confluence} < 40)")

if breakdown_count == 0:
    print("\n❌ NO BEARISH_BREAKDOWN SIGNALS FOUND!")
    print("   Double top never reached breakdown state in 180 days.")
else:
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY: Found {breakdown_count} BEARISH_BREAKDOWN signals")
    print(f"{'='*80}")