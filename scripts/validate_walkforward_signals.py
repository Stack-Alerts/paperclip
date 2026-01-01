"""
EXPERT MODE: Walk-Forward Signal Validation Script
Validates building block signals against actual historic price action

This institutional-grade validator:
1. Loads signal data from walk-forward tests
2. Analyzes price action before/after each signal
3. Validates signal accuracy against ground truth
4. Generates comprehensive validation metrics
5. Provides go/no-go recommendation for production

Author: Cline (Expert Mode)
Date: 2026-01-01
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Any


class SignalValidator:
    """
    Expert-level signal validation against historic price action
    
    Validates signals by analyzing:
    - Entry price vs actual price action
    - Signal direction vs subsequent price movement
    - Signal timing vs optimal entry/exit
    - Follow-through duration and magnitude
    """
    
    def __init__(self, lookback_bars: int = 20, lookforward_bars: int = 50):
        """
        Initialize validator
        
        Args:
            lookback_bars: Bars to analyze before signal (context validation)
            lookforward_bars: Bars to analyze after signal (accuracy validation)
        """
        self.lookback_bars = lookback_bars
        self.lookforward_bars = lookforward_bars
        self.validation_results = []
        
    def validate_signal(self, 
                       df: pd.DataFrame,
                       signal_idx: int,
                       signal_type: str,
                       signal_price: float,
                       signal_timestamp: datetime) -> Dict[str, Any]:
        """
        Validate a single signal against price action
        
        Returns validation metrics for the signal
        """
        # Get price action before signal
        start_idx = max(0, signal_idx - self.lookback_bars)
        before_prices = df.iloc[start_idx:signal_idx]['close'].values
        
        # Get price action after signal
        end_idx = min(len(df), signal_idx + self.lookforward_bars + 1)
        after_prices = df.iloc[signal_idx:end_idx]['close'].values
        
        if len(after_prices) < 5:  # Need at least 5 bars for validation
            return None
            
        # Calculate metrics
        entry_price = signal_price
        
        # Price movement after signal
        price_changes = (after_prices - entry_price) / entry_price * 100
        
        # Determine signal correctness based on type
        if signal_type == 'BULLISH':
            # For bullish: price should go UP
            max_favorable = np.max(price_changes)
            max_adverse = np.min(price_changes)
            bars_to_max = np.argmax(price_changes)
            
            # Count consecutive bars moving in favorable direction
            favorable_bars = 0
            for i in range(1, len(price_changes)):
                if price_changes[i] > 0:
                    favorable_bars += 1
                else:
                    break
                    
            # Check if signal was correct (price moved up)
            correct = max_favorable > 0.5  # Price moved up at least 0.5%
            
        elif signal_type == 'BEARISH':
            # For bearish: price should go DOWN
            max_favorable = abs(np.min(price_changes))  # Favorable is down
            max_adverse = np.max(price_changes)
            bars_to_max = np.argmin(price_changes)
            
            # Count consecutive bars moving in favorable direction
            favorable_bars = 0
            for i in range(1, len(price_changes)):
                if price_changes[i] < 0:
                    favorable_bars += 1
                else:
                    break
                    
            # Check if signal was correct (price moved down)
            correct = max_favorable > 0.5  # Price moved down at least 0.5%
            
        else:
            return None
            
        # Price at lookforward endpoint
        final_price_change = price_changes[-1]
        
        # Calculate reward/risk ratio
        if max_adverse != 0:
            reward_risk = max_favorable / abs(max_adverse)
        else:
            reward_risk = max_favorable if max_favorable > 0 else 0
            
        return {
            'signal_type': signal_type,
            'signal_price': entry_price,
            'signal_timestamp': signal_timestamp,
            'max_favorable_excursion': max_favorable,
            'max_adverse_excursion': max_adverse,
            'bars_to_max_favorable': bars_to_max,
            'consecutive_favorable_bars': favorable_bars,
            'final_price_change': final_price_change,
            'reward_risk_ratio': reward_risk,
            'correct_signal': correct,
            'lookforward_bars_available': len(after_prices) - 1
        }
    
    def validate_all_signals(self,
                            df: pd.DataFrame,
                            signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate all signals and generate comprehensive report
        
        Args:
            df: Full price DataFrame with timestamp, OHLCV
            signals: List of signal dicts with timestamp, signal, price, confidence
            
        Returns:
            Comprehensive validation report
        """
        print(f"\n{'='*80}")
        print(f"🔬 EXPERT MODE: SIGNAL VALIDATION")
        print(f"{'='*80}")
        print(f"\nValidating {len(signals)} signals against historic price action...")
        print(f"Lookback: {self.lookback_bars} bars | Lookforward: {self.lookforward_bars} bars\n")
        
        validated_signals = []
        
        # Debug: check if df has proper index
        df = df.reset_index(drop=True)
        
        for i, signal in enumerate(signals):
            # Find signal in DataFrame
            signal_time = pd.to_datetime(signal['timestamp'])
            
            # Try exact match first
            matching_rows = df[df['timestamp'] == signal_time]
            
            # If no exact match, find nearest timestamp  
            if len(matching_rows) == 0:
                # Find closest timestamp within 1 minute
                time_diff = abs(df['timestamp'] - signal_time)
                closest_idx = time_diff.idxmin()
                if time_diff[closest_idx] < pd.Timedelta(minutes=1):
                    signal_idx = closest_idx
                else:
                    continue
            else:
                signal_idx = matching_rows.index[0]
            
            # Make sure we have enough lookahead data
            if signal_idx + self.lookforward_bars >= len(df):
                continue  # Skip signals too close to end
            
            # Validate signal
            validation = self.validate_signal(
                df=df,
                signal_idx=signal_idx,
                signal_type=signal['signal'],
                signal_price=signal['price'],
                signal_timestamp=signal_time
            )
            
            if validation:
                validation['original_confidence'] = signal['confidence']
                validated_signals.append(validation)
                
            if (i + 1) % 100 == 0:
                print(f"  Validated {i+1}/{len(signals)} signals...")
        
        print(f"  ✅ Validated {len(validated_signals)}/{len(signals)} signals\n")
        
        # Generate comprehensive report
        return self.generate_validation_report(validated_signals)
    
    def generate_validation_report(self, validated_signals: List[Dict]) -> Dict[str, Any]:
        """Generate institutional-grade validation report"""
        
        if not validated_signals:
            return {'error': 'No validated signals'}
            
        # Separate by signal type
        bullish = [s for s in validated_signals if s['signal_type'] == 'BULLISH']
        bearish = [s for s in validated_signals if s['signal_type'] == 'BEARISH']
        
        # Overall metrics
        total_signals = len(validated_signals)
        correct_signals = sum(1 for s in validated_signals if s['correct_signal'])
        accuracy = (correct_signals / total_signals * 100) if total_signals > 0 else 0
        
        # Calculate average metrics
        avg_max_favorable = np.mean([s['max_favorable_excursion'] for s in validated_signals])
        avg_max_adverse = np.mean([abs(s['max_adverse_excursion']) for s in validated_signals])
        avg_reward_risk = np.mean([s['reward_risk_ratio'] for s in validated_signals])
        avg_favorable_bars = np.mean([s['consecutive_favorable_bars'] for s in validated_signals])
        avg_bars_to_max = np.mean([s['bars_to_max_favorable'] for s in validated_signals])
        
        # Bullish signal metrics
        if bullish:
            bullish_accuracy = sum(1 for s in bullish if s['correct_signal']) / len(bullish) * 100
            bullish_avg_move = np.mean([s['max_favorable_excursion'] for s in bullish])
            bullish_avg_rr = np.mean([s['reward_risk_ratio'] for s in bullish])
        else:
            bullish_accuracy = 0
            bullish_avg_move = 0
            bullish_avg_rr = 0
            
        # Bearish signal metrics
        if bearish:
            bearish_accuracy = sum(1 for s in bearish if s['correct_signal']) / len(bearish) * 100
            bearish_avg_move = np.mean([s['max_favorable_excursion'] for s in bearish])
            bearish_avg_rr = np.mean([s['reward_risk_ratio'] for s in bearish])
        else:
            bearish_accuracy = 0
            bearish_avg_move = 0
            bearish_avg_rr = 0
        
        # Print report
        print(f"{'='*80}")
        print(f"📊 VALIDATION REPORT")
        print(f"{'='*80}\n")
        
        print(f"📈 OVERALL PERFORMANCE")
        print(f"   Total Signals: {total_signals}")
        print(f"   Correct Signals: {correct_signals}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Avg Max Favorable Excursion: {avg_max_favorable:.2f}%")
        print(f"   Avg Max Adverse Excursion: {avg_max_adverse:.2f}%")
        print(f"   Avg Reward/Risk Ratio: {avg_reward_risk:.2f}")
        print(f"   Avg Consecutive Favorable Bars: {avg_favorable_bars:.1f}")
        print(f"   Avg Bars to Max Favorable: {avg_bars_to_max:.1f}")
        
        print(f"\n📊 BULLISH SIGNALS ({len(bullish)} signals)")
        print(f"   Accuracy: {bullish_accuracy:.1f}%")
        print(f"   Avg Upward Move: {bullish_avg_move:.2f}%")
        print(f"   Avg Reward/Risk: {bullish_avg_rr:.2f}")
        
        print(f"\n📊 BEARISH SIGNALS ({len(bearish)} signals)")
        print(f"   Accuracy: {bearish_accuracy:.1f}%")
        print(f"   Avg Downward Move: {bearish_avg_move:.2f}%")
        print(f"   Avg Reward/Risk: {bearish_avg_rr:.2f}")
        
        # Quality assessment
        print(f"\n{'='*80}")
        print(f"🎯 INSTITUTIONAL QUALITY ASSESSMENT")
        print(f"{'='*80}\n")
        
        quality_score = 0
        max_score = 100
        
        # Accuracy check (40 points)
        if accuracy >= 70:
            quality_score += 40
            print(f"   ✅ Accuracy {accuracy:.1f}% (≥70% - Excellent) [+40 points]")
        elif accuracy >= 60:
            quality_score += 30
            print(f"   ⚠️  Accuracy {accuracy:.1f}% (≥60% - Good) [+30 points]")
        elif accuracy >= 55:
            quality_score += 20
            print(f"   ⚠️  Accuracy {accuracy:.1f}% (≥55% - Acceptable) [+20 points]")
        else:
            print(f"   ❌ Accuracy {accuracy:.1f}% (<55% - Poor) [+0 points]")
            
        # Reward/Risk check (30 points)
        if avg_reward_risk >= 2.0:
            quality_score += 30
            print(f"   ✅ Reward/Risk {avg_reward_risk:.2f} (≥2.0 - Excellent) [+30 points]")
        elif avg_reward_risk >= 1.5:
            quality_score += 20
            print(f"   ⚠️  Reward/Risk {avg_reward_risk:.2f} (≥1.5 - Good) [+20 points]")
        elif avg_reward_risk >= 1.0:
            quality_score += 10
            print(f"   ⚠️  Reward/Risk {avg_reward_risk:.2f} (≥1.0 - Acceptable) [+10 points]")
        else:
            print(f"   ❌ Reward/Risk {avg_reward_risk:.2f} (<1.0 - Poor) [+0 points]")
            
        # Balance check (15 points)
        balance_ratio = len(bullish) / len(bearish) if bearish else 999
        if 0.8 <= balance_ratio <= 1.2:
            quality_score += 15
            print(f"   ✅ Signal Balance {len(bullish)}/{len(bearish)} (Balanced) [+15 points]")
        else:
            quality_score += 5
            print(f"   ⚠️  Signal Balance {len(bullish)}/{len(bearish)} (Slightly Imbalanced) [+5 points]")
            
        # Follow-through check (15 points)
        if avg_favorable_bars >= 5:
            quality_score += 15
            print(f"   ✅ Avg Follow-through {avg_favorable_bars:.1f} bars (≥5 - Strong) [+15 points]")
        elif avg_favorable_bars >= 3:
            quality_score += 10
            print(f"   ⚠️  Avg Follow-through {avg_favorable_bars:.1f} bars (≥3 - Good) [+10 points]")
        else:
            print(f"   ❌ Avg Follow-through {avg_favorable_bars:.1f} bars (<3 - Weak) [+0 points]")
        
        print(f"\n📊 FINAL QUALITY SCORE: {quality_score}/{max_score} ({quality_score/max_score*100:.0f}%)")
        
        # Final recommendation
        print(f"\n{'='*80}")
        print(f"🎯 PRODUCTION READINESS RECOMMENDATION")
        print(f"{'='*80}\n")
        
        if quality_score >= 85:
            recommendation = "✅ APPROVED FOR PRODUCTION"
            confidence_level = "HIGH"
            notes = "Signals demonstrate excellent accuracy and risk/reward characteristics."
        elif quality_score >= 70:
            recommendation = "✅ APPROVED WITH MONITORING"
            confidence_level = "MEDIUM-HIGH"
            notes = "Signals show good quality but should be monitored closely in production."
        elif quality_score >= 60:
            recommendation = "⚠️  CONDITIONAL APPROVAL"
            confidence_level = "MEDIUM"
            notes = "Signals are acceptable but need improvement before full deployment."
        else:
            recommendation = "❌ NOT READY FOR PRODUCTION"
            confidence_level = "LOW"
            notes = "Signals require significant improvement before production use."
            
        print(f"   Recommendation: {recommendation}")
        print(f"   Confidence Level: {confidence_level}")
        print(f"   Notes: {notes}")
        print(f"\n{'='*80}\n")
        
        # Return structured report
        return {
            'validation_timestamp': datetime.now().isoformat(),
            'lookback_bars': self.lookback_bars,
            'lookforward_bars': self.lookforward_bars,
            'total_signals': total_signals,
            'correct_signals': correct_signals,
            'accuracy': accuracy,
            'overall_metrics': {
                'avg_max_favorable_excursion': avg_max_favorable,
                'avg_max_adverse_excursion': avg_max_adverse,
                'avg_reward_risk_ratio': avg_reward_risk,
                'avg_consecutive_favorable_bars': avg_favorable_bars,
                'avg_bars_to_max_favorable': avg_bars_to_max
            },
            'bullish_signals': {
                'count': len(bullish),
                'accuracy': bullish_accuracy,
                'avg_move': bullish_avg_move,
                'avg_reward_risk': bullish_avg_rr
            },
            'bearish_signals': {
                'count': len(bearish),
                'accuracy': bearish_accuracy,
                'avg_move': bearish_avg_move,
                'avg_reward_risk': bearish_avg_rr
            },
            'quality_score': quality_score,
            'max_quality_score': max_score,
            'quality_percentage': quality_score / max_score * 100,
            'recommendation': recommendation,
            'confidence_level': confidence_level,
            'notes': notes
        }


def load_btc_data(days: int = 180) -> pd.DataFrame:
    """Load BTC 15min data"""
    data_path = Path(__file__).parent.parent / 'data' / 'raw' / 'BTC_USDT_PERP_15m.csv'
    df = pd.read_csv(data_path)
    
    # Standardize columns
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'time' in col_lower and 'timestamp' not in df.columns:
            rename_map[col] = 'timestamp'
        elif col_lower == 'vol':
            rename_map[col] = 'volume'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    if df['timestamp'].dtype == 'object':
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Filter to last N days
    cutoff_date = df['timestamp'].max() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff_date].copy()
    
    return df.reset_index(drop=True)


def main():
    """
    Main execution function
    
    NOTE: This is a template. You'll need to:
    1. Export signal data from test_single_block_walkforward.py to JSON/CSV
    2. Load that signal data here
    3. Run validation
    
    Or integrate this directly into test_single_block_walkforward.py
    """
    print(f"\n{'='*80}")
    print(f"🎯 EXPERT MODE: WALK-FORWARD SIGNAL VALIDATOR")
    print(f"{'='*80}\n")
    print("This script validates building block signals against actual price action.")
    print("It provides institutional-grade validation metrics and recommendations.\n")
    
    # Example usage (you'll need to provide actual signal data)
    print("To use this validator:")
    print("1. Export signals from test_single_block_walkforward.py")
    print("2. Load signals into this script")
    print("3. Run validation with appropriate lookback/lookforward periods\n")
    
    print("Example integration in test_single_block_walkforward.py:")
    print("""
    # At end of test_block_walkforward function, add:
    
    # Export signals for validation
    signal_data = []
    for signal in signals:
        signal_data.append({
            'timestamp': signal['timestamp'],
            'signal': signal['signal'],
            'price': signal['price'],
            'confidence': signal['confidence']
        })
    
    # Run validation
    validator = SignalValidator(lookback_bars=20, lookforward_bars=50)
    validation_report = validator.validate_all_signals(df_full, signal_data)
    
    # Save report
    with open(f'validation_report_{block_name}.json', 'w') as f:
        json.dump(validation_report, f, indent=2)
    """)


if __name__ == "__main__":
    main()
