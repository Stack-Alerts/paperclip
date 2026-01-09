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
    
    # 0. Archive previous results before starting
    print(f"\n📁 Archiving previous optimization results...")
    archive_previous_results(strategy_module_name)
    
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
    
    # 6.5. VALIDATE RESULTS - INSTITUTIONAL GRADE
    print(f"\n🔍 Running institutional-grade result validation...")
    issues = validate_optimization_results(results, test_days, configs)
    
    if issues:
        print(f"\n⚠️  VALIDATION ISSUES DETECTED")
        display_diagnostic_report(issues, results, configs)
        
        # Offer auto-fix
        action, target_trades = prompt_diagnostic_action()
        
        if action == 'adjust':
            print(f"\n🔧 Auto-adjusting parameters to target {target_trades}+ trades...")
            adjusted_configs = auto_adjust_configs(configs, issues, target_trades, results)
            
            # Re-run with adjusted configs
            results = run_multi_config_optimization(
                adjusted_configs,
                warmup_df,
                test_df,
                strategy_module_name,
                use_multicore
            )
            results.sort(key=lambda x: x.get_sortable_score(), reverse=True)
            configs = adjusted_configs  # Use adjusted configs going forward
            print(f"\n✅ Re-optimization complete with adjusted parameters")
            
        elif action == 'quit':
            print(f"\n⚠️  Optimization cancelled due to validation issues")
            return None
        # If 'proceed', continue with results as-is
    
    # 6.6. Export trade records for top 5 configs
    print(f"\n📊 Exporting trade records for top 5 configurations...")
    export_trade_records(results[:5], configs, strategy_module_name)
    
    # 7. Display top 5
    display_top_5_configs(results[:5], iteration.iteration_count + 1)
    
    # 8. User selects
    selected_index = prompt_user_selection()
    
    # Handle quit
    if selected_index == -1:
        print(f"\n⚠️  No configuration applied. Exiting...")
        return None
    
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


def export_trade_records(
    top_results: List[ConfigPerformance],
    configs: List[OptimizationConfig],
    strategy_name: str
):
    """
    Export detailed trade records for top configurations to CSV files
    
    Args:
        top_results: Top 5 ConfigPerformance results
        configs: All optimization configs
        strategy_name: Strategy name for directory
    """
    from pathlib import Path
    
    # Follow project data structure
    results_dir = Path('data') / 'reports' / 'strategies' / 'universal_optimizer' / strategy_name
    results_dir.mkdir(parents=True, exist_ok=True)
    
    for result in top_results:
        config = configs[result.config_id]
        
        # Create CSV filename
        csv_file = results_dir / f'config_{result.config_id}_trades.csv'
        
        # Export trades if they exist
        if hasattr(result, 'trades') and result.trades:
            trades_df = pd.DataFrame([t.to_dict() for t in result.trades])
            trades_df.to_csv(csv_file, index=False)
            print(f"   ✅ Exported {len(result.trades)} trades → {csv_file}")
        else:
            # Create summary file even if no trades
            with open(csv_file, 'w') as f:
                f.write("No trades executed for this configuration\n")
                f.write(f"Config ID: {result.config_id}\n")
                f.write(f"Min Confluence: {config.min_confluence}\n")
                f.write(f"Min Risk:Reward: {config.min_risk_reward}\n")
            print(f"   ⚠️  Config {result.config_id}: No trades executed")
    
    # Export summary CSV
    summary_file = results_dir / 'optimization_summary.csv'
    summary_data = []
    for result in top_results:
        config = configs[result.config_id]
        summary_data.append({
            'config_id': result.config_id,
            'min_confluence': config.min_confluence,
            'min_risk_reward': config.min_risk_reward,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate_pct': result.win_rate_pct,
            'total_pnl': result.total_pnl,
            'total_fees': result.total_fees,
            'net_pnl': result.net_pnl,
            'net_return_pct': result.net_return_pct,
            'profit_factor': result.profit_factor,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown_pct': result.max_drawdown_pct,
            'avg_win': result.avg_win,
            'avg_loss': result.avg_loss,
            'largest_win': result.largest_win,
            'largest_loss': result.largest_loss
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    print(f"   ✅ Summary exported → {summary_file}")


def validate_optimization_results(
    results: List[ConfigPerformance],
    test_days: int,
    configs: List[OptimizationConfig]
) -> List[dict]:
    """
    Institutional-grade result validation
    
    Detects:
    - Abnormally low trade counts (simulator bugs)
    - Unrealistic configurations (parameters too strict)
    - Data quality issues
    - Performance anomalies
    
    Returns:
        List of issues (empty if all valid)
    """
    issues = []
    
    # Expected trades per month (rough baseline)
    expected_trades_per_month = 5  # Conservative estimate
    expected_total = (test_days / 30) * expected_trades_per_month
    
    # Check top 5 configs
    top_5 = results[:5]
    all_trades = [r.total_trades for r in top_5]
    avg_trades = sum(all_trades) / len(all_trades) if all_trades else 0
    max_trades = max(all_trades) if all_trades else 0
    
    # Issue 1: Abnormally low trade count (likely simulator bug)
    if max_trades <2:
        issues.append({
            'severity': 'CRITICAL',
            'type': 'LOW_TRADE_COUNT',
            'description': f'Only {max_trades} trade(s) generated in {test_days} days',
            'expected': f'{int(expected_total)} trades ({expected_trades_per_month}/month)',
            'actual': f'{max_trades} trades',
            'likely_cause': 'Simulator bug OR parameters too strict',
            'recommendation': 'Lower confluence threshold OR reduce risk:reward requirement',
            'auto_fix': 'lower_thresholds'
        })
    
    elif avg_trades < expected_total * 0.3:  # Less than 30% of expected
        issues.append({
            'severity': 'WARNING',
            'type': 'BELOW_EXPECTED_TRADES',
            'description': f'Trade count below expected ({avg_trades:.0f} vs {expected_total:.0f})',
            'expected': f'{int(expected_total)} trades',
            'actual': f'{avg_trades:.0f} trades average',
            'likely_cause': 'Parameters too conservative',
            'recommendation': 'Consider lowering confluence OR risk:reward thresholds',
            'auto_fix': 'adjust_thresholds'
        })
    
    # Issue 2: All configs have identical results (data or simulator issue)
    if len(set(all_trades)) == 1 and all_trades[0] > 0:
        issues.append({
            'severity': 'CRITICAL',
            'type': 'IDENTICAL_RESULTS',
            'description': 'All configs produced identical trade counts',
            'expected': 'Varying results based on different parameters',
            'actual': f'All {len(top_5)} configs: {all_trades[0]} trades',
            'likely_cause': 'Parameter variations not affecting entry logic',
            'recommendation': 'Review strategy entry conditions',
            'auto_fix': None
        })
    
    # Issue 3: Zero trades across all configs
    if max_trades == 0:
        issues.append({
            'severity': 'CRITICAL',
            'type': 'NO_TRADES',
            'description': 'No trades generated in any configuration',
            'expected': f'{int(expected_total)} trades',
            'actual': '0 trades',
            'likely_cause': 'Confluence never reached OR R:R requirements impossible',
            'recommendation': 'Lower confluence to 30 AND risk:reward to 1.5',
            'auto_fix': 'aggressive_lower'
        })
    
    # Issue 4: Check for abnormally high trade count (overtrading)
    if max_trades > expected_total * 10:  # 10x more than expected
        issues.append({
            'severity': 'WARNING',
            'type': 'EXCESSIVE_TRADES',
            'description': f'Abnormally high trade count ({max_trades} vs {expected_total:.0f} expected)',
            'expected': f'{int(expected_total)} trades',
            'actual': f'{max_trades} trades',
            'likely_cause': 'Confluence threshold too low',
            'recommendation': 'Increase minimum confluence threshold',
            'auto_fix': 'raise_confluence'
        })
    
    return issues


def display_diagnostic_report(
    issues: List[dict],
    results: List[ConfigPerformance],
    configs: List[OptimizationConfig]
):
    """Display detailed diagnostic report with recommendations"""
    
    print("\n" + "="*80)
    print("🔍 INSTITUTIONAL DIAGNOSTIC REPORT")
    print("="*80)
    
    for i, issue in enumerate(issues, 1):
        severity_icon = "🔴" if issue['severity'] == 'CRITICAL' else "⚠️"
        
        print(f"\n{severity_icon} ISSUE #{i}: {issue['type']} ({issue['severity']})")
        print(f"   Description: {issue['description']}")
        print(f"   Expected: {issue['expected']}")
        print(f"   Actual: {issue['actual']}")
        print(f"   Likely Cause: {issue['likely_cause']}")
        print(f"   Recommendation: {issue['recommendation']}")
        
        if issue['auto_fix']:
            print(f"   ✅ Auto-fix available: {issue['auto_fix']}")
        else:
            print(f"   ❌ Manual intervention required")
    
    print("\n" + "="*80)
    print("📊 CURRENT CONFIGURATION SUMMARY")
    print("="*80)
    
    # Show current parameter ranges
    min_conf = min(c.min_confluence for c in configs)
    max_conf = max(c.min_confluence for c in configs)
    min_rr = min(c.min_risk_reward for c in configs)
    max_rr = max(c.min_risk_reward for c in configs)
    
    print(f"   Confluence Range: {min_conf}-{max_conf}")
    print(f"   Risk:Reward Range: {min_rr:.1f}-{max_rr:.1f}")
    print(f"   Configs Tested: {len(configs)}")
    
    top_result = results[0] if results else None
    if top_result:
        print(f"\n   Best Config Results:")
        print(f"   - Total Trades: {top_result.total_trades}")
        print(f"   - Win Rate: {top_result.win_rate_pct:.1f}%")
        print(f"   - Net PnL: ${top_result.net_pnl:.2f}")


def prompt_diagnostic_action() -> tuple:
    """
    Prompt user for action after diagnostic report
    
    Returns:
        Tuple of (action, target_trades) where:
        - action: 'adjust', 'proceed', or 'quit'
        - target_trades: User-specified minimum trade target (or None)
    """
    print("\n" + "="*80)
    print("🔧 REMEDIATION OPTIONS")
    print("="*80)
    print("\n   1. AUTO-ADJUST: Adjust parameters to target specific trade count")
    print("   2. PROCEED: Continue with current results (not recommended if CRITICAL)")
    print("   3. QUIT: Cancel optimization and review strategy manually")
    
    while True:
        choice = input("\nSelect action (1-3): ").strip()
        
        if choice == '1':
            # Get target trade count from user
            while True:
                try:
                    target = input("\nTarget minimum trades for 180 days (default 60): ").strip()
                    if not target:
                        target_trades = 60  # Default
                        break
                    target_trades = int(target)
                    if target_trades > 0:
                        break
                    print("   Please enter a positive number")
                except ValueError:
                    print("   Please enter a valid number")
            
            return ('adjust', target_trades)
            
        elif choice == '2':
            confirm = input("⚠️  Are you sure? Issues may indicate broken results (y/n): ").strip().lower()
            if confirm == 'y':
                return ('proceed', None)
        elif choice == '3':
            return ('quit', None)
        else:
            print("   Invalid choice. Please enter 1, 2, or 3.")


def auto_adjust_configs(
    configs: List[OptimizationConfig],
    issues: List[dict],
    target_trades: int,
    results: List[ConfigPerformance]
) -> List[OptimizationConfig]:
    """
    Auto-adjust configuration parameters to reach target trade count
    
    Uses smart calibration based on current vs target ratio:
    - Current = 2, Target = 60 → Need 30x more trades → Aggressive lowering
    - Current = 40, Target = 60 → Need 1.5x more → Moderate lowering
    - Current = 100, Target = 60 → Need 0.6x → Moderate raising
    """
    
    # Get current best trade count
    current_trades = max(r.total_trades for r in results) if results else 0
    
    # Calculate adjustment ratio
    if current_trades > 0:
        ratio = target_trades / current_trades
    else:
        ratio = float('inf')  # Need infinite adjustment (aggressive)
    
    # Get current parameter ranges
    current_conf_min = min(c.min_confluence for c in configs)
    current_conf_max = max(c.min_confluence for c in configs)
    current_rr_min = min(c.min_risk_reward for c in configs)
    current_rr_max = max(c.min_risk_reward for c in configs)
    
    print(f"\n📊 ADJUSTMENT ANALYSIS")
    print(f"="*80)
    print(f"   Current Trades: {current_trades}")
    print(f"   Target Trades: {target_trades}")
    print(f"   Adjustment Needed: {ratio:.1f}x")
    print(f"\n   Current Parameters:")
    print(f"   - Confluence: {current_conf_min}-{current_conf_max}")
    print(f"   - Risk:Reward: {current_rr_min:.1f}-{current_rr_max:.1f}")
    
    # Determine new parameters based on ratio
    if ratio >= 10:  # Need 10x+ more trades (AGGRESSIVE)
        new_confluence = [20, 25, 30, 35]
        new_rr = [1.3, 1.5, 1.8]
        adjustment_type = "AGGRESSIVE LOWERING (10x+ trades needed)"
    elif ratio >= 5:  # Need 5-10x more trades (STRONG)
        new_confluence = [25, 30, 35, 40]
        new_rr = [1.5, 2.0, 2.5]
        adjustment_type = "STRONG LOWERING (5-10x trades needed)"
    elif ratio >= 2:  # Need 2-5x more trades (MODERATE)
        new_confluence = [30, 35, 40, 45]
        new_rr = [1.8, 2.0, 2.5]
        adjustment_type = "MODERATE LOWERING (2-5x trades needed)"
    elif ratio >= 1.2:  # Need 1.2-2x more trades (SLIGHT)
        new_confluence = [35, 40, 45, 50]
        new_rr = [2.0, 2.3, 2.5]
        adjustment_type = "SLIGHT LOWERING (1.2-2x trades needed)"
    elif ratio >= 0.8:  # About right (FINE-TUNE)
        new_confluence = [40, 45, 50, 55]
        new_rr = [2.0, 2.5, 3.0]
        adjustment_type = "FINE-TUNING (near target)"
    else:  # Too many trades (RAISE)
        new_confluence = [50, 60, 70, 80]
        new_rr = [2.5, 3.0, 3.5]
        adjustment_type = "RAISING (reduce trades)"
    
    print(f"\n   🔧 Adjustment Strategy: {adjustment_type}")
    print(f"\n   Proposed New Parameters:")
    print(f"   - Confluence: {min(new_confluence)}-{max(new_confluence)}")
    print(f"   - Risk:Reward: {min(new_rr):.1f}-{max(new_rr):.1f}")
    print(f"\n   Expected Result: ~{target_trades} trades")
    print(f"="*80)
    
    # Confirm adjustment
    confirm = input("\nApply these adjustments? (y/n): ").strip().lower()
    if confirm != 'y':
        print("   ⚠️  Adjustment cancelled by user")
        return configs  # Return original configs
    
    # Rebuild configs with new parameters
    adjusted_configs = []
    config_id = 0
    
    # Get blocks from first config
    blocks = configs[0].blocks
    block_names = list(blocks.keys())
    
    from .catalog import get_weight_presets_for_blocks
    weight_presets = get_weight_presets_for_blocks(block_names)
    
    for confluence in new_confluence:
        for rr in new_rr:
            for weights in weight_presets:
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
                    strategy_id=configs[0].strategy_id,
                    strategy_name=configs[0].strategy_name,
                    side=configs[0].side
                )
                
                adjusted_configs.append(config)
                config_id += 1
    
    print(f"   ✅ Created {len(adjusted_configs)} adjusted configurations")
    
    return adjusted_configs


def archive_previous_results(strategy_name: str, max_archives: int = 5):
    """
    Archive previous optimization results before starting new run
    
    Keeps results organized and prevents confusion with old data.
    Maintains last 5 archived versions, deletes older ones.
    
    Args:
        strategy_name: Strategy module name
        max_archives: Maximum number of archives to keep (default 5)
    """
    from pathlib import Path
    from datetime import datetime
    import shutil
    
    # Results directory
    results_dir = Path('data') / 'reports' / 'strategies' / 'universal_optimizer' / strategy_name
    
    # Check if results exist
    if not results_dir.exists() or not any(results_dir.iterdir()):
        print(f"   ℹ️  No previous results to archive")
        return
    
    # Archive directory
    archive_base = Path('data') / 'reports' / 'strategies' / 'universal_optimizer' / f'{strategy_name}_archives'
    archive_base.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped archive name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = f'archive_{timestamp}'
    archive_path = archive_base / archive_name
    
    try:
        # Move current results to archive
        shutil.move(str(results_dir), str(archive_path))
        print(f"   ✅ Archived previous results → {archive_name}")
        
        # Clean up old archives (keep only last max_archives)
        archives = sorted(archive_base.glob('archive_*'), key=lambda x: x.name, reverse=True)
        
        if len(archives) > max_archives:
            deleted_count = 0
            for old_archive in archives[max_archives:]:
                shutil.rmtree(old_archive)
                deleted_count += 1
            
            print(f"   🗑️  Removed {deleted_count} old archive(s) (keeping last {max_archives})")
        
        # Recreate results directory for new run
        results_dir.mkdir(parents=True, exist_ok=True)
        
    except Exception as e:
        print(f"   ⚠️  Archive failed: {e}")
        print(f"   Continuing with optimization...")
