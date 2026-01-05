"""
LuxAlgo Island Reversal - Advanced Usage & Trading Strategies
==============================================================

Advanced analysis utilities for Island Reversal trading strategies,
including pattern confirmation, target calculation, risk management,
and multi-timeframe confluence detection.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from luxalgo_island_reversal import (
    IslandReversalDetector,
    IslandReversalPattern,
    Gap,
    ReversalDirection,
    PatternQuality,
)


class IslandReversalTradeSetup:
    """Advanced analyzer for island reversal trading opportunities."""
    
    def __init__(self, detector: IslandReversalDetector):
        self.detector = detector
    
    def calculate_entry_targets(
        self, pattern: IslandReversalPattern, df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate entry targets based on island reversal pattern.
        
        Returns:
            Dictionary with entry prices and confidence levels
        """
        current_price = df['close'].iloc[-1]
        island_high = pattern.island_consolidation.high_price
        island_low = pattern.island_consolidation.low_price
        island_mid = (island_high + island_low) / 2
        
        if pattern.direction == ReversalDirection.BULLISH:
            # Bullish reversal: Price should go up from island
            # Best entry is near island support after gap down
            return {
                'entry_low': island_low,
                'entry_mid': island_mid,
                'entry_high': island_high,
                'aggressive_entry': pattern.second_gap.gap_low,
                'conservative_entry': island_mid,
            }
        else:
            # Bearish reversal: Price should go down from island
            # Best entry is near island resistance after gap up
            return {
                'entry_low': island_low,
                'entry_mid': island_mid,
                'entry_high': island_high,
                'aggressive_entry': pattern.second_gap.gap_high,
                'conservative_entry': island_mid,
            }
    
    def calculate_profit_targets(
        self,
        pattern: IslandReversalPattern,
        atr: float,
        risk_reward_ratio: float = 2.0,
    ) -> Dict[str, float]:
        """
        Calculate profit targets based on pattern size and ATR.
        
        Args:
            pattern: Island reversal pattern
            atr: Average True Range value
            risk_reward_ratio: Desired risk/reward (e.g., 1:2)
        
        Returns:
            Dictionary with multiple profit targets
        """
        pattern_size = pattern.get_total_pattern_size()
        island_range = pattern.island_consolidation.range_size
        
        if pattern.direction == ReversalDirection.BULLISH:
            entry = pattern.island_consolidation.mid_price
            
            # Target 1: First island range extension
            target1 = entry + island_range
            
            # Target 2: Full pattern size extension
            target2 = entry + pattern_size
            
            # Target 3: ATR-based extension
            target3 = entry + (atr * 3)
            
            return {
                'target_1': target1,
                'target_1_ratio': self._calculate_risk_reward(entry, pattern.support_level, target1),
                'target_2': target2,
                'target_2_ratio': self._calculate_risk_reward(entry, pattern.support_level, target2),
                'target_3': target3,
                'target_3_ratio': self._calculate_risk_reward(entry, pattern.support_level, target3),
            }
        else:
            entry = pattern.island_consolidation.mid_price
            
            target1 = entry - island_range
            target2 = entry - pattern_size
            target3 = entry - (atr * 3)
            
            return {
                'target_1': target1,
                'target_1_ratio': self._calculate_risk_reward(entry, pattern.resistance_level, target1),
                'target_2': target2,
                'target_2_ratio': self._calculate_risk_reward(entry, pattern.resistance_level, target2),
                'target_3': target3,
                'target_3_ratio': self._calculate_risk_reward(entry, pattern.resistance_level, target3),
            }
    
    def _calculate_risk_reward(self, entry: float, stop: float, target: float) -> float:
        """Calculate risk/reward ratio."""
        if entry == stop:
            return 0.0
        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk == 0:
            return 0.0
        return reward / risk
    
    def calculate_stop_loss(
        self,
        pattern: IslandReversalPattern,
        buffer_pct: float = 0.1,
    ) -> Dict[str, float]:
        """
        Calculate stop-loss levels for island reversal trade.
        
        Args:
            pattern: Island reversal pattern
            buffer_pct: Buffer percentage beyond extremes
        
        Returns:
            Dictionary with various stop-loss options
        """
        if pattern.direction == ReversalDirection.BULLISH:
            # For bullish, stop is below island low
            island_low = pattern.island_consolidation.low_price
            gap_low = pattern.second_gap.gap_low
            buffer = gap_low * buffer_pct / 100
            
            return {
                'island_low': island_low,
                'gap_low': gap_low,
                'gap_low_with_buffer': gap_low - buffer,
                'tight_stop': island_low - (pattern.island_consolidation.range_size * 0.1),
            }
        else:
            # For bearish, stop is above island high
            island_high = pattern.island_consolidation.high_price
            gap_high = pattern.second_gap.gap_high
            buffer = gap_high * buffer_pct / 100
            
            return {
                'island_high': island_high,
                'gap_high': gap_high,
                'gap_high_with_buffer': gap_high + buffer,
                'tight_stop': island_high + (pattern.island_consolidation.range_size * 0.1),
            }
    
    def calculate_pattern_purity_score(
        self, pattern: IslandReversalPattern
    ) -> Dict[str, any]:
        """
        Calculate how 'textbook' the pattern is.
        
        Factors:
        - Gap overlap (no overlap = purer)
        - Consolidation flatness
        - Volume confirmation
        - Filter passes
        """
        purity = pattern.get_pattern_purity()
        
        # Filter adherence
        filter_score = sum([
            1 if pattern.trend_filter_pass else 0,
            1 if pattern.volume_filter_pass else 0,
            1 if pattern.horizontality_filter_pass else 0,
            1 if pattern.volatility_filter_pass else 0,
        ]) / 4.0
        
        # Trend strength
        trend_score = pattern.trend_strength
        
        # Combined purity
        combined_purity = (purity * 0.4) + (filter_score * 0.4) + (trend_score * 0.2)
        
        return {
            'pattern_purity': purity,
            'filter_adherence': filter_score,
            'trend_strength': trend_score,
            'combined_purity': combined_purity,
            'interpretation': 'EXCELLENT' if combined_purity > 0.8 else 'GOOD' if combined_purity > 0.6 else 'FAIR',
        }
    
    def detect_failed_reversals(
        self,
        df: pd.DataFrame,
        patterns: List[IslandReversalPattern],
        confirmation_bars: int = 5,
    ) -> List[Dict]:
        """
        Identify island reversals that failed to reverse.
        
        (Price continued in original direction instead of reversing)
        """
        failed = []
        
        for pattern in patterns:
            # Get data after second gap
            gap_end_idx = df.index.get_loc(pattern.second_gap.gap_end_timestamp)
            confirmation_df = df.iloc[gap_end_idx:gap_end_idx + confirmation_bars]
            
            if len(confirmation_df) < 2:
                continue
            
            direction = pattern.direction
            first_bar_after = confirmation_df.iloc[0]
            last_bar_after = confirmation_df.iloc[-1]
            
            # Check if price continued in ORIGINAL trend (failed reversal)
            if direction == ReversalDirection.BULLISH:
                # Should bounce up, if continued down = failed
                if last_bar_after['close'] < first_bar_after['close']:
                    failed.append({
                        'pattern': pattern,
                        'expected': 'UP',
                        'actual': 'DOWN',
                        'failure_rate': (first_bar_after['close'] - last_bar_after['close']) / first_bar_after['close'],
                    })
            else:
                # Should bounce down, if continued up = failed
                if last_bar_after['close'] > first_bar_after['close']:
                    failed.append({
                        'pattern': pattern,
                        'expected': 'DOWN',
                        'actual': 'UP',
                        'failure_rate': (last_bar_after['close'] - first_bar_after['close']) / first_bar_after['close'],
                    })
        
        return failed


class MultiTimeframeIslandAnalysis:
    """Analyze island reversals across multiple timeframes."""
    
    def __init__(self, detector: IslandReversalDetector):
        self.detector = detector
    
    def find_timeframe_confluences(
        self,
        timeframes: Dict[str, pd.DataFrame],
        max_timestamp_diff_bars: int = 10,
    ) -> List[Dict]:
        """
        Find island reversals that align across multiple timeframes.
        
        Args:
            timeframes: Dict of {timeframe_name: DataFrame}
            max_timestamp_diff_bars: Maximum bars apart to count as confluence
        
        Returns:
            List of confluence signals
        """
        # Detect patterns for each timeframe
        all_patterns = {}
        for tf_name, df in timeframes.items():
            gaps = self.detector.detect_gaps(df)
            patterns = self.detector.detect_island_reversals(df, gaps)
            all_patterns[tf_name] = patterns
        
        confluences = []
        
        # Find timeframes with same direction patterns
        for pattern_1h in all_patterns.get('1H', []):
            for pattern_4h in all_patterns.get('4H', []):
                # Check if patterns are same direction and close in time
                if pattern_1h.direction != pattern_4h.direction:
                    continue
                
                time_diff = abs(
                    (pattern_1h.pattern_end_timestamp - pattern_4h.pattern_end_timestamp).days
                )
                
                if time_diff <= max_timestamp_diff_bars:
                    confluences.append({
                        'direction': pattern_1h.direction.value,
                        '1H_pattern': pattern_1h,
                        '4H_pattern': pattern_4h,
                        'confluence_strength': 'STRONG' if pattern_1h.quality_score > 0.7 and pattern_4h.quality_score > 0.7 else 'GOOD',
                    })
        
        return confluences
    
    def calculate_position_size_by_quality(
        self,
        pattern: IslandReversalPattern,
        account_risk_pct: float = 1.0,
        account_size: float = 10000,
    ) -> Dict[str, float]:
        """
        Calculate position size based on pattern quality.
        
        Higher quality patterns = larger position size.
        """
        # Quality multiplier
        quality_multiplier = {
            PatternQuality.EXCELLENT: 1.5,
            PatternQuality.GOOD: 1.0,
            PatternQuality.FAIR: 0.65,
            PatternQuality.POOR: 0.0,  # Don't trade
        }
        
        base_multiplier = quality_multiplier.get(pattern.quality, 0.5)
        adjusted_risk = account_risk_pct * base_multiplier
        
        # Calculate position size
        entry_price = pattern.island_consolidation.high_price
        stop_loss = pattern.support_level if pattern.direction == ReversalDirection.BULLISH else pattern.resistance_level
        
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = (adjusted_risk / 100) * account_size
        position_size = risk_amount / risk_per_share if risk_per_share > 0 else 0
        
        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'quality_multiplier': base_multiplier,
            'effective_risk_pct': adjusted_risk,
        }


def example_trade_setup():
    """Example: Complete trade setup for island reversal."""
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1h')
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(len(dates)) * 0.3),
        'low': prices - np.abs(np.random.randn(len(dates)) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 5000, len(dates)),
    }, index=dates)
    
    # Setup detector
    detector = IslandReversalDetector(min_gap_size_pct=0.5)
    
    print("=" * 60)
    print("ISLAND REVERSAL TRADE SETUP ANALYSIS")
    print("=" * 60)
    
    # Find patterns
    gaps = detector.detect_gaps(df)
    patterns = detector.detect_island_reversals(df, gaps)
    
    if not patterns:
        print("No island reversals found")
        return
    
    pattern = patterns[0]
    analyzer = IslandReversalTradeSetup(detector)
    
    print(f"\nPattern: {pattern.direction.value.upper()}")
    print(f"Quality: {pattern.quality.value}")
    print(f"Quality Score: {pattern.quality_score:.2f}")
    
    # Entry targets
    print("\n--- ENTRY TARGETS ---")
    entries = analyzer.calculate_entry_targets(pattern, df)
    for name, price in entries.items():
        print(f"  {name}: ${price:.2f}")
    
    # Calculate ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        )
    )
    atr = df['tr'].tail(14).mean()
    
    # Profit targets
    print("\n--- PROFIT TARGETS ---")
    targets = analyzer.calculate_profit_targets(pattern, atr)
    for name, value in targets.items():
        if 'ratio' not in name:
            print(f"  {name}: ${value:.2f}")
    
    # Stop loss
    print("\n--- STOP LOSS OPTIONS ---")
    stops = analyzer.calculate_stop_loss(pattern)
    for name, price in stops.items():
        print(f"  {name}: ${price:.2f}")
    
    # Risk/Reward
    print("\n--- RISK/REWARD ANALYSIS ---")
    entry = entries['conservative_entry']
    stop = stops['gap_low'] if pattern.direction == ReversalDirection.BULLISH else stops['gap_high']
    target1 = targets['target_1']
    
    risk = abs(entry - stop)
    reward = abs(target1 - entry)
    print(f"  Entry: ${entry:.2f}")
    print(f"  Stop: ${stop:.2f}")
    print(f"  Target: ${target1:.2f}")
    print(f"  Risk: ${risk:.2f}")
    print(f"  Reward: ${reward:.2f}")
    print(f"  R/R Ratio: 1:{reward/risk:.2f}")
    
    # Pattern purity
    print("\n--- PATTERN PURITY ---")
    purity = analyzer.calculate_pattern_purity_score(pattern)
    print(f"  Combined Purity: {purity['combined_purity']:.1%}")
    print(f"  {purity['interpretation']}")


if __name__ == "__main__":
    example_trade_setup()
