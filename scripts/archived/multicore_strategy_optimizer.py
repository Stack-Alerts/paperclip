"""
Multicore Strategy Parameter Optimizer

Uses all 32 CPU cores to rapidly test parameter combinations
and find optimal settings for each strategy.

Features:
- Parallel testing across all cores
- Grid search over parameters
- Automatic best parameter selection
- Complete results tracking
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import multiprocessing as mp
from itertools import product
from typing import Dict, List, Tuple

# Import test components
from tests.strategies.backtest_simulator import BacktestSimulator, BacktestConfig


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


def run_single_test(params: Dict) -> Dict:
    """
    Run a single parameter combination test
    
    Args:
        params: Dictionary with:
            - df: Price data
            - strategy_config: Strategy configuration
            - test_id: Unique ID for this test
    
    Returns:
        Dictionary with test results
    """
    try:
        from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
        
        df = params['df']
        config = params['strategy_config']
        test_id = params['test_id']
        
        # Create strategy with test parameters
        class TestStrategy:
            def __init__(self, conf):
                self.strategy_id = "01_M_PATTERN_REVERSAL"
                self.strategy_name = "M Pattern Reversal - Standard"
                self.min_confluence = conf['min_confluence']
                self.max_bars_held = 1000
                self.lookback_period = 100
                self.min_risk_reward = conf['min_risk_reward']
                self.peak_tolerance = 0.002
                self.bars_data = []
                
                # Adjust weights
                self.blocks = {
                    'double_top': {'name': 'DoubleTopPattern', 'weight': conf['weights']['double_top'], 'enabled': True},
                    'rsi_divergence': {'name': 'RSIDivergence', 'weight': conf['weights']['rsi_divergence'], 'enabled': True},
                    'hod': {'name': 'HOD', 'weight': conf['weights']['hod'], 'enabled': True},
                    'asia_50': {'name': 'AsiaSession50Percent', 'weight': conf['weights']['asia_50'], 'enabled': True},
                    'session_time': {'name': 'SessionTime', 'weight': conf['weights']['session_time'], 'enabled': True},
                    'vwap': {'name': 'VWAP', 'weight': conf['weights']['vwap'], 'enabled': True}
                }
        
        strategy = TestStrategy(config)
        
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
        
        # Initialize simulator
        sim_config = BacktestConfig(
            starting_capital=10000.0,
            max_leverage=15.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            risk_per_trade_pct=1.0
        )
        
        simulator = BacktestSimulator(sim_config)
        
        # Run walk-forward test
        min_bars = strategy.lookback_period
        
        for i in range(len(df)):
            current_bar = df.iloc[i]
            
            # Add bar
            strategy.bars_data.append({
                'timestamp': current_bar['timestamp'],
                'open': current_bar['open'],
                'high': current_bar['high'],
                'low': current_bar['low'],
                'close': current_bar['close'],
                'volume': current_bar['volume']
            })
            
            if len(strategy.bars_data) > strategy.max_bars_held:
                strategy.bars_data.pop(0)
            
            # Update position
            if simulator.open_trade is not None:
                simulator.update_open_position(current_bar)
            
            # Check for signals
            if simulator.open_trade is None and len(strategy.bars_data) >= min_bars:
                try:
                    analysis_df = pd.DataFrame(strategy.bars_data)
                    results = strategy._analyze_blocks(analysis_df)
                    confluence, signal_list = strategy._calculate_confluence(results)
                    
                    if confluence >= strategy.min_confluence:
                        tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                        side = 'SHORT'
                        
                        risk = abs(current_bar['close'] - sl)
                        reward_tp2 = abs(current_bar['close'] - tp2)
                        rr = reward_tp2 / risk if risk > 0 else 0
                        
                        if rr >= strategy.min_risk_reward:
                            simulator.open_position(
                                entry_time=current_bar['timestamp'],
                                entry_price=current_bar['close'],
                                side=side,
                                tp1=tp1, tp2=tp2, tp3=tp3, sl=sl,
                                confluence=confluence,
                                signals=signal_list
                            )
                except:
                    pass
        
        # Close any open position
        if simulator.open_trade is not None:
            simulator.close_position(df.iloc[-1]['timestamp'], df.iloc[-1]['close'], 'END_OF_TEST')
        
        # Get results
        metrics = simulator.get_performance_metrics()
        
        return {
            'test_id': test_id,
            'config': config,
            'metrics': metrics,
            'success': True
        }
        
    except Exception as e:
        return {
            'test_id': params.get('test_id', 'unknown'),
            'config': params.get('strategy_config', {}),
            'error': str(e),
            'success': False
        }


def optimize_strategy_01(num_cores: int = 32):
    """
    Optimize Strategy 01 using multicore grid search
    
    Tests combinations of:
    - Confluence threshold: 40, 50, 60, 70
    - Block weights: various combinations
    - Min R:R: 2.0, 2.5, 3.0
    """
    
    print("="*80)
    print("MULTICORE STRATEGY OPTIMIZER - STRATEGY 01")
    print("="*80)
    print(f"\n🚀 Using {num_cores} CPU cores")
    
    # Load data once
    print("\n📊 Loading BTC data...")
    df = load_btc_data(days=180)
    if df is None:
        print("❌ Failed to load data")
        return
    
    print(f"✅ Loaded {len(df)} bars")
    
    # Define parameter grid
    print("\n🔧 Building parameter grid...")
    
    confluence_values = [40, 50, 60, 70]
    rr_values = [2.0, 2.5, 3.0]
    
    # Weight combinations (simplified for speed)
    weight_sets = [
        # Baseline
        {'double_top': 30, 'rsi_divergence': 25, 'hod': 20, 'asia_50': 18, 'session_time': 15, 'vwap': 12},
        # Emphasize pattern
        {'double_top': 40, 'rsi_divergence': 30, 'hod': 15, 'asia_50': 10, 'session_time': 10, 'vwap': 15},
        # Emphasize levels
        {'double_top': 25, 'rsi_divergence': 20, 'hod': 30, 'asia_50': 25, 'session_time': 10, 'vwap': 10},
        # Balanced
        {'double_top': 35, 'rsi_divergence': 28, 'hod': 18, 'asia_50': 15, 'session_time': 12, 'vwap': 12},
    ]
    
    # Generate all combinations
    test_configs = []
    test_id = 0
    
    for conf, rr, weights in product(confluence_values, rr_values, weight_sets):
        test_configs.append({
            'df': df,
            'strategy_config': {
                'min_confluence': conf,
                'min_risk_reward': rr,
                'weights': weights
            },
            'test_id': test_id
        })
        test_id += 1
    
    total_tests = len(test_configs)
    print(f"   Total parameter combinations: {total_tests}")
    print(f"   Estimated time: {total_tests * 30 / num_cores:.0f} seconds ({total_tests * 30 / num_cores / 60:.1f} minutes)")
    
    # Run parallel tests
    print(f"\n🔄 Running {total_tests} tests across {num_cores} cores...")
    
    with mp.Pool(num_cores) as pool:
        results = pool.map(run_single_test, test_configs)
    
    # Analyze results
    print("\n📊 Analyzing results...")
    
    successful_tests = [r for r in results if r.get('success', False)]
    failed_tests = [r for r in results if not r.get('success', False)]
    
    print(f"   Successful: {len(successful_tests)}")
    print(f"   Failed: {len(failed_tests)}")
    
    if not successful_tests:
        print("\n❌ No successful tests!")
        return
    
    # Sort by performance metrics
    # Primary: Sharpe Ratio, Secondary: Total Return
    successful_tests.sort(key=lambda x: (
        x['metrics'].get('sharpe_ratio', -999),
        x['metrics'].get('total_return_pct', -999)
    ), reverse=True)
    
    # Show top 10
    print("\n" + "="*80)
    print("TOP 10 PARAMETER COMBINATIONS")
    print("="*80)
    
    for i, result in enumerate(successful_tests[:10], 1):
        config = result['config']
        metrics = result['metrics']
        
        print(f"\n#{i}: Test {result['test_id']}")
        print(f"   Confluence: {config['min_confluence']}, R:R: {config['min_risk_reward']}")
        print(f"   Weights: DT={config['weights']['double_top']}, RSI={config['weights']['rsi_divergence']}, HOD={config['weights']['hod']}")
        print(f"   → Sharpe: {metrics['sharpe_ratio']:.2f}, Return: {metrics['total_return_pct']:.2f}%, Win Rate: {metrics['win_rate_pct']:.1f}%")
        print(f"   → Trades: {metrics['total_trades']}, Wins: {metrics['winning_trades']}, Profit Factor: {metrics['profit_factor']:.2f}")
    
    # Save best configuration
    best = successful_tests[0]
    
    output_dir = Path(__file__).parent.parent / 'data' / 'reports' / 'optimizations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    optimization_report = {
        'optimization_date': datetime.now().isoformat(),
        'total_tests': total_tests,
        'successful_tests': len(successful_tests),
        'cores_used': num_cores,
        'best_params': best['config'],
        'best_metrics': best['metrics'],
        'top_10': [{
            'rank': i+1,
            'test_id': r['test_id'],
            'config': r['config'],
            'metrics': r['metrics']
        } for i, r in enumerate(successful_tests[:10])]
    }
    
    output_file = output_dir / 'strategy_01_optimization_results.json'
    with open(output_file, 'w') as f:
        json.dump(optimization_report, f, indent=2)
    
    print(f"\n💾 Optimization results saved: {output_file}")
    
    # Show best configuration
    print("\n" + "="*80)
    print("🏆 BEST CONFIGURATION FOUND")
    print("="*80)
    print(f"\nMin Confluence:      {best['config']['min_confluence']}")
    print(f"Min Risk:Reward:     {best['config']['min_risk_reward']}")
    print(f"\nBlock Weights:")
    for block, weight in best['config']['weights'].items():
        print(f"   {block:20s}: {weight}")
    
    print(f"\nExpected Performance:")
    print(f"   Sharpe Ratio:     {best['metrics']['sharpe_ratio']:.2f}")
    print(f"   Total Return:     {best['metrics']['total_return_pct']:.2f}%")
    print(f"   Win Rate:         {best['metrics']['win_rate_pct']:.1f}%")
    print(f"   Trades:           {best['metrics']['total_trades']}")
    print(f"   Profit Factor:    {best['metrics']['profit_factor']:.2f}")
    print(f"   Max Drawdown:     {best['metrics']['max_drawdown_pct']:.2f}%")
    
    print("\n" + "="*80)
    
    return best


if __name__ == "__main__":
    # Use all 32 cores
    best_config = optimize_strategy_01(num_cores=32)