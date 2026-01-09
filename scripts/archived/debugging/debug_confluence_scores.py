"""
Debug script to see actual confluence scores being generated
"""
import sys
sys.path.insert(0, '/home/sirrus/projects/BTC_Engine_v3')

import pandas as pd
from datetime import datetime, timedelta
from src.data_manager.unified_manager import UnifiedDataManager
from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator

# Load data
print("Loading data...")
manager = UnifiedDataManager()
end_date = datetime(2025, 12, 16)
start_date = end_date - timedelta(days=180)

df = manager.get_bars(
    timeframe='15m',
    start_date=start_date,
    end_date=end_date
)

print(f"Loaded {len(df)} bars from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")

# Create strategy instance
class DebugConfig:
    strategy_id = "01_M_PATTERN_REVERSAL"
    strategy_name = "M Pattern Reversal - Standard"
    min_confluence = 40
    min_risk_reward = 2.0
    side = 'SHORT'
    blocks = {
        'double_top': {'weight': 35, 'enabled': True},
        'rsi_divergence': {'weight': 30, 'enabled': True},
        'hod': {'weight': 15, 'enabled': True},
        'asia_50': {'weight': 12, 'enabled': True},
        'session_time': {'weight': 10, 'enabled': True},
        'vwap': {'weight': 10, 'enabled': True},
    }

config = DebugConfig()
strategy = MPatternReversalStandard(config)

# Initialize building blocks
strategy._initialize_blocks()

print(f"\nInitialized {len(strategy.detectors)} building blocks")
print("Building blocks:", list(strategy.detectors.keys()))

# Sample every 100 bars to check confluence
confluence_scores = []
signals_found = {name: 0 for name in strategy.detectors.keys()}

print("\nScanning bars for signals and confluence...")
sample_interval = 100
bar_count = 0

for i in range(1000, len(df), sample_interval):
    history = df.iloc[:i+1]
    
    # Run building blocks
    results = strategy._analyze_blocks(history)
    
    # Calculate confluence
    confluence, signals = ConfluenceCalculator.calculate_confluence(results, config.blocks)
    
    if confluence > 0:
        confluence_scores.append(confluence)
        bar_count += 1
        
        # Track which blocks fired
        for block_name, result in results.items():
            signal = result.get('signal', '')
            if signal and signal not in ['NO_SIGNAL', 'NO_PATTERN', 'ERROR', 'NEUTRAL']:
                signals_found[block_name] += 1
        
        # Print high confluence setups
        if confluence >= 40:
            print(f"\n🎯 Bar {i} ({history.iloc[-1]['timestamp']}): Confluence = {confluence}")
            for sig in signals:
                print(f"   {sig}")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"Total bars sampled: {len(range(1000, len(df), sample_interval))}")
print(f"Bars with any signals: {bar_count}")
print(f"Bars with confluence >= 40: {sum(1 for c in confluence_scores if c >= 40)}")
print(f"Bars with confluence >= 50: {sum(1 for c in confluence_scores if c >= 50)}")
print(f"Bars with confluence >= 60: {sum(1 for c in confluence_scores if c >= 60)}")
print(f"Bars with confluence >= 70: {sum(1 for c in confluence_scores if c >= 70)}")

if confluence_scores:
    print(f"\nConfluence Statistics:")
    print(f"  Max: {max(confluence_scores)}")
    print(f"  Mean: {sum(confluence_scores)/len(confluence_scores):.1f}")
    print(f"  Min (non-zero): {min(confluence_scores)}")
else:
    print("\n❌ NO CONFLUENCE SCORES > 0 FOUND!")

print(f"\nSignal Counts by Block:")
for block_name, count in sorted(signals_found.items(), key=lambda x: x[1], reverse=True):
    if count > 0:
        print(f"  {block_name}: {count} signals")