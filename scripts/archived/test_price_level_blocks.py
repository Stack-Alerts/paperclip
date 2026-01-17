"""
Test Price Level Building Blocks - Registry Integration Test
=============================================================

Tests the updated/new price level blocks and verifies registry integration:

UPDATED BLOCKS:
- HOD: Now tracks YESTERDAY's high (not today's)
- LOD: Now tracks YESTERDAY's low (not today's)

NEW BLOCKS:
- IHOD: Today's high (intraday)
- ILOD: Today's low (intraday)
- 50%H-LOD: Yesterday's 50% equilibrium
- 50%Intra-H-LOD: Today's 50% equilibrium (dynamic)

This script verifies:
1. All blocks work correctly
2. Registry auto-discovered them
3. ConfluenceCalculator knows about them (NO manual updates needed!)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append('.')

print("="*80)
print("PRICE LEVEL BLOCKS - REGISTRY INTEGRATION TEST")
print("="*80)
print()

# ============================================================================
# TEST 1: Verify Registry Auto-Discovery
# ============================================================================
print("TEST 1: Registry Auto-Discovery")
print("-" * 80)

# Import price_levels module to trigger @register_block decorators
import src.detectors.building_blocks.price_levels

from src.detectors.building_blocks.registry import BlockRegistry

# Get all price level blocks
all_blocks = BlockRegistry.get_all_blocks()
price_level_blocks = {
    name: meta for name, meta in all_blocks.items() 
    if meta.category == 'PRICE_LEVELS'
}

print(f"Total Price Level Blocks in Registry: {len(price_level_blocks)}")
print()

# Check for our specific blocks
target_blocks = ['hod', 'lod', 'ihod', 'ilod', 'fifty_pct_hod_lod', 'fifty_pct_intra_hod_lod']

for block_name in target_blocks:
    if block_name in price_level_blocks:
        meta = price_level_blocks[block_name]
        print(f"✅ {block_name.upper()}: Registered")
        print(f"   Class: {meta.class_name}")
        print(f"   Weight: {meta.default_weight}")
        print(f"   Signals: {', '.join(meta.valid_signals[:3])}...")
    else:
        print(f"❌ {block_name.upper()}: NOT FOUND")
print()

# ============================================================================
# TEST 2: Create Test Data (2 days)
# ============================================================================
print("TEST 2: Creating Test Data (2 days)")
print("-" * 80)

# Day 1: Yesterday (full day - 96 bars @ 15min)
day1_start = datetime(2024, 1, 1, 0, 0)
day1_dates = pd.date_range(start=day1_start, periods=96, freq='15min')

np.random.seed(42)
day1_highs = 45000 + np.random.uniform(-200, 500, 96)
day1_lows = day1_highs - np.random.uniform(100, 300, 96)
day1_closes = day1_lows + (day1_highs - day1_lows) * np.random.uniform(0.3, 0.7, 96)

# Day 2: Today (partial day - 50 bars @ 15min, ~12.5 hours)
day2_start = datetime(2024, 1, 2, 0, 0)
day2_dates = pd.date_range(start=day2_start, periods=50, freq='15min')

day2_highs = 45500 + np.cumsum(np.random.uniform(-50, 100, 50))
day2_lows = day2_highs - np.random.uniform(100, 250, 50)
day2_closes = day2_lows + (day2_highs - day2_lows) * np.random.uniform(0.3, 0.7, 50)

# Combine into full dataset
all_dates = pd.concat([pd.Series(day1_dates), pd.Series(day2_dates)])
all_highs = np.concatenate([day1_highs, day2_highs])
all_lows = np.concatenate([day1_lows, day2_lows])
all_closes = np.concatenate([day1_closes, day2_closes])

df = pd.DataFrame({
    'timestamp': all_dates,
    'high': all_highs,
    'low': all_lows,
    'close': all_closes,
    'open': all_closes,
    'volume': np.random.uniform(100, 1000, len(all_dates))
})

# Calculate reference levels
day1_hod = df[df['timestamp'].dt.date == day1_start.date()]['high'].max()
day1_lod = df[df['timestamp'].dt.date == day1_start.date()]['low'].min()
day1_fifty = (day1_hod + day1_lod) / 2

day2_ihod = df[df['timestamp'].dt.date == day2_start.date()]['high'].max()
day2_ilod = df[df['timestamp'].dt.date == day2_start.date()]['low'].min()
day2_fifty = (day2_ihod + day2_ilod) / 2

print(f"Day 1 (Yesterday - {day1_start.date()}):")
print(f"  HOD: ${day1_hod:.2f}")
print(f"  LOD: ${day1_lod:.2f}")
print(f"  50%: ${day1_fifty:.2f}")
print()
print(f"Day 2 (Today - {day2_start.date()}):")
print(f"  IHOD (so far): ${day2_ihod:.2f}")
print(f"  ILOD (so far): ${day2_ilod:.2f}")
print(f"  50% (so far): ${day2_fifty:.2f}")
print()

# ============================================================================
# TEST 3: Test Each Block Individually
# ============================================================================
print("TEST 3: Testing Each Block")
print("-" * 80)

# Test HOD (should return YESTERDAY's high)
print("3a. HOD (Yesterday's High)")
print("-" * 40)
hod_block = BlockRegistry.instantiate('hod', timeframe='15min')
hod_result = hod_block.analyze(df)
print(f"Signal: {hod_result['signal']}")
print(f"Confidence: {hod_result['confidence']}%")
print(f"HOD Value: ${hod_result['metadata']['hod']:.2f}")
print(f"Expected (Day 1 HOD): ${day1_hod:.2f}")
print(f"✅ CORRECT" if abs(hod_result['metadata']['hod'] - day1_hod) < 1.0 else f"❌ WRONG")
print()

# Test LOD (should return YESTERDAY's low)
print("3b. LOD (Yesterday's Low)")
print("-" * 40)
lod_block = BlockRegistry.instantiate('lod', timeframe='15min')
lod_result = lod_block.analyze(df)
print(f"Signal: {lod_result['signal']}")
print(f"Confidence: {lod_result['confidence']}%")
print(f"LOD Value: ${lod_result['metadata']['lod']:.2f}")
print(f"Expected (Day 1 LOD): ${day1_lod:.2f}")
print(f"✅ CORRECT" if abs(lod_result['metadata']['lod'] - day1_lod) < 1.0 else f"❌ WRONG")
print()

# Test IHOD (should return TODAY's high)
print("3c. IHOD (Today's High)")
print("-" * 40)
ihod_block = BlockRegistry.instantiate('ihod', timeframe='15min')
ihod_result = ihod_block.analyze(df)
print(f"Signal: {ihod_result['signal']}")
print(f"Confidence: {ihod_result['confidence']}%")
print(f"IHOD Value: ${ihod_result['metadata']['ihod']:.2f}")
print(f"Expected (Day 2 IHOD): ${day2_ihod:.2f}")
print(f"✅ CORRECT" if abs(ihod_result['metadata']['ihod'] - day2_ihod) < 1.0 else f"❌ WRONG")
print()

# Test ILOD (should return TODAY's low)
print("3d. ILOD (Today's Low)")
print("-" * 40)
ilod_block = BlockRegistry.instantiate('ilod', timeframe='15min')
ilod_result = ilod_block.analyze(df)
print(f"Signal: {ilod_result['signal']}")
print(f"Confidence: {ilod_result['confidence']}%")
print(f"ILOD Value: ${ilod_result['metadata']['ilod']:.2f}")
print(f"Expected (Day 2 ILOD): ${day2_ilod:.2f}")
print(f"✅ CORRECT" if abs(ilod_result['metadata']['ilod'] - day2_ilod) < 1.0 else f"❌ WRONG")
print()

# Test 50%H-LOD (should return YESTERDAY's 50%)
print("3e. 50%H-LOD (Yesterday's 50%)")
print("-" * 40)
fifty_pct_block = BlockRegistry.instantiate('fifty_pct_hod_lod', timeframe='15min')
fifty_result = fifty_pct_block.analyze(df)
print(f"Signal: {fifty_result['signal']}")
print(f"Confidence: {fifty_result['confidence']}%")
print(f"50% Value: ${fifty_result['metadata']['fifty_pct']:.2f}")
print(f"Expected (Day 1 50%): ${day1_fifty:.2f}")
print(f"✅ CORRECT" if abs(fifty_result['metadata']['fifty_pct'] - day1_fifty) < 1.0 else f"❌ WRONG")
print()

# Test 50%Intra-H-LOD (should return TODAY's 50%)
print("3f. 50%Intra-H-LOD (Today's 50%)")
print("-" * 40)
fifty_intra_block = BlockRegistry.instantiate('fifty_pct_intra_hod_lod', timeframe='15min')  
fifty_intra_result = fifty_intra_block.analyze(df)
print(f"Signal: {fifty_intra_result['signal']}")
print(f"Confidence: {fifty_intra_result['confidence']}%")
print(f"Intra 50% Value: ${fifty_intra_result['metadata']['intra_fifty_pct']:.2f}")
print(f"Expected (Day 2 50%): ${day2_fifty:.2f}")
print(f"✅ CORRECT" if abs(fifty_intra_result['metadata']['intra_fifty_pct'] - day2_fifty) < 1.0 else f"❌ WRONG")
print()

# ============================================================================
# TEST 4: Verify ConfluenceCalculator Integration (NO MANUAL UPDATES!)
# ============================================================================
print("TEST 4: ConfluenceCalculator Integration (Auto-Discovery)")
print("-" * 80)

from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator

# Test that ConfluenceCalculator knows about all blocks
test_results = {
    'hod': hod_result,
    'lod': lod_result,
    'ihod': ihod_result,
    'ilod': ilod_result,
    'fifty_pct_hod_lod': fifty_result,
    'fifty_pct_intra_hod_lod': fifty_intra_result
}

test_blocks = {
    'hod': {'name': 'HOD', 'weight': 20, 'enabled': True},
    'lod': {'name': 'LOD', 'weight': 20, 'enabled': True},
    'ihod': {'name': 'IHOD', 'weight': 20, 'enabled': True},
    'ilod': {'name': 'ILOD', 'weight': 20, 'enabled': True},
    'fifty_pct_hod_lod': {'name': 'FiftyPctHODLOD', 'weight': 18, 'enabled': True},
    'fifty_pct_intra_hod_lod': {'name': 'FiftyPctIntraHODLOD', 'weight': 18, 'enabled': True}
}

print("Testing ConfluenceCalculator.calculate_confluence()...")
print()

try:
    confluence, signals = ConfluenceCalculator.calculate_confluence(test_results, test_blocks)
    print(f"✅ ConfluenceCalculator Integration: WORKING")
    print(f"   Total Confluence: {confluence} points")
    print(f"   Signals Processed: {len(signals)}")
    print()
    print("Signal Breakdown:")
    for sig in signals:
        print(f"   • {sig}")
except Exception as e:
    print(f"❌ ConfluenceCalculator Integration: FAILED")
    print(f"   Error: {e}")
print()

# ============================================================================
# TEST 5: Summary
# ============================================================================
print("="*80)
print("SUMMARY: Registry Integration Test Results")
print("="*80)
print()

results = []
results.append(("Registry Auto-Discovery", all(name in price_level_blocks for name in target_blocks)))
results.append(("HOD (Yesterday's High)", abs(hod_result['metadata']['hod'] - day1_hod) < 1.0))
results.append(("LOD (Yesterday's Low)", abs(lod_result['metadata']['lod'] - day1_lod) < 1.0))
results.append(("IHOD (Today's High)", abs(ihod_result['metadata']['ihod'] - day2_ihod) < 1.0))
results.append(("ILOD (Today's Low)", abs(ilod_result['metadata']['ilod'] - day2_ilod) < 1.0))
results.append(("50%H-LOD (Yesterday's 50%)", abs(fifty_result['metadata']['fifty_pct'] - day1_fifty) < 1.0))
results.append(("50%Intra-H-LOD (Today's 50%)", abs(fifty_intra_result['metadata']['intra_fifty_pct'] - day2_fifty) < 1.0))

try:
    ConfluenceCalculator.calculate_confluence(test_results, test_blocks)
    results.append(("ConfluenceCalculator Integration", True))
except:
    results.append(("ConfluenceCalculator Integration", False))

all_passed = all(result[1] for result in results)

for test_name, passed in results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")

print()
print("="*80)
if all_passed:
    print("🎉 ALL TESTS PASSED - REGISTRY INTEGRATION WORKING PERFECTLY!")
    print()
    print("KEY ACHIEVEMENTS:")
    print("✅ All 6 blocks auto-registered (NO manual registration)")
    print("✅ HOD/LOD now track YESTERDAY's levels correctly")
    print("✅ IHOD/ILOD track TODAY's levels correctly")
    print("✅ 50% blocks calculate correctly (both yesterday and today)")
    print("✅ ConfluenceCalculator knows about ALL blocks (NO manual updates!)")
    print("✅ Registry handled updates AND new blocks seamlessly")
else:
    print("❌ SOME TESTS FAILED - SEE DETAILS ABOVE")
print("="*80)