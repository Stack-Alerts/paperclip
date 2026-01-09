"""
Enhanced Strategy Test with Full Backtest Simulation

Institutional-grade testing with:
- Starting capital: $10,000
- Max leverage: 15x
- Trading fees (maker/taker)
- Sharpe Ratio
- Complete P&L tracking
- Win/loss statistics
- Detailed trade log
- Final capital calculation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

# Import backtest simulator
from backtest_simulator import BacktestSimulator, BacktestConfig


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data for backtesting"""
    print(f"Loading {days} days of BTC data...")
    
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    if data_path.exists():
        df = pd.read_csv(data_path)
        
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
        
        cutoff_date = df['timestamp'].max() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff_date].copy()
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    else:
        print("❌ No real data found")
        return None


def run_backtest_for_strategy(strategy, df: pd.DataFrame, strategy_name: str):
    """
    Run full backtest simulation for a strategy
    
    Args:
        strategy: Strategy object with analysis methods
        df: Price data
        strategy_name: Name for reporting
    """
    
    print("\n" + "="*80)
    print(f"🧪 BACKTESTING: {strategy_name}")
    print("="*80)
    
    # Initialize backtest
    config = BacktestConfig(
        starting_capital=10000.0,
        max_leverage=15.0,
        maker_fee=0.0002,  # 0.02%
        taker_fee=0.0005,  # 0.05%
        risk_per_trade_pct=1.0
    )
    
    simulator = BacktestSimulator(config)
    
    print(f"\n📋 Configuration:")
    print(f"   Starting Capital: ${config.starting_capital:,.2f}")
    print(f"   Max Leverage: {config.max_leverage}x")
    print(f"   Maker Fee: {config.maker_fee*100:.3f}%")
    print(f"   Taker Fee: {config.taker_fee*100:.3f}%")
    print(f"   Risk Per Trade: {config.risk_per_trade_pct}%")
    
    print(f"\n📊 Dataset:")
    print(f"   Total Bars: {len(df)}")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")
    
    # Run simulation
    print(f"\n🔄 Running simulation...")
    
    min_bars = strategy.lookback_period
    signals_checked = 0
    signals_taken = 0
    
    for i in range(min_bars, len(df)):
        current_bar = df.iloc[i]
        
        # Update open position if exists
        if simulator.open_trade is not None:
            exit_reason = simulator.update_open_position(current_bar)
            if exit_reason:
                print(f"   Trade closed: {exit_reason} at ${current_bar['close']:.2f}")
        
        # Check for new signals (only if no open position)
        if simulator.open_trade is None:
            # Get historical data for analysis
            hist_df = df.iloc[:i+1].copy()
            
            # Update strategy bars
            strategy.bars_data = []
            for _, row in hist_df.iterrows():
                strategy.bars_data.append({
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })
            
            if len(strategy.bars_data) > strategy.max_bars_held:
                strategy.bars_data = strategy.bars_data[-strategy.max_bars_held:]
            
            # Analyze with building blocks
            try:
                analysis_df = pd.DataFrame(strategy.bars_data)
                results = strategy._analyze_blocks(analysis_df)
                confluence, signal_list = strategy._calculate_confluence(results)
                
                signals_checked += 1
                
                # Check if signal meets threshold
                if confluence >= strategy.min_confluence:
                    # Calculate TP/SL
                    tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                    
                    # Determine side (M-pattern = SHORT, W-pattern = LONG)
                    side = 'SHORT' if 'double_top' in strategy.blocks else 'LONG'
                    
                    # Try to open position
                    success = simulator.open_position(
                        entry_time=current_bar['timestamp'],
                        entry_price=current_bar['close'],
                        side=side,
                        tp1=tp1,
                        tp2=tp2,
                        tp3=tp3,
                        sl=sl,
                        confluence=confluence,
                        signals=signal_list
                    )
                    
                    if success:
                        signals_taken += 1
                        print(f"   Trade opened: {side} at ${current_bar['close']:.2f} (Confluence: {confluence})")
                        
            except Exception as e:
                continue
    
    # Close any remaining open position at end
    if simulator.open_trade is not None:
        simulator.close_position(df.iloc[-1]['timestamp'], df.iloc[-1]['close'], 'END_OF_DATA')
    
    # Print results
    print(f"\n✅ Simulation complete")
    print(f"   Signals checked: {signals_checked}")
    print(f"   Signals taken: {signals_taken}")
    
    # Get performance metrics
    simulator.print_summary()
    
    # Show trade details
    if len(simulator.trades) > 0:
        print("\n" + "="*80)
        print("DETAILED TRADE LOG")
        print("="*80)
        
        for i, trade in enumerate(simulator.trades[:10]):  # Show first 10
            print(f"\nTrade #{i+1}")
            print(f"   Entry: {trade.entry_time} @ ${trade.entry_price:.2f}")
            print(f"   Exit:  {trade.exit_time} @ ${trade.exit_price:.2f}")
            print(f"   Side: {trade.side}")
            print(f"   Size: ${trade.position_size_usd:,.2f} ({trade.position_size_btc:.4f} BTC)")
            print(f"   Leverage: {trade.leverage:.2f}x")
            print(f"   Exit: {trade.exit_reason}")
            print(f"   P&L: ${trade.net_pnl:,.2f} ({trade.pnl_pct:.2f}%)")
            print(f"   Fees: ${trade.fees_paid:.2f}")
        
        if len(simulator.trades) > 10:
            print(f"\n   ... and {len(simulator.trades) - 10} more trades")
    
    # Save detailed report
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'strategy_backtests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metrics = simulator.get_performance_metrics()
    trade_log = simulator.get_trade_log()
    
    report = {
        'strategy_name': strategy_name,
        'strategy_id': strategy.strategy_id,
        'backtest_date': datetime.now().isoformat(),
        'config': {
            'starting_capital': config.starting_capital,
            'max_leverage': config.max_leverage,
            'maker_fee': config.maker_fee,
            'taker_fee': config.taker_fee,
            'risk_per_trade_pct': config.risk_per_trade_pct
        },
        'performance': metrics,
        'trades': trade_log
    }
    
    output_file = output_dir / f'{strategy.strategy_id}_backtest_results.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved: {output_file}")
    print("="*80 + "\n")
    
    return metrics


def test_m_pattern_strategy():
    """Test M-Pattern Reversal Strategy with full backtest"""
    from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
    
    print("\n" + "="*80)
    print("STRATEGY 01: M PATTERN REVERSAL - FULL BACKTEST")
    print("="*80)
    
    # Load data
    df = load_btc_data(days=180)
    if df is None or len(df) == 0:
        print("❌ Failed to load data")
        return False
    
    # Create mock strategy for testing
    class MockStrategy:
        def __init__(self):
            self.strategy_id = "01_M_PATTERN_REVERSAL"
            self.strategy_name = "M Pattern Reversal - Standard"
            self.min_confluence = 70
            self.max_bars_held = 1000
            self.lookback_period = 100
            self.min_risk_reward = 3.0
            self.peak_tolerance = 0.002
            self.bars_data = []
            
            self.blocks = {
                'double_top': {'name': 'DoubleTopPattern', 'weight': 30, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 25, 'enabled': True},
                'hod': {'name': 'HOD', 'weight': 20, 'enabled': True},
                'asia_50': {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 15, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 12, 'enabled': True}
            }
    
    strategy = MockStrategy()
    
    # Bind methods
    strategy._analyze_blocks = MPatternReversalStandard._analyze_blocks.__get__(strategy)
    strategy._calculate_confluence = MPatternReversalStandard._calculate_confluence.__get__(strategy)
    strategy._calculate_tp_sl = MPatternReversalStandard._calculate_tp_sl.__get__(strategy)
    strategy._detect_double_top = MPatternReversalStandard._detect_double_top.__get__(strategy)
    strategy._detect_rsi_divergence = MPatternReversalStandard._detect_rsi_divergence.__get__(strategy)
    strategy._check_hod_rejection = MPatternReversalStandard._check_hod_rejection.__get__(strategy)
    strategy._check_asia_50_position = MPatternReversalStandard._check_asia_50_position.__get__(strategy)
    strategy._check_session_timing = MPatternReversalStandard._check_session_timing.__get__(strategy)
    strategy._check_vwap_position = MPatternReversalStandard._check_vwap_position.__get__(strategy)
    
    # Run backtest
    metrics = run_backtest_for_strategy(strategy, df, strategy.strategy_name)
    
    # Validation
    print("\n" + "="*80)
    print("BACKTEST VALIDATION")
    print("="*80)
    
    passed = True
    
    if metrics['total_trades'] == 0:
        print("⚠️  No trades generated - strategy may be too restrictive")
        passed = False
    else:
        print(f"✅ Trades generated: {metrics['total_trades']}")
    
    if metrics['sharpe_ratio'] > 1.5:
        print(f"✅ Excellent Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    elif metrics['sharpe_ratio'] > 0.5:
        print(f"⚠️  Acceptable Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    else:
        print(f"❌ Poor Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        passed = False
    
    if metrics['total_return_pct'] > 0:
        print(f"✅ Profitable: {metrics['total_return_pct']:.2f}%")
    else:
        print(f"❌ Losing: {metrics['total_return_pct']:.2f}%")
        passed = False
    
    print("="*80 + "\n")
    
    return passed


if __name__ == "__main__":
    success = test_m_pattern_strategy()
    sys.exit(0 if success else 1)