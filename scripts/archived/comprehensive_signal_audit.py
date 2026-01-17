"""
COMPREHENSIVE BUILDING BLOCK SIGNAL AUDIT
==========================================

Test EVERY building block to determine actual signal names returned.
This is CRITICAL for ConfluenceCalculator accuracy.

Author: BTC_Engine_v3
Date: 2026-01-09
Purpose: Audit all building blocks and document actual signals
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import importlib
import inspect

# Create comprehensive test data
def create_test_data(bars=300, trend='neutral'):
    """Create realistic test data with various market conditions"""
    dates = pd.date_range(start='2025-01-01', periods=bars, freq='15min')
    np.random.seed(42)
    
    # Base price with trend
    if trend == 'bullish':
        base_prices = 50000 + np.cumsum(np.random.randn(bars) * 30 + 10)
    elif trend == 'bearish':
        base_prices = 55000 + np.cumsum(np.random.randn(bars) * 30 - 10)
    else:
        base_prices = 50000 + np.cumsum(np.random.randn(bars) * 50)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': base_prices,
        'high': base_prices + np.random.rand(bars) * 100,
        'low': base_prices - np.random.rand(bars) * 100,
        'close': base_prices + np.random.randn(bars) * 50,
        'volume': np.random.rand(bars) * 1000 + 500
    })
    
    return df

# Building blocks organized by category
BUILDING_BLOCKS = {
    'PATTERNS': [
        ('patterns.double_top', 'DoubleTop'),
        ('patterns.double_bottom', 'DoubleBottom'),
        ('patterns.triple_top', 'TripleTop'),
        ('patterns.triple_bottom', 'TripleBottom'),
        ('patterns.head_and_shoulders', 'HeadAndShoulders'),
        ('patterns.inverse_head_and_shoulders', 'InverseHeadAndShoulders'),
    ],
    'OSCILLATORS': [
        ('oscillators.rsi_divergence', 'RSIDivergence'),
        ('oscillators.macd_signal', 'MACDSignal'),
        ('oscillators.stochastic_rsi', 'StochasticRSI'),
    ],
    'PRICE_LEVELS': [
        ('price_levels.hod', 'HOD'),
        ('price_levels.lod', 'LOD'),
        ('price_levels.asia_50', 'Asia50'),
        ('price_levels.london_open', 'LondonOpen'),
        ('price_levels.ny_open', 'NYOpen'),
    ],
    'SESSIONS': [
        ('sessions.session_time', 'SessionTime'),
        ('sessions.kill_zones', 'KillZones'),
    ],
    'MOVING_AVERAGES': [
        ('moving_averages.ema_20_50_trend', 'EMA2050Trend'),
        ('moving_averages.ema_20_50_cross', 'EMA2050Cross'),
        ('moving_averages.ema_200_trend', 'EMA200Trend'),
        ('moving_averages.ema_50_vector', 'EMA50Vector'),
    ],
    'MARKET_STRUCTURE': [
        ('market_structure.swing_points', 'SwingPoints'),
        ('market_structure.premium_discount_zones', 'PremiumDiscountZones'),
        ('market_structure.market_structure_shift', 'MarketStructureShift'),
    ],
    'VOLATILITY': [
        ('volatility.atr', 'ATR'),
        ('volatility.adr', 'ADR'),
        ('volatility.bollinger_bands', 'BollingerBands'),
    ],
    'INSTITUTIONAL': [
        ('institutional.vwap', 'VWAP'),
        ('institutional.anchored_vwap', 'AnchoredVWAP'),
        ('institutional.volume_profile', 'VolumeProfile'),
    ],
    'SMC_ICT': [
        ('smc_ict.order_block', 'OrderBlock'),
        ('smc_ict.fair_value_gap', 'FairValueGap'),
        ('smc_ict.liquidity_sweep', 'LiquiditySweep'),
        ('smc_ict.break_of_structure', 'BreakOfStructure'),
        ('smc_ict.change_of_character', 'ChangeOfCharacter'),
    ],
}

def test_building_block(module_path, class_name, df):
    """Test a single building block and return its signals"""
    try:
        # Import the module
        full_path = f'src.detectors.building_blocks.{module_path}'
        module = importlib.import_module(full_path)
        
        # Get the class
        detector_class = getattr(module, class_name)
        
        # Instantiate
        detector = detector_class(timeframe='15min')
        
        # Analyze
        result = detector.analyze(df)
        
        return {
            'status': 'SUCCESS',
            'signal': result.get('signal', 'UNKNOWN'),
            'confidence': result.get('confidence', 0),
            'metadata_keys': list(result.get('metadata', {}).keys()),
            'has_confluence_factors': 'confluence_factors' in result,
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'error': str(e),
            'signal': None,
            'confidence': None,
        }

def main():
    """Run comprehensive audit of all building blocks"""
    
    print("="*100)
    print("COMPREHENSIVE BUILDING BLOCK SIGNAL AUDIT")
    print("="*100)
    print("\nTesting all building blocks with multiple market conditions...")
    print("This will take ~1-2 minutes to complete.\n")
    
    # Test with different market conditions
    test_conditions = {
        'neutral': create_test_data(300, 'neutral'),
        'bullish': create_test_data(300, 'bullish'),
        'bearish': create_test_data(300, 'bearish'),
    }
    
    all_results = {}
    
    for category, blocks in BUILDING_BLOCKS.items():
        print(f"\n{'='*100}")
        print(f"CATEGORY: {category}")
        print(f"{'='*100}")
        
        for module_path, class_name in blocks:
            block_key = module_path.split('.')[-1]
            print(f"\n📦 Testing: {block_key} ({class_name})")
            print(f"   Module: {module_path}")
            
            all_results[block_key] = {
                'class_name': class_name,
                'module_path': module_path,
                'category': category,
                'signals_found': set(),
                'conditions_tested': {},
            }
            
            for condition_name, df in test_conditions.items():
                result = test_building_block(module_path, class_name, df)
                
                all_results[block_key]['conditions_tested'][condition_name] = result
                
                if result['status'] == 'SUCCESS':
                    signal = result['signal']
                    all_results[block_key]['signals_found'].add(signal)
                    
                    print(f"   ✅ {condition_name:>10}: {signal} @ {result['confidence']}%")
                else:
                    print(f"   ❌ {condition_name:>10}: ERROR - {result['error']}")
            
            # Summary for this block
            unique_signals = all_results[block_key]['signals_found']
            print(f"\n   📊 Unique signals found: {len(unique_signals)}")
            for sig in sorted(unique_signals):
                print(f"      - {sig}")
    
    # Generate comprehensive report
    print("\n" + "="*100)
    print("GENERATING COMPREHENSIVE REPORT")
    print("="*100)
    
    report_lines = []
    report_lines.append("# BUILDING BLOCK SIGNAL REFERENCE")
    report_lines.append("=" * 100)
    report_lines.append("")
    report_lines.append("**Generated:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    report_lines.append("**Purpose:** Comprehensive reference of actual signals returned by each building block")
    report_lines.append("**Usage:** Update ConfluenceCalculator.SIGNAL_TIERS to match these EXACT signal names")
    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    for category, blocks in BUILDING_BLOCKS.items():
        report_lines.append(f"\n## {category}")
        report_lines.append("-" * 100)
        report_lines.append("")
        
        for module_path, class_name in blocks:
            block_key = module_path.split('.')[-1]
            
            if block_key not in all_results:
                continue
            
            block_data = all_results[block_key]
            signals = sorted(block_data['signals_found'])
            
            report_lines.append(f"### {block_key}")
            report_lines.append(f"**Class:** `{class_name}`  ")
            report_lines.append(f"**Module:** `src.detectors.building_blocks.{module_path}`  ")
            report_lines.append("")
            report_lines.append("**Possible Signals:**")
            
            if signals:
                for sig in signals:
                    report_lines.append(f"- `{sig}`")
            else:
                report_lines.append("- ⚠️ NO SIGNALS DETECTED (may need specific conditions)")
            
            report_lines.append("")
            
            # Add test results
            report_lines.append("**Test Results:**")
            for condition, result in block_data['conditions_tested'].items():
                if result['status'] == 'SUCCESS':
                    report_lines.append(f"- {condition}: `{result['signal']}` @ {result['confidence']}%")
                else:
                    report_lines.append(f"- {condition}: ❌ ERROR - {result.get('error', 'Unknown')}")
            
            report_lines.append("")
    
    # Save report
    report_path = Path('docs/v3/building_blocks/BUILDING_BLOCK_SIGNAL_REFERENCE.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n✅ Comprehensive report saved to: {report_path}")
    
    # Generate ConfluenceCalculator update suggestions
    print("\n" + "="*100)
    print("CONFLUENCE CALCULATOR UPDATE NEEDED")
    print("="*100)
    print("\nThe following blocks need signal tier definitions:")
    
    for block_key, data in all_results.items():
        if data['signals_found']:
            print(f"\n'{block_key}': {{")
            print(f"    'tiers': {{")
            for signal in sorted(data['signals_found']):
                if signal not in ['ERROR', 'INSUFFICIENT_DATA', 'NO_SIGNAL']:
                    print(f"        '{signal}': {{'base_points': XX, 'formula': 'scaled'}},")
            print(f"    }}")
            print(f"}},")
    
    print("\n" + "="*100)
    print("AUDIT COMPLETE")
    print("="*100)
    print(f"\n📊 Total blocks tested: {len(all_results)}")
    print(f"📄 Report location: {report_path}")
    print("\n🔧 Next steps:")
    print("   1. Review the generated report")
    print("   2. Update ConfluenceCalculator.SIGNAL_TIERS with exact signal names")
    print("   3. Test with optimizer to verify all blocks score correctly")
    print("="*100)

if __name__ == '__main__':
    main()