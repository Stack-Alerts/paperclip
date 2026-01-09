"""
Universal Strategy Optimizer - Works with ALL 80 Building Blocks

Automatically detects any building blocks in any strategy and optimizes:
- Block weights
- Confluence thresholds
- Risk/reward ratios
- Any other parameters

Usage:
    python scripts/universal_optimizer.py strategy_01_reversal_m_pattern
    python scripts/universal_optimizer.py strategy_XX_any_strategy
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
import re

from tests.strategies.backtest_simulator import BacktestSimulator, BacktestConfig


# Map all 80 building blocks to their categories
BUILDING_BLOCK_CATALOG = {
    # Moving Averages (7)
    'ema_20_50_cross': {'category': 'moving_averages', 'type': 'SIGNAL', 'weight_range': (15, 30)},
    'ema_20_50_trend': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (10, 20)},
    'ema_50_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'ema_55_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'ema_200_trend': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'ema_255_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (5, 12)},
    'ema_800_vector': {'category': 'moving_averages', 'type': 'CONTEXT', 'weight_range': (5, 10)},
    
    # Oscillators (3)
    'macd_signal': {'category': 'oscillators', 'type': 'SIGNAL', 'weight_range': (15, 25)},
    'rsi_divergence': {'category': 'oscillators', 'type': 'EVENT', 'weight_range': (20, 30)},
    'stochastic_rsi': {'category': 'oscillators', 'type': 'SIGNAL', 'weight_range': (12, 22)},
    
    # Price Action (4)
    'order_block': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (18, 25)},
    'fair_value_gap': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (15, 22)},
    'liquidity_sweep': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (18, 25)},
    'breaker_block': {'category': 'price_action', 'type': 'EVENT', 'weight_range': (15, 22)},
    
    # Patterns (20)
    'double_top': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 35)},
    'double_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 35)},
    'triple_top': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (18, 30)},
    'triple_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (18, 30)},
    'head_shoulders': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 32)},
    'inverse_head_shoulders': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (20, 32)},
    'cup_handle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (15, 25)},
    'rounding_bottom': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (15, 25)},
    'flag_pattern': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'pennant_pattern': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'symmetrical_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'ascending_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'descending_triangle': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (14, 24)},
    'falling_wedge': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
    'rising_wedge': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 22)},
   'three_bar_reversal': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (10, 18)},
    'candle_2_close': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (8, 15)},
    'internal_pivot': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (10, 18)},
    'swing_breakout': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 20)},
    'initial_balance_breakout': {'category': 'patterns', 'type': 'EVENT', 'weight_range': (12, 20)},
    
    # Price Levels (6)
    'hod': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (15, 25)},
    'how': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'lod': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (15, 25)},
    'low': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'asia_50': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (12, 22)},
    'us_settlement': {'category': 'price_levels', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # SMC/ICT (9)
    'break_of_structure': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (18, 25)},
    'market_structure_shift': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (20, 28)},
    'displacement': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 20)},
    'inducement': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (15, 22)},
    'optimal_trade_entry': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (18, 25)},
    'swing_failure_pattern': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (15, 22)},
    'change_of_character': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 20)},
    'mitigation_block': {'category': 'smc_ict', 'type': 'EVENT', 'weight_range': (12, 18)},
    'balanced_price_range': {'category': 'smc_ict', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    
    # Institutional (5)
    'vwap': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'anchored_vwap': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'ema_crossover': {'category': 'institutional', 'type': 'SIGNAL', 'weight_range': (12, 20)},
    'market_depth': {'category': 'institutional', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'order_flow_imbalance': {'category': 'institutional', 'type': 'EVENT', 'weight_range': (10, 18)},
    
    # Sessions (2)
    'kill_zones': {'category': 'sessions', 'type': 'CONTEXT', 'weight_range': (12, 20)},
    'session_time': {'category': 'sessions', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # Market Structure (6)
    'premium_discount_zones': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    'range_liquidity': {'category': 'market_structure', 'type': 'EVENT', 'weight_range': (10, 18)},
    'swing_points': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (12, 18)},
    'liquidity': {'category': 'market_structure', 'type': 'EVENT', 'weight_range': (12, 18)},
    'power_hour_trends': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    'wave_consolidation': {'category': 'market_structure', 'type': 'CONTEXT', 'weight_range': (8, 15)},
    
    # Supply/Demand (1)
    'supply_demand_zones': {'category': 'supply_demand', 'type': 'EVENT', 'weight_range': (12, 20)},
    
    # Fibonacci (1)
    'fibonacci_retracements': {'category': 'fibonacci', 'type': 'CONTEXT', 'weight_range': (10, 18)},
    
    # Signals (4)
    'macd_price_forecasting': {'category': 'signals', 'type': 'HYBRID', 'weight_range': (10, 18)},
    'adaptive_momentum_oscillator': {'category': 'signals', 'type': 'HYBRID', 'weight_range': (10, 18)},
    'ict_silver_bullet': {'category': 'signals', 'type': 'EVENT', 'weight_range': (15, 22)},
    'asfx_a2_vwap': {'category': 'signals', 'type': 'SIGNAL', 'weight_range': (10, 18)},
    
    # Trend/Momentum (2)
    'ichimoku_cloud': {'category': 'trend_momentum', 'type': 'HYBRID', 'weight_range': (12, 20)},
    'adx': {'category': 'trend_momentum', 'type': 'HYBRID', 'weight_range': (15, 22)},
    
    # Volatility (3)
    'atr': {'category': 'volatility', 'type': 'CONTEXT', 'weight_range': (0, 0)},  # Not for confluence
    'adr': {'category': 'volatility', 'type': 'CONTEXT', 'weight_range': (5, 12)},
    'bollinger_bands': {'category': 'volatility', 'type': 'SIGNAL', 'weight_range': (10, 18)},
    
    # Risk Management (1)
    'trailing_stop': {'category': 'risk_management', 'type': 'CONTEXT', 'weight_range': (0, 0)},  # Not for confluence
}


def extract_blocks_from_strategy(strategy_module_name: str) -> Dict:
    """
    Extract building blocks from strategy file by reading source code
    
    Returns:
        Dict with block names and their initial configs
    """
    strategy_path = Path(__file__).parent.parent / 'src' / 'strategies' / f'{strategy_module_name}.py'
    
    if not strategy_path.exists():
        print(f"⚠️  Strategy file not found: {strategy_path}")
        return {}
    
    blocks = {}
    
    # Read strategy file
    with open(strategy_path, 'r') as f:
        content = f.read()
    
    # Pattern 1: Look for self.blocks = {...} (single dict assignment)
    blocks_match = re.search(r'self\.blocks\s*=\s*\{([^}]+)\}', content, re.DOTALL)
    
    if blocks_match:
        blocks_content = blocks_match.group(1)
        
        # Extract each block definition from dict
        pattern = r"'(\w+)':\s*\{[^}]*'name':\s*'([^']+)'[^}]*'weight':\s*(\d+)[^}]*'enabled':\s*(True|False)[^}]*\}"
        matches = re.findall(pattern, blocks_content)
        
        for match in matches:
            block_key, block_name, weight, enabled = match
            blocks[block_key] = {
                'name': block_name,
                'weight': int(weight),
                'enabled': enabled == 'True'
            }
    
    # Pattern 2: Look for self.blocks['key'] = {...} (individual assignments)
    if not blocks:
        # Find all individual block assignments
        individual_pattern = r"self\.blocks\['(\w+)'\]\s*=\s*\{([^}]+)\}"
        matches = re.findall(individual_pattern, content, re.DOTALL)
        
        for block_key, block_content in matches:
            # Extract name, weight, enabled from block content
            name_match = re.search(r"'name':\s*'([^']+)'", block_content)
            weight_match = re.search(r"'weight':\s*(\d+)", block_content)
            enabled_match = re.search(r"'enabled':\s*(True|False)", block_content)
            
            if name_match and weight_match and enabled_match:
                blocks[block_key] = {
                    'name': name_match.group(1),
                    'weight': int(weight_match.group(1)),
                    'enabled': enabled_match.group(1) == 'True'
                }
    
    return blocks


def get_weight_presets_for_blocks(block_keys: List[str]) -> List[Dict]:
    """
    Generate optimized weight presets based on block types
    
    Args:
        block_keys: List of block keys used in strategy
    
    Returns:
        List of weight configurations to test
    """
    presets = []
    
    # Categorize blocks
    event_blocks = []
    signal_blocks = []
    context_blocks = []
    
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            block_type = BUILDING_BLOCK_CATALOG[key]['type']
            if block_type == 'EVENT':
                event_blocks.append(key)
            elif block_type == 'SIGNAL':
                signal_blocks.append(key)
            else:  # CONTEXT or HYBRID
                context_blocks.append(key)
    
    # Preset 1: Balanced
    balanced = {}
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            balanced[key] = (min_w + max_w) // 2
        else:
            balanced[key] = 15  # Default
    presets.append(balanced)
    
    # Preset 2: Event-Heavy (favor EVENT blocks)
    event_heavy = balanced.copy()
    for key in event_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            _, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            event_heavy[key] = max_w
    for key in context_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, _ = BUILDING_BLOCK_CATALOG[key]['weight_range']
            event_heavy[key] = min_w
    presets.append(event_heavy)
    
    # Preset 3: Context-Heavy (favor CONTEXT blocks)
    context_heavy = balanced.copy()
    for key in context_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            _, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            context_heavy[key] = max_w
    for key in event_blocks:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, _ = BUILDING_BLOCK_CATALOG[key]['weight_range']
            context_heavy[key] = min_w
    presets.append(context_heavy)
    
    # Preset 4: Conservative (lower all weights slightly)
    conservative = {}
    for key in block_keys:
        if key in BUILDING_BLOCK_CATALOG:
            min_w, max_w = BUILDING_BLOCK_CATALOG[key]['weight_range']
            conservative[key] = min_w + (max_w - min_w) // 3
        else:
            conservative[key] = 12
    presets.append(conservative)
    
    return presets


def load_btc_data(test_days: int = 180, warmup_bars: int = 5000) -> tuple:
    """
    Load BTC 15min data with warmup period
    
    Args:
        test_days: Days to test on (walk-forward period)
        warmup_bars: Bars to warmup building blocks (default 5000)
    
    Returns:
        (warmup_df, test_df): Warmup data and test data
    """
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
        
        # Calculate total bars needed: warmup + test period
        bars_per_day = 96  # 15min bars
        test_bars = test_days * bars_per_day
        total_bars_needed = warmup_bars + test_bars
        
        # Get most recent data
        if len(df) < total_bars_needed:
            print(f"⚠️  Warning: Only {len(df)} bars available, need {total_bars_needed}")
            warmup_bars = min(warmup_bars, len(df) // 2)
            test_bars = len(df) - warmup_bars
        
        # Split into warmup and test
        warmup_df = df.iloc[-total_bars_needed:-test_bars].copy()
        test_df = df.iloc[-test_bars:].copy()
        
        warmup_df = warmup_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        test_df = test_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        
        return warmup_df, test_df
    
    return None, None


def get_strategy_class(strategy_module_name: str):
    """Dynamically import strategy class"""
    try:
        module = importlib.import_module(f'src.strategies.{strategy_module_name}')
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and hasattr(obj, '_analyze_blocks'):
                return obj
        
        raise ValueError(f"No strategy class found in {strategy_module_name}")
        
    except ImportError as e:
        raise ImportError(f"Failed to import {strategy_module_name}: {e}")


def run_single_test(params: Dict) -> Dict:
    """
    Run single parameter combination test
    
    Process:
    1. Warmup building blocks with 5000 bars (no trading)
    2. Walk-forward test on 180 days (with trading)
    3. Building blocks have full historical context
    """
    try:
        warmup_df = params['warmup_df']
        test_df = params['test_df']
        strategy_class = params['strategy_class']
        config = params['strategy_config']
        test_id = params['test_id']
        
        # Create strategy with parameters
        class TestStrategy:
            def __init__(self, strategy_class, conf):
                self.strategy_id = conf.get('strategy_id', 'UNKNOWN')
                self.strategy_name = conf.get('strategy_name', 'Unknown')
                self.min_confluence = conf['min_confluence']
                self.max_bars_held = conf.get('max_bars_held', 1000)
                self.lookback_period = conf.get('lookback_period', 100)
                self.min_risk_reward = conf['min_risk_reward']
                self.peak_tolerance = conf.get('peak_tolerance', 0.002)
                self.bars_data = []
                self.blocks = conf['blocks']
                self.detectors = {}  # For REAL building block instances
        
        strategy = TestStrategy(strategy_class, config)
        
        # Bind methods
        for method_name in dir(strategy_class):
            if method_name.startswith('_') and not method_name.startswith('__'):
                method = getattr(strategy_class, method_name)
                if callable(method):
                    setattr(strategy, method_name, method.__get__(strategy))
        
        # CRITICAL: Initialize REAL building block detectors
        if hasattr(strategy, '_initialize_blocks'):
            strategy._initialize_blocks()
        
        # Initialize simulator
        sim_config = BacktestConfig(
            starting_capital=10000.0,
            max_leverage=15.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            risk_per_trade_pct=1.0
        )
        
        simulator = BacktestSimulator(sim_config)
        side = config.get('side', 'SHORT')
        min_bars = strategy.lookback_period
        
        # PHASE 1: WARMUP - Process 5000 bars to initialize building blocks (NO TRADING)
        # Building blocks need historical context to properly detect patterns
        print(f"  Warming up with {len(warmup_df)} bars...")
        
        # Combine warmup and test dataframes for building blocks
        full_df = pd.concat([warmup_df, test_df], ignore_index=True)
        warmup_bar_count = len(warmup_df)
        
        # PHASE 2: WALK-FORWARD TEST on 180 days (WITH TRADING)
        # Start trading after warmup period
        for i in range(warmup_bar_count, len(full_df)):
            current_bar = full_df.iloc[i]
            
            # Update open position
            if simulator.open_trade is not None:
                simulator.update_open_position(current_bar)
            
            # Check for new entries (only if no position)
            if simulator.open_trade is None:
                try:
                    # CRITICAL: Pass FULL historical data including warmup
                    # Building blocks see: warmup_df + test_df[:current_bar]
                    analysis_df = full_df.iloc[:i+1].copy()
                    
                    # Run building block analysis with full historical context
                    results = strategy._analyze_blocks(analysis_df)
                    confluence, signal_list = strategy._calculate_confluence(results)
                    
                    if confluence >= strategy.min_confluence:
                        tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                        
                        if side == 'SHORT':
                            risk = abs(current_bar['close'] - sl)
                            reward_tp2 = abs(current_bar['close'] - tp2)
                        else:
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
        
        # Close any open position at end of test
        if simulator.open_trade is not None:
            simulator.close_position(
                full_df.iloc[-1]['timestamp'], 
                full_df.iloc[-1]['close'], 
                'END_OF_TEST'
            )
        
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


def optimize_strategy(strategy_module_name: str, num_cores: int = 32):
    """
    Universal optimizer - works with ANY strategy and ANY building blocks
    """
    
    print("="*80)
    print("UNIVERSAL STRATEGY OPTIMIZER")
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
    
    # Extract blocks from strategy file
    print(f"\n🔍 Extracting building blocks from strategy...")
    blocks = extract_blocks_from_strategy(strategy_module_name)
    
    if not blocks:
        print(f"⚠️  No blocks found in strategy file, using defaults...")
        # Fallback to pattern-based detection
        if 'm_pattern' in strategy_module_name.lower():
            blocks = {
                'double_top': {'name': 'DoubleTopPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'hod': {'name': 'HOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
            side = 'SHORT'
            strategy_id = "01_M_PATTERN_REVERSAL"
            strategy_name = "M Pattern Reversal"
        elif 'w_pattern' in strategy_module_name.lower():
            blocks = {
                'double_bottom': {'name': 'DoubleBottomPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'lod': {'name': 'LOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
            side = 'LONG'
            strategy_id = "02_W_PATTERN_REVERSAL"
            strategy_name = "W Pattern Reversal"
        else:
            print(f"❌ Cannot determine strategy type")
            return None
    else:
        # Determine side from blocks
        side = 'SHORT' if 'double_top' in blocks else 'LONG'
        strategy_id = strategy_module_name
        strategy_name = strategy_module_name.replace('_', ' ').title()
    
    print(f"✅ Found {len(blocks)} building blocks:")
    for block_name, block_info in blocks.items():
        block_meta = BUILDING_BLOCK_CATALOG.get(block_name, {})
        block_type = block_meta.get('type', 'UNKNOWN')
        print(f"   - {block_name:25s} [{block_type:7s}] weight={block_info['weight']}")
    
    print(f"\n📊 Strategy Details:")
    print(f"   ID: {strategy_id}")
    print(f"   Name: {strategy_name}")
    print(f"   Side: {side}")
    
    # Load data with warmup + test split
    print("\n📊 Loading BTC data...")
    warmup_df, test_df = load_btc_data(test_days=180, warmup_bars=5000)
    if warmup_df is None or test_df is None:
        print("❌ Failed to load data")
        return None
    
    print(f"✅ Loaded {len(warmup_df)} warmup bars + {len(test_df)} test bars")
    print(f"   Warmup: {warmup_df['timestamp'].min()} to {warmup_df['timestamp'].max()}")
    print(f"   Test:   {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    
    # Build parameter grid
    print("\n🔧 Building parameter grid...")
    
    param_grid = {
        'min_confluence': [40, 50, 60, 70],
        'min_risk_reward': [2.0, 2.5, 3.0]
    }
    
    # Generate weight presets
    block_keys = list(blocks.keys())
    weight_configs = get_weight_presets_for_blocks(block_keys)
    
    print(f"   Confluence values: {param_grid['min_confluence']}")
    print(f"   Risk:Reward ratios: {param_grid['min_risk_reward']}")
    print(f"   Weight presets: {len(weight_configs)}")
    
    # Generate test configs
    test_configs = []
    test_id = 0
    
    for conf, rr, weights in product(
        param_grid['min_confluence'],
        param_grid['min_risk_reward'],
        weight_configs
    ):
        blocks_with_weights = {}
        for block_name, block_info in blocks.items():
            blocks_with_weights[block_name] = {
                'name': block_info['name'],
                'weight': weights.get(block_name, block_info['weight']),
                'enabled': block_info['enabled']
            }
        
        test_configs.append({
            'warmup_df': warmup_df,
            'test_df': test_df,
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
    print(f"\n   Total combinations: {total_tests}")
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
    
    # Save results
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
            'config': {k: v for k, v in r['config'].items() if k != 'blocks'},
            'metrics': r['metrics']
        } for i, r in enumerate(successful_tests[:10])]
    }
    
    output_file = output_dir / f'{strategy_id}_universal_optimization_results.json'
    with open(output_file, 'w') as f:
        json.dump(optimization_report, f, indent=2)
    
    print(f"\n💾 Results saved: {output_file}")
    
    # Show best configuration
    print("\n" + "="*80)
    print("🏆 BEST CONFIGURATION FOUND")
    print("="*80)
    print(f"\nStrategy: {strategy_name}")
    print(f"Min Confluence: {best['config']['min_confluence']}")
    print(f"Min Risk:Reward: {best['config']['min_risk_reward']}")
    print(f"Trade Side: {best['config']['side']}")
    
    print(f"\nBlock Weights (Optimized):")
    for block_name, block_info in best['config']['blocks'].items():
        print(f"   {block_name:25s}: {block_info['weight']}")
    
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
    parser = argparse.ArgumentParser(description='Universal Strategy Optimizer - Works with ALL 80 building blocks')
    parser.add_argument('strategy', type=str, help='Strategy module name (e.g., strategy_01_reversal_m_pattern)')
    parser.add_argument('--cores', type=int, default=32, help='Number of CPU cores (default: 32)')
    
    args = parser.parse_args()
    
    # Run optimization
    best_config = optimize_strategy(args.strategy, num_cores=args.cores)
    
    if best_config:
        print("\n✅ Universal optimization complete!")
        sys.exit(0)
    else:
        print("\n❌ Optimization failed!")
        sys.exit(1)
        sys.exit(0)
