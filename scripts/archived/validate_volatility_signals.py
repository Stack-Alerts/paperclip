"""
EXPERT MODE: Volatility Signal Validator
Validates volatility-based descriptive signals against actual price volatility

For signals like:
- VOLATILITY_HIGH, VOLATILITY_CALM, VOLATILITY_RISING, etc.
- SQUEEZE_BREAKOUT_BULL, NEAR_UPPER, BELOW_LOWER, etc.

Validation Logic:
- Measure actual volatility after signal
- Compare to expected volatility level
- Calculate accuracy based on volatility prediction correctness

Author: Cline (Expert Mode)
Date: 2026-01-01
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime


class VolatilitySignalValidator:
    """
    Expert-level validator for volatility/descriptive signals
    
    Unlike directional signals (BULLISH/BEARISH), volatility signals
    describe market state (VOLATILITY_HIGH, CALM, etc.)
    
    Validates by checking if actual volatility matches predicted level
    """
    
    def __init__(self, lookback_bars: int = 20, lookforward_bars: int = 50):
        """
        Initialize validator
        
        Args:
            lookback_bars: Bars to look back for baseline volatility
            lookforward_bars: Bars to look forward to measure actual volatility
        """
        self.lookback_bars = lookback_bars
        self.lookforward_bars = lookforward_bars
        
        # Volatility level thresholds (ATR % of price)
        self.volatility_thresholds = {
            'CALM': (0, 0.5),           # 0-0.5% ATR
            'NORMAL': (0.5, 1.5),       # 0.5-1.5% ATR
            'HIGH': (1.5, 2.5),         # 1.5-2.5% ATR
            'VERY_HIGH': (2.5, 4.0),    # 2.5-4.0% ATR
            'EXTREME': (4.0, 100.0)     # >4.0% ATR
        }
    
    def calculate_atr_percent(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate ATR as percentage of price
        
        Args:
            df: OHLCV DataFrame
            period: ATR period
            
        Returns:
            ATR as percentage of current price
        """
        if len(df) < period + 1:
            return 0.0
        
        # True Range
        high_low = df['high'] - df['low']
        high_prev_close = abs(df['high'] - df['close'].shift(1))
        low_prev_close = abs(df['low'] - df['close'].shift(1))
        
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        
        # ATR (exponential moving average)
        atr = true_range.ewm(alpha=1/period, adjust=False).mean()
        
        current_atr = atr.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        return (current_atr / current_price) * 100 if current_price > 0 else 0.0
    
    def classify_actual_volatility(self, atr_percent: float) -> str:
        """
        Classify actual volatility into levels
        
        Args:
            atr_percent: ATR as percentage
            
        Returns:
            Volatility classification
        """
        for level, (low, high) in self.volatility_thresholds.items():
            if low <= atr_percent < high:
                return level
        return 'EXTREME'
    
    def validate_single_signal(self, df: pd.DataFrame, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single volatility signal
        
        Args:
            df: Full OHLCV DataFrame
            signal: Signal dictionary with timestamp, signal, confidence
            
        Returns:
            Validation result dictionary
        """
        # Find signal bar index
        signal_timestamp = signal['timestamp']
        signal_idx = df[df['timestamp'] == signal_timestamp].index
        
        if len(signal_idx) == 0:
            return {'error': 'Signal timestamp not found in data'}
        
        signal_idx = signal_idx[0]
        
        # Need enough bars before and after
        if signal_idx < self.lookback_bars:
            return {'error': 'Insufficient lookback data'}
        
        if signal_idx + self.lookforward_bars >= len(df):
            return {'error': 'Insufficient lookforward data'}
        
        # Get signal type and extract volatility level
        signal_type = signal['signal']
        
        # Parse signal to get predicted volatility level
        predicted_level = self.parse_volatility_level(signal_type)
        
        if not predicted_level:
            return {'error': f'Unknown signal type: {signal_type}'}
        
        # Calculate baseline volatility (before signal)
        baseline_df = df.iloc[signal_idx - self.lookback_bars:signal_idx + 1]
        baseline_volatility = self.calculate_atr_percent(baseline_df)
        
        # Calculate actual volatility (after signal)
        actual_df = df.iloc[signal_idx:signal_idx + self.lookforward_bars + 1]
        actual_volatility = self.calculate_atr_percent(actual_df)
        
        # Classify actual volatility
        actual_level = self.classify_actual_volatility(actual_volatility)
        
        # Check if prediction was correct
        is_correct = (predicted_level == actual_level)
        
        # For RISING/FALLING, check trend
        if 'RISING' in signal_type:
            is_correct = actual_volatility > baseline_volatility * 1.1  # 10% increase
        elif 'FALLING' in signal_type:
            is_correct = actual_volatility < baseline_volatility * 0.9  # 10% decrease
        elif 'STABLE' in signal_type:
            is_correct = abs(actual_volatility - baseline_volatility) < baseline_volatility * 0.1  # Within 10%
        
        return {
            'signal_type': signal_type,
            'predicted_level': predicted_level,
            'actual_level': actual_level,
            'baseline_volatility': baseline_volatility,
            'actual_volatility': actual_volatility,
            'is_correct': is_correct,
            'volatility_change_pct': ((actual_volatility - baseline_volatility) / baseline_volatility * 100) if baseline_volatility > 0 else 0,
            'timestamp': signal_timestamp,
            'bar_index': signal_idx
        }
    
    def parse_volatility_level(self, signal_type: str) -> str:
        """
        Parse volatility level from signal type
        
        Args:
            signal_type: Signal string (e.g., 'VOLATILITY_HIGH', 'CALM', 'SQUEEZE_BREAKOUT_BULL')
            
        Returns:
            Volatility level or special indicator
        """
        signal_upper = signal_type.upper()
        
        # Direct volatility level keywords (with or without VOLATILITY_ prefix)
        # Handles both 'VOLATILITY_HIGH' and 'HIGH', 'CALM' and 'VOLATILITY_CALM', etc.
        if 'EXTREME' in signal_upper:
            return 'EXTREME'
        elif 'VERY_HIGH' in signal_upper or 'VERY HIGH' in signal_upper:
            return 'VERY_HIGH'
        elif 'ELEVATED' in signal_upper:  # ADR uses ELEVATED for HIGH
            return 'HIGH'
        elif 'HIGH' in signal_upper and 'VERY' not in signal_upper:
            return 'HIGH'
        elif 'NORMAL' in signal_upper:
            return 'NORMAL'
        elif 'CALM' in signal_upper or (signal_upper == 'LOW'):
            return 'CALM'
        
        # Trend signals
        if 'RISING' in signal_upper or 'EXPANDING' in signal_upper:
            return 'RISING'
        if 'FALLING' in signal_upper or 'CONTRACTING' in signal_upper:
            return 'FALLING'
        if 'STABLE' in signal_upper:
            return 'STABLE'
        
        # Bollinger Bands signals (imply volatility levels)
        if 'SQUEEZE' in signal_upper:
            return 'CALM'  # Squeeze = low volatility
        if 'BREAKOUT' in signal_upper:
            return 'HIGH'  # Breakout = high volatility spike
        
        return None
    
    def validate_all_signals(self, df: pd.DataFrame, signals: List[Dict]) -> Dict[str, Any]:
        """
        Validate all signals
        
        Args:
            df: Full OHLCV DataFrame
            signals: List of signal dictionaries
            
        Returns:
            Comprehensive validation report
        """
        print(f"\n{'='*80}")
        print(f"🔬 EXPERT MODE: VOLATILITY SIGNAL VALIDATION")
        print(f"{'='*80}\n")
        print(f"Validating {len(signals)} signals against actual volatility...")
        print(f"Lookback: {self.lookback_bars} bars | Lookforward: {self.lookforward_bars} bars\n")
        
        validated_signals = []
        errors = 0
        
        for i, signal in enumerate(signals):
            if (i + 1) % 100 == 0 or i == 0:
                print(f"  Validated {i+1}/{len(signals)} signals...")
            
            result = self.validate_single_signal(df, signal)
            
            if 'error' in result:
                errors += 1
                continue
            
            validated_signals.append(result)
        
        print(f"  ✅ Validated {len(validated_signals)}/{len(signals)} signals\n")
        
        if len(validated_signals) == 0:
            return {
                'error': 'No signals could be validated',
                'total_signals': len(signals),
                'validation_errors': errors
            }
        
        # Calculate metrics
        correct_signals = [s for s in validated_signals if s['is_correct']]
        accuracy = (len(correct_signals) / len(validated_signals)) * 100
        
        # Group by predicted level
        level_stats = {}
        for level in list(self.volatility_thresholds.keys()) + ['RISING', 'FALLING', 'STABLE']:
            level_signals = [s for s in validated_signals if s['predicted_level'] == level]
            if level_signals:
                level_correct = [s for s in level_signals if s['is_correct']]
                level_stats[level] = {
                    'count': len(level_signals),
                    'correct': len(level_correct),
                    'accuracy': (len(level_correct) / len(level_signals)) * 100,
                    'avg_actual_volatility': np.mean([s['actual_volatility'] for s in level_signals]),
                    'avg_volatility_change': np.mean([s['volatility_change_pct'] for s in level_signals])
                }
        
        # Calculate avg volatility metrics
        avg_baseline_vol = np.mean([s['baseline_volatility'] for s in validated_signals])
        avg_actual_vol = np.mean([s['actual_volatility'] for s in validated_signals])
        avg_vol_change = np.mean([s['volatility_change_pct'] for s in validated_signals])
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(
            accuracy,
            len(validated_signals),
            level_stats
        )
        
        # Print report
        self.print_validation_report(
            len(validated_signals),
            accuracy,
            level_stats,
            avg_baseline_vol,
            avg_actual_vol,
            avg_vol_change,
            quality_score
        )
        
        return {
            'total_signals': len(validated_signals),
            'correct_signals': len(correct_signals),
            'accuracy': accuracy,
            'quality_score': quality_score,
            'level_statistics': level_stats,
            'overall_metrics': {
                'avg_baseline_volatility': avg_baseline_vol,
                'avg_actual_volatility': avg_actual_vol,
                'avg_volatility_change_pct': avg_vol_change
            },
            'validated_signals': validated_signals
        }
    
    def calculate_quality_score(self, accuracy: float, signal_count: int, 
                                level_stats: Dict) -> int:
        """
        Calculate quality score 0-100
        
        Args:
            accuracy: Overall accuracy percentage
            signal_count: Number of signals
            level_stats: Statistics by level
            
        Returns:
            Quality score 0-100
        """
        score = 0
        
        # Accuracy component (max 40 points)
        if accuracy >= 70:
            score += 40
        elif accuracy >= 60:
            score += 30
        elif accuracy >= 55:
            score += 20
        elif accuracy >= 50:
            score += 10
        
        # Signal count component (max 20 points)
        if signal_count >= 100:
            score += 20
        elif signal_count >= 50:
            score += 15
        elif signal_count >= 20:
            score += 10
        elif signal_count >= 10:
            score += 5
        
        # Level diversity component (max 20 points)
        num_levels = len(level_stats)
        if num_levels >= 4:
            score += 20
        elif num_levels >= 3:
            score += 15
        elif num_levels >= 2:
            score += 10
        elif num_levels >= 1:
            score += 5
        
        # Level accuracy consistency (max 20 points)
        if level_stats:
            level_accuracies = [stats['accuracy'] for stats in level_stats.values()]
            min_level_acc = min(level_accuracies)
            if min_level_acc >= 60:
                score += 20
            elif min_level_acc >= 50:
                score += 15
            elif min_level_acc >= 40:
                score += 10
            elif min_level_acc >= 30:
                score += 5
        
        return min(100, score)
    
    def print_validation_report(self, total_signals: int, accuracy: float,
                               level_stats: Dict, avg_baseline: float,
                               avg_actual: float, avg_change: float,
                               quality_score: int):
        """Print formatted validation report"""
        print(f"{'='*80}")
        print(f"📊 VOLATILITY VALIDATION REPORT")
        print(f"{'='*80}\n")
        
        print(f"📈 OVERALL PERFORMANCE")
        print(f"   Total Signals: {total_signals}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Avg Baseline Volatility: {avg_baseline:.2f}%")
        print(f"   Avg Actual Volatility: {avg_actual:.2f}%")
        print(f"   Avg Volatility Change: {avg_change:+.1f}%\n")
        
        print(f"📊 BY VOLATILITY LEVEL")
        for level, stats in sorted(level_stats.items()):
            print(f"   {level}: {stats['count']} signals")
            print(f"      Accuracy: {stats['accuracy']:.1f}%")
            print(f"      Avg Actual Vol: {stats['avg_actual_volatility']:.2f}%")
            print(f"      Avg Vol Change: {stats['avg_volatility_change']:+.1f}%\n")
        
        print(f"{'='*80}")
        print(f"🎯 INSTITUTIONAL QUALITY ASSESSMENT")
        print(f"{'='*80}\n")
        
        # Print quality assessment
        if accuracy >= 70:
            print(f"   ✅ Accuracy {accuracy:.1f}% (≥70% - Excellent) [+40 points]")
        elif accuracy >= 60:
            print(f"   ✅ Accuracy {accuracy:.1f}% (≥60% - Good) [+30 points]")
        elif accuracy >= 55:
            print(f"   ⚠️  Accuracy {accuracy:.1f}% (≥55% - Acceptable) [+20 points]")
        elif accuracy >= 50:
            print(f"   ⚠️  Accuracy {accuracy:.1f}% (≥50% - Marginal) [+10 points]")
        else:
            print(f"   ❌ Accuracy {accuracy:.1f}% (<50% - Poor) [+0 points]")
        
        if total_signals >= 100:
            print(f"   ✅ Signal Count {total_signals} (≥100 - Excellent) [+20 points]")
        elif total_signals >= 50:
            print(f"   ✅ Signal Count {total_signals} (≥50 - Good) [+15 points]")
        elif total_signals >= 20:
            print(f"   ⚠️  Signal Count {total_signals} (≥20 - Acceptable) [+10 points]")
        else:
            print(f"   ❌ Signal Count {total_signals} (<20 - Low) [+5 points]")
        
        print(f"\n📊 FINAL QUALITY SCORE: {quality_score}/100 ({quality_score}%)\n")
        
        print(f"{'='*80}")
        print(f"🎯 PRODUCTION READINESS RECOMMENDATION")
        print(f"{'='*80}\n")
        
        if quality_score >= 80:
            print(f"   Recommendation: ✅ APPROVED FOR PRODUCTION")
            print(f"   Confidence Level: HIGH")
            print(f"   Notes: Volatility predictions are reliable and consistent.\n")
        elif quality_score >= 70:
            print(f"   Recommendation: ✅ APPROVED WITH MONITORING")
            print(f"   Confidence Level: MEDIUM-HIGH")
            print(f"   Notes: Good quality but monitor in production for improvements.\n")
        elif quality_score >= 60:
            print(f"   Recommendation: ⚠️  CONDITIONAL APPROVAL")
            print(f"   Confidence Level: MEDIUM")
            print(f"   Notes: Acceptable but needs improvement before full deployment.\n")
        else:
            print(f"   Recommendation: ❌ NOT READY FOR PRODUCTION")
            print(f"   Confidence Level: LOW")
            print(f"   Notes: Volatility predictions need significant improvement.\n")
        
        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Test with sample data
    print("Volatility Signal Validator - Ready for use with ATR, Bollinger Bands, ADR, etc.")
