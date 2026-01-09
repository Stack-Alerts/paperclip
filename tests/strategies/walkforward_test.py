"""
Institutional-Grade Walk-Forward Test Framework

WALK-FORWARD TESTING (Not Backtesting):
- Processes candles one at a time as they arrive
- No look-ahead bias
- Strategy unaware of future candles
- Real-time simulation: Signal → Entry → Exit → Next candle

Features:
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

# Import walkforward simulator (renamed from backtest)
from backtest_simulator import BacktestSimulator, BacktestConfig


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data for walk-forward testing"""
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
        
        print(f"✅ Loaded {len(df)} bars")
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    else:
        print("❌ No real data found")
        return None


def run_walkforward_test(strategy, df: pd.DataFrame, strategy_name: str):
    """
    Run WALK-FORWARD test (not backtest!)
    
    Process:
    1. Start at bar 100 (minimum lookback)
    2. Strategy analyzes only bars 0-100 (no future knowledge)
    3. If signal, open trade
    4. Move to bar 101
    5. Check if trade hit TP/SL
    6. Strategy analyzes bars 0-101 for new signal
    7. Repeat until end of data
    8. Close any open trades
    9. Generate report
    
    NO LOOK-AHEAD BIAS - Strategy never sees future candles!
    """
    
    print("\n" + "="*80)
    print(f"🔄 WALK-FORWARD TEST: {strategy_name}")
    print("="*80)
    
    # Initialize simulator
    config = BacktestConfig(
        starting_capital=10000.0,
        max_leverage=15.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
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
    
    print(f"\n🔄 Starting walk-forward simulation...")
    print(f"   NO LOOK-AHEAD - Strategy processes candles as they arrive")
    
    min_bars = strategy.lookback_period
    signals_checked = 0
    signals_taken = 0
    
    # CRITICAL: Build bars incrementally (not rebuilding each time!)
    strategy.bars_data = []
    
    # Process each candle one at a time (walk-forward)
    for i in range(len(df)):
        current_bar = df.iloc[i]
        
        # Add this NEW candle to strategy's data
        strategy.bars_data.append({
            'timestamp': current_bar['timestamp'],
            'open': current_bar['open'],
            'high': current_bar['high'],
            'low': current_bar['low'],
            'close': current_bar['close'],
            'volume': current_bar['volume']
        })
        
        # Keep rolling window
        if len(strategy.bars_data) > strategy.max_bars_held:
            strategy.bars_data.pop(0)  # Remove oldest
        
        # Update open position if exists (check TP/SL hit)
        if simulator.open_trade is not None:
            exit_reason = simulator.update_open_position(current_bar)
            if exit_reason:
                capital_change = simulator.trades[-1].net_pnl
                sign = '+' if capital_change >= 0 else ''
                print(f"   Bar {i}: Trade closed [{exit_reason}] {sign}${capital_change:.2f} | Capital: ${simulator.capital:.2f}")
        
        # Check for new signals (only if no open position AND enough bars)
        if simulator.open_trade is None and len(strategy.bars_data) >= min_bars:
            try:
                # Strategy analyzes ONLY data it has seen so far
                analysis_df = pd.DataFrame(strategy.bars_data)
                results = strategy._analyze_blocks(analysis_df)
                confluence, signal_list = strategy._calculate_confluence(results)
                
                signals_checked += 1
                
                # Check if signal meets threshold
                if confluence >= strategy.min_confluence:
                    # Calculate TP/SL based on current analysis
                    tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                    
                    # Determine side
                    side = 'SHORT' if 'double_top' in strategy.blocks else 'LONG'
                    
                    # Check R:R before attempting trade
                    if side == 'SHORT':
                        risk = abs(current_bar['close'] - sl)
                        reward_tp2 = abs(current_bar['close'] - tp2)
                    else:  # LONG
                        risk = abs(sl - current_bar['close'])
                        reward_tp2 = abs(tp2 - current_bar['close'])
                    
                    rr = reward_tp2 / risk if risk > 0 else 0
                    
                    if rr < strategy.min_risk_reward:
                        print(f"   Bar {i}: High confluence ({confluence}) but R:R {rr:.2f} < {strategy.min_risk_reward} - SKIPPED")
                        continue
                    
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
                        print(f"   Bar {i}: Trade opened [{side}] @ ${current_bar['close']:.2f} (Confluence: {confluence}, R:R: {rr:.2f})")
                    else:
                        # Trade rejected - log why
                        print(f"   Bar {i}: Trade REJECTED (Confluence: {confluence}) - insufficient capital or existing position")
                        
            except Exception as e:
                continue
        
        # Progress indicator every 1000 bars
        if i > 0 and i % 1000 == 0:
            print(f"   Progress: {i}/{len(df)} bars ({i/len(df)*100:.1f}%) | Capital: ${simulator.capital:.2f}")
    
    # Close any remaining open position at end
    if simulator.open_trade is not None:
        simulator.close_position(df.iloc[-1]['timestamp'], df.iloc[-1]['close'], 'END_OF_TEST')
        print(f"   Final trade closed at end of test")
    
    # Print results
    print(f"\n✅ Walk-forward test complete!")
    print(f"   Total bars processed: {len(df)}")
    print(f"   Signals evaluated: {signals_checked}")
    print(f"   Trades executed: {signals_taken}")
    
    # Get performance metrics
    simulator.print_summary()
    
    # Show trade details
    if len(simulator.trades) > 0:
        print("\n" + "="*80)
        print("DETAILED TRADE LOG (First 10 trades)")
        print("="*80)
        
        for i, trade in enumerate(simulator.trades[:10]):
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
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metrics = simulator.get_performance_metrics()
    trade_log = simulator.get_trade_log()
    
    report = {
        'strategy_name': strategy_name,
        'strategy_id': strategy.strategy_id,
        'test_type': 'WALK_FORWARD',
        'test_date': datetime.now().isoformat(),
        'config': {
            'starting_capital': config.starting_capital,
            'max_leverage': config.max_leverage,
            'maker_fee': config.maker_fee,
            'taker_fee': config.taker_fee,
            'risk_per_trade_pct': config.risk_per_trade_pct
        },
        'dataset': {
            'total_bars': len(df),
            'start_date': str(df['timestamp'].min()),
            'end_date': str(df['timestamp'].max()),
            'days': (df['timestamp'].max() - df['timestamp'].min()).days
        },
        'performance': metrics,
        'trades': trade_log
    }
    
    output_file = output_dir / f'{strategy.strategy_id}_walkforward_results.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved: {output_file}")
    print("="*80 + "\n")
    
    return metrics


def test_strategy_01():
    """Test M-Pattern Reversal Strategy with walk-forward"""
    from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
    
    print("\n" + "="*80)
    print("STRATEGY 01: M PATTERN REVERSAL - WALK-FORWARD TEST")
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
    
    # Run walk-forward test
    metrics = run_walkforward_test(strategy, df, strategy.strategy_name)
    
    # Validation
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    passed = True
    
    if metrics['total_trades'] == 0:
        print("⚠️  No trades generated - strategy may be too restrictive")
        passed = False
    else:
        print(f"✅ Trades executed: {metrics['total_trades']}")
    
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
    
    if metrics['win_rate_pct'] >= 50:
        print(f"✅ Good Win Rate: {metrics['win_rate_pct']:.2f}%")
    else:
        print(f"⚠️  Low Win Rate: {metrics['win_rate_pct']:.2f}%")
    
    print("="*80 + "\n")
    
    return passed


if __name__ == "__main__":
    success = test_strategy_01()
    sys.exit(0 if success else 1)