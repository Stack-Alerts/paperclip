"""
LuxAlgo Power Hour Trendlines - Advanced Analysis
================================================

Advanced utilities for power hour trendline analysis including breakout
detection, trend strength measurement, and multi-session comparison.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from luxalgo_power_hour_trendlines import (
    PowerHourTrendlines,
    TrendlineAnalysis,
    TrendDirection,
    VolatilityRegime,
)


@dataclass
class BreakoutSignal:
    """Breakout signal from trendlines."""
    timestamp: pd.Timestamp
    signal_type: str  # 'bullish_breakout', 'bearish_breakout'
    breakout_level: float
    breakout_distance: float
    channel_width: float
    volatility_regime: str
    trend_before: str


class BreakoutDetector:
    """Detect breakouts from power hour trendlines."""
    
    @staticmethod
    def detect_breakouts(analyses: List[TrendlineAnalysis], 
                        prices: pd.Series) -> List[BreakoutSignal]:
        """Detect all breakouts in analysis series."""
        breakouts = []
        
        for i, analysis in enumerate(analyses):
            if i == 0:
                continue
            
            prev_analysis = analyses[i - 1]
            current_price = prices.iloc[i] if i < len(prices) else analysis.resistance_level
            
            # Bullish breakout
            if (current_price > analysis.resistance_level and 
                current_price <= prev_analysis.resistance_level):
                breakouts.append(BreakoutSignal(
                    timestamp=analysis.timestamp,
                    signal_type='bullish_breakout',
                    breakout_level=analysis.resistance_level,
                    breakout_distance=current_price - analysis.resistance_level,
                    channel_width=analysis.channel_width,
                    volatility_regime=analysis.volatility_regime.value,
                    trend_before=analysis.trend_direction.value,
                ))
            
            # Bearish breakout
            if (current_price < analysis.support_level and
                current_price >= prev_analysis.support_level):
                breakouts.append(BreakoutSignal(
                    timestamp=analysis.timestamp,
                    signal_type='bearish_breakout',
                    breakout_level=analysis.support_level,
                    breakout_distance=analysis.support_level - current_price,
                    channel_width=analysis.channel_width,
                    volatility_regime=analysis.volatility_regime.value,
                    trend_before=analysis.trend_direction.value,
                ))
        
        return breakouts


class TrendStrengthAnalyzer:
    """Analyze trend strength from trendlines."""
    
    @staticmethod
    def calculate_slope_strength(slope: float, price_level: float) -> float:
        """
        Calculate trend strength as % of price change per session.
        
        Args:
            slope: Trendline slope
            price_level: Current price level
        
        Returns:
            Strength percentage (0-100)
        """
        if price_level == 0:
            return 0.0
        
        pct_change = (slope / price_level) * 100
        return min(100, abs(pct_change) * 10)
    
    @staticmethod
    def calculate_r_squared_confidence(r_squared: float) -> float:
        """
        Calculate confidence from R-squared value.
        
        Args:
            r_squared: R-squared value (0-1)
        
        Returns:
            Confidence percentage (0-100)
        """
        return r_squared * 100
    
    @staticmethod
    def analyze_trend_strength(analysis: TrendlineAnalysis) -> Dict[str, float]:
        """Get complete trend strength metrics."""
        slope_strength = TrendStrengthAnalyzer.calculate_slope_strength(
            analysis.middle_trendline.slope,
            analysis.distance_from_middle
        )
        
        r_squared_conf = TrendStrengthAnalyzer.calculate_r_squared_confidence(
            analysis.middle_trendline.r_squared
        )
        
        # Volatility strength impact (high volatility = lower trend confidence)
        vol_factor = 1.0
        if analysis.volatility_regime == VolatilityRegime.EXTREME:
            vol_factor = 0.5
        elif analysis.volatility_regime == VolatilityRegime.HIGH:
            vol_factor = 0.7
        elif analysis.volatility_regime == VolatilityRegime.MODERATE:
            vol_factor = 0.85
        
        overall_strength = (slope_strength * 0.4 + r_squared_conf * 0.6) * vol_factor
        
        return {
            'slope_strength': slope_strength,
            'r_squared_confidence': r_squared_conf,
            'volatility_factor': vol_factor,
            'overall_strength': overall_strength,
        }


class SessionComparator:
    """Compare trendlines across multiple session windows."""
    
    def __init__(self, pht: PowerHourTrendlines):
        self.pht = pht
    
    def compare_sessions(self, df: pd.DataFrame,
                        session_windows: List[int]) -> Dict[int, Dict]:
        """
        Compare trendlines across different session memory windows.
        
        Args:
            df: OHLCV DataFrame
            session_windows: List of session memory values to compare
        
        Returns:
            Dictionary with analysis for each window
        """
        results = {}
        
        for window in session_windows:
            # Temporarily change memory
            original_memory = self.pht.sessions_memory
            self.pht.sessions_memory = window
            
            _, analyses = self.pht.analyze(df)
            
            if analyses:
                latest = analyses[-1]
                results[window] = {
                    'trend': latest.trend_direction.value,
                    'slope': latest.middle_trendline.slope,
                    'r_squared': latest.middle_trendline.r_squared,
                    'channel_width': latest.channel_width,
                    'volatility': latest.volatility_regime.value,
                    'num_sessions': len(analyses),
                }
            
            # Restore memory
            self.pht.sessions_memory = original_memory
        
        return results
    
    def detect_trend_consistency(self, analyses: List[TrendlineAnalysis],
                                lookback: int = 10) -> Dict[str, any]:
        """
        Detect if trend direction is consistent over lookback.
        
        Args:
            analyses: List of analyses
            lookback: Number of sessions to look back
        
        Returns:
            Consistency metrics
        """
        if len(analyses) < lookback:
            return {'consistent': False, 'lookback_insufficient': True}
        
        recent = analyses[-lookback:]
        trend_counts = {}
        
        for analysis in recent:
            trend = analysis.trend_direction.value
            trend_counts[trend] = trend_counts.get(trend, 0) + 1
        
        dominant_trend = max(trend_counts, key=trend_counts.get)
        consistency = trend_counts[dominant_trend] / lookback
        
        return {
            'dominant_trend': dominant_trend,
            'consistency': consistency,
            'trend_changes': len(trend_counts) - 1,
            'breakdown_bars': len([a for a in recent 
                                  if a.trend_direction.value != dominant_trend]),
        }


class SupportResistanceValidator:
    """Validate support and resistance levels."""
    
    @staticmethod
    def validate_level_touches(level: float, prices: pd.Series,
                              tolerance: float = 0.001) -> Dict[str, int]:
        """
        Count touches of a support/resistance level.
        
        Args:
            level: Price level to validate
            prices: Series of prices
            tolerance: Tolerance for "touching" level
        
        Returns:
            Dictionary with touch statistics
        """
        tolerance_range = level * tolerance
        touches = 0
        rejections = 0
        breakouts = 0
        
        for i, price in enumerate(prices):
            if abs(price - level) < tolerance_range:
                touches += 1
                
                # Check if next candle rejects
                if i < len(prices) - 1:
                    next_price = prices.iloc[i + 1]
                    if price < level and next_price < price:
                        rejections += 1
                    elif price > level and next_price > price:
                        rejections += 1
            elif price > level:
                breakouts += 1
        
        return {
            'touches': touches,
            'rejections': rejections,
            'breakouts': breakouts,
            'strength': touches / (len(prices) / 100) if prices.shape[0] > 0 else 0,
        }
    
    @staticmethod
    def find_key_levels(analyses: List[TrendlineAnalysis],
                       min_touches: int = 2) -> Dict[str, List[float]]:
        """Find key support/resistance levels with minimum touches."""
        supports = {}
        resistances = {}
        
        for analysis in analyses:
            support = analysis.support_level
            resistance = analysis.resistance_level
            
            # Track support touches
            if support not in supports:
                supports[support] = 0
            supports[support] += 1
            
            # Track resistance touches
            if resistance not in resistances:
                resistances[resistance] = 0
            resistances[resistance] += 1
        
        # Filter by minimum touches
        key_supports = sorted(
            [s for s, count in supports.items() if count >= min_touches]
        )
        key_resistances = sorted(
            [r for r, count in resistances.items() if count >= min_touches],
            reverse=True
        )
        
        return {
            'support_levels': key_supports,
            'resistance_levels': key_resistances,
        }


class PowerHourReporter:
    """Generate power hour trendline reports."""
    
    @staticmethod
    def generate_analysis_report(analyses: List[TrendlineAnalysis],
                                df: pd.DataFrame) -> str:
        """Generate comprehensive power hour analysis report."""
        if not analyses:
            return "No power hour data available for analysis."
        
        latest = analyses[-1]
        strength = TrendStrengthAnalyzer.analyze_trend_strength(latest)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           POWER HOUR TRENDLINES ANALYSIS REPORT                ║
╚════════════════════════════════════════════════════════════════╝

📊 Current Status
   Timestamp: {latest.timestamp}
   Trend: {latest.trend_direction.value.upper()}
   Volatility: {latest.volatility_regime.value.upper()}

📈 Trendline Levels
   Resistance: ${latest.resistance_level:.2f}
   Middle: ${latest.middle_trendline.calculate_value(0):.2f}
   Support: ${latest.support_level:.2f}
   Channel Width: ${latest.channel_width:.4f}

💪 Trend Strength
   Slope Strength: {strength['slope_strength']:.1f}%
   R² Confidence: {strength['r_squared_confidence']:.1f}%
   Overall Strength: {strength['overall_strength']:.1f}%

📍 Price Position
   Distance from Middle: ${latest.distance_from_middle:.4f}
   Position: {'Above Middle' if latest.distance_from_middle > 0 else 'Below Middle'}

✅ Status: Analysis Complete
"""
        
        return report
    
    @staticmethod
    def generate_breakout_report(breakout: BreakoutSignal) -> str:
        """Generate breakout signal report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║              POWER HOUR BREAKOUT SIGNAL                        ║
╚════════════════════════════════════════════════════════════════╝

🚀 Breakout Details
   Type: {breakout.signal_type.upper().replace('_', ' ')}
   Timestamp: {breakout.timestamp}
   Level: ${breakout.breakout_level:.2f}
   Distance: ${breakout.breakout_distance:.4f}

📊 Market Context
   Channel Width: ${breakout.channel_width:.4f}
   Volatility: {breakout.volatility_regime.upper()}
   Previous Trend: {breakout.trend_before.upper()}

⚠️ Action Required
   Monitor breakout for follow-through
   Set appropriate stops
   Consider target levels
"""
        
        return report


if __name__ == "__main__":
    import numpy as np
    from datetime import datetime
    
    dates = pd.date_range('2023-12-01', periods=250, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(250) * 0.3),
        'low': prices - np.abs(np.random.randn(250) * 0.3),
        'close': prices,
        'volume': np.random.randint(100000, 500000, 250),
    }, index=dates)
    
    pht = PowerHourTrendlines(sessions_memory=20)
    df_result, analyses = pht.analyze(df)
    
    print("=" * 70)
    print("POWER HOUR TRENDLINES - ADVANCED ANALYSIS")
    print("=" * 70)
    
    if analyses:
        reporter = PowerHourReporter()
        report = reporter.generate_analysis_report(analyses, df_result)
        print(report)
    
    # Breakout detection
    breakouts = BreakoutDetector.detect_breakouts(analyses, df['close'])
    print(f"\n✓ Breakouts detected: {len(breakouts)}")
    for bo in breakouts[-2:]:
        print(f"  {bo.timestamp}: {bo.signal_type}")
    
    # Session comparison
    print(f"\n✓ Total power hours: {len(analyses)}")
    
    # Consistency
    if analyses:
        consistency = SessionComparator(pht).detect_trend_consistency(analyses)
        print(f"\n✓ Trend Consistency:")
        print(f"  Dominant: {consistency['dominant_trend'].upper()}")
        print(f"  Consistency: {consistency['consistency']:.1%}")
