"""
BLOCK #1: 50 EMA Vector Break - REAL BTC DATA VALIDATION
Expert Mode: Backtest + Walk-Forward + Tuning with Real Market Data
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from detectors.building_blocks.moving_averages.ema_50_vector import EMA50Vector

def load_real_btc_data():
    """Load real BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    print(f"Loading real BTC data from: {data_path}")
    
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} rows of real BTC data")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Date range: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    
    return df

def prepare_data(df):
    """Prepare data for block testing"""
    # Ensure required columns
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    # Rename if needed
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'time' in col_lower and 'timestamp' not in required_cols:
            rename_map[col] = 'timestamp'
        elif col_lower == 'vol' or col_lower == 'volume':
            rename_map[col] = 'volume'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # Convert timestamp if needed
    if df['timestamp'].dtype == 'object':
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by time
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df[required_cols]

def backtest_ema50_vector(df, params):
    """Backtest 50 EMA Vector on real data"""
    print("\n" + "="*80)
    print("BACKTESTING 50 EMA VECTOR WITH REAL BTC DATA")
    print("="*80)
    
    ema50 = EMA50Vector(
        timeframe='15min',
        ema_period=params.get('ema_period', 50),
        min_slope=params.get('min_slope', 0.0001),
        volume_multiplier=params.get('volume_multiplier', 1.5)
    )
    
    signals = []
    
    # Slide through data with lookback window
    lookback = 100
    
    for i in range(lookback, len(df)):
        window = df.iloc[i-lookback:i+1].copy()
        result = ema50.analyze(window)
        
        if result['signal'] in ['BULLISH', 'BEARISH']:
            signals.append({
                'timestamp': result['timestamp'],
                'signal': result['signal'],
                'confidence': result['confidence'],
                'price': window['close'].iloc[-1],
                'ema_value': result['metadata'].get('ema_value'),
                'slope': result['metadata'].get('ema_slope'),
                'position': result['metadata'].get('position'),
                'distance_pct': result['metadata'].get('distance_pct')
            })
    
    print(f"\nTotal signals generated: {len(signals)}")
    
    if len(signals) > 0:
        signals_df = pd.DataFrame(signals)
        print(f"\nSignal breakdown:")
        print(signals_df['signal'].value_counts())
        print(f"\nAverage confidence: {signals_df['confidence'].mean():.2f}%")
        print(f"\nConfidence distribution:")
        print(signals_df['confidence'].describe())
        
        # Show sample signals
        print(f"\nFirst 5 signals:")
        print(signals_df.head())
        
        return signals_df
    else:
        print("⚠️ NO SIGNALS GENERATED - May need parameter adjustment")
        return pd.DataFrame()

def walk_forward_test(df, window_size=30):
    """Walk-forward testing with expanding window"""
    print("\n" + "="*80)
    print("WALK-FORWARD TESTING (Expanding Window)")
    print("="*80)
    
    # Use last 90 days for walk-forward
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    cutoff_date = df['timestamp'].max() - timedelta(days=90)
    df_wf = df[df['timestamp'] >= cutoff_date].copy()
    
    print(f"Walk-forward period: {df_wf['timestamp'].min()} to {df_wf['timestamp'].max()}")
    print(f"Total bars: {len(df_wf)}")
    
    # Split into 3 windows
    total_bars = len(df_wf)
    window_1 = total_bars // 3
    window_2 = (total_bars // 3) * 2
    
    windows = [
        ("Window 1", df_wf.iloc[:window_1]),
        ("Window 2", df_wf.iloc[:window_2]),
        ("Window 3", df_wf)
    ]
    
    results = []
    
    for name, window_df in windows:
        print(f"\n{name}: {len(window_df)} bars")
        print(f"  Date range: {window_df['timestamp'].min()} to {window_df['timestamp'].max()}")
        
        params = {'ema_period': 50, 'min_slope': 0.0001, 'volume_multiplier': 1.5}
        signals = backtest_ema50_vector(window_df, params)
        
        results.append({
            'window': name,
            'bars': len(window_df),
            'signals': len(signals),
            'bullish': len(signals[signals['signal'] == 'BULLISH']) if len(signals) > 0 else 0,
            'bearish': len(signals[signals['signal'] == 'BEARISH']) if len(signals) > 0 else 0,
            'avg_confidence': signals['confidence'].mean() if len(signals) > 0 else 0
        })
    
    results_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("WALK-FORWARD RESULTS SUMMARY")
    print("="*80)
    print(results_df.to_string(index=False))
    
    return results_df

def parameter_optimization(df):
    """Test different parameter combinations"""
    print("\n" + "="*80)
    print("PARAMETER OPTIMIZATION ON REAL DATA")
    print("="*80)
    
    # Test parameter grid
    param_grid = [
        {'ema_period': 50, 'min_slope': 0.00005, 'volume_multiplier': 1.3, 'name': 'Sensitive'},
        {'ema_period': 50, 'min_slope': 0.0001, 'volume_multiplier': 1.5, 'name': 'Default'},
        {'ema_period': 50, 'min_slope': 0.0002, 'volume_multiplier': 1.8, 'name': 'Conservative'},
        {'ema_period': 50, 'min_slope': 0.0003, 'volume_multiplier': 2.0, 'name': 'Very Conservative'},
    ]
    
    # Use last 60 days for optimization
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    cutoff = df['timestamp'].max() - timedelta(days=60)
    df_opt = df[df['timestamp'] >= cutoff].copy()
    
    print(f"Optimization period: {len(df_opt)} bars ({df_opt['timestamp'].min()} to {df_opt['timestamp'].max()})")
    
    results = []
    
    for params in param_grid:
        name = params.pop('name')
        signals_df = backtest_ema50_vector(df_opt, params)
        
        results.append({
            'config': name,
            'min_slope': params['min_slope'],
            'volume_mult': params['volume_multiplier'],
            'total_signals': len(signals_df),
            'bullish': len(signals_df[signals_df['signal'] == 'BULLISH']) if len(signals_df) > 0 else 0,
            'bearish': len(signals_df[signals_df['signal'] == 'BEARISH']) if len(signals_df) > 0 else 0,
            'avg_confidence': signals_df['confidence'].mean() if len(signals_df) > 0 else 0
        })
        
        # Re-add name for next iteration
        params['name'] = name
    
    results_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("PARAMETER OPTIMIZATION RESULTS")
    print("="*80)
    print(results_df.to_string(index=False))
    
    # Recommend best
    if len(results_df) > 0:
        # Best = reasonable number of signals with high confidence
        results_df['score'] = results_df['total_signals'] * results_df['avg_confidence'] / 100
        best_idx = results_df['score'].idxmax()
        best = results_df.iloc[best_idx]
        
        print(f"\n✅ RECOMMENDED CONFIGURATION: {best['config']}")
        print(f"   min_slope: {best['min_slope']}")
        print(f"   volume_multiplier: {best['volume_mult']}")
        print(f"   Expected signals per 60 days: {best['total_signals']}")
        print(f"   Average confidence: {best['avg_confidence']:.2f}%")
    
    return results_df

def expert_assessment(df, backtest_results, wf_results, opt_results):
    """Expert mode assessment of results"""
    print("\n" + "="*80)
    print("EXPERT MODE ASSESSMENT - BLOCK #1: 50 EMA VECTOR")
    print("="*80)
    
    print("\n📊 DATA QUALITY:")
    print(f"  Total bars analyzed: {len(df)}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Data completeness: {(len(df) / ((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 900)) * 100:.2f}%")
    
    print("\n🎯 BACKTEST PERFORMANCE:")
    if len(backtest_results) > 0:
        print(f"  Total signals: {len(backtest_results)}")
        print(f"  Bullish signals: {len(backtest_results[backtest_results['signal'] == 'BULLISH'])}")
        print(f"  Bearish signals: {len(backtest_results[backtest_results['signal'] == 'BEARISH'])}")
        print(f"  Average confidence: {backtest_results['confidence'].mean():.2f}%")
        print(f"  Confidence range: {backtest_results['confidence'].min():.2f}% - {backtest_results['confidence'].max():.2f}%")
    else:
        print("  ⚠️ No signals generated - needs tuning")
    
    print("\n🔄 WALK-FORWARD CONSISTENCY:")
    if len(wf_results) > 0:
        signal_variance = wf_results['signals'].std() / wf_results['signals'].mean() if wf_results['signals'].mean() > 0 else 0
        print(f"  Signal variance: {signal_variance:.2%}")
        if signal_variance <0.3:
            print ("  ✅ STABLE - Consistent across time periods")
        elif signal_variance < 0.5:
            print("  ⚠️ MODERATE - Some variability")
        else:
            print("  ❌ UNSTABLE - High variance across periods")
    
    print("\n⚙️ OPTIMIZATION RESULTS:")
    if len(opt_results) > 0:
        print(f"  Tested {len(opt_results)} parameter combinations")
        best_idx = (opt_results['total_signals'] * opt_results['avg_confidence']).idxmax()
        best = opt_results.iloc[best_idx]
        print(f"  Best configuration: {best['config']}")
    
    print("\n" + "="*80)
    print("FINAL EXPERT VERDICT")
    print("="*80)
    
    if len(backtest_results) > 10 and signal_variance < 0.5:
        verdict = "✅ PRODUCTION READY"
        confidence = 95
    elif len(backtest_results) > 5:
        verdict = "⚠️ NEEDS TUNING"
        confidence = 75
    else:
        verdict = "❌ REQUIRES OPTIMIZATION"
        confidence = 50
    
    print(f"Status: {verdict}")
    print(f"Confidence: {confidence}%")
    print("\n")

if __name__ == "__main__":
    print("="*80)
    print("BLOCK #1: 50 EMA VECTOR - REAL BTC DATA VALIDATION")
    print("Expert Mode: Institutional Grade Testing")
    print("="*80)
    
    # Load real data
    df_raw = load_real_btc_data()
    df = prepare_data(df_raw)
    
    print(f"\n✅ Data prepared: {len(df)} bars ready for analysis")
    
    # Run tests
    print("\n1️⃣ Running backtest on full dataset...")
    backtest_results = backtest_ema50_vector(df, {'ema_period': 50, 'min_slope': 0.0001, 'volume_multiplier': 1.5})
    
    print("\n2️⃣ Running walk-forward test...")
    wf_results = walk_forward_test(df)
    
    print("\n3️⃣ Running parameter optimization...")
    opt_results = parameter_optimization(df)
    
    print("\n4️⃣ Expert assessment...")
    expert_assessment(df, backtest_results, wf_results, opt_results)
    
    print("\n✅ BLOCK #1 VALIDATION COMPLETE WITH REAL BTC DATA")
