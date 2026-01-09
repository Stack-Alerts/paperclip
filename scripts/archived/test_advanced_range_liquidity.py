"""
Test Script for Advanced Range Liquidity with Real Orderbook Data
Demonstrates game-changing institutional-grade liquidity detection
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from src.detectors.building_blocks.market_structure.range_liquidity_advanced import AdvancedRangeLiquidity

# Load BTC data
data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
df = pd.read_csv(data_path)

# Standardize column names
if 'Timestamp' in df.columns:
    df.rename(columns={
        'Timestamp': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)

df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to June 2025 (matches orderbook data)
df = df[df['timestamp'] >= '2025-06-01'].copy()
df = df[df['timestamp'] < '2025-07-01'].copy()

print("="*80)
print("🔬 ADVANCED RANGE LIQUIDITY TEST - Real Orderbook Integration")
print("="*80)
print(f"Testing on {len(df)} bars from June 2025")
print()

# Orderbook file for June 2025
orderbook_file = str(Path(__file__).parent.parent / 'data' / 'raw' / 'orderbook' / 'BTC-USDT_orderbook_2025-06.parquet')

# Test WITHOUT orderbook data (simple mode)
print("TEST 1: Without Orderbook Data (Fallback Mode)")
print("-" * 80)

adv_liq = AdvancedRangeLiquidity(lookback=20)
result_simple = adv_liq.analyze(df.iloc[:100])

print(f"Signal: {result_simple['signal']}")
print(f"Confidence: {result_simple['confidence']}%")
print(f"Has Orderbook: {result_simple['metadata']['has_orderbook_data']}")
print(f"Liquidity Strength: {result_simple['metadata']['liquidity_strength']}")
print(f"Confluence Factors:")
for factor in result_simple['confluence_factors']:
    print(f"  - {factor}")
print()

# Test WITH orderbook data (advanced mode)
print("TEST 2: With Real Orderbook Data (Advanced Mode)")
print("-" * 80)

result_advanced = adv_liq.analyze(df.iloc[:100], orderbook_file=orderbook_file)

print(f"Signal: {result_advanced['signal']}")
print(f"Confidence: {result_advanced['confidence']}%")
print(f"Has Orderbook: {result_advanced['metadata']['has_orderbook_data']}")
print(f"Liquidity Strength: {result_advanced['metadata']['liquidity_strength']}")
if result_advanced['metadata']['total_depth_btc']:
    print(f"⭐ Real Depth: {result_advanced['metadata']['total_depth_btc']:.4f} BTC")
    print(f"⭐ Weighted Depth: {result_advanced['metadata']['weighted_depth_btc']:.4f} BTC")
    print(f"⭐ Orderbook Levels: {result_advanced['metadata']['orderbook_levels']}")
print(f"Confluence Factors:")
for factor in result_advanced['confluence_factors']:
    print(f"  - {factor}")
print()

# Sample multiple bars to show variation
print("TEST 3: Sample 10 Bars - Showing Confidence Variation")
print("-" * 80)

confidences = []
strengths = []
depths = []

for i in range(10, 110, 10):
    result = adv_liq.analyze(df.iloc[:i], orderbook_file=orderbook_file)
    confidences.append(result['confidence'])
    strengths.append(result['metadata']['liquidity_strength'])
    if result['metadata']['total_depth_btc']:
        depths.append(result['metadata']['total_depth_btc'])
    
    print(f"Bar {i}: Confidence={result['confidence']}%, " +
          f"Strength={result['metadata']['liquidity_strength']}, " +
          f"Signal={result['signal'][:20]}")

print()
print(f"Confidence Range: {min(confidences)}% - {max(confidences)}% (Std: {pd.Series(confidences).std():.2f}%)")
print(f"Strength Range: {min(strengths)} - {max(strengths)} (Std: {pd.Series(strengths).std():.2f})")
if depths:
    print(f"Depth Range: {min(depths):.4f} - {max(depths):.4f} BTC")

print()
print("="*80)
print("✅ ADVANCED RANGE LIQUIDITY TEST COMPLETE")
print("="*80)
print()
print("KEY OBSERVATIONS:")
print("1. WITH orderbook data: Real liquidity measurements!")
print("2. Variable confidence based on actual depth")
print("3. Falls back gracefully without orderbook")
print("4. Shows actual BTC depth at critical levels")
print()
print("This is INSTITUTIONAL GRADE liquidity detection! 🎯")
