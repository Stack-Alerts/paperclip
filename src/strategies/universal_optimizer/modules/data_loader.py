"""
Data Loader

Loads BTC data with warmup period and provides strategy class loading.
"""

import pandas as pd
import importlib
import inspect
from pathlib import Path
from typing import Tuple


def load_btc_data(test_days: int = 180, warmup_bars: int = 5000) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load BTC 15min data with warmup period
    
    Args:
        test_days: Days to test on (walk-forward period)
        warmup_bars: Bars to warmup building blocks (default 5000)
    
    Returns:
        (warmup_df, test_df) tuple
    """
    # __file__ is in: src/strategies/universal_optimizer/modules/data_loader.py
    # parent = modules, parent.parent = universal_optimizer, 
    # parent.parent.parent = strategies, parent.parent.parent.parent = src
    # parent.parent.parent.parent.parent = PROJECT ROOT
    project_root = Path(__file__).parent.parent.parent.parent.parent
    data_path = project_root / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    if not data_path.exists():
        return None, None
    
    df = pd.read_csv(data_path)
    
    # Standardize columns
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
    
    # Calculate bars needed
    bars_per_day = 96  # 15min bars
    test_bars = test_days * bars_per_day
    total_bars_needed = warmup_bars + test_bars
    
    if len(df) < total_bars_needed:
        print(f"⚠️  Warning: Only {len(df)} bars available, need {total_bars_needed}")
        warmup_bars = min(warmup_bars, len(df) // 2)
        test_bars = len(df) - warmup_bars
    
    # Split into warmup and test
    warmup_df = df.iloc[-total_bars_needed:-test_bars].copy()
    test_df = df.iloc[-test_bars:].copy()
    
    # Clean
    warmup_df = warmup_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
    test_df = test_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
    
    return warmup_df, test_df


def get_strategy_class(strategy_module_name: str):
    """
    Dynamically import strategy class
    
    Args:
        strategy_module_name: Module name (e.g., 'strategy_01_reversal_m_pattern')
    
    Returns:
        Strategy class
    """
    try:
        module = importlib.import_module(f'src.strategies.{strategy_module_name}')
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and hasattr(obj, '_analyze_blocks'):
                return obj
        
        raise ValueError(f"No strategy class with _analyze_blocks found in {strategy_module_name}")
        
    except ImportError as e:
        raise ImportError(f"Failed to import {strategy_module_name}: {e}")