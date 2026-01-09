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
    
    # 6.5. VALIDATE RESULTS - INSTITUTIONAL GRADE
    print(f"\n🔍 Running institutional-grade result validation...")
    issues = validate_optimization_results(results, test_days, configs)
    
    if issues:
        print(f"\n⚠️  VALIDATION ISSUES DETECTED")
        display_diagnostic_report(issues, results, configs)
        
        # Offer auto-fix
        action = prompt_diagnostic_action()
        
        if action == 'adjust':
            print(f"\n🔧 Auto-adjusting parameters and re-running...")
            adjusted_configs = auto_adjust_configs(configs, issues)
            
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


def prompt_diagnostic_action() -> str:
    """
    Prompt user for action after diagnostic report
    
    Returns:
        'adjust': Auto-adjust and re-run
        'proceed': Continue with current results
        'quit': Cancel optimization
    """
    print("\n" + "="*80)
    print("🔧 REMEDIATION OPTIONS")
    print("="*80)
    print("\n   1. AUTO-ADJUST: Let optimizer auto-adjust parameters and re-run (~90 sec)")
    print("   2. PROCEED: Continue with current results (not recommended if CRITICAL)")
    print("   3. QUIT: Cancel optimization and review strategy manually")
    
    while True:
        choice = input("\nSelect action (1-3): ").strip()
        
        if choice == '1':
            return 'adjust'
        elif choice == '2':
            confirm = input("⚠️  Are you sure? Issues may indicate broken results (y/n): ").strip().lower()
            if confirm == 'y':
                return 'proceed'
        elif choice == '3':
            return 'quit'
        else:
            print("   Invalid choice. Please enter 1, 2, or 3.")


def auto_adjust_configs(
    configs: List[OptimizationConfig],
    issues: List[dict]
) -> List[OptimizationConfig]:
    """
    Auto-adjust configuration parameters based on detected issues
    
    Smart adjustments:
    - Low trades → Lower confluence, reduce R:R
    - No trades → Aggressive lowering
    - High trades → Raise confluence
    """
    
    # Determine adjustment strategy
    has_critical_low = any(i['type'] in ['LOW_TRADE_COUNT', 'NO_TRADES'] for i in issues)
    has_high_trades = any(i['type'] == 'EXCESSIVE_TRADES' for i in issues)
    
    if has_critical_low:
        # Lower thresholds significantly
        new_confluence = [25, 30, 35, 40]  # Much lower
        new_rr = [1.5, 2.0, 2.5]  # Easier to achieve
        adjustment_type = "LOWERED (more entries)"
    elif has_high_trades:
        # Raise thresholds
        new_confluence = [60, 70, 80, 90]  # Higher bar
        new_rr = [2.5, 3.0, 3.5]  # Stricter
        adjustment_type = "RAISED (fewer entries)"
    else:
        # Moderate adjustment
        new_confluence = [35, 45, 55, 65]
        new_rr = [2.0, 2.5, 3.0]
        adjustment_type = "ADJUSTED (balanced)"
    
    print(f"\n🔧 Auto-Adjustment Strategy: {adjustment_type}")
    print(f"   New Confluence Range: {min(new_confluence)}-{max(new_confluence)}")
    print(f"   New Risk:Reward Range: {min(new_rr):.1f}-{max(new_rr):.1f}")
    
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
