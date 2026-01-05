"""
LuxAlgo MACD Based Price Forecasting - Advanced Analysis
========================================================

Advanced utilities for MACD forecasting including accuracy analysis,
confidence scoring, volatility adjustment, and forecast visualization.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from luxalgo_macd_forecasting import (
    MACDPriceForecaster,
    PriceSignal,
    ForecastRange,
    SignalType,
    TrendDetermination,
)


@dataclass
class ForecastAccuracy:
    """Measures forecast accuracy."""
    signal_timestamp: pd.Timestamp
    signal_type: str
    predicted_high: float
    actual_high: float
    predicted_low: float
    actual_low: float
    predicted_range: float
    actual_range: float
    range_accuracy: float  # % of actual range contained in predicted
    midpoint_error: float
    upper_breach: bool
    lower_breach: bool


class ForecastValidator:
    """Validate forecast accuracy against actual price movement."""
    
    def __init__(self, forecaster: MACDPriceForecaster):
        self.forecaster = forecaster
    
    def validate_forecasts(
        self,
        df: pd.DataFrame,
        signals: List[PriceSignal],
        forecasts: List[ForecastRange],
    ) -> List[ForecastAccuracy]:
        """
        Validate forecasts against actual price movement.
        
        Args:
            df: Complete OHLCV DataFrame
            signals: List of MACD signals
            forecasts: List of forecasts
        
        Returns:
            List of accuracy measurements
        """
        accuracies = []
        
        for forecast in forecasts:
            try:
                signal_idx = df.index.get_loc(forecast.timestamp)
            except KeyError:
                continue
            
            # Get actual prices over forecast period
            forecast_end = min(signal_idx + forecast.forecast_bars + 1, len(df))
            
            if forecast_end <= signal_idx + 1:
                continue
            
            future_df = df.iloc[signal_idx + 1:forecast_end]
            
            if len(future_df) == 0:
                continue
            
            actual_high = future_df['high'].max()
            actual_low = future_df['low'].min()
            actual_range = actual_high - actual_low
            predicted_range = forecast.upper_bound - forecast.lower_bound
            
            # Calculate accuracy metrics
            if actual_high > forecast.upper_bound:
                upper_breach = True
            else:
                upper_breach = False
            
            if actual_low < forecast.lower_bound:
                lower_breach = True
            else:
                lower_breach = False
            
            # Range accuracy: how much of actual range fits in predicted
            actual_contained = min(actual_high, forecast.upper_bound) - max(actual_low, forecast.lower_bound)
            range_accuracy = actual_contained / actual_range if actual_range > 0 else 0
            
            # Midpoint error
            actual_midpoint = (actual_high + actual_low) / 2
            predicted_midpoint = (forecast.upper_bound + forecast.lower_bound) / 2
            midpoint_error = abs(actual_midpoint - predicted_midpoint)
            
            accuracy = ForecastAccuracy(
                signal_timestamp=forecast.timestamp,
                signal_type=forecast.signal_type.value,
                predicted_high=forecast.upper_bound,
                actual_high=actual_high,
                predicted_low=forecast.lower_bound,
                actual_low=actual_low,
                predicted_range=predicted_range,
                actual_range=actual_range,
                range_accuracy=range_accuracy,
                midpoint_error=midpoint_error,
                upper_breach=upper_breach,
                lower_breach=lower_breach,
            )
            
            accuracies.append(accuracy)
        
        return accuracies
    
    def calculate_accuracy_stats(self, accuracies: List[ForecastAccuracy]) -> Dict:
        """
        Calculate overall forecast accuracy statistics.
        
        Args:
            accuracies: List of accuracy measurements
        
        Returns:
            Statistics dictionary
        """
        if not accuracies:
            return {
                'total_forecasts': 0,
                'avg_range_accuracy': 0,
                'avg_midpoint_error': 0,
                'contained_percentage': 0,
                'upper_breach_percentage': 0,
                'lower_breach_percentage': 0,
                'bullish_accuracy': 0,
                'bearish_accuracy': 0,
            }
        
        bullish = [a for a in accuracies if a.signal_type == 'bullish']
        bearish = [a for a in accuracies if a.signal_type == 'bearish']
        
        contained = [a for a in accuracies if not a.upper_breach and not a.lower_breach]
        upper_breaches = [a for a in accuracies if a.upper_breach]
        lower_breaches = [a for a in accuracies if a.lower_breach]
        
        return {
            'total_forecasts': len(accuracies),
            'avg_range_accuracy': np.mean([a.range_accuracy for a in accuracies]),
            'avg_midpoint_error': np.mean([a.midpoint_error for a in accuracies]),
            'contained_percentage': len(contained) / len(accuracies) * 100 if accuracies else 0,
            'upper_breach_percentage': len(upper_breaches) / len(accuracies) * 100 if accuracies else 0,
            'lower_breach_percentage': len(lower_breaches) / len(accuracies) * 100 if accuracies else 0,
            'bullish_accuracy': np.mean([a.range_accuracy for a in bullish]) if bullish else 0,
            'bearish_accuracy': np.mean([a.range_accuracy for a in bearish]) if bearish else 0,
        }


class ConfidenceScorer:
    """Score confidence of forecasts."""
    
    @staticmethod
    def calculate_confidence(
        forecast: ForecastRange,
        signal_strength: float = 0.5,
        trajectory_count: int = 50,
    ) -> float:
        """
        Calculate confidence score 0-100.
        
        Args:
            forecast: The forecast range
            signal_strength: Signal strength (0-1)
            trajectory_count: Number of historical trajectories used
        
        Returns:
            Confidence score 0-100
        """
        # Factors:
        # 1. Confidence range (narrower = higher confidence)
        # 2. Signal strength
        # 3. Sample size (more trajectories = higher confidence)
        
        # Normalize confidence range (assume typical range 0-5)
        range_score = max(0, 1 - forecast.confidence_range / 5.0) * 40
        
        # Signal strength (0-1 -> 0-30)
        signal_score = signal_strength * 30
        
        # Sample size (0-100+ -> 0-30)
        sample_score = min(1, trajectory_count / 100) * 30
        
        total = range_score + signal_score + sample_score
        return min(100, max(0, total))
    
    @staticmethod
    def score_reversal(
        forecast: ForecastRange,
        previous_forecast: Optional[ForecastRange] = None,
    ) -> float:
        """
        Score probability of reversal.
        
        Args:
            forecast: Current forecast
            previous_forecast: Previous forecast (optional)
        
        Returns:
            Reversal probability 0-100
        """
        score = 0
        
        if previous_forecast:
            # Signal type change = higher reversal probability
            if forecast.signal_type != previous_forecast.signal_type:
                score += 60
            
            # Range overlap indicates weakness
            overlap = max(0, min(forecast.upper_bound, previous_forecast.upper_bound) -
                         max(forecast.lower_bound, previous_forecast.lower_bound))
            max_range = max(forecast.upper_bound - forecast.lower_bound,
                           previous_forecast.upper_bound - previous_forecast.lower_bound)
            
            if max_range > 0:
                overlap_pct = overlap / max_range
                if overlap_pct < 0.3:  # Low overlap = reversal likely
                    score += 30
        
        # Histogram divergence indicates weakness
        if abs(forecast.confidence_range) > 0:
            score += 10
        
        return min(100, score)


class ForecastBiasAnalyzer:
    """Analyze bias in price movement after signals."""
    
    @staticmethod
    def calculate_average_bias(
        forecasts: List[ForecastRange],
        actual_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """
        Calculate directional bias after signals.
        
        Args:
            forecasts: List of forecasts
            actual_data: Optional actual price data to measure against
        
        Returns:
            Bias statistics
        """
        bullish_forecasts = [f for f in forecasts if f.signal_type == SignalType.BULLISH]
        bearish_forecasts = [f for f in forecasts if f.signal_type == SignalType.BEARISH]
        
        if not bullish_forecasts and not bearish_forecasts:
            return {'bullish_bias': 0, 'bearish_bias': 0}
        
        # Calculate average displacement from signal
        bullish_displacements = []
        for f in bullish_forecasts:
            displacement = (f.upper_bound - f.signal_price) / f.signal_price if f.signal_price > 0 else 0
            bullish_displacements.append(displacement)
        
        bearish_displacements = []
        for f in bearish_forecasts:
            displacement = (f.signal_price - f.lower_bound) / f.signal_price if f.signal_price > 0 else 0
            bearish_displacements.append(displacement)
        
        return {
            'bullish_bias': np.mean(bullish_displacements) if bullish_displacements else 0,
            'bearish_bias': np.mean(bearish_displacements) if bearish_displacements else 0,
            'bullish_count': len(bullish_forecasts),
            'bearish_count': len(bearish_forecasts),
        }


class VolatilityAdjuster:
    """Adjust forecasts based on volatility conditions."""
    
    @staticmethod
    def adjust_forecast_by_volatility(
        forecast: ForecastRange,
        current_atr: float,
        historical_atr: float,
    ) -> ForecastRange:
        """
        Adjust forecast bounds based on volatility regime.
        
        High volatility -> wider bounds
        Low volatility -> tighter bounds
        
        Args:
            forecast: Original forecast
            current_atr: Current ATR value
            historical_atr: Historical average ATR
        
        Returns:
            Adjusted forecast
        """
        if historical_atr <= 0:
            return forecast
        
        vol_ratio = current_atr / historical_atr
        
        # Adjust bounds
        center = (forecast.upper_bound + forecast.lower_bound) / 2
        half_range = (forecast.upper_bound - forecast.lower_bound) / 2
        
        adjusted_range = half_range * vol_ratio
        
        new_forecast = ForecastRange(
            timestamp=forecast.timestamp,
            signal_price=forecast.signal_price,
            top_percentile_price=forecast.top_percentile_price,
            upper_bound=center + adjusted_range,
            average_price=forecast.average_price,
            middle_price=center,
            lower_bound=center - adjusted_range,
            bottom_percentile_price=forecast.bottom_percentile_price,
            confidence_range=forecast.confidence_range * vol_ratio,
            signal_type=forecast.signal_type,
            forecast_bars=forecast.forecast_bars,
        )
        
        return new_forecast


class ForecastReporter:
    """Generate comprehensive forecast reports."""
    
    @staticmethod
    def generate_forecast_report(
        forecast: ForecastRange,
        confidence: float = 0,
        reversal_prob: float = 0,
        avg_bias: Optional[Dict] = None,
    ) -> str:
        """Generate formatted forecast report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           MACD PRICE FORECAST REPORT                           ║
╚════════════════════════════════════════════════════════════════╝

📊 Signal Information
   Timestamp: {forecast.timestamp}
   Signal Type: {forecast.signal_type.value.upper()}
   Signal Price: ${forecast.signal_price:.2f}
   Forecast Horizon: {forecast.forecast_bars} bars

📈 Forecast Range
   Upper Bound: ${forecast.upper_bound:.2f}
   Middle Price: ${forecast.middle_price:.2f}
   Average Price: ${forecast.average_price:.2f}
   Lower Bound: ${forecast.lower_bound:.2f}
   Total Range: ${forecast.confidence_range:.2f}

📊 Percentile Prices
   Top ({95}%): ${forecast.top_percentile_price:.2f}
   Bottom ({5}%): ${forecast.bottom_percentile_price:.2f}

🎯 Confidence & Risk
   Confidence Score: {confidence:.1f}%
   Reversal Probability: {reversal_prob:.1f}%

🔍 Support/Resistance
   If BULLISH: Support at ${forecast.lower_bound:.2f}, Target ${forecast.upper_bound:.2f}
   If BEARISH: Resistance at ${forecast.upper_bound:.2f}, Target ${forecast.lower_bound:.2f}

💡 Implications
   {'Wide range suggests high volatility and uncertainty' if forecast.confidence_range > 1 else 'Narrow range suggests low volatility and stability'}
   {'Consider tighter stops for risk management' if confidence < 50 else 'Reasonable confidence in forecast'}
"""
        
        return report
    
    @staticmethod
    def generate_accuracy_report(stats: Dict) -> str:
        """Generate forecast accuracy report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           FORECAST ACCURACY ANALYSIS                           ║
╚════════════════════════════════════════════════════════════════╝

📊 Overall Statistics
   Total Forecasts: {stats['total_forecasts']}
   Avg Range Accuracy: {stats['avg_range_accuracy']:.1%}
   Avg Midpoint Error: ${stats['avg_midpoint_error']:.2f}

✅ Success Metrics
   Contained Percentage: {stats['contained_percentage']:.1f}%
   Upper Breach: {stats['upper_breach_percentage']:.1f}%
   Lower Breach: {stats['lower_breach_percentage']:.1f}%

📈 By Signal Type
   Bullish Accuracy: {stats['bullish_accuracy']:.1%}
   Bearish Accuracy: {stats['bearish_accuracy']:.1%}
"""
        
        return report


def example_macd_forecasting():
    """Example: Complete MACD forecasting."""
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='1D')
    
    # Trend with oscillations
    trend = np.linspace(100, 120, 500)
    noise = np.random.randn(500) * 2
    prices = trend + noise + 10 * np.sin(np.linspace(0, 10*np.pi, 500))
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(500) * 0.5),
        'low': prices - np.abs(np.random.randn(500) * 0.5),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 500),
    }, index=dates)
    
    print("=" * 70)
    print("MACD BASED PRICE FORECASTING - COMPLETE ANALYSIS")
    print("=" * 70)
    
    # Setup forecaster
    forecaster = MACDPriceForecaster(
        fast_length=12,
        slow_length=26,
        signal_length=9,
        max_memory=100,
        forecasting_length=20,
        top_percentile=95,
        average_percentile=50,
        bottom_percentile=5,
    )
    
    # Generate forecasts
    df_macd, signals, forecasts = forecaster.forecast(df, TrendDetermination.MACD)
    print(f"\n✓ Forecasting complete")
    print(f"  Signals detected: {len(signals)}")
    print(f"  Forecasts generated: {len(forecasts)}")
    
    # Validate forecasts
    validator = ForecastValidator(forecaster)
    accuracies = validator.validate_forecasts(df, signals, forecasts)
    accuracy_stats = validator.calculate_accuracy_stats(accuracies)
    
    print(f"\n✓ Forecast accuracy:")
    print(f"  Range accuracy: {accuracy_stats['avg_range_accuracy']:.1%}")
    print(f"  Contained: {accuracy_stats['contained_percentage']:.1f}%")
    
    # Confidence scoring
    scorer = ConfidenceScorer()
    if forecasts:
        latest = forecasts[-1]
        confidence = scorer.calculate_confidence(latest, signal_strength=0.7, trajectory_count=50)
        reversal_prob = scorer.score_reversal(latest, forecasts[-2] if len(forecasts) > 1 else None)
        
        print(f"\n✓ Latest forecast confidence: {confidence:.1f}%")
        print(f"  Reversal probability: {reversal_prob:.1f}%")
    
    # Identify reversals
    reversals = forecaster.identify_reversals(forecasts)
    print(f"\n✓ Potential reversals: {len(reversals)}")
    
    # Identify support/resistance
    sr = forecaster.identify_support_resistance(forecasts)
    print(f"\n✓ Support/Resistance levels:")
    print(f"  Supports: {len(sr['support_levels'])}")
    print(f"  Resistances: {len(sr['resistance_levels'])}")


if __name__ == "__main__":
    example_macd_forecasting()
