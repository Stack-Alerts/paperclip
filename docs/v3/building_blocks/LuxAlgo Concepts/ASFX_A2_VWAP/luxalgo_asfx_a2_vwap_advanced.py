"""
LuxAlgo ASFX A2 VWAP - Advanced Analysis
========================================

Advanced utilities for A2 VWAP analysis including signal performance tracking,
support/resistance identification, and multi-timeframe analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from luxalgo_asfx_a2_vwap import (
    A2Signal, SignalType, StopLoss, ASFXA2VWAP
)


@dataclass
class SignalPerformance:
    """Track signal performance metrics."""
    signal: A2Signal
    entry_price: float
    entry_time: pd.Timestamp
    exit_price: Optional[float] = None
    exit_time: Optional[pd.Timestamp] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    bars_to_target: Optional[int] = None
    hit_stop: bool = False
    hit_target: bool = False


class SignalPerformanceAnalyzer:
    """Analyze A2 signal performance and accuracy."""
    
    @staticmethod
    def analyze_signal_trades(signals: List[A2Signal], df: pd.DataFrame,
                             stop_losses: List[StopLoss],
                             lookforward_bars: int = 20) -> List[SignalPerformance]:
        """
        Analyze how many bars forward before hitting target or stop.
        
        Args:
            signals: List of A2 signals
            df: OHLCV DataFrame
            stop_losses: List of stop-loss levels
            lookforward_bars: Bars to look forward
        
        Returns:
            List of SignalPerformance objects
        """
        performances = []
        
        for i, signal in enumerate(signals):
            if signal.timestamp not in df.index:
                continue
            
            signal_idx = df.index.get_loc(signal.timestamp)
            entry_price = signal.price_close
            
            # Look forward
            lookforward_end = min(signal_idx + lookforward_bars, len(df))
            future_bars = df.iloc[signal_idx:lookforward_end]
            
            exit_price = None
            exit_time = None
            bars_to_target = None
            hit_stop = False
            hit_target = False
            
            # Get stop-loss
            stop = stop_losses[i] if i < len(stop_losses) else None
            
            # Check for target/stop hit
            for j, (idx, bar) in enumerate(future_bars.iterrows()):
                if signal.signal_type == SignalType.BULLISH:
                    # Check stop-loss (low below stop)
                    if stop and bar['low'] < stop.stop_level:
                        exit_price = stop.stop_level
                        exit_time = idx
                        hit_stop = True
                        bars_to_target = j
                        break
                    
                    # Check for high target (arbitrary 2% or VWAP band hit)
                    target = entry_price * 1.02
                    if bar['high'] > target:
                        exit_price = target
                        exit_time = idx
                        hit_target = True
                        bars_to_target = j
                        break
                
                else:  # BEARISH
                    # Check stop-loss (high above stop)
                    if stop and bar['high'] > stop.stop_level:
                        exit_price = stop.stop_level
                        exit_time = idx
                        hit_stop = True
                        bars_to_target = j
                        break
                    
                    # Check for low target
                    target = entry_price * 0.98
                    if bar['low'] < target:
                        exit_price = target
                        exit_time = idx
                        hit_target = True
                        bars_to_target = j
                        break
            
            # Calculate P&L if exit found
            pnl = None
            pnl_pct = None
            if exit_price:
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
            
            performances.append(SignalPerformance(
                signal=signal,
                entry_price=entry_price,
                entry_time=signal.timestamp,
                exit_price=exit_price,
                exit_time=exit_time,
                pnl=pnl,
                pnl_pct=pnl_pct,
                bars_to_target=bars_to_target,
                hit_stop=hit_stop,
                hit_target=hit_target,
            ))
        
        return performances
    
    @staticmethod
    def calculate_win_rate(performances: List[SignalPerformance]) -> Dict:
        """
        Calculate signal accuracy metrics.
        
        Args:
            performances: List of signal performances
        
        Returns:
            Dictionary with accuracy metrics
        """
        if not performances:
            return {}
        
        total = len(performances)
        winners = sum(1 for p in performances if p.hit_target)
        losers = sum(1 for p in performances if p.hit_stop)
        pending = total - winners - losers
        
        bullish = [p for p in performances if p.signal.signal_type == SignalType.BULLISH]
        bearish = [p for p in performances if p.signal.signal_type == SignalType.BEARISH]
        
        avg_bars = np.mean([p.bars_to_target for p in performances 
                           if p.bars_to_target is not None])
        
        return {
            'total_signals': total,
            'winners': winners,
            'losers': losers,
            'pending': pending,
            'win_rate': (winners / (winners + losers) * 100) if (winners + losers) > 0 else 0,
            'bullish_count': len(bullish),
            'bearish_count': len(bearish),
            'bullish_win_rate': (sum(1 for p in bullish if p.hit_target) / len(bullish) * 100) if bullish else 0,
            'bearish_win_rate': (sum(1 for p in bearish if p.hit_target) / len(bearish) * 100) if bearish else 0,
            'avg_bars_to_exit': avg_bars,
        }


class VWAPSupportResistance:
    """Identify support and resistance from VWAP bands."""
    
    @staticmethod
    def identify_support_levels(df: pd.DataFrame, vwap: List[float],
                               bands: Dict, strength_threshold: int = 2) -> List[Dict]:
        """
        Identify support levels from VWAP bands.
        
        Args:
            df: OHLCV DataFrame
            vwap: VWAP values
            bands: Band dictionary
            strength_threshold: Minimum touches for significance
        
        Returns:
            List of support level dictionaries
        """
        supports = []
        
        # Central VWAP as support in uptrend
        for i in range(1, len(df)):
            if (df.iloc[i-1]['close'] > vwap[i-1] and 
                df.iloc[i]['low'] < vwap[i]):
                level = vwap[i]
                
                # Count touches
                touches = sum(1 for j in range(i, len(df)) 
                            if abs(df.iloc[j]['low'] - level) < (level * 0.005))
                
                if touches >= strength_threshold:
                    supports.append({
                        'level': level,
                        'type': 'vwap_center',
                        'touches': touches,
                        'first_test': df.index[i],
                    })
        
        # 1x StDev as support
        if 'lower_1.0' in bands:
            for i in range(1, len(df)):
                if (df.iloc[i-1]['close'] > bands['lower_1.0'][i-1] and 
                    df.iloc[i]['low'] < bands['lower_1.0'][i]):
                    level = bands['lower_1.0'][i]
                    supports.append({
                        'level': level,
                        'type': 'vwap_lower_1sd',
                        'touches': 1,
                        'first_test': df.index[i],
                    })
        
        return supports
    
    @staticmethod
    def identify_resistance_levels(df: pd.DataFrame, vwap: List[float],
                                  bands: Dict, strength_threshold: int = 2) -> List[Dict]:
        """
        Identify resistance levels from VWAP bands.
        
        Args:
            df: OHLCV DataFrame
            vwap: VWAP values
            bands: Band dictionary
            strength_threshold: Minimum touches for significance
        
        Returns:
            List of resistance level dictionaries
        """
        resistances = []
        
        # Central VWAP as resistance in downtrend
        for i in range(1, len(df)):
            if (df.iloc[i-1]['close'] < vwap[i-1] and 
                df.iloc[i]['high'] > vwap[i]):
                level = vwap[i]
                
                # Count touches
                touches = sum(1 for j in range(i, len(df)) 
                            if abs(df.iloc[j]['high'] - level) < (level * 0.005))
                
                if touches >= strength_threshold:
                    resistances.append({
                        'level': level,
                        'type': 'vwap_center',
                        'touches': touches,
                        'first_test': df.index[i],
                    })
        
        # 1x StDev as resistance
        if 'upper_1.0' in bands:
            for i in range(1, len(df)):
                if (df.iloc[i-1]['close'] < bands['upper_1.0'][i-1] and 
                    df.iloc[i]['high'] > bands['upper_1.0'][i]):
                    level = bands['upper_1.0'][i]
                    resistances.append({
                        'level': level,
                        'type': 'vwap_upper_1sd',
                        'touches': 1,
                        'first_test': df.index[i],
                    })
        
        return resistances


class MultiTimeframeAnalyzer:
    """Analyze A2 VWAP across multiple timeframes."""
    
    @staticmethod
    def align_signals(daily_results: Dict, intraday_results: Dict,
                     timeframe_ratio: int = 5) -> List[Dict]:
        """
        Find aligned signals across timeframes.
        
        Args:
            daily_results: Daily ASFX results
            intraday_results: Intraday ASFX results
            timeframe_ratio: Intraday/daily ratio
        
        Returns:
            List of aligned signal opportunities
        """
        aligned = []
        
        daily_signals = daily_results['signals']
        intraday_signals = intraday_results['signals']
        
        for daily_sig in daily_signals:
            # Find intraday signals within timeframe window
            matching_intraday = [s for s in intraday_signals 
                               if abs((s.timestamp - daily_sig.timestamp).total_seconds()) 
                                  < (86400 / timeframe_ratio)]  # Within session
            
            if matching_intraday:
                # Check direction alignment
                same_direction = [s for s in matching_intraday 
                                if s.signal_type == daily_sig.signal_type]
                
                if same_direction:
                    aligned.append({
                        'daily_signal': daily_sig,
                        'intraday_signals': same_direction,
                        'alignment_strength': len(same_direction),
                        'confidence': 'high' if len(same_direction) > 1 else 'medium',
                    })
        
        return aligned


class ASFXA2VWAPReporter:
    """Generate A2 VWAP analysis reports."""
    
    @staticmethod
    def generate_signal_report(signals: List[A2Signal],
                             performances: List[SignalPerformance]) -> str:
        """Generate signal analysis report."""
        
        metrics = SignalPerformanceAnalyzer.calculate_win_rate(performances)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║            ASFX A2 VWAP - SIGNAL ANALYSIS REPORT               ║
╚════════════════════════════════════════════════════════════════╝

📊 Signal Statistics:
   Total Signals: {metrics.get('total_signals', 0)}
   Bullish: {metrics.get('bullish_count', 0)}
   Bearish: {metrics.get('bearish_count', 0)}

✓ Performance:
   Win Rate: {metrics.get('win_rate', 0):.1f}%
   Winners: {metrics.get('winners', 0)}
   Losers: {metrics.get('losers', 0)}
   Pending: {metrics.get('pending', 0)}

📈 Bullish Signals:
   Win Rate: {metrics.get('bullish_win_rate', 0):.1f}%
   Count: {metrics.get('bullish_count', 0)}

📉 Bearish Signals:
   Win Rate: {metrics.get('bearish_win_rate', 0):.1f}%
   Count: {metrics.get('bearish_count', 0)}

⏱️ Timing:
   Avg Bars to Exit: {metrics.get('avg_bars_to_exit', 0):.0f}

"""
        return report
    
    @staticmethod
    def generate_vwap_report(df: pd.DataFrame, vwap: List[float],
                            supports: List[Dict], resistances: List[Dict]) -> str:
        """Generate VWAP bands and levels report."""
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║        ASFX A2 VWAP - SUPPORT & RESISTANCE REPORT              ║
╚════════════════════════════════════════════════════════════════╝

📍 Current Price: ${df['close'].iloc[-1]:.2f}
📍 Current VWAP: ${vwap[-1]:.2f}

Support Levels: {len(supports)}
"""
        for supp in supports[:3]:
            report += f"\n   {supp['type']}: ${supp['level']:.2f}"
            report += f" (Touches: {supp['touches']})"
        
        report += f"\n\nResistance Levels: {len(resistances)}\n"
        for resis in resistances[:3]:
            report += f"\n   {resis['type']}: ${resis['level']:.2f}"
            report += f" (Touches: {resis['touches']})"
        
        return report


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=50, freq='1D')
    prices = 100 + np.cumsum(np.random.randn(50) * 1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(50) * 0.5,
        'high': prices + np.abs(np.random.randn(50) * 1),
        'low': prices - np.abs(np.random.randn(50) * 1),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 50),
    }, index=dates)
    
    asfx = ASFXA2VWAP()
    df_result, results = asfx.analyze(df)
    
    print("=" * 70)
    print("ASFX A2 VWAP - ADVANCED ANALYSIS")
    print("=" * 70)
    
    performances = SignalPerformanceAnalyzer.analyze_signal_trades(
        results['signals'], df_result, results['stop_losses']
    )
    
    reporter = ASFXA2VWAPReporter()
    print(reporter.generate_signal_report(results['signals'], performances))
    
    supports = VWAPSupportResistance.identify_support_levels(
        df_result, results['vwap'], results['bands']
    )
    resistances = VWAPSupportResistance.identify_resistance_levels(
        df_result, results['vwap'], results['bands']
    )
    
    print(reporter.generate_vwap_report(df_result, results['vwap'], supports, resistances))
