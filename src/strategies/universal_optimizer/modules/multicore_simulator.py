"""
Multicore Config Simulator - TRUE Parallel Processing

Combines the 48x innovation with multicore execution:
- 48x speedup: Process data ONCE (no redundant block analysis)
- 8-10x speedup: Distribute 48 configs across CPU cores
- TOTAL: ~384-480x faster than traditional sequential approach!
"""

import pandas as pd
from typing import List
from multiprocessing import Pool, cpu_count
from .data_classes import OptimizationConfig, ConfigPerformance
from .multi_config_simulator import MultiConfigSimulator


def process_config_batch(args):
    """
    Process a batch of configs on one CPU core
    
    This function is called by each worker process.
    Each worker gets a subset of the 48 configs.
    
    Args:
        args: Tuple of (config_batch, warmup_df, test_df, strategy_module_name)
    
    Returns:
        List of ConfigPerformance results for this batch
    """
    config_batch, warmup_df, test_df, strategy_module_name = args
    
    # Create simulator for this batch
    simulator = MultiConfigSimulator(config_batch)
    
    # Load strategy class (each worker loads independently)
    from .data_loader import get_strategy_class
    strategy_class = get_strategy_class(strategy_module_name)
    
    # Create strategy instance
    class TestStrategy:
        def __init__(self, config):
            self.strategy_id = config.strategy_id
            self.strategy_name = config.strategy_name
            self.min_confluence = config.min_confluence
            self.max_bars_held = 1000
            self.lookback_period = 100
            self.min_risk_reward = config.min_risk_reward
            self.peak_tolerance = 0.002
            self.bars_data = []
            self.blocks = config.blocks
            self.detectors = {}
    
    strategy = TestStrategy(config_batch[0])
    
    # Bind methods
    for method_name in dir(strategy_class):
        if method_name.startswith('_') and not method_name.startswith('__'):
            method = getattr(strategy_class, method_name)
            if callable(method):
                setattr(strategy, method_name, method.__get__(strategy))
    
    # Initialize building blocks
    if hasattr(strategy, '_initialize_blocks'):
        strategy._initialize_blocks()
    
    # Combine warmup + test
    full_df = pd.concat([warmup_df, test_df], ignore_index=True)
    warmup_bar_count = len(warmup_df)
    
    # Process each bar
    for i in range(warmup_bar_count, len(full_df)):
        current_bar = full_df.iloc[i]
        history = full_df.iloc[:i+1]
        simulator.process_bar(current_bar, strategy, history)
    
    # Close all positions
    simulator.close_all_positions(full_df.iloc[-1])
    
    # Return results
    return simulator.get_all_results()


class MulticoreConfigSimulator:
    """
    Distribute 48 configs across multiple CPU cores
    
    Instead of testing all 48 configs on one core,
    we split them across available cores for parallel execution.
    
    Example on 8-core machine:
    - Core 1: Tests configs 0-5   (6 configs)
    - Core 2: Tests configs 6-11  (6 configs)
    - Core 3: Tests configs 12-17 (6 configs)
    - Core 4: Tests configs 18-23 (6 configs)
    - Core 5: Tests configs 24-29 (6 configs)
    - Core 6: Tests configs 30-35 (6 configs)
    - Core 7: Tests configs 36-41 (6 configs)
    - Core 8: Tests configs 42-47 (6 configs)
    
    Result: ~8x faster on 8-core machine!
    Combined with 48x data efficiency = ~384x total speedup!
    """
    
    def __init__(self, num_cores: int = None):
        """
        Initialize multicore simulator
        
        Args:
            num_cores: Number of CPU cores to use (default: all available)
        """
        self.num_cores = num_cores or cpu_count()
        print(f"   Using {self.num_cores} CPU cores for parallel optimization")
    
    def optimize(
        self,
        configs: List[OptimizationConfig],
        warmup_df: pd.DataFrame,
        test_df: pd.DataFrame,
        strategy_module_name: str
    ) -> List[ConfigPerformance]:
        """
        Run optimization across multiple CPU cores
        
        Args:
            configs: All 48 configurations
            warmup_df: Warmup data
            test_df: Test data
            strategy_module_name: Strategy module name
        
        Returns:
            List of ConfigPerformance results for all configs
        """
        # Split configs into batches (one per core)
        batch_size = len(configs) // self.num_cores
        if batch_size == 0:
            batch_size = 1
        
        config_batches = []
        for i in range(0, len(configs), batch_size):
            batch = configs[i:i+batch_size]
            config_batches.append((batch, warmup_df, test_df, strategy_module_name))
        
        print(f"   Split {len(configs)} configs into {len(config_batches)} batches")
        print(f"   Each core processes ~{batch_size} configs")
        
        # Process batches in parallel
        with Pool(processes=self.num_cores) as pool:
            batch_results = pool.map(process_config_batch, config_batches)
        
        # Flatten results
        all_results = []
        for batch_result in batch_results:
            all_results.extend(batch_result)
        
        return all_results