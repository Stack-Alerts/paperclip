"""
LuxAlgo Adaptive Momentum Oscillator - Advanced Analysis
=======================================================

Advanced utilities for momentum analysis including signal confirmation,
divergence validation, trend regime detection, and performance analytics.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from luxalgo_momentum_oscillator import (
    AdaptiveMomentumOscillator,
    MomentumSignalPoint,
    DivergenceDetection,
    MomentumSignal,
    DataSource,
)


@dataclass
class SignalQuality:
    """Measures signal quality."""
    timestamp: pd.Timestamp
    signal_type: str
    strength: float
    crossover_distance: float
    momentum_acceleration: float
    volume_confirmation: Optional[float]
    overall_quality: float


class SignalConfirmation:
    """Confirm momentum signals with additional analysis."""
    
    @staticmethod
    def calculate_signal_quality(
        signal: MomentumSignalPoint,
        df: pd.DataFrame,
        index: int,
        volume_threshold: float = 0.5,
    ) -> SignalQuality:
        """Calculate quality of momentum signal."""
        crossover_distance = abs(signal.momentum)
        momentum_accel = signal.momentum_velocity
        
        volume_conf = None
        if index > 0 and 'volume' in df.columns:
            vol = df.iloc[index]['volume']
            avg_vol = df['volume'].tail(20).mean()
            volume_conf = vol / avg_vol if avg_vol > 0 else 0
        
        quality = 0
        quality += min(40, signal.strength * 100)
        quality += min(30, crossover_distance * 100)
        quality += min(20, abs(momentum_accel) * 100)
        
        if volume_conf and volume_conf > volume_threshold:
            quality += 10
        
        return SignalQuality(
            timestamp=signal.timestamp,
            signal_type=signal.signal_type.value,
            strength=signal.strength,
            crossover_distance=crossover_distance,
            momentum_acceleration=momentum_accel,
            volume_confirmation=volume_conf,
            overall_quality=min(100, quality),
        )
    
    @staticmethod
    def filter_by_quality(
        signals: List[MomentumSignalPoint],
        quality_threshold: float = 60.0,
    ) -> List[MomentumSignalPoint]:
        """Filter signals by quality threshold."""
        return [s for s in signals if s.strength >= (quality_threshold / 100)]


class DivergenceValidator:
    """Validate divergence signals."""
    
    @staticmethod
    def validate_divergence(
        divergence: DivergenceDetection,
        df: pd.DataFrame,
        lookback_bars: int = 20,
    ) -> Dict[str, any]:
        """Validate divergence with additional checks."""
        try:
            div_idx = df.index.get_loc(divergence.timestamp)
        except KeyError:
            return {'valid': False, 'reason': 'timestamp not found'}
        
        future_start = div_idx + 1
        future_end = min(div_idx + lookback_bars + 1, len(df))
        
        if future_start >= len(df):
            return {'valid': False, 'reason': 'no future data'}
        
        future_data = df.iloc[future_start:future_end]
        
        valid = False
        reason = 'no movement'
        
        if divergence.divergence_type == MomentumSignal.DIVERGENCE_BULLISH:
            if future_data['close'].max() > divergence.price_level:
                valid = True
                reason = 'price moved higher'
        
        elif divergence.divergence_type == MomentumSignal.DIVERGENCE_BEARISH:
            if future_data['close'].min() < divergence.price_level:
                valid = True
                reason = 'price moved lower'
        
        return {
            'valid': valid,
            'reason': reason,
            'severity': divergence.severity,
            'bars_to_confirm': lookback_bars,
        }


class TrendRegimeDetector:
    """Detect momentum trend regimes."""
    
    @staticmethod
    def classify_regime(df: pd.DataFrame, lookback: int = 20) -> Dict[str, any]:
        """Classify market regime based on momentum."""
        if 'momentum' not in df.columns:
            return {'regime': 'unknown'}
        
        recent = df.tail(lookback)
        momentum_values = recent['momentum']
        
        positive_count = (momentum_values > 0).sum()
        positive_pct = positive_count / len(momentum_values)
        
        avg_momentum = momentum_values.mean()
        momentum_std = momentum_values.std()
        
        above_signal = (
            (momentum_values > recent['momentum_signal'].values).sum() / len(momentum_values)
        )
        
        regime = 'neutral'
        if positive_pct > 0.7:
            regime = 'bullish'
        elif positive_pct < 0.3:
            regime = 'bearish'
        
        strength = 'strong' if abs(avg_momentum) > momentum_std else 'weak'
        
        return {
            'regime': regime,
            'strength': strength,
            'positive_pct': positive_pct,
            'avg_momentum': avg_momentum,
            'momentum_std': momentum_std,
            'signal_alignment': above_signal,
            'volatility': momentum_std,
        }
    
    @staticmethod
    def detect_regime_change(
        df: pd.DataFrame, window: int = 20
    ) -> Optional[Dict]:
        """Detect changes in momentum regime."""
        if len(df) < window * 2:
            return None
        
        period1 = df.iloc[-window*2:-window]
        period2 = df.iloc[-window:]
        
        regime1 = TrendRegimeDetector.classify_regime(period1, window)
        regime2 = TrendRegimeDetector.classify_regime(period2, window)
        
        if regime1['regime'] != regime2['regime']:
            return {
                'change': True,
                'from_regime': regime1['regime'],
                'to_regime': regime2['regime'],
                'timestamp': df.index[-1],
            }
        
        return None


class MomentumOscillatorAnalyzer:
    """Comprehensive momentum analysis."""
    
    def __init__(self, oscillator: AdaptiveMomentumOscillator):
        self.oscillator = oscillator
    
    def analyze_signal_sequence(
        self, signals: List[MomentumSignalPoint], window: int = 5
    ) -> Dict[str, any]:
        """Analyze sequence of signals for patterns."""
        if len(signals) < window:
            return {'insufficient_signals': True}
        
        recent_signals = signals[-window:]
        
        bullish = sum(1 for s in recent_signals if s.signal_type == MomentumSignal.BULLISH)
        bearish = sum(1 for s in recent_signals if s.signal_type == MomentumSignal.BEARISH)
        
        avg_strength = np.mean([s.strength for s in recent_signals])
        
        alternating = True
        for i in range(len(recent_signals) - 1):
            curr_bull = recent_signals[i].signal_type == MomentumSignal.BULLISH
            next_bull = recent_signals[i + 1].signal_type == MomentumSignal.BULLISH
            if curr_bull == next_bull:
                alternating = False
                break
        
        return {
            'bullish_count': bullish,
            'bearish_count': bearish,
            'avg_strength': avg_strength,
            'alternating_pattern': alternating,
            'sequence_quality': 'good' if alternating else 'poor',
        }
    
    def calculate_momentum_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive momentum metrics."""
        if 'momentum' not in df.columns:
            return {}
        
        momentum = df['momentum'].tail(50)
        
        return {
            'current_momentum': df['momentum'].iloc[-1],
            'momentum_mean': momentum.mean(),
            'momentum_std': momentum.std(),
            'momentum_range': momentum.max() - momentum.min(),
            'positive_momentum_count': (momentum > 0).sum(),
            'momentum_above_signal': (
                (df['momentum'] > df['momentum_signal']).tail(50).sum()
            ),
            'signal_line_value': df['momentum_signal'].iloc[-1],
            'histogram_value': df['momentum_histogram'].iloc[-1],
        }
    
    def generate_trading_score(
        self, df: pd.DataFrame, signals: List[MomentumSignalPoint], window: int = 20
    ) -> Dict[str, any]:
        """Generate overall trading score (0-100)."""
        score = 50
        
        momentum_val = df['momentum'].iloc[-1]
        if momentum_val > 0.1:
            score += 20
        elif momentum_val < -0.1:
            score -= 20
        
        recent = df.tail(window)
        alignment = (recent['momentum'] > recent['momentum_signal']).sum() / len(recent)
        if alignment > 0.6:
            score += 15
        elif alignment < 0.4:
            score -= 15
        
        if signals:
            avg_strength = np.mean([s.strength for s in signals[-5:]])
            score += (avg_strength * 15)
        
        regime = TrendRegimeDetector.classify_regime(df, window)
        if regime['regime'] == 'bullish':
            score += 20
        elif regime['regime'] == 'bearish':
            score -= 20
        
        score = max(0, min(100, score))
        
        return {
            'trading_score': score,
            'interpretation': 'bullish' if score > 60 else ('bearish' if score < 40 else 'neutral'),
            'confidence': abs(score - 50) / 50,
        }


class MomentumReporter:
    """Generate momentum analysis reports."""
    
    @staticmethod
    def generate_signal_report(signal: MomentumSignalPoint) -> str:
        """Generate formatted signal report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           MOMENTUM SIGNAL REPORT                               ║
╚════════════════════════════════════════════════════════════════╝

📊 Signal Information
   Timestamp: {signal.timestamp}
   Signal Type: {signal.signal_type.value.upper()}
   Strength: {signal.strength:.2%}

📈 Momentum Values
   Momentum: {signal.momentum:.4f}
   Signal Line: {signal.signal_line:.4f}
   Histogram: {signal.histogram:.4f}
   Velocity: {signal.momentum_velocity:.6f}

💡 Interpretation
   {'Price momentum accelerating' if signal.momentum_velocity > 0 else 'Price momentum decelerating'}
   {'Strong signal' if signal.strength > 0.7 else 'Moderate signal' if signal.strength > 0.4 else 'Weak signal'}
"""
        
        return report
    
    @staticmethod
    def generate_analysis_report(
        df: pd.DataFrame,
        signals: List[MomentumSignalPoint],
        divergences: List[DivergenceDetection],
    ) -> str:
        """Generate comprehensive momentum analysis report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           ADAPTIVE MOMENTUM OSCILLATOR REPORT                  ║
╚════════════════════════════════════════════════════════════════╝

📊 Recent Momentum
   Current Value: {df['momentum'].iloc[-1]:.4f}
   Signal Line: {df['momentum_signal'].iloc[-1]:.4f}
   Histogram: {df['momentum_histogram'].iloc[-1]:.4f}

📈 Signal Statistics
   Total Signals: {len(signals)}
   Recent Signals: {len(signals[-5:])}
"""
        
        if signals:
            recent = signals[-1]
            report += f"   Latest Signal: {recent.signal_type.value.upper()} @ {recent.timestamp}\n"
        
        report += f"""
🔍 Divergence Detection
   Total Divergences: {len(divergences)}
"""
        
        if divergences:
            recent_div = divergences[-1]
            report += f"   Latest: {recent_div.divergence_type.value.upper()} @ {recent_div.timestamp}\n"
        
        report += f"""
⚡ Trend Regime
   Positive Momentum: {(df['momentum'] > 0).sum()} bars
   Negative Momentum: {(df['momentum'] < 0).sum()} bars

✅ Status
   Ready for analysis and trading
"""
        
        return report


if __name__ == "__main__":
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='1D')
    trend = np.linspace(100, 120, 500)
    oscillation = 10 * np.sin(np.linspace(0, 10*np.pi, 500))
    noise = np.random.randn(500) * 2
    prices = trend + oscillation + noise
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(500) * 0.5),
        'low': prices - np.abs(np.random.randn(500) * 0.5),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 500),
    }, index=dates)
    
    osc = AdaptiveMomentumOscillator(
        data_length=20,
        smoothing_length=10,
        divergence_length=14,
    )
    
    df_momentum, signals, divergences = osc.analyze(df, detect_divergences=True)
    reporter = MomentumReporter()
    report = reporter.generate_analysis_report(df_momentum, signals, divergences)
    print(report)
    
    if signals:
        sig_confirm = SignalConfirmation()
        latest_idx = len(df_momentum) - 1
        quality = sig_confirm.calculate_signal_quality(signals[-1], df_momentum, latest_idx)
        print(f"\n✓ Signal Quality: {quality.overall_quality:.1f}%")
    
    if divergences:
        validator = DivergenceValidator()
        for div in divergences[-2:]:
            val_result = validator.validate_divergence(div, df_momentum)
            print(f"\n✓ Divergence validation: {val_result['valid']} ({val_result['reason']})")
    
    regime = TrendRegimeDetector.classify_regime(df_momentum)
    print(f"\n✓ Trend Regime: {regime['regime'].upper()}")
    
    analyzer = MomentumOscillatorAnalyzer(osc)
    metrics = analyzer.calculate_momentum_metrics(df_momentum)
    print(f"\n✓ Momentum Metrics: Current={metrics['current_momentum']:.4f}")
    
    score_result = analyzer.generate_trading_score(df_momentum, signals)
    print(f"\n✓ Trading Score: {score_result['trading_score']:.1f}/100")
