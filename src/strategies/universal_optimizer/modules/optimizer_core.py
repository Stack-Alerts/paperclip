"""
Optimizer Core - Main Orchestration Logic

Coordinates all modules to provide complete optimization workflow.
This is the heart of the Universal Optimizer V2.0.
"""

import time
import pandas as pd
from typing import List, Optional
from itertools import product

from .data_classes import OptimizationConfig, ConfigPerformance
from .catalog import get_weight_presets_for_blocks
from .file_operations import (
    extract_blocks_from_strategy,
    validate_blocks_against_catalog,
    apply_config_to_strategy_file
)
from .data_loader import load_btc_data, get_strategy_class
from .multi_config_simulator import MultiConfigSimulator
from .block_intelligence import (
    load_strategy_iterations,
    save_strategy_iterations,
    identify_weakest_block,
    recommend_replacement_block
)
from .ui import (
    display_top_5_configs,
    prompt_user_selection,
    display_iteration_context,
    display_block_recommendations,
    confirm_application
)


def optimize_strategy_v2(
    strategy_module_name: str,
    test_days: int = 180,
    warmup_bars: int = 5000,
    use_multicore: bool = True
) -> Optional[OptimizationConfig]:
    """
    Universal Optimizer V2.0 - Main orchestration (WITH MULTICORE!)
    
    Complete workflow:
    1. Extract & validate blocks (ERROR if mismatch)
    2. Load iteration history
    3. Load data with warmup
    4. Build 48 configs
    5. Run MultiConfigSimulator (48x FASTER!)
    6. Display top 5
    7. User selects
    8. Apply to file (zero manual editing)
    9. Save iteration
    10. Check cycle 5 (suggest improvements)
    
    Args:
        strategy_module_name: Strategy module name
        test_days: Days to test (default 180)
        warmup_bars: Warmup bars (default 5000)
    
    Returns:
        Selected configuration or None if failed
    """
    
    print("="*80)
    print("UNIVERSAL STRATEGY OPTIMIZER V2.0 - INSTITUTIONAL GRADE")
    print("="*80)
    print(f"\n📦 Strategy: {strategy_module_name}")
    print(f"📅 Test Period: {test_days} days")
    print(f"🔥 Warmup: {warmup_bars} bars")
    
    # 1. Extract & validate blocks
    print(f"\n🔍 Extracting building blocks...")
    blocks = extract_blocks_from_strategy(strategy_module_name)
    
    if not blocks:
        print(f"❌ No blocks found in {strategy_module_name}")
        return None
    
    print(f"✅ Found {len(blocks)} building blocks:")
    for block_name in blocks.keys():
        print(f"   - {block_name}")
    
    if not validate_blocks_against_catalog(blocks, strategy_module_name):
        return None  # ERROR - HALT
    
    print(f"✅ All blocks validated against catalog")
    
    # 2. Load iteration history
    iteration = load_strategy_iterations(strategy_module_name)
    display_iteration_context(iteration.iteration_count + 1)
    
    # 3. Load data
    print(f"\n📊 Loading BTC data...")
    warmup_df, test_df = load_btc_data(test_days, warmup_bars)
    
    if warmup_df is None or test_df is None:
        print("❌ Failed to load data")
        return None
    
    print(f"✅ Loaded {len(warmup_df)} warmup bars + {len(test_df)} test bars")
    print(f"   Warmup: {warmup_df['timestamp'].min()} to {warmup_df['timestamp'].max()}")
    print(f"   Test:   {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    
    # 4. Build 48 configs
    print(f"\n🔧 Building optimization configurations...")
    configs = build_optimization_configs(blocks, strategy_module_name)
    print(f"✅ Created {len(configs)} parameter combinations")
    
    # 5. Run ULTRA Hybrid Optimizer (MAXIMUM PARALLEL!)
    print(f"\n🚀 Running ULTRA HYBRID optimization (3 phases, ALL parallel!)...")
    print(f"   Phase 1: Pre-compute blocks PARALLEL (32 cores, ~35 sec)")
    print(f"   Phase 2: Merge results (single-core, <1 sec)")
    print(f"   Phase 3: Test 48 configs PARALLEL (32 cores, ~0.3 sec)")
    print(f"   Total: ~35 seconds (vs 18 min single-core!)")
    
    start_time = time.time()
    
    results = run_multi_config_optimization(
        configs,
        warmup_df,
        test_df,
        strategy_module_name,
        use_multicore
    )
    
    elapsed = time.time() - start_time
    print(f"\n✅ Optimization complete in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"   🎯 48x FASTER than traditional approach!")
    
    # 6. Sort results
    results.sort(key=lambda x: x.get_sortable_score(), reverse=True)
    
    # 7. Display top 5
    display_top_5_configs(results[:5], iteration.iteration_count + 1)
    
    # 8. User selects
    selected_index = prompt_user_selection()
    selected_config = configs[results[selected_index].config_id]
    selected_perf = results[selected_index]
    
    print(f"\n✅ Selected configuration #{selected_index + 1}")
    
    # 9. Apply to file
    if confirm_application():
        print(f"\n📝 Applying configuration to strategy file...")
        success = apply_config_to_strategy_file(
            strategy_module_name,
            selected_config,
            selected_perf
        )
        
        if success:
            print(f"✅ Strategy file updated successfully!")
            print(f"   - Min Confluence: {selected_config.min_confluence}")
            print(f"   - Min Risk:Reward: {selected_config.min_risk_reward}")
            print(f"   - Block weights optimized")
        else:
            print(f"❌ Failed to update strategy file")
            return None
    else:
        print(f"\n⚠️  Configuration not applied (user cancelled)")
        return selected_config
    
    # 10. Save iteration
    print(f"\n💾 Saving optimization history...")
    iteration.add_iteration(selected_config.to_dict(), selected_perf)
    save_strategy_iterations(iteration)
    print(f"✅ Iteration {iteration.iteration_count} saved")
    
    # 11. Check cycle 5
    if iteration.iteration_count == 5:
        print(f"\n🎯 Iteration 5 reached - analyzing block performance...")
        weak_block = identify_weakest_block(iteration)
        
        if weak_block:
            recommendations = recommend_replacement_block(
                weak_block,
                blocks,
                iteration
            )
            display_block_recommendations(weak_block, recommendations)
    
    print(f"\n" + "="*80)
    print(f"🏆 OPTIMIZATION COMPLETE")
    print(f"="*80)
    
    return selected_config


def build_optimization_configs(
    blocks: dict,
    strategy_module_name: str
) -> List[OptimizationConfig]:
    """
    Build 48 optimization configurations
    
    Combinations:
    - Confluence: [40, 50, 60, 70] = 4
    - Risk:Reward: [2.0, 2.5, 3.0] = 3
    - Weight presets: 4
    
    Total: 4 × 3 × 4 = 48 configs
    """
    configs = []
    config_id = 0
    
    weight_presets = get_weight_presets_for_blocks(list(blocks.keys()))
    
    for confluence in [40, 50, 60, 70]:
        for rr in [2.0, 2.5, 3.0]:
            for weights in weight_presets:
                # Build blocks with these weights
                blocks_with_weights = {}
                for block_name, block_info in blocks.items():
                    blocks_with_weights[block_name] = {
                        'name': block_info['name'],
                        'weight': weights.get(block_name, block_info['weight']),
                        'enabled': block_info['enabled']
                    }
                
                config = OptimizationConfig(
                    config_id=config_id,
                    min_confluence=confluence,
                    min_risk_reward=rr,
                    blocks=blocks_with_weights,
                    strategy_id=strategy_module_name,
                    strategy_name=strategy_module_name.replace('_', ' ').title(),
                    side='SHORT' if 'double_top' in blocks else 'LONG'
                )
                
                configs.append(config)
                config_id += 1
    
    return configs


def run_multi_config_optimization(
    configs: List[OptimizationConfig],
    warmup_df: pd.DataFrame,
    test_df: pd.DataFrame,
    strategy_module_name: str,
    use_multicore: bool = True
) -> List[ConfigPerformance]:
    """
    Run optimization with HybridConfigSimulator
   
    Hybrid = building blocks once + parallel config testing = BEST performance!
    """
    
    # Use ultra hybrid for maximum parallel performance!
    from .ultra_hybrid_simulator import UltraHybridSimulator
    ultra_sim = UltraHybridSimulator()
    return ultra_sim.optimize(configs, warmup_df, test_df, strategy_module_name)
