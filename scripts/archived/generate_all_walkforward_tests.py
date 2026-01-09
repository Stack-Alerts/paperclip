#!/usr/bin/env python3
"""
Generate Individual Walkforward Test Scripts for All Building Blocks
Creates one test script per block in scripts/walkforward_tests/
"""

import os
from pathlib import Path

# Complete list of all 67 building blocks from directory structure
BUILDING_BLOCKS = [
    # MOVING AVERAGES (6)
    ("moving_averages/ema_20_50_cross.py", "EMA2050Cross", "EMA_20_50_Cross"),
    ("moving_averages/ema_50_vector.py", "EMA50Vector", "EMA_50_Vector"),
    ("moving_averages/ema_55_vector.py", "EMA55VectorBreak", "EMA_55_Vector"),
    ("moving_averages/ema_200_trend.py", "EMA200Trend", "EMA_200_Trend"),
    ("moving_averages/ema_255_vector.py", "EMA255VectorBreak", "EMA_255_Vector"),
    ("moving_averages/ema_800_vector.py", "EMA800VectorBreak", "EMA_800_Vector"),
    
    # OSCILLATORS (3)
    ("oscillators/macd_signal.py", "MACDSignal", "MACD_Signal"),
    ("oscillators/rsi_divergence.py", "RSIDivergence", "RSI_Divergence"),
    ("oscillators/stochastic_rsi.py", "StochasticRSI", "Stochastic_RSI"),
    
    # PRICE ACTION (4)
    ("price_action/order_block.py", "OrderBlock", "Order_Block"),
    ("price_action/fair_value_gap.py", "FairValueGap", "Fair_Value_Gap"),
    ("price_action/liquidity_sweep.py", "LiquiditySweep", "Liquidity_Sweep"),
    ("price_action/breaker_block.py", "BreakerBlock", "Breaker_Block"),
    
    # TREND (2)
    ("trend/ichimoku_cloud.py", "IchimokuCloud", "Ichimoku_Cloud"),
    ("trend/adx.py", "ADX", "ADX"),
    
    # SMC/ICT (10)
    ("smc_ict/break_of_structure.py", "BreakOfStructure", "Break_Of_Structure"),
    ("smc_ict/market_structure_shift.py", "MarketStructureShift", "Market_Structure_Shift"),
    ("smc_ict/displacement.py", "Displacement", "Displacement"),
    ("smc_ict/inducement.py", "Inducement", "Inducement"),
    ("smc_ict/optimal_trade_entry.py", "OptimalTradeEntry", "Optimal_Trade_Entry"),
    ("smc_ict/swing_failure_pattern.py", "SwingFailurePattern", "Swing_Failure_Pattern"),
    ("smc_ict/premium_discount.py", "PremiumDiscount", "Premium_Discount"),
    ("smc_ict/change_of_character.py", "ChangeOfCharacter", "Change_Of_Character"),
    ("smc_ict/mitigation_block.py", "MitigationBlock", "Mitigation_Block"),
    ("smc_ict/balanced_price_range.py", "BalancedPriceRange", "Balanced_Price_Range"),
    
    # INSTITUTIONAL (1)
    ("institutional/vwap.py", "VWAP", "VWAP"),
    
    # VOLATILITY (3)
    ("volatility/atr.py", "ATR", "ATR"),
    ("volatility/adr.py", "ADR", "ADR"),
    ("volatility/bollinger_bands.py", "BollingerBands", "Bollinger_Bands"),
    
    # PATTERNS (15)
    ("patterns/double_top.py", "DoubleTop", "Double_Top"),
    ("patterns/double_bottom.py", "DoubleBottom", "Double_Bottom"),
    ("patterns/triple_top.py", "TripleTop", "Triple_Top"),
    ("patterns/triple_bottom.py", "TripleBottom", "Triple_Bottom"),
    ("patterns/head_and_shoulders.py", "HeadAndShoulders", "Head_And_Shoulders"),
    ("patterns/inverse_head_and_shoulders.py", "InverseHeadAndShoulders", "Inverse_Head_And_Shoulders"),
    ("patterns/cup_and_handle.py", "CupAndHandle", "Cup_And_Handle"),
    ("patterns/rounding_bottom.py", "RoundingBottom", "Rounding_Bottom"),
    ("patterns/flag_pattern.py", "FlagPattern", "Flag_Pattern"),
    ("patterns/pennant_pattern.py", "PennantPattern", "Pennant_Pattern"),
    ("patterns/symmetrical_triangle.py", "SymmetricalTriangle", "Symmetrical_Triangle"),
    ("patterns/ascending_triangle.py", "AscendingTriangle", "Ascending_Triangle"),
    ("patterns/descending_triangle.py", "DescendingTriangle", "Descending_Triangle"),
    ("patterns/falling_wedge.py", "FallingWedge", "Falling_Wedge"),
    ("patterns/rising_wedge.py", "RisingWedge", "Rising_Wedge"),
    
    # PRICE LEVELS (4)
    ("price_levels/hod.py", "HOD", "HOD"),
    ("price_levels/how.py", "HOW", "HOW"),
    ("price_levels/lod.py", "LOD", "LOD"),
    ("price_levels/low.py", "LOW", "LOW"),
    
    # SESSIONS (1)
    ("sessions/asia_session_50_percent.py", "AsiaSession50Percent", "Asia_Session_50_Percent"),
    
    # ELLIOTT WAVE (2)
    ("elliott_wave/elliott_wave_count.py", "ElliottWaveCount", "Elliott_Wave_Count"),
    ("elliott_wave/elliott_wave_oscillator.py", "ElliottWaveOscillator", "Elliott_Wave_Oscillator"),
    
    # WYCKOFF (3)
    ("wyckoff/wyckoff_accumulation.py", "WyckoffAccumulation", "Wyckoff_Accumulation"),
    ("wyckoff/wyckoff_distribution.py", "WyckoffDistribution", "Wyckoff_Distribution"),
    ("wyckoff/wyckoff_reaccumulation.py", "WyckoffReaccumulation", "Wyckoff_Reaccumulation"),
    
    # FIBONACCI (1)
    ("fibonacci/fibonacci_retracements.py", "FibonacciRetracements", "Fibonacci_Retracements"),
    
    # SUPPLY DEMAND (1)
    ("supply_demand/anchored_vwap.py", "AnchoredVWAP", "Anchored_VWAP"),
    
    # MARKET STRUCTURE (1)
    ("market_structure/kill_zones.py", "KillZones", "Kill_Zones"),
]

TEMPLATE = '''"""
Walk-Forward Test for {display_name}
Auto-generated test script for individual block validation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Standardize column names
    if 'Timestamp' in df.columns:
        df.rename(columns={{
            'Timestamp': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }}, inplace=True)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Filter to last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def test_block_walkforward(block, block_name: str, df_full: pd.DataFrame):
    """Walk-forward test the block"""
    
    print("="*80)
    print(f"🔬 WALK-FORWARD TEST: {{block_name}}")
    print("="*80)
    print(f"Full Dataset: {{len(df_full)}} bars from {{df_full['timestamp'].min()}} to {{df_full['timestamp'].max()}}")
    
    # Test on full period
    all_signals = []
    window_size = 100
    
    print(f"\\nTesting with expanding window (min {{window_size}} bars)...")
    
    for i in range(window_size, len(df_full), 20):  # Test every 20th bar
        hist_df = df_full.iloc[:i+1].copy()
        
        try:
            result = block.analyze(hist_df)
            
            if result and isinstance(result, dict):
                signal = result.get('signal', 'UNKNOWN')
                confidence = result.get('confidence', 0)
                
                # Skip non-actionable signals
                if signal not in ['NEUTRAL', 'INSUFFICIENT_DATA', 'ERROR', 'NO_BREAK']:
                    all_signals.append({{
                        'timestamp': hist_df['timestamp'].iloc[-1],
                        'signal': signal,
                        'confidence': confidence,
                        'price': hist_df['close'].iloc[-1],
                        'bar_index': i
                    }})
                    
                    if len(all_signals) <= 10:  # Show first 10 signals
                        print(f"  🎯 Signal {{len(all_signals)}}: {{signal}} @ {{hist_df['timestamp'].iloc[-1]}} | "
                              f"Price: ${{hist_df['close'].iloc[-1]:.2f}} | Confidence: {{confidence}}%")
        
        except Exception as e:
            if i == window_size:  # Only print first error
                print(f"  ⚠️  Error at bar {{i}}: {{e}}")
    
    # Summary
    print(f"\\n📊 RESULTS:")
    print(f"   Total signals: {{len(all_signals)}}")
    
    if all_signals:
        confidences = [s['confidence'] for s in all_signals]
        print(f"   Avg confidence: {{np.mean(confidences):.1f}}%")
        
        # Signal types
        signal_types = {{}}
        for s in all_signals:
            signal_types[s['signal']] = signal_types.get(s['signal'], 0) + 1
        
        print(f"   Signal distribution:")
        for sig_type, count in sorted(signal_types.items(), key=lambda x: -x[1]):
            print(f"      {{sig_type}}: {{count}}")
        
        # Calculate signals per day
        days = (df_full['timestamp'].max() - df_full['timestamp'].min()).days
        density = len(all_signals) / max(1, days)
        print(f"\\n   Signal density: {{density:.2f}} signals/day")
        
        # Save results to proper directory structure
        output_dir = Path(__file__).parent.parent.parent / 'data' / 'reports' / 'walkforward_tests'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f'walkforward_results_{{block_name}}.json'
        results = {{
            'block': block_name,
            'total_signals': len(all_signals),
            'avg_confidence': float(np.mean(confidences)),
            'signal_types': signal_types,
            'signals_per_day': float(density),
            'test_period': {{
                'start': str(df_full['timestamp'].min()),
                'end': str(df_full['timestamp'].max()),
                'days': days,
                'bars': len(df_full)
            }}
        }}
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\\n✅ Results saved to: {{output_file}}")
    else:
        print("   ❌ NO SIGNALS GENERATED")
    
    print("="*80)


if __name__ == "__main__":
    from src.detectors.building_blocks.{rel_path_import} import {class_name}
    
    print("Loading 180 days of BTC 15min data...")
    df = load_btc_data(days=180)
    
    if df is not None and len(df) > 0:
        block = {class_name}()
        test_block_walkforward(block, "{file_name}", df)
    else:
        print("❌ Failed to load data")
'''


def generate_all_test_scripts():
    """Generate individual test script for each building block"""
    
    output_dir = Path(__file__).parent / 'walkforward_tests'
    output_dir.mkdir(exist_ok=True)
    
    print(f"Generating test scripts in: {output_dir}")
    print(f"Total blocks to process: {len(BUILDING_BLOCKS)}")
    print("="*80)
    
    for idx, (rel_path, class_name, display_name) in enumerate(BUILDING_BLOCKS, 1):
        # Create import path (replace / with .)
        import_path = rel_path.replace('.py', '').replace('/', '.')
        
        # Create file name
        file_name = display_name.lower().replace('_', '_')
        output_filename = f"{idx:02d}_test_{file_name}.py"
        output_path = output_dir / output_filename
        
        # Generate script content
        content = TEMPLATE.format(
            display_name=display_name.replace('_', ' '),
            rel_path_import=rel_path.replace('.py', '').replace('/', '.'),
            class_name=class_name,
            file_name=file_name
        )
        
        # Write file
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"✅ [{idx:02d}/67] {output_filename}")
    
    print("="*80)
    print(f"✅ Generated {len(BUILDING_BLOCKS)} test scripts successfully!")
    print(f"📁 Location: {output_dir}")


if __name__ == "__main__":
    generate_all_test_scripts()
