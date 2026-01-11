"""
User Interface

Displays top 5 configurations and gets user selection.
Shows iteration suggestions after cycle 5.
"""

from typing import List
from .data_classes import ConfigPerformance, OptimizationConfig


def display_top_5_configs(results: List[ConfigPerformance], iteration: int, configs: List[OptimizationConfig] = None):
    """
    Display top 5 configurations with COMPREHENSIVE institutional-grade metrics
    
    Args:
        results: Top 5 performance results
        iteration: Current iteration number
        configs: All optimization configs (to extract actual risk params)
    """
    print("\n" + "="*80)
    print("OPTIMIZATION RESULTS - INSTITUTIONAL GRADE REPORT")
    print("="*80)
    print(f"\nIteration: {iteration} of 5")
    
    # Extract actual risk params from configs (NO HARDCODING!)
    if configs and len(configs) > 0:
        first_config = configs[0]
        starting_capital = getattr(first_config, 'starting_capital', 10000.0)
        max_leverage = getattr(first_config, 'max_leverage', 10.0)
        risk_per_trade_pct = getattr(first_config, 'risk_per_trade_pct', 1.0)
    else:
        # Fallback if configs not provided (backward compatibility)
        starting_capital = 10000.0
        max_leverage = 10.0
        risk_per_trade_pct = 1.0
    
    # Calculate position sizing from ACTUAL config values
    margin_per_trade = starting_capital * (risk_per_trade_pct / 100.0)
    notional_per_trade = margin_per_trade * max_leverage
    btc_position_size = notional_per_trade / 95000.0  # Approximate @ $95K BTC
    
    # Display test parameters (USING ACTUAL CONFIG VALUES)
    print("\n" + "-"*80)
    print("TEST PARAMETERS:")
    print("-"*80)
    print(f"   ├─ Market: BTC/USDT Perpetual (Binance Futures)")
    print(f"   ├─ Starting Capital: ${starting_capital:,.2f} USDT")
    print(f"   ├─ Position Sizing:")
    print(f"   │  ├─ Risk per trade: {risk_per_trade_pct}% of capital = ${margin_per_trade:,.2f} margin")
    print(f"   │  ├─ Leverage: {max_leverage:.0f}x")
    print(f"   │  ├─ Notional per trade: ${margin_per_trade:,.2f} × {max_leverage:.0f} = ${notional_per_trade:,.2f}")
    print(f"   │  └─ BTC Position: ~{btc_position_size:.3f} BTC @ $95K BTC (${notional_per_trade:,.2f} notional)")
    print(f"   ├─ Timeframe: 15-minute bars (primary trading timeframe)")
    print(f"   ├─ Fee Structure (Binance Perpetual):")
    print(f"   │  ├─ Maker Fee: -0.01% (rebate)")
    print(f"   │  └─ Taker Fee: 0.05%")
    print(f"   ├─ Order Type: Market Orders (Taker fees)")
    print(f"   ├─ Test Period: 180 days")
    print(f"   └─ Total Configs Tested: {len(configs) if configs else 48}\n")
    
    preset_names = ['Balanced', 'Event-Heavy', 'Context-Heavy', 'Conservative']
    
    for i, result in enumerate(results, 1):
        # Determine config type from config_id
        config_type = preset_names[(result.config_id // 12) % 4]
        
        # Calculate final capital (use actual starting capital from config)
        config_starting_capital = starting_capital  # From top of function
        final_capital = config_starting_capital + result.net_pnl
        
        if i == 1:
            label = f"#{i}: {config_type} Configuration (RECOMMENDED)"
        else:
            label = f"#{i}: {config_type} Configuration"
        
        print(f"\n{label}")
        print(f"   ├─ Config ID: {result.config_id}")
        print(f"   │")
        # Calculate hold time statistics if trades available
        avg_hold_bars = 0
        min_hold_bars = 0
        max_hold_bars = 0
        if hasattr(result, 'trades') and result.trades:
            # Extract hold times from trade exit reasons
            hold_times = []
            for trade in result.trades:
                reason = trade.reason
                # Extract bars from "Held X bars" format
                if 'Held' in reason and 'bars' in reason:
                    try:
                        bars = int(reason.split('Held ')[1].split(' bars')[0])
                        hold_times.append(bars)
                    except:
                        pass
            
            if hold_times:
                avg_hold_bars = sum(hold_times) / len(hold_times)
                min_hold_bars = min(hold_times)
                max_hold_bars = max(hold_times)
        
        # Convert bars to hours (15min bars)
        avg_hold_hours = avg_hold_bars * 0.25
        min_hold_hours = min_hold_bars * 0.25
        max_hold_hours = max_hold_bars * 0.25
        
        print(f"   ├─ TRADING PERFORMANCE:")
        print(f"   │  ├─ Total Trades: {result.total_trades}")
        print(f"   │  ├─ Winning Trades: {result.winning_trades} ({result.win_rate_pct:.1f}%)")
        print(f"   │  ├─ Losing Trades: {result.losing_trades}")
        if avg_hold_bars > 0:
            print(f"   │  ├─ Avg Hold Time: {avg_hold_bars:.0f} bars ({avg_hold_hours:.1f} hours)")
            print(f"   │  ├─ Min Hold Time: {min_hold_bars} bars ({min_hold_hours:.1f} hours)")
            print(f"   │  ├─ Max Hold Time: {max_hold_bars} bars ({max_hold_hours:.1f} hours)")
        print(f"   │  ├─ Avg Win: ${result.avg_win:.2f}")
        print(f"   │  ├─ Avg Loss: ${result.avg_loss:.2f}")
        print(f"   │  ├─ Largest Win: ${result.largest_win:.2f}")
        print(f"   │  └─ Largest Loss: ${result.largest_loss:.2f}")
        print(f"   │")
        print(f"   ├─ FINANCIAL RESULTS:")
        print(f"   │  ├─ Gross PnL: ${result.total_pnl:+.2f}")
        print(f"   │  ├─ Total Fees: -${result.total_fees:.2f}")
        print(f"   │  ├─ Net PnL: ${result.net_pnl:+.2f}")
        print(f"   │  ├─ Net Return: {result.net_return_pct:+.2f}%")
        print(f"   │  ├─ Starting Capital: ${starting_capital:,.2f}")
        print(f"   │  └─ Final Capital: ${final_capital:,.2f}")
        print(f"   │")
        print(f"   ├─ RISK METRICS:")
        print(f"   │  ├─ Profit Factor: {result.profit_factor:.2f}")
        print(f"   │  ├─ Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"   │  ├─ Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"   │  └─ Risk-Adjusted Return: {result.net_return_pct / max(result.max_drawdown_pct, 0.1):.2f}")
        print(f"   │")
        print(f"   └─ TRADE RECORD: data/reports/strategies/universal_optimizer/{result.config_id}_trades.csv")


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
