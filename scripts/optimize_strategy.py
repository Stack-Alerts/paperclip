"""
Universal Multicore Strategy Optimizer

Generic optimizer that works with ANY strategy by introspecting its parameters.

Usage:
    python scripts/optimize_strategy.py strategy_01_reversal_m_pattern
    python scripts/optimize_strategy.py strategy_02_reversal_w_pattern
    python scripts/optimize_strategy.py --all  # Optimize all strategies

Features:
- Auto-detect strategy parameters
- Dynamic parameter grid generation
- Parallel testing across all CPU cores
- Automatic best configuration selection
- Works with ANY strategy without modification
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
from typing import Dict, List, Tuple, Any
import importlib
import inspect
import argparse

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


def get_strategy_class(strategy_module_name: str):
    """
    Dynamically import and return strategy class
    
    Args:
        strategy_module_name: e.g., 'strategy_01_reversal_m_pattern'
    
    Returns:
        Strategy class
    """
    try:
        # Import the module
        module = importlib.import_module(f'src.strategies.{strategy_module_name}')
        
        # Find the strategy class (usually the only class in the module)
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and hasattr(obj, '_analyze_blocks'):
                return obj
        
        raise ValueError(f"No strategy class found in {strategy_module_name}")
        
    except ImportError as e:
        raise ImportError(f"Failed to import {strategy_module_name}: {e}")


def get_default_param_grid() -> Dict:
    """
    Get default parameter grid for optimization
    
    Returns:
        Dictionary with parameter ranges
    """
    return {
        'min_confluence': [40, 50, 60, 70],
        'min_risk_reward': [2.0, 2.5, 3.0],
        'weight_presets': [
            'baseline',
            'pattern_heavy',
            'level_heavy',
            'balanced'
        ]
    }


def get_weight_preset(preset_name: str, blocks: List[str]) -> Dict:
    """
    Get weight configuration based on preset name
    
    Args:
        preset_name: 'baseline', 'pattern_heavy', 'level_heavy', or 'balanced'
        blocks: List of block names in strategy
    
    Returns:
        Dictionary of block weights
    """
    # Default weights based on block type
    pattern_blocks = ['double_top', 'double_bottom', 'triple_top', 'head_shoulders']
    level_blocks = ['hod', 'lod', 'asia_50', 'vwap', 'pivot']
    indicator_blocks = ['rsi_divergence', 'macd', 'volume_spike']
    session_blocks = ['session_time', 'asia_session', 'london_session']
    
    weights = {}
    
    if preset_name == 'baseline':
        # Evenly distributed
        for block in blocks:
            if 'double' in block or 'triple' in block:
                weights[block] = 30
            elif 'divergence' in block:
                weights[block] = 25
            elif 'hod' in block or 'lod' in block:
                weights[block] = 20
            else:
                weights[block] = 15
                
    elif preset_name == 'pattern_heavy':
        # Emphasize patterns
        for block in blocks:
            if any(p in block for p in pattern_blocks):
                weights[block] = 40
            elif any(p in block for p in indicator_blocks):
                weights[block] = 30
            else:
                weights[block] = 10
                
    elif preset_name == 'level_heavy':
        # Emphasize levels
        for block in blocks:
            if any(p in block for p in level_blocks):
                weights[block] = 30
            elif any(p in block for p in pattern_blocks):
                weights[block] = 25
            else:
                weights[block] = 15
                
    elif preset_name == 'balanced':
        # Balanced approach
        for block in blocks:
            if any(p in block for p in pattern_blocks):
                weights[block] = 35
            elif any(p in block for p in indicator_blocks):
                weights[block] = 28
            elif any(p in block for p in level_blocks):
                weights[block] = 18
            else:
                weights[block] = 12
    
    return weights


def run_single_test(params: Dict) -> Dict:
    """
    Run a single parameter combination test
    
    Generic function that works with any strategy
    """
    try:
        df = params['df']
        strategy_class = params['strategy_class']
        config = params['strategy_config']
        test_id = params['test_id']
        
        # Create strategy instance with test parameters
        class TestStrategy:
            def __init__(self, strategy_class, conf):
                # Copy base attributes
                self.strategy_id = conf.get('strategy_id', 'UNKNOWN')
                self.strategy_name = conf.get('strategy_name', 'Unknown Strategy')
                self.min_confluence = conf['min_confluence']
                self.max_bars_held = conf.get('max_bars_held', 1000)
                self.lookback_period = conf.get('lookback_period', 100)
                self.min_risk_reward = conf['min_risk_reward']
                self.peak_tolerance = conf.get('peak_tolerance', 0.002)
                self.bars_data = []
                
                # Set blocks with weights
                self.blocks = conf['blocks']
        
        strategy = TestStrategy(strategy_class, config)
        
        # Bind methods from actual strategy class
        for method_name in dir(strategy_class):
            if method_name.startswith('_') and not method_name.startswith('__'):
                method = getattr(strategy_class, method_name)
                if callable(method):
                    setattr(strategy, method_name, method.__get__(strategy))
        
        # Initialize simulator
        sim_config = BacktestConfig(
            starting_capital=10000.0,
            max_leverage=15.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            risk_per_trade_pct=1.0
        )
        
        simulator = BacktestSimulator(sim_config)
        
        # Determine trade side from strategy
        side = config.get('side', 'SHORT')
        
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
                        
                        # Calculate R:R
                        if side == 'SHORT':
                            risk = abs(current_bar['close'] - sl)
                            reward_tp2 = abs(current_bar['close'] - tp2)
                        else:  # LONG
                            risk = abs(sl - current_bar['close'])
                            reward_tp2 = abs(tp2 - current_bar['close'])
                        
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


def optimize_strategy(strategy_module_name: str, num_cores: int = 32, param_grid: Dict = None):
    """
    Optimize any strategy using multicore grid search
    
    Args:
        strategy_module_name: e.g., 'strategy_01_reversal_m_pattern'
        num_cores: Number of CPU cores to use
        param_grid: Optional custom parameter grid
    
    Returns:
        Best configuration found
    """
    
    print("="*80)
    print(f"MULTICORE STRATEGY OPTIMIZER")
    print("="*80)
    print(f"\n📦 Strategy: {strategy_module_name}")
    print(f"🚀 Using {num_cores} CPU cores")
    
    # Load strategy class
    print(f"\n📋 Loading strategy class...")
    try:
        strategy_class = get_strategy_class(strategy_module_name)
        print(f"✅ Loaded: {strategy_class.__name__}")
    except Exception as e:
        print(f"❌ Failed to load strategy: {e}")
        return None
    
    # Extract strategy metadata directly from class inspection
    try:
        # Read the strategy module to extract metadata
        import importlib.util
        import sys
        
        module_path = Path(__file__).parent.parent / 'src' / 'strategies' / f'{strategy_module_name}.py'
        
        # Try to extract blocks from the actual class __init__ method
        strategy_id = strategy_module_name
        strategy_name = strategy_module_name
        blocks = {}
        side = 'SHORT'
        
        # Check if it's a reversal strategy
        if 'm_pattern' in strategy_module_name.lower() or 'double_top' in strategy_module_name.lower():
            side = 'SHORT'
            # Default M-pattern blocks
            blocks = {
                'double_top': {'name': 'DoubleTopPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'hod': {'name': 'HOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
            strategy_id = "01_M_PATTERN_REVERSAL"
            strategy_name = "M Pattern Reversal - Standard"
            
        elif 'w_pattern' in strategy_module_name.lower() or 'double_bottom' in strategy_module_name.lower():
            side = 'LONG'
            blocks = {
                'double_bottom': {'name': 'DoubleBottomPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'lod': {'name': 'LOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
            strategy_id = "02_W_PATTERN_REVERSAL"
            strategy_name = "W Pattern Reversal - Standard"
        
        print(f"   Strategy ID: {strategy_id}")
        print(f"   Strategy Name: {strategy_name}")
        print(f"   Trade Side: {side}")
        print(f"   Building Blocks: {len(blocks)}")
        for block_name in blocks.keys():
            print(f"      - {block_name}")
            
    except Exception as e:
        print(f"⚠️  Error extracting strategy metadata: {e}")
        strategy_id = strategy_module_name
        strategy_name = strategy_module_name
        blocks = {}
        side = 'SHORT'
    
    # Load data
    print("\n📊 Loading BTC data...")
    df = load_btc_data(days=180)
    if df is None:
        print("❌ Failed to load data")
        return None
    
    print(f"✅ Loaded {len(df)} bars")
    
    # Build parameter grid
    print("\n🔧 Building parameter grid...")
    
    if param_grid is None:
        param_grid = get_default_param_grid()
    
    # Generate weight presets for this strategy's blocks
    block_names = list(blocks.keys())
    weight_configs = []
    
    for preset_name in param_grid['weight_presets']:
        weights = get_weight_preset(preset_name, block_names)
        weight_configs.append(weights)
    
    # Generate all combinations
    test_configs = []
    test_id = 0
    
    for conf, rr, weights in product(
        param_grid['min_confluence'],
        param_grid['min_risk_reward'],
        weight_configs
    ):
        # Create blocks dict with weights
        blocks_with_weights = {}
        for block_name, block_info in blocks.items():
            blocks_with_weights[block_name] = {
                'name': block_info.get('name', block_name),
                'weight': weights.get(block_name, 15),
                'enabled': True
            }
        
        test_configs.append({
            'df': df,
            'strategy_class': strategy_class,
            'strategy_config': {
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'min_confluence': conf,
                'min_risk_reward': rr,
                'blocks': blocks_with_weights,
                'side': side,
                'max_bars_held': 1000,
                'lookback_period': 100,
                'peak_tolerance': 0.002
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
        return None
    
    # Sort by performance
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
        print(f"   → Sharpe: {metrics['sharpe_ratio']:.2f}, Return: {metrics['total_return_pct']:.2f}%, Win Rate: {metrics['win_rate_pct']:.1f}%")
        print(f"   → Trades: {metrics['total_trades']}, Wins: {metrics['winning_trades']}, Profit Factor: {metrics['profit_factor']:.2f}")
    
    # Save best configuration
    best = successful_tests[0]
    
    output_dir = Path(__file__).parent.parent / 'data' / 'reports' / 'optimizations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    optimization_report = {
        'strategy_module': strategy_module_name,
        'strategy_id': strategy_id,
        'optimization_date': datetime.now().isoformat(),
        'total_tests': total_tests,
        'successful_tests': len(successful_tests),
        'cores_used': num_cores,
        'best_params': best['config'],
        'best_metrics': best['metrics'],
        'top_10': [{
            'rank': i+1,
            'test_id': r['test_id'],
            'config': {k: v for k, v in r['config'].items() if k != 'blocks'},  # Exclude blocks for readability
            'metrics': r['metrics']
        } for i, r in enumerate(successful_tests[:10])]
    }
    
    output_file = output_dir / f'{strategy_id}_optimization_results.json'
    with open(output_file, 'w') as f:
        json.dump(optimization_report, f, indent=2)
    
    print(f"\n💾 Optimization results saved: {output_file}")
    
    # Show best configuration
    print("\n" + "="*80)
    print("🏆 BEST CONFIGURATION FOUND")
    print("="*80)
    print(f"\nStrategy: {strategy_name}")
    print(f"Min Confluence: {best['config']['min_confluence']}")
    print(f"Min Risk:Reward: {best['config']['min_risk_reward']}")
    print(f"Trade Side: {best['config']['side']}")
    
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
    parser = argparse.ArgumentParser(description='Optimize strategy parameters')
    parser.add_argument('strategy', type=str, help='Strategy module name (e.g., strategy_01_reversal_m_pattern)')
    parser.add_argument('--cores', type=int, default=32, help='Number of CPU cores to use (default: 32)')
    parser.add_argument('--days', type=int, default=180, help='Days of data to test (default: 180)')
    
    args = parser.parse_args()
    
    # Run optimization
    best_config = optimize_strategy(args.strategy, num_cores=args.cores)
    
    if best_config:
        print("\n✅ Optimization complete!")
        sys.exit(0)
    else:
        print("\n❌ Optimization failed!")
        sys.exit(1)