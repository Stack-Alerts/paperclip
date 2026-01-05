"""
LuxAlgo Wave Consolidation - Advanced Analysis
==============================================

Advanced utilities for wave consolidation analysis including zone trading,
performance metrics, and zone interaction analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from luxalgo_wave_consolidation import (
    ConsolidationZone, ZoneBias, ZoneStatus
)


@dataclass
class ZoneInteraction:
    """Track zone interaction event."""
    zone: ConsolidationZone
    interaction_type: str  # 'touch', 'rejection', 'break', 'consolidation'
    bar_index: int
    timestamp: pd.Timestamp
    price: float
    bar_close: float


@dataclass
class ZoneTrade:
    """Track zone-based trade performance."""
    zone: ConsolidationZone
    entry_bar: int
    entry_price: float
    entry_reason: str  # 'rejection', 'break', 'consolidation'
    
    exit_bar: Optional[int] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    target_reached: bool = False
    stop_hit: bool = False
    bars_held: int = 0


class ZoneInteractionAnalyzer:
    """Analyze how price interacts with zones."""
    
    @staticmethod
    def analyze_interactions(zones: List[ConsolidationZone],
                           df: pd.DataFrame) -> List[ZoneInteraction]:
        """
        Identify all zone interactions.
        
        Args:
            zones: List of zones
            df: OHLCV DataFrame
        
        Returns:
            List of interactions
        """
        interactions = []
        
        for zone in zones:
            for bar_idx in range(zone.start_bar, min(zone.end_bar + 100, len(df))):
                bar = df.iloc[bar_idx]
                close = bar['close']
                high = bar['high']
                low = bar['low']
                
                # Check for zone crossing
                in_zone = zone.zone_low <= close <= zone.zone_high
                
                # Rejection from zone
                if zone.zone_bias == ZoneBias.BULLISH:
                    if low < zone.zone_low and close > zone.zone_low:
                        interactions.append(ZoneInteraction(
                            zone=zone,
                            interaction_type='rejection',
                            bar_index=bar_idx,
                            timestamp=df.index[bar_idx],
                            price=low,
                            bar_close=close,
                        ))
                else:
                    if high > zone.zone_high and close < zone.zone_high:
                        interactions.append(ZoneInteraction(
                            zone=zone,
                            interaction_type='rejection',
                            bar_index=bar_idx,
                            timestamp=df.index[bar_idx],
                            price=high,
                            bar_close=close,
                        ))
                
                # Touch
                if in_zone and bar_idx > zone.end_bar:
                    interactions.append(ZoneInteraction(
                        zone=zone,
                        interaction_type='touch',
                        bar_index=bar_idx,
                        timestamp=df.index[bar_idx],
                        price=close,
                        bar_close=close,
                    ))
                
                # Break
                if zone.zone_bias == ZoneBias.BULLISH and close < zone.zone_low:
                    interactions.append(ZoneInteraction(
                        zone=zone,
                        interaction_type='break',
                        bar_index=bar_idx,
                        timestamp=df.index[bar_idx],
                        price=close,
                        bar_close=close,
                    ))
                elif zone.zone_bias == ZoneBias.BEARISH and close > zone.zone_high:
                    interactions.append(ZoneInteraction(
                        zone=zone,
                        interaction_type='break',
                        bar_index=bar_idx,
                        timestamp=df.index[bar_idx],
                        price=close,
                        bar_close=close,
                    ))
        
        return interactions


class ZoneTradeAnalyzer:
    """Analyze zone-based trading performance."""
    
    @staticmethod
    def generate_trades(zones: List[ConsolidationZone],
                       df: pd.DataFrame,
                       entry_on: str = 'rejection',
                       lookforward_bars: int = 50) -> List[ZoneTrade]:
        """
        Generate trades from zone interactions.
        
        Args:
            zones: List of zones
            df: OHLCV DataFrame
            entry_on: 'rejection', 'break', or 'consolidation'
            lookforward_bars: Bars to look forward
        
        Returns:
            List of zone trades
        """
        trades = []
        
        for zone in zones:
            for bar_idx in range(zone.end_bar, min(zone.end_bar + 100, len(df))):
                bar = df.iloc[bar_idx]
                close = bar['close']
                high = bar['high']
                low = bar['low']
                
                entry_signal = False
                entry_price = close
                entry_reason = None
                
                # Rejection entry
                if entry_on == 'rejection':
                    if zone.zone_bias == ZoneBias.BULLISH:
                        if low < zone.zone_low and close > zone.zone_low:
                            entry_signal = True
                            entry_price = close
                            entry_reason = 'rejection'
                    else:
                        if high > zone.zone_high and close < zone.zone_high:
                            entry_signal = True
                            entry_price = close
                            entry_reason = 'rejection'
                
                # Break entry
                elif entry_on == 'break':
                    if zone.zone_bias == ZoneBias.BULLISH and close > zone.zone_high:
                        entry_signal = True
                        entry_price = close
                        entry_reason = 'break'
                    elif zone.zone_bias == ZoneBias.BEARISH and close < zone.zone_low:
                        entry_signal = True
                        entry_price = close
                        entry_reason = 'break'
                
                if not entry_signal:
                    continue
                
                trade = ZoneTrade(
                    zone=zone,
                    entry_bar=bar_idx,
                    entry_price=entry_price,
                    entry_reason=entry_reason,
                )
                
                # Look forward for target/stop
                end_idx = min(bar_idx + lookforward_bars, len(df))
                
                for j in range(bar_idx, end_idx):
                    next_bar = df.iloc[j]
                    
                    if zone.zone_bias == ZoneBias.BULLISH:
                        # Target = zone midpoint + zone width
                        target = zone.zone_midpoint + (zone.zone_high - zone.zone_low)
                        stop = zone.zone_low * 0.99
                        
                        if next_bar['high'] >= target:
                            trade.exit_price = target
                            trade.exit_bar = j
                            trade.target_reached = True
                            trade.bars_held = j - bar_idx
                            break
                        elif next_bar['low'] < stop:
                            trade.exit_price = stop
                            trade.exit_bar = j
                            trade.stop_hit = True
                            trade.bars_held = j - bar_idx
                            break
                    
                    else:  # BEARISH
                        # Target = zone midpoint - zone width
                        target = zone.zone_midpoint - (zone.zone_high - zone.zone_low)
                        stop = zone.zone_high * 1.01
                        
                        if next_bar['low'] <= target:
                            trade.exit_price = target
                            trade.exit_bar = j
                            trade.target_reached = True
                            trade.bars_held = j - bar_idx
                            break
                        elif next_bar['high'] > stop:
                            trade.exit_price = stop
                            trade.exit_bar = j
                            trade.stop_hit = True
                            trade.bars_held = j - bar_idx
                            break
                
                # Calculate P&L
                if trade.exit_price:
                    trade.pnl = trade.exit_price - trade.entry_price
                    trade.pnl_pct = (trade.pnl / trade.entry_price) * 100
                
                trades.append(trade)
        
        return trades
    
    @staticmethod
    def calculate_statistics(trades: List[ZoneTrade]) -> Dict:
        """
        Calculate trade statistics.
        
        Args:
            trades: List of trades
        
        Returns:
            Statistics dictionary
        """
        if not trades:
            return {}
        
        completed_trades = [t for t in trades if t.exit_price is not None]
        winners = [t for t in completed_trades if t.target_reached]
        losers = [t for t in completed_trades if t.stop_hit]
        
        rejection_trades = [t for t in trades if t.entry_reason == 'rejection']
        break_trades = [t for t in trades if t.entry_reason == 'break']
        
        bullish_zones = [t for t in trades if t.zone.zone_bias == ZoneBias.BULLISH]
        bearish_zones = [t for t in trades if t.zone.zone_bias == ZoneBias.BEARISH]
        
        return {
            'total_trades': len(trades),
            'completed': len(completed_trades),
            'pending': len(trades) - len(completed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': (len(winners) / len(completed_trades) * 100) if completed_trades else 0,
            'rejection_trades': len(rejection_trades),
            'break_trades': len(break_trades),
            'rejection_win_rate': (sum(1 for t in rejection_trades if t.target_reached) / len(rejection_trades) * 100) if rejection_trades else 0,
            'break_win_rate': (sum(1 for t in break_trades if t.target_reached) / len(break_trades) * 100) if break_trades else 0,
            'bullish_count': len(bullish_zones),
            'bearish_count': len(bearish_zones),
            'bullish_win_rate': (sum(1 for t in bullish_zones if t.target_reached) / len(bullish_zones) * 100) if bullish_zones else 0,
            'bearish_win_rate': (sum(1 for t in bearish_zones if t.target_reached) / len(bearish_zones) * 100) if bearish_zones else 0,
            'avg_bars_to_target': np.mean([t.bars_held for t in winners if t.bars_held]) if winners else 0,
            'avg_bars_to_stop': np.mean([t.bars_held for t in losers if t.bars_held]) if losers else 0,
            'avg_win': np.mean([t.pnl_pct for t in winners if t.pnl_pct]) if winners else 0,
            'avg_loss': np.mean([t.pnl_pct for t in losers if t.pnl_pct]) if losers else 0,
        }


class ZoneCharacteristicsAnalyzer:
    """Analyze zone characteristics and quality."""
    
    @staticmethod
    def analyze_zone_quality(zones: List[ConsolidationZone]) -> List[Dict]:
        """
        Analyze quality metrics for each zone.
        
        Args:
            zones: List of zones
        
        Returns:
            Quality metrics per zone
        """
        quality_metrics = []
        
        for zone in zones:
            quality_score = 50.0
            
            # Width matters - not too tight, not too loose
            if zone.zone_width_pct < 1:
                quality_score += 15
            elif zone.zone_width_pct < 3:
                quality_score += 10
            elif zone.zone_width_pct > 10:
                quality_score -= 10
            
            # Touches indicate strength
            if zone.touches > 2:
                quality_score += min(15, zone.touches * 2)
            
            # Rejections indicate quality
            if zone.rejections > 0:
                quality_score += zone.rejections * 5
            
            quality_metrics.append({
                'zone': zone,
                'quality_score': min(100, max(0, quality_score)),
                'width_pct': zone.zone_width_pct,
                'touches': zone.touches,
                'rejections': zone.rejections,
                'breaks': zone.breaks,
            })
        
        return quality_metrics


class WaveConsolidationReporter:
    """Generate wave consolidation analysis reports."""
    
    @staticmethod
    def generate_zone_report(zones: List[ConsolidationZone]) -> str:
        """Generate zone analysis report."""
        
        active_zones = [z for z in zones if z.status == ZoneStatus.ACTIVE]
        mitigated_zones = [z for z in zones if z.status == ZoneStatus.MITIGATED]
        
        bullish = [z for z in zones if z.zone_bias == ZoneBias.BULLISH]
        bearish = [z for z in zones if z.zone_bias == ZoneBias.BEARISH]
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║       WAVE CONSOLIDATION - ZONE ANALYSIS REPORT                ║
╚════════════════════════════════════════════════════════════════╝

📊 Zone Statistics:
   Total Zones: {len(zones)}
   Active: {len(active_zones)}
   Mitigated: {len(mitigated_zones)}

📈 By Bias:
   Bullish (Support): {len(bullish)}
   Bearish (Resistance): {len(bearish)}

📌 Zone Characteristics:
   Avg Width: {np.mean([z.zone_width_pct for z in zones]):.2f}%
   Avg Touches: {np.mean([z.touches for z in zones]):.1f}
   Total Rejections: {sum(z.rejections for z in zones)}
   Total Breaks: {sum(z.breaks for z in zones)}

"""
        return report
    
    @staticmethod
    def generate_trade_report(trades: List[ZoneTrade]) -> str:
        """Generate zone trade performance report."""
        
        stats = ZoneTradeAnalyzer.calculate_statistics(trades)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║      WAVE CONSOLIDATION - TRADE PERFORMANCE REPORT             ║
╚════════════════════════════════════════════════════════════════╝

📊 Trade Statistics:
   Total Trades: {stats.get('total_trades', 0)}
   Completed: {stats.get('completed', 0)}
   Winners: {stats.get('winners', 0)}
   Losers: {stats.get('losers', 0)}
   Pending: {stats.get('pending', 0)}

✓ Win Rate: {stats.get('win_rate', 0):.1f}%

📊 By Entry Type:
   Rejection Entries: {stats.get('rejection_trades', 0)} ({stats.get('rejection_win_rate', 0):.1f}% win rate)
   Break Entries: {stats.get('break_trades', 0)} ({stats.get('break_win_rate', 0):.1f}% win rate)

📈 By Zone Bias:
   Bullish: {stats.get('bullish_count', 0)} ({stats.get('bullish_win_rate', 0):.1f}% win rate)
   Bearish: {stats.get('bearish_count', 0)} ({stats.get('bearish_win_rate', 0):.1f}% win rate)

💰 P&L:
   Avg Winner: {stats.get('avg_win', 0):+.2f}%
   Avg Loser: {stats.get('avg_loss', 0):+.2f}%

⏱️ Timing:
   Avg Bars to Target: {stats.get('avg_bars_to_target', 0):.0f}
   Avg Bars to Stop: {stats.get('avg_bars_to_stop', 0):.0f}

"""
        return report


if __name__ == "__main__":
    dates = pd.date_range('2024-01-01', periods=200, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.2)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + np.abs(np.random.randn(200) * 0.3),
        'low': prices - np.abs(np.random.randn(200) * 0.3),
        'close': prices,
        'volume': np.random.uniform(1000, 5000, 200),
    }, index=dates)
    
    from luxalgo_wave_consolidation import WaveConsolidationDetector
    
    detector = WaveConsolidationDetector()
    df_result, results = detector.analyze(df)
    
    trades = ZoneTradeAnalyzer.generate_trades(results['zones'], df)
    
    reporter = WaveConsolidationReporter()
    print(reporter.generate_zone_report(results['zones']))
    print(reporter.generate_trade_report(trades))
