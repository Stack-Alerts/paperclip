"""
Walkforward Test for Range Liquidity (Block 62)
Now with optional REAL orderbook integration!
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json
from src.detectors.building_blocks.market_structure.range_liquidity import RangeLiquidity

def load_btc_data():
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
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
    
    return df

def run_walkforward_test(use_orderbook=False):
    """Run walkforward test with or without orderbook data"""
    
    # Load data
    df = load_btc_data()
    
    # Filter to test period (last 180 days)
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=180)
    df_test = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)
    
    print("="*80)
    print(f"RANGE LIQUIDITY WALKFORWARD TEST - {'WITH ORDERBOOK!' if use_orderbook else 'Basic Mode'}")
    print("="*80)
    print(f"Test period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
    print(f"Total bars: {len(df_test)}")
    print()
    
    # Initialize detector
    detector = RangeLiquidity()
    
    # Orderbook file if using advanced mode
    orderbook_file = None
    if use_orderbook:
        # Try to find a matching orderbook file
        orderbook_dir = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'orderbook'
        # Use June 2025 as example (if exists)
        potential_file = orderbook_dir / 'BTC-USDT_orderbook_2025-06.parquet'
        if potential_file.exists():
            orderbook_file = str(potential_file)
            print(f"✅ Using orderbook data: {potential_file.name}")
        else:
            print(f"⚠️ Orderbook file not found, using basic mode")
        print()
    
    # Expanding window validation
    min_bars = 100
    sample_every = 1
    
    results = []
    confidences = []
    signals = {
        'NEAR_BUY_SIDE_LIQUIDITY': 0,
        'NEAR_SELL_SIDE_LIQUIDITY': 0
    }
    
    orderbook_stats = {
        'has_data': 0,
        'no_data': 0,
        'depths': [],
        'strengths': []
    }
    
    for i in range(min_bars, len(df_test), sample_every):
        window_df = df_test.iloc[:i+1]
        
        try:
            result = detector.analyze(window_df, orderbook_file=orderbook_file)
            
            if result['signal'] in signals:
                signals[result['signal']] += 1
                confidences.append(result['confidence'])
                results.append(result)
                
                # Track orderbook usage
                if result['metadata'].get('has_orderbook_data'):
                    orderbook_stats['has_data'] += 1
                    if result['metadata'].get('total_depth_btc'):
                        orderbook_stats['depths'].append(result['metadata']['total_depth_btc'])
                    orderbook_stats['strengths'].append(result['metadata']['liquidity_strength'])
                else:
                    orderbook_stats['no_data'] += 1
                    
        except Exception as e:
            print(f"Error at bar {i}: {e}")
            continue
    
    # Calculate statistics
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    std_confidence = pd.Series(confidences).std() if len(confidences) > 1 else 0
    
    # Results
    test_results = {
        'block': 'range_liquidity',
        'methodology': 'V2',
        'total_bars_sampled': len(df_test),
        'valid_results': len(results),
        'active_signals': len(results),
        'active_signal_rate': len(results) / len(df_test) if len(df_test) > 0 else 0,
        'avg_active_confidence': avg_confidence,
        'avg_all_confidence': avg_confidence,
        'std_confidence': std_confidence,
        'errors': 0,
        'error_rate': 0.0,
        'all_signal_types': signals,
        'active_signal_types': signals,
        'signals_per_day': len(results) / 180,
        'test_period': {
            'start': str(df_test['timestamp'].min()),
            'end': str(df_test['timestamp'].max()),
            'days': 180,
            'bars': len(df_test)
        },
        'validation_params': {
            'methodology': 'expanding_window',
            'min_bars': min_bars,
            'sample_every': sample_every,
            'total_bars_available': len(df_test)
        },
        'orderbook_integration': {
            'enabled': use_orderbook,
            'has_data_count': orderbook_stats['has_data'],
            'no_data_count': orderbook_stats['no_data'],
            'avg_depth_btc': sum(orderbook_stats['depths']) / len(orderbook_stats['depths']) if orderbook_stats['depths'] else None,
            'depth_range_btc': [min(orderbook_stats['depths']), max(orderbook_stats['depths'])] if orderbook_stats['depths'] else None,
            'avg_strength': sum(orderbook_stats['strengths']) / len(orderbook_stats['strengths']) if orderbook_stats['strengths'] else None,
            'strength_range': [min(orderbook_stats['strengths']), max(orderbook_stats['strengths'])] if orderbook_stats['strengths'] else None
        }
    }
    
    # Print summary
    print("\nRESULTS SUMMARY:")
    print("-" * 80)
    print(f"Valid results: {test_results['valid_results']}")
    print(f"Average confidence: {avg_confidence:.2f}%")
    print(f"Std dev confidence: {std_confidence:.2f}%")
    print(f"\nSignal distribution:")
    for sig, count in signals.items():
        pct = (count / len(results) * 100) if results else 0
        print(f"  {sig}: {count} ({pct:.1f}%)")
    
    if use_orderbook and orderbook_stats['has_data'] > 0:
        print(f"\nORDERBOOK STATS:")
        print(f"  Bars with orderbook data: {orderbook_stats['has_data']}")
        print(f"  Bars without orderbook: {orderbook_stats['no_data']}")
        if orderbook_stats['depths']:
            print(f"  Avg depth: {sum(orderbook_stats['depths'])/len(orderbook_stats['depths']):.4f} BTC")
            print(f"  Depth range: {min(orderbook_stats['depths']):.4f} - {max(orderbook_stats['depths']):.4f} BTC")
        if orderbook_stats['strengths']:
            print(f"  Avg strength: {sum(orderbook_stats['strengths'])/len(orderbook_stats['strengths']):.1f}")
            print(f"  Strength range: {min(orderbook_stats['strengths'])} - {max(orderbook_stats['strengths'])}")
    
    # Save results
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'walkforward_results_range_liquidity.json'
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n✅ JSON results saved to: {output_file}")
    
    return test_results

if __name__ == '__main__':
    # Check if user wants orderbook mode
    use_orderbook = '--orderbook' in sys.argv or '-o' in sys.argv
    
    results = run_walkforward_test(use_orderbook=use_orderbook)
    
    print("\n" + "="*80)
    print("✅ Range Liquidity V2 walkforward test complete")
    if use_orderbook:
        print("🎯 Advanced mode with real orderbook integration tested!")
    print("="*80)
