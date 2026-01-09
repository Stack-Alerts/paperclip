"""
User Interface

Displays top 5 configurations and gets user selection.
Shows iteration suggestions after cycle 5.
"""

from typing import List
from .data_classes import ConfigPerformance


def display_top_5_configs(results: List[ConfigPerformance], iteration: int):
    """
    Display top 5 configurations with full details including fees
    """
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE - SELECT CONFIGURATION")
    print("="*80)
    print(f"\nIteration: {iteration} of 5\n")
    
    preset_names = ['Balanced', 'Event-Heavy', 'Context-Heavy', 'Conservative']
    
    for i, result in enumerate(results, 1):
        # Determine config type from config_id
        config_type = preset_names[(result.config_id // 12) % 4]
        
        if i == 1:
            label = f"#{i}: {config_type} Configuration (RECOMMENDED)"
        else:
            label = f"#{i}: {config_type} Configuration"
        
        print(f"\n{label}")
        print(f"   ├─ Trades: {result.total_trades}")
        print(f"   ├─ PnL: ${result.total_pnl:+.2f}")
        print(f"   ├─ Fees: -${result.total_fees:.2f}")
        print(f"   ├─ Net PnL: ${result.net_pnl:+.2f} ({result.net_return_pct:+.2f}%)")
        print(f"   ├─ Win Rate: {result.win_rate_pct:.1f}%")
        print(f"   ├─ Profit Factor: {result.profit_factor:.2f}")
        print(f"   └─ Sharpe: {result.sharpe_ratio:.2f}")


def prompt_user_selection() -> int:
    """
    Prompt user to select configuration
    
    Returns:
        Selected index (0-4), or -1 to quit
    """
    while True:
        try:
            choice = input("\nSelect configuration to apply (1-5, or 'q' to quit): ").strip().lower()
            
            # Check for quit
            if choice in ['q', 'quit', 'exit']:
                print("\n⚠️  Optimization cancelled by user.")
                return -1
            
            # Try to convert to number
            idx = int(choice) - 1
            
            if 0 <= idx < 5:
                return idx
            else:
                print("❌ Invalid choice. Please select 1-5, or 'q' to quit.")
        except (ValueError, KeyboardInterrupt):
            print("\n⚠️  Interrupted. Exiting...")
            return -1
        except EOFError:
            # Handle non-interactive mode
            print("\n⚠️  Non-interactive mode detected. Selecting #1 (recommended).")
            return 0


def display_block_recommendations(weak_block: str, recommendations: List[tuple]):
    """
    Display block replacement recommendations after iteration 5
    
    Args:
        weak_block: Name of weakest performing block
        recommendations: List of (block_name, score) tuples
    """
    print("\n" + "="*80)
    print("ITERATION 5 COMPLETE - BLOCK IMPROVEMENT SUGGESTIONS")
    print("="*80)
    print(f"\n⚠️  Weakest Block Identified: '{weak_block}'")
    print("\nTop 5 Replacement Recommendations:\n")
    
    for i, (block_name, score) in enumerate(recommendations, 1):
        print(f"   #{i}: {block_name:30s} (Score: {score:.1f})")
    
    print("\nTo replace block:")
    print(f"1. Edit strategy file")
    print(f"2. Remove '{weak_block}' block")
    print(f"3. Add recommended block")
    print(f"4. Re-run optimizer")
    print("="*80 + "\n")


def display_iteration_context(iteration: int):
    """Display context about current iteration"""
    if iteration == 1:
        print("\n💡 First optimization - establishing baseline")
    elif iteration < 5:
        print(f"\n💡 Iteration {iteration} - refining parameters")
    elif iteration == 5:
        print(f"\n💡 Iteration 5 - final refinement + block evaluation")
    else:
        print(f"\n💡 Iteration {iteration} - continuing optimization")


def confirm_application() -> bool:
    """
    Confirm before applying configuration to file
    
    Returns:
        True if user confirms, False otherwise
    """
    try:
        response = input("\nApply this configuration to strategy file? (y/n): ")
        return response.lower() in ['y', 'yes']
    except (KeyboardInterrupt, EOFError):
        return True  # Auto-confirm in non-interactive mode