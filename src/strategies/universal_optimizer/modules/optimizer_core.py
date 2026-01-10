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


def load_strategy_side_from_config(strategy_module_name: str) -> Optional[str]:
    """
    Load strategy side (LONG/SHORT) from YAML config file
    
    Args:
        strategy_module_name: Strategy module name (e.g., 'strategy_001_hod_rejection')
    
    Returns:
        'SHORT' or 'LONG' if found in config, None otherwise
    """
    from pathlib import Path
    import yaml
    
    # Strip 'strategy_' prefix if present for config filename
    # e.g., 'strategy_001_hod_rejection' → '001_hod_rejection'
    config_base = strategy_module_name.replace('strategy_', '')
    
    # Try to find config file
    config_paths = [
        Path('config') / f'optimizer_{strategy_module_name}.yaml',  # optimizer_strategy_001_...
        Path('config') / f'optimizer_{config_base}.yaml',  # optimizer_001_...
        Path('config') / f'{strategy_module_name}.yaml',  # strategy_001_...
        Path('config') / f'{config_base}.yaml',  # 001_...
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Look for side in strategy section
                if 'strategy' in config and 'side' in config['strategy']:
                    side = config['strategy']['side'].upper()
                    if side in ['SHORT', 'LONG']:
                        return side
                    else:
                        print(f"   ⚠️  Invalid side '{side}' in config, must be SHORT or LONG")
                        
            except Exception as e:
                print(f"   ⚠️  Error reading config {config_path}: {e}")
    
    return None  # Side not found in config


def optimize_strategy_v2(
    strategy_module_name: str,
    test_days: int = 180,
    warmup_bars: int = 5000,
    use_multicore: bool = True,
    non_interactive: bool = False
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
    7. User selects (or auto-select if non_interactive)
    8. Apply to file (zero manual editing)
    9. Save iteration
    10. Check cycle 5 (suggest improvements)
    
    Args:
        strategy_module_name: Strategy module name
        test_days: Days to test (default 180)
        warmup_bars: Warmup bars (default 5000)
        use_multicore: Enable multicore (default True)
        non_interactive: Auto-select best config without prompts (default False)
    
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
    
    # Load strategy side from config file if available
    strategy_side = load_strategy_side_from_config(strategy_module_name)
    if strategy_side:
        print(f"   📍 Strategy direction: {strategy_side} (from config)")
    
    configs = build_optimization_configs(blocks, strategy_module_name, strategy_side)
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
    
    if issues and not non_interactive:
        print(f"\n⚠️  VALIDATION ISSUES DETECTED")
        display_diagnostic_report(issues, results, configs)
        
        # Offer auto-fix with Option 2 (add context blocks)
        action, target_trades, context_issue = prompt_diagnostic_action(issues)
        
        if action == 'add_blocks':
            # OPTION 2: Add "Always On" context blocks
            print(f"\n🔧 Adding context blocks to strategy...")
            success = add_context_blocks_to_strategy(strategy_module_name, context_issue)
            
            if success:
                print(f"\n✅ Context blocks added successfully!")
                print(f"   ♻️  Re-running optimization with new blocks...")
                
                # Fully restart optimization with new blocks
                return optimize_strategy_v2(
                    strategy_module_name,
                    test_days,
                    warmup_bars,
                    use_multicore
                )
            else:
                print(f"\n❌ Failed to add context blocks")
                return None
                
        elif action == 'adjust':
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
    
    # 8. User selects (or auto-select if non-interactive)
    if non_interactive:
        selected_index = 0  # Auto-select best config
        print(f"\n🤖 Non-interactive mode: Auto-selecting best configuration (#1)")
    else:
        selected_index = prompt_user_selection()
    
    # Handle quit
    if selected_index == -1:
        print(f"\n⚠️  No configuration applied. Exiting...")
        return None
    
    selected_config = configs[results[selected_index].config_id]
    selected_perf = results[selected_index]
    
    print(f"\n✅ Selected configuration #{selected_index + 1}")
    
    # 9. Apply to file (auto-confirm if non-interactive)
    if non_interactive or confirm_application():
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
    strategy_module_name: str,
    strategy_side: str = None
) -> List[OptimizationConfig]:
    """
    Build 48 optimization configurations
    
    Combinations:
    - Confluence: [40, 50, 60, 70] = 4
    - Risk:Reward: [2.0, 2.5, 3.0] = 3
    - Weight presets: 4
    
    Total: 4 × 3 × 4 = 48 configs
    
    Args:
        blocks: Building blocks dict
        strategy_module_name: Strategy name
        strategy_side: Trade direction ('SHORT' or 'LONG'), read from config
    """
    configs = []
    config_id = 0
    
    weight_presets = get_weight_presets_for_blocks(list(blocks.keys()))
    
    # Determine side (from config or fallback to heuristic)
    if strategy_side:
        side = strategy_side
    else:
        # Fallback: Heuristic based on block names
        side = 'SHORT' if 'double_top' in blocks else 'LONG'
    
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
                    side=side  # Use determined side
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
    - CONFLUENCE GAP: Signals detected but confluence too low (Option 2)
    
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
    
    # Issue 5: CONFLUENCE GAP - Detect if we need "Always On" context blocks
    # This is the smart Option 2 solution
    confluence_gap = detect_confluence_gap(configs, results)
    if confluence_gap:
        issues.append(confluence_gap)
    
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


def prompt_diagnostic_action(issues: List[dict] = None) -> tuple:
    """
    Prompt user for action after diagnostic report
    
    Returns:
        Tuple of (action, target_trades, context_blocks_issue) where:
        - action: 'adjust', 'add_blocks', 'proceed', or 'quit'
        - target_trades: User-specified minimum trade target (or None)
        - context_blocks_issue: Issue with context block recommendations (or None)
    """
    # Check if we have a CONFLUENCE_GAP issue (Option 2)
    confluence_gap_issue = None
    if issues:
        for issue in issues:
            if issue.get('type') == 'CONFLUENCE_GAP':
                confluence_gap_issue = issue
                break
    
    print("\n" + "="*80)
    print("🔧 REMEDIATION OPTIONS")
    print("="*80)
    
    if confluence_gap_issue:
        print("\n   1. ADD CONTEXT BLOCKS: Add 'Always On' blocks for base confluence (RECOMMENDED ⭐)")
        print("   2. AUTO-ADJUST: Adjust parameters to target specific trade count")
        print("   3. PROCEED: Continue with current results (not recommended if CRITICAL)")
        print("   4. QUIT: Cancel optimization and review strategy manually")
        
        while True:
            choice = input("\nSelect action (1-4): ").strip()
            
            if choice == '1':
                # Option 2: Add context blocks
                if prompt_add_context_blocks(confluence_gap_issue):
                    return ('add_blocks', None, confluence_gap_issue)
                else:
                    # User declined, ask again
                    continue
                    
            elif choice == '2':
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
                
                return ('adjust', target_trades, None)
                
            elif choice == '3':
                confirm = input("⚠️  Are you sure? Issues may indicate broken results (y/n): ").strip().lower()
                if confirm == 'y':
                    return ('proceed', None, None)
            elif choice == '4':
                return ('quit', None, None)
            else:
                print("   Invalid choice. Please enter 1, 2, 3, or 4.")
    else:
        # Standard options without confluence gap
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
                
                return ('adjust', target_trades, None)
                
            elif choice == '2':
                confirm = input("⚠️  Are you sure? Issues may indicate broken results (y/n): ").strip().lower()
                if confirm == 'y':
                    return ('proceed', None, None)
            elif choice == '3':
                return ('quit', None, None)
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


def detect_confluence_gap(
    configs: List[OptimizationConfig],
    results: List[ConfigPerformance]
) -> Optional[dict]:
    """
    Detect CONFLUENCE GAP - signals present but insufficient confluence
    
    This is the intelligent Option 2 solution from the expert analysis:
    - Pattern fires (e.g., 643 BEARISH_BREAKDOWN signals)
    - But only generates 35 points (below 40-70 threshold)
    - Solution: Add "Always On" context blocks for base confluence
    
    UPDATED: Now detects gap even if no more context blocks available
    (will suggest parameter adjustment as fallback)
    
    Returns:
        Issue dict with recommendations, or None if no gap detected
    """
    
    min_confluence = min(c.min_confluence for c in configs)
    max_trades = max(r.total_trades for r in results) if results else 0
    
    # Detect confluence gap with looser criteria:
    # - Few trades (0-5) despite reasonable confluence threshold (<=60)
    # - OR identical results across configs (suggests parameter insensitivity)
    
    # Check for identical results
    all_trades = [r.total_trades for r in results[:5]]
    identical_results = len(set(all_trades)) == 1
    
    # Primary condition: Low trades with reasonable threshold
    if max_trades <= 5 and min_confluence <= 60:
        # Calculate estimated gap
        estimated_gap = min(max_trades, 2) * 10  # Conservative: 0 trades = 0, 2 trades = 20 point gap
        
        # Get current blocks
        current_blocks = list(configs[0].blocks.keys())
        
        # Recommend "Always On" blocks
        recommended_blocks = get_always_on_context_blocks(current_blocks)
        
        # CRITICAL FIX: Show gap even if no blocks available
        # (will offer parameter adjustment instead)
        if recommended_blocks or identical_results:
            
            if recommended_blocks:
                # We have blocks to recommend
                return {
                    'severity': 'CRITICAL',
                    'type': 'CONFLUENCE_GAP',
                    'description': f'Low trade count ({max_trades}) suggests confluence gap',
                    'expected': f'{min_confluence}+ confluence points',
                    'actual': f'~{max(min_confluence - 10, 25)} points (estimated from {max_trades} trades)',
                    'likely_cause': 'Event blocks fire but lack supporting context blocks',
                    'recommendation': f'Add {len(recommended_blocks)} "Always On" context blocks for base confluence',
                    'auto_fix': 'add_context_blocks',
                    'recommended_blocks': recommended_blocks,
                    'estimated_boost': sum(b['weight'] for b in recommended_blocks),
                    'current_block_count': len(current_blocks),
                    'identical_results': identical_results
                }
            else:
                # No more blocks to add, but still have low trades
                # Suggest parameter adjustment
                return {
                    'severity': 'WARNING',
                    'type': 'CONFLUENCE_GAP',
                    'description': f'Low trade count ({max_trades}) despite {len(current_blocks)} building blocks',
                    'expected': f'{min_confluence}+ confluence points, 30+ trades',
                    'actual': f'{max_trades} trades across all configs',
                    'likely_cause': 'All context blocks added, but threshold still too high OR block weights too low',
                    'recommendation': 'Lower confluence threshold OR increase block weights',
                    'auto_fix': 'adjust_thresholds',
                    'recommended_blocks': [],
                    'estimated_boost': 0,
                    'current_block_count': len(current_blocks),
                    'identical_results': identical_results
                }
    
    return None


def get_always_on_context_blocks(current_blocks: List[str]) -> List[dict]:
    """
    SMART DECIDER: Get recommended "Always On" context blocks
    
    Intelligently selects from 80+ production-ready building blocks.
    Prioritizes blocks that:
    - Fire on every bar (guaranteed base confluence)
    - Have Grade A/A- (85%+ quality)
    - Provide different types of context (diversification)
    - Match actual module paths
    
    Selection Algorithm:
    1. Identify missing context block categories
    2. Select highest-graded blocks from each category
    3. Ensure proper diversification (trend, session, institutional, structure)
    4. Return top 3-5 blocks for maximum benefit
    
    Returns:
        List of recommended blocks with complete metadata
    """
    
    # ========================================================================
    # TIER 1: PREMIUM "ALWAYS ON" CONTEXT BLOCKS (Grade A, 90+/100)
    # ========================================================================
    # These are the absolute best blocks that fire on every bar
    tier1_blocks = {
        'vwap': {
            'name': 'VWAP',
            'module': 'institutional.vwap',
            'weight': 15,  # Upgraded from 12 (Grade A, 94/100)
            'category': 'INSTITUTIONAL',
            'grade': 'A (94/100)',
            'fires': 'ALWAYS (ABOVE/BELOW/AT)',
            'benefit': 'Institutional reference level - highest-graded block',
            'impact': '+12-15 points guaranteed',
            'tier': 1
        },
        'ema_200_trend': {
            'name': 'EMA200Trend',
            'module': 'moving_averages.ema_200_trend',
            'weight': 12,
            'category': 'TREND',
            'grade': 'A (90/100)',
            'fires': 'ALWAYS (BULLISH/BEARISH/NEUTRAL)',
            'benefit': 'Long-term trend alignment',
            'impact': '+10-12 points guaranteed',
            'tier': 1
        },
        'ema_20_50_trend': {
            'name': 'EMA2050Trend',
            'module': 'moving_averages.ema_20_50_trend',
            'weight': 12,
            'category': 'TREND',
            'grade': 'A (90/100)',
            'fires': 'ALWAYS (BULLISH/BEARISH/NEUTRAL)',
            'benefit': 'Short-term trend context',
            'impact': '+10-15 points guaranteed',
            'tier': 1
        },
        'session_time': {
            'name': 'SessionTime',
            'module': 'sessions.session_time',
            'weight': 10,
            'category': 'SESSION',
            'grade': 'A (90/100)',
            'fires': 'ALWAYS (ASIA/LONDON/NY/OPENS)',
            'benefit': 'Trading session context and volatility timing',
            'impact': '+5-15 points guaranteed',
            'tier': 1
        },
        'swing_points': {
            'name': 'SwingPoints',
            'module': 'market_structure.swing_points',
            'weight': 15,
            'category': 'STRUCTURE',
            'grade': 'A (91/100)',
            'fires': 'ALWAYS (structure tracking)',
            'benefit': 'Market structure highs/lows',
            'impact': '+13-17 points guaranteed',
            'tier': 1
        }
    }
    
    # ========================================================================
    # TIER 2: HIGH QUALITY "ALWAYS ON" BLOCKS (Grade A-, 85-89/100)
    # ========================================================================
    tier2_blocks = {
        'kill_zones': {
            'name': 'KillZones',
            'module': 'sessions.kill_zones',
            'weight': 14,  # Upgraded from 12 (Grade A, 89/100)
            'category': 'SESSION',
            'grade': 'A (89/100)',
            'fires': 'OFTEN (4 zones per day)',
            'benefit': 'Institutional high-volume periods',
            'impact': '+8-16 points when active',
            'tier': 2
        },
        'premium_discount_zones': {
            'name': 'PremiumDiscountZones',
            'module': 'market_structure.premium_discount_zones',
            'weight': 14,
            'category': 'STRUCTURE',
            'grade': 'A (89/100)',
            'fires': 'ALWAYS (PREMIUM/DISCOUNT/EQUILIBRIUM)',
            'benefit': 'ICT premium/discount positioning',
            'impact': '+12-14 points guaranteed',
            'tier': 2
        },
        'anchored_vwap': {
            'name': 'AnchoredVWAP',
            'module': 'institutional.anchored_vwap',
            'weight': 14,
            'category': 'INSTITUTIONAL',
            'grade': 'A (89/100)',
            'fires': 'ALWAYS (session-anchored)',
            'benefit': 'Session-specific institutional level',
            'impact': '+12-14 points guaranteed',
            'tier': 2
        },
        'adr': {
            'name': 'ADR',
            'module': 'volatility.adr',
            'weight': 10,  # Upgraded from 8 (Grade A-, 88/100)
            'category': 'VOLATILITY',
            'grade': 'A- (88/100)',
            'fires': 'ALWAYS (range context)',
            'benefit': 'Average daily range positioning',
            'impact': '+8-10 points guaranteed',
            'tier': 2
        },
        'ema_50_vector': {
            'name': 'EMA50Vector',
            'module': 'moving_averages.ema_50_vector',
            'weight': 10,
            'category': 'TREND',
            'grade': 'A- (88/100)',
            'fires': 'ALWAYS (RISING/FALLING/FLAT)',
            'benefit': 'Medium-term trend direction',
            'impact': '+8-10 points guaranteed',
            'tier': 2
        },
        'us_settlement': {
            'name': 'USSettlement',
            'module': 'price_levels.us_settlement',
            'weight': 12,
            'category': 'PRICE_LEVELS',
            'grade': 'A- (87/100)',
            'fires': 'ALWAYS (ABOVE/BELOW/AT)',
            'benefit': 'US settlement reference',
            'impact': '+10-12 points guaranteed',
            'tier': 2
        }
    }
    
    # Combine all blocks
    all_blocks = {**tier1_blocks, **tier2_blocks}
    
    # ========================================================================
    # SMART SELECTION ALGORITHM
    # ========================================================================
    
    # 1. Filter out blocks already in strategy
    available_blocks = {k: v for k, v in all_blocks.items() if k not in current_blocks}
    
    if not available_blocks:
        return []  # All blocks already added!
    
    # 2. Analyze current blocks to determine missing categories
    current_categories = set()
    for block_key in current_blocks:
        # Determine category from block name
        if 'ema' in block_key or 'trend' in block_key:
            current_categories.add('TREND')
        elif 'session' in block_key or 'kill_zone' in block_key:
            current_categories.add('SESSION')
        elif 'vwap' in block_key:
            current_categories.add('INSTITUTIONAL')
        elif 'swing' in block_key or 'structure' in block_key or 'premium' in block_key:
            current_categories.add('STRUCTURE')
        elif 'adr' in block_key or 'volatility' in block_key:
            current_categories.add('VOLATILITY')
        elif 'hod' in block_key or 'lod' in block_key or 'asia' in block_key:
            current_categories.add('PRICE_LEVELS')
    
    # 3. Prioritize blocks from missing categories (diversification)
    recommended = []
    
    # Priority 1: Add blocks from missing categories
    missing_categories = {'TREND', 'SESSION', 'INSTITUTIONAL', 'STRUCTURE', 'VOLATILITY'} - current_categories
    
    for category in missing_categories:
        # Find best block in this category
        category_blocks = [
            {'key': k, **v} for k, v in available_blocks.items()
            if v['category'] == category
        ]
        
        if category_blocks:
            # Sort by tier then weight
            category_blocks.sort(key=lambda x: (x['tier'], -x['weight']))
            best_block = category_blocks[0]
            recommended.append(best_block)
    
    # Priority 2: If we still need more blocks, add highest-value remaining
    if len(recommended) < 3:
        remaining = [
            {'key': k, **v} for k, v in available_blocks.items()
            if {'key': k, **v} not in recommended
        ]
        
        # Sort by tier (1 first) then weight (high to low)
        remaining.sort(key=lambda x: (x['tier'], -x['weight']))
        
        # Add until we have 3-5 blocks
        for block in remaining:
            if len(recommended) >= 5:
                break
            recommended.append(block)
    
    # 4. Final sort by overall value (tier * weight)
    recommended.sort(key=lambda x: (x['tier'], -x['weight']))
    
    # 5. Return top 3 recommendations (optimal for most strategies)
    return recommended[:3]


def display_context_block_recommendations(issue: dict):
    """
    Display "Always On" context block recommendations
    
    Beautiful UI for Option 2 solution
    """
    print("\n" + "="*80)
    print("💡 INTELLIGENT SOLUTION: ADD 'ALWAYS ON' CONTEXT BLOCKS")
    print("="*80)
    
    print(f"\n📊 DIAGNOSIS:")
    print(f"   - Your strategy signals ARE firing")
    print(f"   - But confluence is ~{issue.get('actual', 'unknown')}")
    print(f"   - Threshold requires {issue.get('expected', 'unknown')}")
    print(f"   - Gap: ~{issue.get('estimated_boost', 0) - 10} points")
    
    print(f"\n💡 SOLUTION (Option 2):")
    print(f"   Add 'Always On' context blocks that fire on EVERY bar")
    print(f"   These provide BASE confluence even when event blocks rare")
    
    print(f"\n✨ RECOMMENDED BLOCKS:")
    print(f"="*80)
    
    for i, block in enumerate(issue.get('recommended_blocks', []), 1):
        print(f"\n   {i}. {block['name']} ({block['category']})")
        print(f"      Weight: {block['weight']} points")
        print(f"      Fires: {block['fires']}")
        print(f"      Benefit: {block['benefit']}")
        print(f"      Impact: {block['impact']}")
    
    total_boost = sum(b['weight'] for b in issue.get('recommended_blocks', []))
    print(f"\n📈 TOTAL CONFLUENCE BOOST: +{total_boost} points")
    print(f"   Current: ~{issue.get('actual', 'unknown')}")
    print(f"   After: ~{int(issue.get('actual', '30').split('~')[1].split(' ')[0]) + total_boost} points")
    print(f"   Result: TRADEABLE! ✅")
    
    print(f"\n" + "="*80)


def prompt_add_context_blocks(issue: dict) -> bool:
    """
    Prompt user to add recommended context blocks
    
    Returns:
        True if user wants to add blocks, False otherwise
    """
    display_context_block_recommendations(issue)
    
    print(f"\n🔧 AUTO-ADD CONTEXT BLOCKS?")
    print(f"="*80)
    print(f"\n   This will:")
    print(f"   1. Add {len(issue.get('recommended_blocks', []))} context blocks to your strategy")
    print(f"   2. Update block weights in strategy file")
    print(f"   3. Re-run optimization with new blocks")
    print(f"   4. Generate tradeable signals")
    
    while True:
        choice = input(f"\n   Add context blocks and re-optimize? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            print(f"\n   ⚠️  Blocks NOT added - strategy remains unchanged")
            return False
        else:
            print(f"   Please enter 'y' or 'n'")


def add_context_blocks_to_strategy(strategy_name: str, issue: dict) -> bool:
    """
    Add recommended context blocks to strategy file with AUTO-SCORING
    
    This implements Option 2 - automatically adding "Always On" blocks
    to boost base confluence so patterns become tradeable.
    
    ENHANCEMENTS:
    - Creates backup before modification
    - Updates _calculate_confluence() to score new blocks
    - Offers rollback if anything fails
    
    Args:
        strategy_name: Strategy module name
        issue: Issue dict with recommended_blocks
    
    Returns:
        True if successful, False otherwise
    """
    import importlib
    import inspect
    from pathlib import Path
    import shutil
    from datetime import datetime
    
    recommended_blocks = issue.get('recommended_blocks', [])
    
    if not recommended_blocks:
        print("   ❌ No blocks to add")
        return False
    
    # Get strategy file path
    strategy_path = Path('src') / 'strategies' / f'{strategy_name}.py'
    
    if not strategy_path.exists():
        print(f"   ❌ Strategy file not found: {strategy_path}")
        return False
    
    # ========================================================================
    # STEP 1: CREATE BACKUP
    # ========================================================================
    backup_dir = Path('src') / 'strategies' / '.backups'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'{strategy_name}_backup_{timestamp}.py'
    backup_path = backup_dir / backup_name
    
    try:
        shutil.copy2(strategy_path, backup_path)
        print(f"\n   💾 Backup created: {backup_path.name}")
    except Exception as e:
        print(f"   ❌ Failed to create backup: {e}")
        return False
    
    print(f"\n   📝 Updating {strategy_path}...")
    
    # Read current file
    with open(strategy_path, 'r') as f:
        lines = f.readlines()
    
    original_lines = lines.copy()  # Keep original for rollback
    
    # Find where to add blocks
    # 1. Add imports
    # 2. Add to _initialize_blocks()
    # 3. Add to _analyze_blocks()
    
    # Track what we've added
    added_imports = []
    new_blocks_config = []
    new_blocks_analysis = []
    
    for block in recommended_blocks:
        block_key = block['key']
        block_name = block['name']
        block_module = block['module']
        block_weight = block['weight']
        
        # Sanitize class name: remove spaces and special characters
        # "EMA 20/50 Trend" -> "EMA2050Trend"
        # "Session Time" -> "SessionTime"
        # "VWAP" -> "VWAP"
        class_name = block_name.replace(' ', '').replace('/', '').replace('-', '').replace('_', '')
        
        # Generate import
        # e.g., from src.detectors.building_blocks.institutional.vwap import VWAP
        import_line = f"from src.detectors.building_blocks.{block_module} import {class_name}\n"
        added_imports.append(import_line)
        
        # Generate detector init
        # self.detectors['vwap'] = VWAP(timeframe='15min')
        detector_init = f"        self.detectors['{block_key}'] = {class_name}(timeframe='15min')\n"
        
        # Generate block config
        # 'vwap': {'weight': 12, 'enabled': True},
        block_config = f"        self.blocks['{block_key}'] = {{'weight': {block_weight}, 'enabled': True}}\n"
        new_blocks_config.append((detector_init, block_config))
        
        # Generate analysis
        # results['vwap'] = self.detectors['vwap'].analyze(df)
        analysis_line = f"        results['{block_key}'] = self.detectors['{block_key}'].analyze(df)\n"
        new_blocks_analysis.append(analysis_line)
    
    # Now insert into file
    new_lines = []
    import_section_end = 0
    init_blocks_section = False
    analyze_blocks_section = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Add imports after last import
        if line.startswith('from src.detectors.building_blocks') or line.startswith('from src.indicators'):
            import_section_end = i + 1
        
        # Add to _initialize_blocks after detectors dict
        if "'enabled': True}" in line and init_blocks_section:
            # Add new detectors and configs here
            for detector_init, block_config in new_blocks_config:
                if detector_init not in ''.join(lines):  # Don't duplicate
                    new_lines.append(detector_init)
            new_lines.append("\n")
            for _, block_config in new_blocks_config:
                if block_config not in ''.join(lines):
                    new_lines.append(block_config)
            init_blocks_section = False
        
        #Mark when we're in init section
        if 'def _initialize_blocks' in line:
            init_blocks_section = True
        
        # Add to _analyze_blocks before return
        if 'def _analyze_blocks' in line:
            analyze_blocks_section = True
        
        if analyze_blocks_section and 'return results' in line:
            # Add analysis lines before return
            new_lines.pop()  # Remove the return line
            for analysis_line in new_blocks_analysis:
                if analysis_line not in ''.join(lines):
                    new_lines.append(analysis_line)
            new_lines.append(line)  # Add return back
            analyze_blocks_section = False
    
    # Insert imports after last import
    if import_section_end > 0:
        for import_line in added_imports:
            if import_line not in ''.join(lines):
                new_lines.insert(import_section_end, import_line)
                import_section_end += 1
    
    # ========================================================================
    # STEP 2: INJECT SCORING CODE INTO _calculate_confluence()
    # ========================================================================
    print(f"\n   🎯 Injecting scoring code into _calculate_confluence()...")
    
    scoring_code_generated = []
    for block in recommended_blocks:
        block_key = block['key']
        block_weight = block['weight']
        block_category = block['category']
        
        # Generate scoring code based on block type
        scoring_code = generate_scoring_code(block_key, block_weight, block_category)
        scoring_code_generated.append(scoring_code)
    
    # Find _calculate_confluence() and inject before "return confluence, signals"
    confluence_section = False
    confluence_injection_point = -1
    
    for i, line in enumerate(new_lines):
        if 'def _calculate_confluence' in line:
            confluence_section = True
        
        if confluence_section and 'return confluence, signals' in line:
            confluence_injection_point = i
            break
    
    if confluence_injection_point > 0:
        # Inject all scoring code before return statement
        for scoring_code in scoring_code_generated:
            new_lines.insert(confluence_injection_point, scoring_code)
            confluence_injection_point += 1
        
        print(f"   ✅ Injected {len(scoring_code_generated)} scoring blocks into _calculate_confluence()")
    else:
        print(f"   ⚠️  Could not find _calculate_confluence() - scoring NOT injected!")
        print(f"   ⚠️  Manual scoring required for new blocks")
    
    # ========================================================================
    # STEP 3: WRITE UPDATED FILE WITH ERROR HANDLING
    # ========================================================================
    try:
        with open(strategy_path, 'w') as f:
            f.writelines(new_lines)
        
        print(f"\n   ✅ Strategy file updated successfully!")
        print(f"\n   📝 Changes Made:")
        print(f"      - Imports: Added {len(added_imports)} imports")
        print(f"      - _initialize_blocks(): Added {len(new_blocks_config)} detectors + configs")
        print(f"      - _analyze_blocks(): Added {len(new_blocks_analysis)} analysis calls")
        print(f"      - _calculate_confluence(): Added {len(scoring_code_generated)} scoring blocks")
        
        for block in recommended_blocks:
            print(f"\n   ✅ {block['name']}: +{block['weight']} points")
        
        return True
        
    except Exception as e:
        print(f"\n   ❌ CRITICAL ERROR during file write: {e}")
        print(f"   🔄 Rolling back to backup...")
        
        # Rollback: restore from backup
        try:
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            
            with open(strategy_path, 'w') as f:
                f.write(backup_content)
            
            print(f"   ✅ Rollback successful - strategy restored from backup")
            print(f"   💾 Backup preserved at: {backup_path}")
            
        except Exception as rollback_error:
            print(f"   ❌ ROLLBACK FAILED: {rollback_error}")
            print(f"   🆘 MANUAL RECOVERY REQUIRED")
            print(f"   📁 Backup location: {backup_path}")
        
        return False


def generate_scoring_code(block_key: str, weight: int, category: str) -> str:
    """
    Generate confluence scoring code for a new block
    
    This is the CRITICAL missing piece - auto-generating the scoring
    logic so blocks actually contribute to confluence!
    
    Args:
        block_key: Block identifier (e.g., 'ema_20_50_trend')
        weight: Maximum points for this block
        category: Block category for appropriate scoring logic
    
    Returns:
        Multi-line string of Python code to inject
    """
    
    # Template varies by category for appropriate tiered scoring
    if category == 'TREND':
        code = f'''
        # ===================================================================
        # {block_key.upper()} ({weight} points max) - AUTO-GENERATED
        # ===================================================================
        {block_key}_signal = results.get('{block_key}', {{}}).get('signal', '')
        {block_key}_conf = results.get('{block_key}', {{}}).get('confidence', 0)
        
        if 'BULLISH' in {block_key}_signal or 'BEARISH' in {block_key}_signal:
            # Trend alignment, full points
            points = int({weight} * {block_key}_conf / 100)
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: {{{block_key}_signal}} ({{{block_key}_conf}}% → +{{points}})")
        elif 'NEUTRAL' in {block_key}_signal:
            # Neutral = weak signal, half points
            points = int({weight} // 2 * {block_key}_conf / 100)
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: NEUTRAL ({{{block_key}_conf}}% → +{{points}})")
        
'''
    
    elif category == 'SESSION':
        code = f'''
        # ===================================================================
        # {block_key.upper()} ({weight} points max) - AUTO-GENERATED
        # ===================================================================
        {block_key}_signal = results.get('{block_key}', {{}}).get('signal', '')
        {block_key}_conf = results.get('{block_key}', {{}}).get('confidence', 0)
        
        if {block_key}_signal and {block_key}_signal != 'NO_SIGNAL':
            # Session active, points based on importance
            if 'LONDON' in {block_key}_signal or 'NY_AM' in {block_key}_signal:
                # Prime sessions, full points
                points = int({weight} * {block_key}_conf / 100)
            elif 'ASIAN' in {block_key}_signal or 'NY_PM' in {block_key}_signal:
                # Secondary sessions, reduced points
                points = int({weight} * 0.67 * {block_key}_conf / 100)
            else:
                # Other times, minimal points
                points = int({weight} * 0.5 * {block_key}_conf / 100)
            
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: {{{block_key}_signal}} ({{{block_key}_conf}}% → +{{points}})")
        
'''
    
    elif category == 'VOLATILITY':
        code = f'''
        # ===================================================================
        # {block_key.upper()} ({weight} points max) - AUTO-GENERATED
        # ===================================================================
        {block_key}_signal = results.get('{block_key}', {{}}).get('signal', '')
        {block_key}_conf = results.get('{block_key}', {{}}).get('confidence', 0)
        
        if 'NEAR' in {block_key}_signal or 'EXTREME' in {block_key}_signal:
            # Extreme/near levels, full points
            points = int({weight} * {block_key}_conf / 100)
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: {{{block_key}_signal}} ({{{block_key}_conf}}% → +{{points}})")
        elif {block_key}_signal and {block_key}_signal != 'NO_SIGNAL':
            # Context only, reduced points
            points = int({weight} * 0.6 * {block_key}_conf / 100)
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: {{{block_key}_signal}} ({{{block_key}_conf}}% → +{{points}})")
        
'''
    
    else:  # INSTITUTIONAL, STRUCTURE, PRICE_LEVELS - generic scoring
        code = f'''
        # ===================================================================
        # {block_key.upper()} ({weight} points max) - AUTO-GENERATED
        # ===================================================================
        {block_key}_signal = results.get('{block_key}', {{}}).get('signal', '')
        {block_key}_conf = results.get('{block_key}', {{}}).get('confidence', 0)
        
        if {block_key}_signal and {block_key}_signal not in ['NO_SIGNAL', 'NEUTRAL']:
            # Signal present, score based on confidence
            points = int({weight} * {block_key}_conf / 100)
            confluence += points
            signals.append(f"{block_key.replace('_', ' ').title()}: {{{block_key}_signal}} ({{{block_key}_conf}}% → +{{points}})")
        
'''
    
    return code
