"""
LuxAlgo Initial Balance Breakout Signals - Advanced Usage Examples
===================================================================

Advanced analysis utilities for Initial Balance trading strategies,
including confluence detection, advanced signal filtering, and
performance analytics.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from luxalgo_initial_balance import (
    InitialBalanceDetector,
    InitialBalance,
    BreakoutSignal,
    BreakoutDirection,
    SessionType,
    ForecastMethod,
)


class IBTradeAnalyzer:
    """Advanced analyzer for Initial Balance trading opportunities."""
    
    def __init__(self, detector: InitialBalanceDetector):
        self.detector = detector
    
    def find_high_probability_setups(
        self,
        df: pd.DataFrame,
        ib: InitialBalance,
        signals: List[BreakoutSignal],
        min_distance_pct: float = 0.1,
        volume_threshold: float = 1.5,
    ) -> Dict[str, List[Dict]]:
        """
        Identify high-probability trading setups from IB signals.
        
        Filters based on:
        - Signal strength
        - Volume confirmation
        - Distance from IB extreme
        """
        setups = {
            'bullish_high_prob': [],
            'bearish_high_prob': [],
            'bullish_medium_prob': [],
            'bearish_medium_prob': [],
        }
        
        avg_volume = df['volume'].tail(20).mean()
        
        for signal in signals:
            distance_pct = signal.get_distance_from_ib() / ib.get_ib_range()
            volume_ratio = df[df.index == signal.timestamp]['volume'].values[0] / avg_volume
            
            # Skip weak setups
            if distance_pct < min_distance_pct and signal.signal_strength == 'weak':
                continue
            
            probability = 'high_prob' if signal.volume_confirmed else 'medium_prob'
            direction = 'bullish' if signal.direction == BreakoutDirection.BULLISH else 'bearish'
            
            key = f'{direction}_{probability}'
            
            setups[key].append({
                'timestamp': signal.timestamp,
                'price': signal.price,
                'distance_pct': distance_pct,
                'volume_ratio': volume_ratio,
                'strength': signal.signal_strength,
                'confirmation_bars': signal.confirmation_bars,
            })
        
        return setups
    
    def analyze_fibonacci_support(
        self,
        df: pd.DataFrame,
        fibs: 'FibonacciLevels',  # Type hint as string to avoid import issues
        ib: InitialBalance,
    ) -> Dict[str, float]:
        """
        Analyze price interaction with Fibonacci levels.
        
        Returns price strength at each Fibonacci level.
        """
        analysis = {}
        current_price = df['close'].iloc[-1]
        
        fib_levels = fibs.get_all_levels()
        
        for level_name, level_price in fib_levels.items():
            distance = abs(current_price - level_price)
            distance_pct = (distance / ib.get_ib_range()) * 100
            
            # Check if price recently tested this level
            tested = (df['low'].tail(50).min() <= level_price <= df['high'].tail(50).max())
            
            analysis[level_name] = {
                'price': level_price,
                'distance_from_current': distance,
                'distance_pct': distance_pct,
                'tested_recently': tested,
                'above_current': level_price > current_price,
            }
        
        return analysis
    
    def calculate_extension_targets(
        self,
        ib: InitialBalance,
        extensions,  # IBExtensions type
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate profit targets based on extensions.
        
        Returns zones where traders typically take profits.
        """
        targets = {
            'bullish': {
                'first_target': extensions.top_25,
                'second_target': extensions.top_50,
                'extended_target': extensions.top_100,
            },
            'bearish': {
                'first_target': extensions.bottom_25,
                'second_target': extensions.bottom_50,
                'extended_target': extensions.bottom_100,
            },
        }
        
        return targets
    
    def evaluate_forecast_strength(
        self,
        df: pd.DataFrame,
        forecast,  # IBForecast type
        ib: InitialBalance,
    ) -> Dict[str, any]:
        """
        Evaluate how strong the IB forecast is.
        
        Compares current IB to expected range.
        """
        current_price = df['close'].iloc[-1]
        forecast_high, forecast_low = forecast.get_forecast_bounds()
        
        # Calculate where current IB sits within forecast
        if forecast_high > forecast_low:
            ib_position = (ib.midpoint - forecast_low) / (forecast_high - forecast_low)
        else:
            ib_position = 0.5
        
        # Determine if IB is stronger than average
        strength_vs_average = 'strong' if ib.get_ib_range() > forecast.historical_average else 'weak'
        
        # Likelihood of breakout
        if abs(ib_position - 0.5) > 0.2:
            breakout_likelihood = 'high'
        elif abs(ib_position - 0.5) > 0.1:
            breakout_likelihood = 'medium'
        else:
            breakout_likelihood = 'low'
        
        return {
            'ib_position_in_forecast': ib_position,
            'strength_vs_average': strength_vs_average,
            'breakout_likelihood': breakout_likelihood,
            'forecast_vs_actual': {
                'forecast_high': forecast_high,
                'forecast_low': forecast_low,
                'actual_high': ib.high,
                'actual_low': ib.low,
                'forecast_range': forecast.forecast_range,
                'actual_range': ib.get_ib_range(),
            }
        }
    
    def detect_ib_rejection(
        self,
        df: pd.DataFrame,
        ib: InitialBalance,
        rejection_threshold_bars: int = 3,
    ) -> Dict[str, any]:
        """
        Detect when breakouts fail and price rejects IB extremes.
        
        This identifies reversal opportunities (failed breakout + mean reversion).
        """
        rejections = {
            'high_rejection': False,
            'low_rejection': False,
            'details': {},
        }
        
        # Look for touches followed by reversals
        recent_df = df.tail(rejection_threshold_bars * 2)
        
        # Check for rejection at IB high
        max_high = recent_df['high'].max()
        if max_high >= ib.high:
            # Check if price pulled back
            recent_close = recent_df['close'].iloc[-1]
            if recent_close < ib.high * 0.99:  # 1% pullback
                rejections['high_rejection'] = True
                rejections['details']['high'] = {
                    'touch_price': max_high,
                    'pullback_price': recent_close,
                    'pullback_pct': (ib.high - recent_close) / ib.high,
                }
        
        # Check for rejection at IB low
        min_low = recent_df['low'].min()
        if min_low <= ib.low:
            # Check if price pulled up
            recent_close = recent_df['close'].iloc[-1]
            if recent_close > ib.low * 1.01:  # 1% pullback
                rejections['low_rejection'] = True
                rejections['details']['low'] = {
                    'touch_price': min_low,
                    'pullback_price': recent_close,
                    'pullback_pct': (recent_close - ib.low) / ib.low,
                }
        
        return rejections
    
    def session_sentiment_analysis(
        self,
        df: pd.DataFrame,
        ib: InitialBalance,
    ) -> Dict[str, any]:
        """
        Analyze overall session sentiment from IB data.
        """
        current_price = df['close'].iloc[-1]
        
        # Determine current market structure
        if current_price > ib.high:
            structure = 'bullish'
            distance_from_ib = (current_price - ib.high) / ib.high * 100
        elif current_price < ib.low:
            structure = 'bearish'
            distance_from_ib = (ib.low - current_price) / ib.low * 100
        else:
            structure = 'neutral'
            distance_from_ib = 0
        
        # Volume profile
        price_above_mid = len(df[df['close'] > ib.midpoint]) / len(df)
        
        return {
            'structure': structure,
            'distance_from_ib_pct': distance_from_ib,
            'price_above_midpoint': price_above_mid,
            'sentiment': 'bullish' if price_above_mid > 0.6 else 'bearish' if price_above_mid < 0.4 else 'neutral',
        }


class MultiSessionAnalyzer:
    """Analyze IB patterns across multiple sessions."""
    
    def __init__(self, detector: InitialBalanceDetector):
        self.detector = detector
    
    def compare_sessions(
        self, past_ibs: List[InitialBalance]
    ) -> Dict[str, any]:
        """
        Compare characteristics across multiple sessions.
        """
        if len(past_ibs) < 2:
            return {}
        
        ranges = [ib.get_ib_range() for ib in past_ibs]
        
        comparison = {
            'number_of_sessions': len(past_ibs),
            'average_range': np.mean(ranges),
            'median_range': np.median(ranges),
            'max_range': np.max(ranges),
            'min_range': np.min(ranges),
            'range_std': np.std(ranges),
            'trend': 'expanding' if ranges[-1] > ranges[0] else 'contracting',
        }
        
        return comparison
    
    def identify_setup_patterns(
        self, past_ibs: List[InitialBalance]
    ) -> Dict[str, List]:
        """
        Identify recurring patterns in IB setup.
        """
        if len(past_ibs) < 3:
            return {}
        
        patterns = {
            'double_bottom': [],
            'double_top': [],
            'expanding_range': [],
            'contracting_range': [],
        }
        
        # Look for consecutive similar ranges
        ranges = [ib.get_ib_range() for ib in past_ibs]
        
        for i in range(len(ranges) - 1):
            current_range = ranges[i]
            next_range = ranges[i + 1]
            
            # Check for similar ranges (double patterns)
            if abs(current_range - next_range) < (current_range * 0.1):
                if i + 1 == len(ranges) - 1:
                    patterns['double_bottom'].append((i, i + 1))
            
            # Check for expanding/contracting
            if i + 2 < len(ranges):
                prev_range = ranges[i - 1] if i > 0 else ranges[i]
                
                if current_range > prev_range and next_range > current_range:
                    patterns['expanding_range'].append((i - 1, i, i + 1))
                elif current_range < prev_range and next_range < current_range:
                    patterns['contracting_range'].append((i - 1, i, i + 1))
        
        return patterns


def example_setup_analysis():
    """Example: Analyze high-probability IB trading setups."""
    
    # Generate sample intraday data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01 09:30', periods=390*5, freq='5min')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(len(dates)) * 0.05,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.2),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.2),
        'close': prices,
        'volume': np.random.randint(100, 1000, len(dates)),
    }, index=dates)
    
    # Setup detector
    detector = InitialBalanceDetector(session_duration_minutes=60)
    analyzer = IBTradeAnalyzer(detector)
    
    # Detect IB
    ib = detector.detect_initial_balance(df)
    print("=" * 60)
    print("HIGH-PROBABILITY SETUP ANALYSIS")
    print("=" * 60)
    print(f"\nInitial Balance: {ib.low:.2f} - {ib.high:.2f}")
    print(f"Range: {ib.range_size:.4f}")
    
    # Find breakouts
    signals = detector.detect_breakouts(df, ib)
    print(f"Breakout Signals: {len(signals)}")
    
    # Analyze setups
    setups = analyzer.find_high_probability_setups(df, ib, signals)
    print(f"\nHigh Probability Setups:")
    print(f"  Bullish: {len(setups['bullish_high_prob'])}")
    print(f"  Bearish: {len(setups['bearish_high_prob'])}")
    
    # Fibonacci analysis
    fibs = detector.calculate_fibonacci_levels(ib)
    print(f"\nFibonacci Support Analysis:")
    fib_analysis = analyzer.analyze_fibonacci_support(df, fibs, ib)
    for level, info in list(fib_analysis.items())[:3]:
        print(f"  {level}%: ${info['price']:.2f} (tested: {info['tested_recently']})")
    
    # Extension targets
    exts = detector.calculate_extensions(ib)
    targets = analyzer.calculate_extension_targets(ib, exts)
    print(f"\nProfit Targets:")
    for direction, tgts in targets.items():
        print(f"  {direction.upper()}:")
        for target_name, target_price in tgts.items():
            print(f"    {target_name}: ${target_price:.2f}")
    
    # Sentiment
    sentiment = analyzer.session_sentiment_analysis(df, ib)
    print(f"\nSession Sentiment:")
    print(f"  Structure: {sentiment['structure']}")
    print(f"  Sentiment: {sentiment['sentiment']}")


if __name__ == "__main__":
    example_setup_analysis()
