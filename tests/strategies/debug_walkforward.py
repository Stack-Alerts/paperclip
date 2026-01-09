"""
Debug Walk-Forward Test - Shows Confluence Scores

This will help us understand why no trades are being generated.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    print(f"Loading {days} days of BTC data...")
    
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
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
        
        print(f"✅ Loaded {len(df)} bars")
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    else:
        print("❌ No data found")
        return None


def test_confluence_scoring():
    """Debug test to see what confluence scores we're getting"""
    from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
    
    print("\n" + "="*80)
    print("DEBUG: CONFLUENCE SCORE ANALYSIS")
    print("="*80)
    
    df = load_btc_data(days=180)
    if df is None:
        return
    
    # Create strategy
    class MockStrategy:
        def __init__(self):
            self.strategy_id = "01_M_PATTERN_REVERSAL"
            self.strategy_name = "M Pattern Reversal - Standard"
            self.min_confluence = 70
            self.max_bars_held = 1000
            self.lookback_period = 100
            self.min_risk_reward = 3.0
            self.peak_tolerance = 0.002
            self.bars_data = []
            
            self.blocks = {
                'double_top': {'name': 'DoubleTopPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'hod': {'name': 'HOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
    
    strategy = MockStrategy()
    
    # Bind methods
    strategy._analyze_blocks = MPatternReversalStandard._analyze_blocks.__get__(strategy)
    strategy._calculate_confluence = MPatternReversalStandard._calculate_confluence.__get__(strategy)
    strategy._calculate_tp_sl = MPatternReversalStandard._calculate_tp_sl.__get__(strategy)
    strategy._detect_double_top = MPatternReversalStandard._detect_double_top.__get__(strategy)
    strategy._detect_rsi_divergence = MPatternReversalStandard._detect_rsi_divergence.__get__(strategy)
    strategy._check_hod_rejection = MPatternReversalStandard._check_hod_rejection.__get__(strategy)
    strategy._check_asia_50_position = MPatternReversalStandard._check_asia_50_position.__get__(strategy)
    strategy._check_session_timing = MPatternReversalStandard._check_session_timing.__get__(strategy)
    strategy._check_vwap_position = MPatternReversalStandard._check_vwap_position.__get__(strategy)
    
    print(f"\n🔍 Analyzing confluence scores...")
    print(f"   Min threshold: {strategy.min_confluence}")
    
    # Track scores
    all_scores = []
    top_scores = []
    
    # Sample every 100th bar for speed
    for i in range(strategy.lookback_period, len(df), 100):
        # Build bars incrementally
        strategy.bars_data = []
        for j in range(max(0, i-strategy.max_bars_held), i+1):
            row = df.iloc[j]
            strategy.bars_data.append({
                'timestamp': row['timestamp'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            })
        
        try:
            analysis_df = pd.DataFrame(strategy.bars_data)
            results = strategy._analyze_blocks(analysis_df)
            confluence, signal_list = strategy._calculate_confluence(results)
            
            all_scores.append(confluence)
            
            # Track top 20 scores
            if len(top_scores) < 20:
                top_scores.append((confluence, i, df.iloc[i]['timestamp'], signal_list))
                top_scores.sort(key=lambda x: x[0], reverse=True)
            elif confluence > top_scores[-1][0]:
                top_scores[-1] = (confluence, i, df.iloc[i]['timestamp'], signal_list)
                top_scores.sort(key=lambda x: x[0], reverse=True)
                
        except Exception as e:
            continue
    
    # Statistics
    print(f"\n📊 CONFLUENCE STATISTICS:")
    print(f"   Bars analyzed: {len(all_scores)}")
    print(f"   Average score: {np.mean(all_scores):.1f}")
    print(f"   Max score: {max(all_scores):.1f}")
    print(f"   Min score: {min(all_scores):.1f}")
    print(f"   Std dev: {np.std(all_scores):.1f}")
    
    # Show distribution
    print(f"\n📈 SCORE DISTRIBUTION:")
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    hist, _ = np.histogram(all_scores, bins=bins)
    for i in range(len(bins)-1):
        count = hist[i]
        pct = count / len(all_scores) * 100
        bar = '█' * int(pct / 2)
        print(f"   {bins[i]:3d}-{bins[i+1]:3d}: {count:4d} ({pct:5.1f}%) {bar}")
    
    # Show top scores
    print(f"\n🏆 TOP 20 CONFLUENCE SCORES:")
    for i, (score, bar_idx, timestamp, signals) in enumerate(top_scores, 1):
        print(f"\n   #{i}: {score:.0f} points at bar {bar_idx} ({timestamp})")
        for sig in signals:
            print(f"      • {sig}")
    
    # Check if any met threshold
    above_threshold = [s for s in all_scores if s >= strategy.min_confluence]
    print(f"\n✅ Scores >= {strategy.min_confluence}: {len(above_threshold)}")
    
    if len(above_threshold) == 0:
        print(f"\n⚠️  PROBLEM IDENTIFIED:")
        print(f"   No bars reached min confluence of {strategy.min_confluence}")
        print(f"   Highest score was {max(all_scores):.0f}")
        print(f"   Recommendation: Lower threshold to {int(max(all_scores) * 0.8)}")
        

if __name__ == "__main__":
    test_confluence_scoring()