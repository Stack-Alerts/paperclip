"""
Debug script to see what REAL building blocks are detecting
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from pathlib import Path
from datetime import timedelta

# Import REAL building blocks
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence
from src.detectors.building_blocks.price_levels.hod import HOD
from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50Percent
from src.detectors.building_blocks.sessions.session_time import SessionTime
from src.detectors.building_blocks.institutional.vwap import VWAP


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    if data_path.exists():
        df = pd.read_csv(data_path)
        
        if 'Timestamp' in df.columns:
            df.rename(columns={
                'Timestamp': 'timestamp', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            }, inplace=True)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        cutoff_date = df['timestamp'].max() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff_date].copy()
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    return None


def main():
    print("="*80)
    print("DEBUGGING REAL BUILDING BLOCKS")
    print("="*80)
    
    # Load data
    print("\n📊 Loading BTC data...")
    df = load_btc_data(days=180)
    print(f"✅ Loaded {len(df)} bars")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Initialize REAL blocks
    print("\n🔧 Initializing REAL building blocks...")
    double_top = DoubleTopPattern(timeframe='15min')
    rsi_div = RSIDivergence(timeframe='15min')
    hod = HOD(timeframe='15min')
    asia_50 = AsiaSession50Percent(timeframe='15min')
    session = SessionTime(timeframe='15min')
    vwap_block = VWAP(timeframe='15min')
    
    print("✅ All blocks initialized")
    
    # Test on full dataset
    print("\n🔍 Running analysis on full dataset...")
    
    print("\n1. Double Top Pattern:")
    dt_result = double_top.analyze(df)
    print(f"   Signal: {dt_result.get('signal', 'NONE')}")
    print(f"   Confidence: {dt_result.get('confidence', 0)}%")
    if dt_result.get('metadata'):
        print(f"   Metadata: {dt_result['metadata']}")
    
    print("\n2. RSI Divergence:")
    rsi_result = rsi_div.analyze(df)
    print(f"   Signal: {rsi_result.get('signal', 'NONE')}")
    print(f"   Confidence: {rsi_result.get('confidence', 0)}%")
    
    print("\n3. HOD:")
    hod_result = hod.analyze(df)
    print(f"   Signal: {hod_result.get('signal', 'NONE')}")
    print(f"   Confidence: {hod_result.get('confidence', 0)}%")
    
    print("\n4. Asia 50%:")
    asia_result = asia_50.analyze(df)
    print(f"   Signal: {asia_result.get('signal', 'NONE')}")
    print(f"   Confidence: {asia_result.get('confidence', 0)}%")
    
    print("\n5. Session Time:")
    session_result = session.analyze(df)
    print(f"   Signal: {session_result.get('signal', 'NONE')}")
    print(f"   Confidence: {session_result.get('confidence', 0)}%")
    
    print("\n6. VWAP:")
    vwap_result = vwap_block.analyze(df)
    print(f"   Signal: {vwap_result.get('signal', 'NONE')}")
    print(f"   Confidence: {vwap_result.get('confidence', 0)}%")
    
    # Test on sliding windows to find ANY signals
    print("\n\n🔍 Searching for signals in sliding windows...")
    
    double_top_signals = []
    window_size = 200
    
    for i in range(window_size, len(df), 10):  # Every 10 bars
        window_df = df.iloc[:i].copy()
        result = double_top.analyze(window_df)
        
        if result.get('signal') != 'NO_PATTERN':
            double_top_signals.append({
                'bar': i,
                'timestamp': window_df['timestamp'].iloc[-1],
                'signal': result.get('signal'),
                'confidence': result.get('confidence'),
                'metadata': result.get('metadata', {})
            })
    
    print(f"\n📊 Double Top Signals Found: {len(double_top_signals)}")
    
    if double_top_signals:
        print("\nSample signals (first 5):")
        for sig in double_top_signals[:5]:
            print(f"\n   Bar {sig['bar']} - {sig['timestamp']}")
            print(f"   Signal: {sig['signal']}, Confidence: {sig['confidence']}%")
            if sig['metadata']:
                print(f"   Peaks: {sig['metadata'].get('peaks', 'N/A')}")
    else:
        print("\n⚠️  NO DOUBLE TOP SIGNALS FOUND IN ENTIRE DATASET!")
        print("\nThis means the building block is TOO STRICT for this data.")
        print("Possible reasons:")
        print("1. Requires 5 confluences (very strict)")
        print("2. Peak tolerance too tight (2%)")
        print("3. Volume requirements not met")
        print("4. No actual M-patterns in this specific data period")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()