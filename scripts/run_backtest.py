#!/usr/bin/env python3
"""
BTC_Engine_v3 - Historical Backtest Runner
Days 6-8: Full NautilusTrader BacktestEngine implementation

This script:
1. Sets up BacktestEngine with proper configuration
2. Creates BTC/USDT instrument
3. Loads historical BTC data
4. Runs M-pattern and/or W-pattern strategies
5. Generates comprehensive performance metrics

Usage:
    python scripts/run_backtest.py --strategy m_pattern --bars 1000
    python scripts/run_backtest.py --strategy w_pattern --bars 5000
    python scripts/run_backtest.py --strategy both --bars all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.enums import AccountType, OmsType, BarAggregation, PriceType
from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.data import BarType, BarSpecification
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from scripts.data_catalog_setup import BTC_DataLoader
from src.strategies.m_pattern_strategy import MPatternStrategy, MPatternStrategyConfig
from src.strategies.w_pattern_strategy import WPatternStrategy, WPatternStrategyConfig


def create_btc_instrument():
    """
    Create BTC/USDT instrument for backtesting using TestInstrumentProvider
    
    Returns:
        CryptoPerpetual instrument
    """
    # Use TestInstrumentProvider for reliable instrument creation
    instrument = TestInstrumentProvider.btcusdt_binance()
    
    return instrument


def setup_backtest_engine(instrument, initial_balance: float = 10000.0):
    """
    Setup NautilusTrader BacktestEngine with configuration
    
    Args:
        instrument: Trading instrument
        initial_balance: Initial account balance in USDT
        
    Returns:
        Configured BacktestEngine
    """
    # Create engine
    engine = BacktestEngine()
    
    # Add simulated exchange venue FIRST (required before instruments)
    # Use FillModel to fill orders from bar data
    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(initial_balance, USDT)],
        fill_model=FillModel(),  # Enable order filling from bar data
    )
    
    # Add instrument AFTER venue
    engine.add_instrument(instrument)
    
    return engine


def load_and_add_data(engine: BacktestEngine, instrument, bars_limit: int = None):
    """
    Load BTC data and add to backtest engine
    
    Args:
        engine: BacktestEngine instance
        instrument: Trading instrument
        bars_limit: Optional limit on number of bars (None = all)
        
    Returns:
        tuple: (number of bars loaded, BarType used)
    """
    print("\n" + "="*70)
    print("LOADING DATA")
    print("="*70)
    
    # Load raw data
    loader = BTC_DataLoader()
    df = loader.load_btc_30m()
    
    #Limit bars if specified
    if bars_limit:
        df = df.head(bars_limit)
        print(f"📊 Using first {bars_limit:,} bars for backtest")
    else:
        print(f"📊 Using all {len(df):,} bars for backtest")
    
    # Create bar specification (30-minute bars)
    bar_spec = BarSpecification(
        step=30,
        aggregation=BarAggregation.MINUTE,
        price_type=PriceType.LAST
    )
    
    # Create bar type using the instrument's ID
    bar_type = BarType(instrument.id, bar_spec)
    
    # Convert DataFrame to bars using the correct instrument ID
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.data import Bar
    
    print(f"🔄 Converting to NautilusTrader Bar objects with {instrument.id}...")
    bars = []
    for timestamp, row in df.iterrows():
        # Convert timestamp to nanoseconds
        ts_event = dt_to_unix_nanos(timestamp.to_pydatetime())
        ts_init = ts_event  # For historical data, init = event
        
        # Create Bar object using the correct bar_type
        # Match precision to instrument: price=2, volume=6
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row['open']:.2f}"),
            high=Price.from_str(f"{row['high']:.2f}"),
            low=Price.from_str(f"{row['low']:.2f}"),
            close=Price.from_str(f"{row['close']:.2f}"),
            volume=Quantity.from_str(f"{row['volume']:.6f}"),  # Match instrument size_precision=6
            ts_event=ts_event,
            ts_init=ts_init,
        )
        bars.append(bar)
    
    print(f"✅ Converted {len(bars)} bars to NautilusTrader format")
    
    # Add bars to engine
    print(f"⏳ Adding bars to BacktestEngine...")
    engine.add_data(bars)
    print(f"✅ Data added to engine")
    
    return len(bars), bar_type


def run_m_pattern_backtest(engine: BacktestEngine, bar_type: BarType):
    """
    Run backtest with M-pattern strategy
    
    Args:
        engine: Configured BacktestEngine
        bar_type: BarType to subscribe to
    """
    print("\n" + "="*70)
    print("M-PATTERN STRATEGY BACKTEST")
    print("="*70)
    
    # Create strategy configuration
    config = MPatternStrategyConfig(
        lookback=50,
        min_confidence=0.70,
        position_size_btc=0.01,  # 0.01 BTC per trade
    )
    
    # Create strategy
    strategy = MPatternStrategy(config=config)
    
    # Add strategy to engine FIRST (required before subscribe)
    engine.add_strategy(strategy)
    
    # Subscribe to bars AFTER registration
    strategy.subscribe_bars(bar_type)
    
    print(f"✅ M-Pattern strategy added to engine")
    print(f"   Min Confidence: {config.min_confidence:.0%}")
    print(f"   Position Size: {config.position_size_btc} BTC")
    print(f"   Subscribed to: {bar_type}")
    
    # Run backtest
    print(f"\n⏳ Running backtest...")
    engine.run()
    print(f"✅ Backtest complete")
    
    return strategy


def run_w_pattern_backtest(engine: BacktestEngine, bar_type: BarType):
    """
    Run backtest with W-pattern strategy
    
    Args:
        engine: Configured BacktestEngine
        bar_type: BarType to subscribe to
    """
    print("\n" + "="*70)
    print("W-PATTERN STRATEGY BACKTEST")
    print("="*70)
    
    # Create strategy configuration
    config = WPatternStrategyConfig(
        lookback=50,
        min_confidence=0.70,
        position_size_btc=0.01,  # 0.01 BTC per trade
    )
    
    # Create strategy
    strategy = WPatternStrategy(config=config)
    
    # Add strategy to engine FIRST (required before subscribe)
    engine.add_strategy(strategy)
    
    # Subscribe to bars AFTER registration
    strategy.subscribe_bars(bar_type)
    
    print(f"✅ W-Pattern strategy added to engine")
    print(f"   Min Confidence: {config.min_confidence:.0%}")
    print(f"   Position Size: {config.position_size_btc} BTC")
    print(f"   Subscribed to: {bar_type}")
    
    # Run backtest
    print(f"\n⏳ Running backtest...")
    engine.run()
    print(f"✅ Backtest complete")
    
    return strategy


def generate_report(engine: BacktestEngine, strategy_name: str):
    """
    Generate comprehensive backtest report
    
    Args:
        engine: BacktestEngine with completed backtest
        strategy_name: Name of strategy for reporting
    """
    print("\n" + "="*70)
    print(f"{strategy_name.upper()} BACKTEST RESULTS")
    print("="*70)
    
    # Get account from cache
    accounts = list(engine.cache.accounts())
    
    if accounts:
        account = accounts[0]
        print(f"\n📊 Account Summary:")
        print(f"   Account ID: {account.id}")
        print(f"   Starting Balance: $10,000.00 USDT")
        print(f"   Ending Balance: ${float(account.balance_total(USDT)):.2f} USDT")
        print(f"   Profit/Loss: ${float(account.balance_total(USDT)) - 10000:.2f} USDT")
        print(f"   Return: {((float(account.balance_total(USDT)) / 10000) - 1) * 100:.2f}%")
    
    # Get filled orders from cache
    filled_orders = list(engine.cache.orders())
    filled = [o for o in filled_orders if o.is_closed]
    
    print(f"\n📈 Trading Activity:")
    print(f"   Total Orders Filled: {len(filled)}")
    print(f"   Total Orders: {len(filled_orders)}")
    
    print("\n" + "="*70)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Run BTC_Engine_v3 backtest')
    parser.add_argument('--strategy', choices=['m_pattern', 'w_pattern', 'both'], 
                       default='m_pattern', help='Strategy to backtest')
    parser.add_argument('--bars', type=str, default='1000',
                       help='Number of bars to test (or "all")')
    parser.add_argument('--balance', type=float, default=10000.0,
                       help='Initial balance in USDT')
    
    args = parser.parse_args()
    
    # Parse bars argument
    bars_limit = None if args.bars.lower() == 'all' else int(args.bars)
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         BTC_Engine_v3 - Historical Backtest (Days 6-8)    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\nConfiguration:")
    print(f"  Strategy: {args.strategy}")
    print(f"  Bars: {args.bars}")
    print(f"  Initial Balance: ${args.balance:,.2f} USDT")
    
    # Create instrument
    print("\n" + "="*70)
    print("CREATE INSTRUMENT")
    print("="*70)
    instrument = create_btc_instrument()
    print(f"✅ Instrument created: {instrument.id}")
    print(f"   Symbol: {instrument.id.symbol}")
    print(f"   Venue: {instrument.id.venue}")
    print(f"   Price precision: {instrument.price_precision}")
    print(f"   Size precision: {instrument.size_precision}")
    
    # Setup backtest engine
    print("\n" + "="*70)
    print("SETUP BACKTEST ENGINE")
    print("="*70)
    engine = setup_backtest_engine(instrument, initial_balance=args.balance)
    print(f"✅ BacktestEngine created")
    print(f"   Venue: BINANCE")
    print(f"   Account Type: MARGIN")
    print(f"   Starting Balance: ${args.balance:,.2f} USDT")
    
    # Load data
    num_bars, bar_type = load_and_add_data(engine, instrument, bars_limit=bars_limit)
    if bar_type is None:
        print("❌ ERROR: No bars loaded")
        return False
    
    # Run selected strategy
    if args.strategy == 'm_pattern':
        strategy = run_m_pattern_backtest(engine, bar_type)
        generate_report(engine, "M-Pattern")
        
    elif args.strategy == 'w_pattern':
        strategy = run_w_pattern_backtest(engine, bar_type)
        generate_report(engine, "W-Pattern")
        
    elif args.strategy == 'both':
        print("\n⚠️  Running both strategies requires separate engine instances")
        print("   Run M-pattern and W-pattern separately for accurate results")
        return False
    
    print("\n✅ BACKTEST COMPLETE")
    print(f"\n💡 Next steps:")
    print(f"   - Review trade logs and performance metrics")
    print(f"   - Run full historical backtest (--bars all)")
    print(f"   - Compare against V2 baseline results")
    print(f"   - Optimize parameters if needed")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
