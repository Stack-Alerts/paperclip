#!/usr/bin/env python3
"""
Debug HOD Signal Detection

Checks if HOD block is detecting signals in the data.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from src.detectors.building_blocks.price_levels.hod import HOD
from src.data_manager.data_loader import load_btc_data


def main():
    print("="*80)
    print("HOD SIGNAL DETECTION DEBUG")
    print("="*80)
    
    # Load same data as optimizer
    print("\n📊 Loading BTC data (90 days)...")
    df = load_btc_data(days=90, warmup_bars=5000)
    
    if df is None:
        print("❌ Failed to load data")
        return
    
    print(f"✅ Loaded {len(df)} bars")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Initialize HOD detector
    print("\n🔍 Initializing HOD detector...")
    hod = HOD(timeframe='15min')
    
    # Count signals
    print("\n📈 Analyzing bars for HOD signals...")
    signal_counts = {}
    bars_with_signals = 0
    
    for idx in range(100, len(df)):  # Skip warmup
        bar_df = df.iloc[:idx+1].copy()
        result = hod.analyze(bar_df)
        
        signal = result.get('signal', 'NO_SIGNAL')
        
        if signal != 'NO_SIGNAL':
            bars_with_signals += 1
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
            
            # Print first few detections
            if bars_with_signals <= 10:
                timestamp = df.iloc[idx]['timestamp']
                confidence = result.get('confidence', 0)
                print(f"   Bar {idx}: {signal} ({confidence}% confidence) @ {timestamp}")
    
    # Summary
    print(f"\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Total bars analyzed: {len(df) - 100}")
    print(f"Bars with signals: {bars_with_signals}")
    print(f"\nSignal breakdown:")
    
    if signal_counts:
        for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / (len(df) - 100)) * 100
            print(f"   {signal}: {count} times ({pct:.2f}%)")
    else:
        print("   ❌ NO SIGNALS DETECTED!")
        print("\n🔍 POSSIBLE CAUSES:")
        print("   1. HOD block logic may not be triggering")
        print("   2. Data doesn't have price action matching HOD patterns")
        print("   3. HOD detector needs threshold adjustments")
    
    # Check for specific signals user selected
    print(f"\n" + "="*80)
    print("USER'S SELECTED SIGNALS")
    print("="*80)
    
    user_signals = ['HOD_REJECTION', 'BEARISH']
    for signal in user_signals:
        count = signal_counts.get(signal, 0)
        if count > 0:
            print(f"   ✅ {signal}: {count} detections")
        else:
            print(f"   ❌ {signal}: 0 detections (NEVER APPEARED!)")
    
    # Recommendations
    if bars_with_signals == 0:
        print(f"\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        print("1. Check HOD block implementation")
        print("2. Try different building blocks that fire more frequently")
        print("3. Add context blocks that fire on every bar (EMA trends, VWAP, etc.)")
        print("4. Lower confluence threshold to 20-30 for testing")


if __name__ == '__main__':
    main()
