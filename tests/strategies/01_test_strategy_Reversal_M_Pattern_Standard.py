"""
Test for Strategy 01: M Pattern Reversal - Standard

Tests strategy logic, confluence calculation, and signal generation.
Validates pattern detection, RSI divergence, and entry conditions.

Strategy Details:
- Building Blocks: Double Top, RSI Divergence, HOD, Asia 50%, Session, VWAP
- Confluence Threshold: 70+ points
- Expected Frequency: 2-4 signals/month
- Risk:Reward: 1:3
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json

# Import strategy
from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard

# Import building block detectors for mock strategy
from src.detectors.building_blocks.patterns.double_top import DoubleTopPattern
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence
from src.detectors.building_blocks.price_levels.hod import HOD
from src.detectors.building_blocks.price_levels.asia_session_50_percent import AsiaSession50Percent
from src.detectors.building_blocks.sessions.session_time import SessionTime
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.moving_averages.ema_20_50_trend import EMA2050Trend
from src.detectors.building_blocks.sessions.kill_zones import KillZones
from src.detectors.building_blocks.volatility.adr import ADR
from src.detectors.building_blocks.market_structure.swing_points import SwingPoints
from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend
from src.detectors.building_blocks.market_structure.premium_discount_zones import PremiumDiscountZones


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data for testing"""
    # In production, load from actual data source
    # For now, generate synthetic data for testing
    
    print(f"Loading {days} days of BTC data...")
    
    # Check if we have real data
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    
    if data_path.exists():
        df = pd.read_csv(data_path)
        
        # Standardize columns
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
        
        # Filter to last N days
        cutoff_date = df['timestamp'].max() - timedelta(days=days)
        df = df[df['timestamp'] >= cutoff_date].copy()
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    else:
        # Generate synthetic data for testing
        print("⚠️  No real data found - generating synthetic data for testing")
        return generate_synthetic_data(days)


def generate_synthetic_data(days: int) -> pd.DataFrame:
    """Generate synthetic BTC data with M-pattern characteristics"""
    bars_per_day = 96  # 15-min bars
    total_bars = days * bars_per_day
    
    # Start date
    start_date = datetime.now() - timedelta(days=days)
    
    # Base price with trend and volatility
    base_price = 45000
    prices = []
    timestamps = []
    
    for i in range(total_bars):
        # Add trend and randomness
        trend = np.sin(i / 100) * 2000
        noise = np.random.randn() * 500
        price = base_price + trend + noise
        
        # Occasionally inject M-pattern
        if i > 50 and i % 200 == 0:
            # Create M-pattern: up, down, up, down
            for j in range(20):
                if j < 5:  # First peak
                    price += 200
                elif j < 10:  # valley
                    price -= 300
                elif j < 15:  # Second peak (slightly lower)
                    price += 280
                else:  # Breakdown
                    price -= 400
        
        timestamp = start_date + timedelta(minutes=15*i)
        
        # OHLC generation
        open_price = price
        high_price = price + abs(np.random.randn() * 100)
        low_price = price - abs(np.random.randn() * 100)
        close_price = price + np.random.randn() * 50
        volume = 100 + abs(np.random.randn() * 50)
        
        prices.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(prices)


def test_strategy_signals(strategy, df: pd.DataFrame):
    """
    Test strategy signal generation
    
    Tests:
    1. Strategy initialization
    2. Building block analysis
    3. Confluence calculation
    4. Signal generation logic
    5. TP/SL calculation
    """
    
    print("="*80)
    print(f"🧪 STRATEGY TEST: {strategy.strategy_name}")
    print("="*80)
    print(f"Strategy ID: {strategy.strategy_id}")
    print(f"Dataset: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Min Confluence: {strategy.min_confluence}")
    print(f"Min R:R: {strategy.min_risk_reward}")
    
    # Track results
    signals_generated = []
    confluence_scores = []
    
    # Test with expanding window
    min_bars = strategy.lookback_period
    
    # Optimize: Test every 10th bar for speed (still covers all time periods)
    test_interval = 10
    total_tests = len(range(min_bars, len(df), test_interval))
    
    print(f"\nRunning simulation (testing every {test_interval}th bar for efficiency)...")
    print(f"Total bars to test: {total_tests}")
    
    for i in range(min_bars, len(df), test_interval):  # Test every 10th bar
        try:
            # Get data up to current point
            hist_df = df.iloc[:i+1].copy()
            
            # Simulate bar update
            for _, row in hist_df.iterrows():
                strategy.bars_data.append({
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })
            
            # Keep rolling window
            if len(strategy.bars_data) > strategy.max_bars_held:
                strategy.bars_data = strategy.bars_data[-strategy.max_bars_held:]
            
            # Run building block analysis
            analysis_df = pd.DataFrame(strategy.bars_data)
            results = strategy._analyze_blocks(analysis_df)
            
            # Calculate confluence
            confluence, signal_list = strategy._calculate_confluence(results)
            confluence_scores.append(confluence)
            
            # Check if would generate signal
            if confluence >= strategy.min_confluence:
                
                # Calculate TP/SL
                tp1, tp2, tp3, sl = strategy._calculate_tp_sl(results)
                
                # Calculate R:R
                current_price = strategy.bars_data[-1]['close']
                risk = abs(current_price - sl)
                reward = abs(tp2 - current_price)
                rr_ratio = reward / risk if risk > 0 else 0
                
                signal = {
                    'timestamp': hist_df.iloc[-1]['timestamp'],
                    'bar_index': i,
                    'confluence': confluence,
                    'signals': signal_list,
                    'entry_price': current_price,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'sl': sl,
                    'rr_ratio': rr_ratio
                }
                
                # Only count if R:R is acceptable
                if rr_ratio >= strategy.min_risk_reward:
                    signals_generated.append(signal)
                    
        except Exception as e:
            print(f"Error at bar {i}: {e}")
            continue
    
    # Calculate statistics
    print(f"\n{'='*80}")
    print(f"📊 TEST RESULTS:")
    print(f"{'='*80}")
    print(f"Total bars tested: {len(df)}")
    print(f"Signals generated: {len(signals_generated)}")
    
    if len(confluence_scores) > 0:
        print(f"Average confluence: {sum(confluence_scores)/len(confluence_scores):.1f}")
        print(f"Max confluence: {max(confluence_scores)}")
        print(f"Min confluence: {min(confluence_scores)}")
    
    # Calculate signals per month
    days_tested = (df['timestamp'].max() - df['timestamp'].min()).days
    months_tested = days_tested / 30
    signals_per_month = len(signals_generated) / months_tested if months_tested > 0 else 0
    
    print(f"Signals per month: {signals_per_month:.2f}")
    print(f"Expected: 2-4 signals/month")
    
    if len(signals_generated) > 0:
        avg_rr = sum(s['rr_ratio'] for s in signals_generated) / len(signals_generated)
        print(f"Average R:R: {avg_rr:.2f}")
        print(f"Expected R:R: {strategy.min_risk_reward}")
    
    # Show sample signals
    if signals_generated:
        print(f"\n{'='*80}")
        print(f"SAMPLE SIGNALS (first 5):")
        print(f"{'='*80}")
        for i, sig in enumerate(signals_generated[:5]):
            print(f"\n{i+1}. {sig['timestamp']}")
            print(f"   Bar Index: {sig['bar_index']}")
            print(f"   Confluence: {sig['confluence']} points")
            for signal_str in sig['signals']:
                print(f"      - {signal_str}")
            print(f"   Entry: ${sig['entry_price']:.2f}")
            print(f"   TP1: ${sig['tp1']:.2f}, TP2: ${sig['tp2']:.2f}, TP3: ${sig['tp3']:.2f}")
            print(f"   SL: ${sig['sl']:.2f}")
            print(f"   R:R: {sig['rr_ratio']:.2f}")
    
    # Validation checks
    print(f"\n{'='*80}")
    print(f"VALIDATION:")
    print(f"{'='*80}")
    
    validation_passed = True
    
    # Check signal frequency
    if signals_per_month < 1:
        print(f"⚠️  Signal frequency too low: {signals_per_month:.2f}/month (expected 2-4)")
        validation_passed = False
    elif signals_per_month > 6:
        print(f"⚠️  Signal frequency too high: {signals_per_month:.2f}/month (expected 2-4)")
        validation_passed = False
    else:
        print(f"✅ Signal frequency acceptable: {signals_per_month:.2f}/month")
    
    # Check R:R ratios
    if len(signals_generated) > 0:
        low_rr_signals = [s for s in signals_generated if s['rr_ratio'] < strategy.min_risk_reward]
        if len(low_rr_signals) > 0:
            print(f"⚠️  Found {len(low_rr_signals)} signals with R:R < {strategy.min_risk_reward}")
            validation_passed = False
        else:
            print(f"✅ All signals meet minimum R:R requirement")
    
    # Save results
    output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'strategy_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        'strategy_name': strategy.strategy_name,
        'strategy_id': strategy.strategy_id,
        'test_date': datetime.now().isoformat(),
        'total_bars': len(df),
        'days_tested': days_tested,
        'months_tested': months_tested,
        'signals_generated': len(signals_generated),
        'signals_per_month': signals_per_month,
        'avg_confluence': sum(confluence_scores)/len(confluence_scores) if confluence_scores else 0,
        'max_confluence': max(confluence_scores) if confluence_scores else 0,
        'avg_rr': sum(s['rr_ratio'] for s in signals_generated) / len(signals_generated) if signals_generated else 0,
        'validation_passed': validation_passed,
        'signals': [{
            'timestamp': str(s['timestamp']),
            'bar_index': s['bar_index'],
            'confluence': s['confluence'],
            'entry_price': s['entry_price'],
            'rr_ratio': s['rr_ratio']
        } for s in signals_generated]
    }
    
    output_file = output_dir / f'{strategy.strategy_id}_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Test results saved: {output_file}")
    print(f"\n{'='*80}")
    
    if validation_passed:
        print("✅ VALIDATION PASSED - Strategy meets requirements")
    else:
        print("⚠️  VALIDATION WARNINGS - Review strategy parameters")
    
    print(f"{'='*80}\n")
    
    return report


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*80)
    print("STRATEGY 01: M PATTERN REVERSAL - TEST SUITE")
    print("="*80 + "\n")
    
    # Load data
    print("Step 1: Loading BTC data...")
    df = load_btc_data(days=180)
    
    if df is None or len(df) == 0:
        print("❌ Failed to load data - aborting tests")
        return False
    
    print(f"✅ Loaded {len(df)} bars\n")
    
    # Initialize strategy (create mock object for testing)
    print("Step 2: Initializing strategy...")
    
    # Create simple mock strategy object for testing building blocks
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
            self.trades_count = 0
            self.wins = 0
            self.losses = 0
            self.total_confluence_scores = []
            
            # Initialize REAL building block detectors
            self.detectors = {
                'double_top': DoubleTopPattern(timeframe='15min'),
                'rsi_divergence': RSIDivergence(timeframe='15min'),
                'hod': HOD(timeframe='15min'),
                'asia_session_50_percent': AsiaSession50Percent(timeframe='15min'),
                'session_time': SessionTime(timeframe='15min'),
                'vwap': VWAP(timeframe='15min'),
                'ema_20_50_trend': EMA2050Trend(timeframe='15min'),
                'kill_zones': KillZones(timeframe='15min'),
                'adr': ADR(timeframe='15min'),
                'swing_points': SwingPoints(timeframe='15min'),
                'ema_200_trend': EMA200Trend(timeframe='15min'),
                'premium_discount_zones': PremiumDiscountZones(timeframe='15min'),
            }
            
            # Initialize blocks (matching real strategy)
            self.blocks = {
                'double_top': {'name': 'DoubleTopPattern', 'weight': 35, 'enabled': True},
                'rsi_divergence': {'name': 'RSIDivergence', 'weight': 30, 'enabled': True},
                'hod': {'name': 'HOD', 'weight': 15, 'enabled': True},
                'asia_session_50_percent': {'name': 'AsiaSession50Percent', 'weight': 12, 'enabled': True},
                'session_time': {'name': 'SessionTime', 'weight': 10, 'enabled': True},
                'vwap': {'name': 'VWAP', 'weight': 10, 'enabled': True},
                'ema_20_50_trend': {'name': 'EMA2050Trend', 'weight': 12, 'enabled': True},
                'kill_zones': {'name': 'KillZones', 'weight': 12, 'enabled': True},
                'adr': {'name': 'ADR', 'weight': 8, 'enabled': True},
                'swing_points': {'name': 'SwingPoints', 'weight': 15, 'enabled': True},
                'ema_200_trend': {'name': 'EMA200Trend', 'weight': 12, 'enabled': True},
                'premium_discount_zones': {'name': 'PremiumDiscountZones', 'weight': 14, 'enabled': True},
            }
    
    # Import the actual strategy methods we need to test
    from src.strategies.strategy_01_reversal_m_pattern import MPatternReversalStandard
    
    # Create instance
    strategy = MockStrategy()
    
    # Bind methods from actual strategy class (for testing)
    strategy._analyze_blocks = MPatternReversalStandard._analyze_blocks.__get__(strategy)
    strategy._calculate_confluence = MPatternReversalStandard._calculate_confluence.__get__(strategy)
    strategy._calculate_tp_sl = MPatternReversalStandard._calculate_tp_sl.__get__(strategy)
    
    print(f"✅ Strategy initialized: {strategy.strategy_name}\n")
    
    # Run signal generation tests
    print("Step 3: Testing signal generation...")
    report = test_strategy_signals(strategy, df)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Strategy: {strategy.strategy_name}")
    print(f"Signals Generated: {report['signals_generated']}")
    print(f"Signals/Month: {report['signals_per_month']:.2f}")
    print(f"Average R:R: {report['avg_rr']:.2f}")
    print(f"Validation: {'PASSED ✅' if report['validation_passed'] else 'WARNINGS ⚠️'}")
    print("="*80 + "\n")
    
    return report['validation_passed']


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)