"""
Quick test to verify new detectors work
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Test SwingPoints
from src.detectors.building_blocks.market_structure.swing_points import SwingPoints
from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend
from src.detectors.building_blocks.market_structure.premium_discount_zones import PremiumDiscountZones

# Create sample data
dates = pd.date_range(start='2025-01-01', periods=200, freq='15min')
np.random.seed(42)
prices = 50000 + np.cumsum(np.random.randn(200) * 50)

df = pd.DataFrame({
    'timestamp': dates,
    'open': prices,
    'high': prices + np.random.rand(200) * 50,
    'low': prices - np.random.rand(200) * 50,
    'close': prices + np.random.randn(200) * 25,
    'volume': np.random.rand(200) * 1000
})

print("="*80)
print("TESTING NEW DETECTORS")
print("="*80)

# Test SwingPoints
print("\n1. Testing SwingPoints...")
try:
    sp = SwingPoints(timeframe='15min')
    result = sp.analyze(df)
    print(f"   ✅ SwingPoints works!")
    print(f"   Signal: {result.get('signal', 'NONE')}")
    print(f"   Confidence: {result.get('confidence', 0)}")
except Exception as e:
    print(f"   ❌ SwingPoints FAILED: {e}")

# Test EMA200Trend  
print("\n2. Testing EMA200Trend...")
try:
    ema = EMA200Trend(timeframe='15min')
    result = ema.analyze(df)
    print(f"   ✅ EMA200Trend works!")
    print(f"   Signal: {result.get('signal', 'NONE')}")
    print(f"   Confidence: {result.get('confidence', 0)}")
except Exception as e:
    print(f"   ❌ EMA200Trend FAILED: {e}")

# Test PremiumDiscountZones
print("\n3. Testing PremiumDiscountZones...")
try:
    pdz = PremiumDiscountZones(timeframe='15min')
    result = pdz.analyze(df)
    print(f"   ✅ PremiumDiscountZones works!")
    print(f"   Signal: {result.get('signal', 'NONE')}")
    print(f"   Confidence: {result.get('confidence', 0)}")
except Exception as e:
    print(f"   ❌ PremiumDiscountZones FAILED: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)