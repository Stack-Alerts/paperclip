"""
Test for Strategy 02: W Pattern Reversal - Standard

Tests strategy logic, confluence calculation, and signal generation.
Validates pattern detection, RSI divergence, and entry conditions.

Strategy Details:
- Building Blocks: Double Bottom, RSI Divergence, LOD, Asia 50%, Session, VWAP
- Confluence Threshold: 70+ points
- Expected Frequency: 2-4 signals/month
- Risk:Reward: 1:3
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.strategies.strategy_02_reversal_w_pattern import WPatternReversalStandard


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data for testing"""
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
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    else:
        print("⚠️  No real data found - generating synthetic data for testing")
        return generate_synthetic_data(days)


def generate_synthetic_data(days: int) -> pd.DataFrame:
    """Generate synthetic BTC data with W-pattern characteristics"""
    bars_per_day = 96
    total_bars = days * bars_per_day
    start_date = datetime.now() - timedelta(days=days)
    base_price = 45000
    prices = []
    
    for i in range(total_bars):
        trend = np.sin(i / 100) * 2000
        noise = np.random.randn() * 500
        price = base_price + trend + noise
        
        # Inject W-pattern occasionally
        if i > 50 and i % 250 == 0:
            for j in range(20):
                if j < 5:  # First trough
                    price -= 200
                elif j < 10:  # Peak
                    price += 300
                elif j < 15:  # Second trough
                    price -= 280
                else:  # Breakout
                    price += 400
        
        timestamp = start_date + timedelta(minutes=15*i)
        open_price = price
        high_price = price + abs(np.random.randn() * 100)
        low_price = price - abs(np.random.randn() * 100)
        close_price = price + np.random.randn() * 50
        volume = 100 + abs(np.random.randn() * 50)
        
        prices.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(prices)


def test_strategy_signals(strategy, df: pd.DataFrame):
    """Test strategy signal generation"""
    print("="*80)
    print(f"🧪 STRATEGY TEST: {strategy.strategy_name}")
    print("="*80)
    print(f"Strategy ID: {strategy.strategy_id}")
    print(f"Dataset: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    signals_generated = []
    confluence_scores = []
    min_bars = strategy.lookback_period
    
    print(f"\nRunning simulation with {len(df)} bars...")
    
    for i in range(min_bars, len(df), 1):
        try:
            hist_df = df.iloc[:i+1].copy()
            
            for _, row in hist_df.iterrows():
                strategy.bars_data.append({
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })
            
            if len(strategy.bars_data) > strategy.max_bars_held:
                strategy.bars_data = strategy.bars_data[-strategy.max_bars_held:]
            
            analysis_df = pd.DataFrame(strategy.bars_data)
            results = strategy._analyze_blocks(analysis_df)
            confluence, signal_list = strategy._calculate_confluence(results)
            confluence_scores.append(confluence)
            
            if confluence >= strategy.min_confluence:
                tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                current_price = strategy.bars_data[-1]['close']
                risk = abs(current_price - sl)
                reward = abs(current_price - tp2)  # LONG trade
                rr_ratio = reward / risk if risk > 0 else 0
                
                signal = {
                    'timestamp': hist_df.iloc[-1]['timestamp'],
                    'bar_index': i,
                    'confluence': confluence,
                    'signals': signal_list,
                    'entry_price': current_price,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'sl': sl,
                    'rr_ratio': rr_ratio
                }
                
                if rr_ratio >= strategy.min_risk_reward:
                    signals_generated.append(signal)
                    
        except Exception as e:
            print(f"Error at bar {i}: {e}")
            continue
    
    # Calculate statistics
    print(f"\n{'='*80}")
    print(f"📊 TEST RESULTS:")
    print(f"{'='*80}")
    print(f"Total bars tested: {len(df)}")
    print(f"Signals generated: {len(signals_generated)}")
    
    if confluence_scores:
        print(f"Average confluence: {sum(confluence_scores)/len(confluence_scores):.1f}")
        print(f"Max confluence: {max(confluence_scores)}")
    
    days_tested = (df['timestamp'].max() - df['timestamp'].min()).days
    months_tested = days_tested / 30
    signals_per_month = len(signals_generated) / months_tested if months_tested > 0 else 0
    
    print(f"Signals per month: {signals_per_month:.2f}")
    print(f"Expected: 2-4 signals/month")
    
    if signals_generated:
        avg_rr = sum(s['rr_ratio'] for s in signals_generated) / len(signals_generated)
        print(f"Average R:R: {avg_rr:.2f}")
    
    # Save results
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'strategy_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        'strategy_name': strategy.strategy_name,
        'strategy_id': strategy.strategy_id,
        'test_date': datetime.now().isoformat(),
        'total_bars': len(df),
        'signals_generated': len(signals_generated),
        'signals_per_month': signals_per_month,
        'avg_rr': sum(s['rr_ratio'] for s in signals_generated) / len(signals_generated) if signals_generated else 0,
        'validation_passed': 1 <= signals_per_month <= 6
    }
    
    output_file = output_dir / f'{strategy.strategy_id}_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Test results saved: {output_file}")
    print("="*80)
    
    return report


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*80)
    print("STRATEGY 02: W PATTERN REVERSAL - TEST SUITE")
    print("="*80 + "\n")
    
    df = load_btc_data(days=180)
    
    if df is None or len(df) == 0:
        print("❌ Failed to load data")
        return False
    
    print(f"✅ Loaded {len(df)} bars\n")
    
    config = {'instrument_id': 'BTC/USDT'}
    strategy = WPatternReversalStandard(config)
    print(f"✅ Strategy initialized\n")
    
    report = test_strategy_signals(strategy, df)
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Strategy: {strategy.strategy_name}")
    print(f"Signals: {report['signals_generated']}")
    print(f"Signals/Month: {report['signals_per_month']:.2f}")
    print(f"Validation: {'PASSED ✅' if report['validation_passed'] else 'WARNINGS ⚠️'}")
    print("="*80 + "\n")
    
    return report['validation_passed']


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)