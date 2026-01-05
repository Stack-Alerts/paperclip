"""
LuxAlgo Volume by Time - Advanced Analysis
==========================================

Advanced utilities for volume by time analysis including pattern detection,
breakout signals, and volume profile analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from luxalgo_volume_by_time import (
    VolumeByTimeAnalyzer,
    VolumeByTimeBar,
    AggregationMethod,
    VolumeDirection,
)


@dataclass
class VolumePattern:
    """Detected volume pattern."""
    pattern_type: str  # 'accumulation', 'distribution', 'breakout', 'exhaustion'
    time_slot: str
    confidence: float  # 0-100
    description: str
    trading_implication: str


class VolumeProfileAnalyzer:
    """Analyze volume profile by price and time."""
    
    @staticmethod
    def create_time_volume_matrix(analyses: List[VolumeByTimeBar]) -> Dict[str, Dict]:
        """
        Create matrix of volume by time slot.
        
        Args:
            analyses: List of bar analyses
        
        Returns:
            Dictionary with time-based volume statistics
        """
        time_data = defaultdict(lambda: {
            'volumes': [],
            'up_volumes': [],
            'down_volumes': [],
            'closes': [],
            'highs': [],
            'lows': [],
        })
        
        for analysis in analyses:
            time_key = analysis.time_slot.strftime('%H:%M')
            time_data[time_key]['volumes'].append(analysis.current_volume)
            time_data[time_key]['up_volumes'].append(analysis.current_up_volume)
            time_data[time_key]['down_volumes'].append(analysis.current_down_volume)
        
        # Calculate statistics
        profile = {}
        for time_key in sorted(time_data.keys()):
            vols = time_data[time_key]['volumes']
            profile[time_key] = {
                'avg_volume': np.mean(vols),
                'median_volume': np.median(vols),
                'std_volume': np.std(vols),
                'max_volume': np.max(vols),
                'min_volume': np.min(vols),
                'count': len(vols),
            }
        
        return profile
    
    @staticmethod
    def identify_volume_zones(profile: Dict[str, Dict],
                             percentile_high: float = 75,
                             percentile_low: float = 25) -> Dict[str, List[str]]:
        """
        Identify high, normal, and low volume zones.
        
        Args:
            profile: Volume profile dictionary
            percentile_high: Upper percentile threshold
            percentile_low: Lower percentile threshold
        
        Returns:
            Dictionary with time slots grouped by volume zone
        """
        all_avgs = [data['avg_volume'] for data in profile.values()]
        high_threshold = np.percentile(all_avgs, percentile_high)
        low_threshold = np.percentile(all_avgs, percentile_low)
        
        zones = {'high_volume': [], 'normal_volume': [], 'low_volume': []}
        
        for time_key, data in profile.items():
            avg = data['avg_volume']
            if avg >= high_threshold:
                zones['high_volume'].append(time_key)
            elif avg <= low_threshold:
                zones['low_volume'].append(time_key)
            else:
                zones['normal_volume'].append(time_key)
        
        return zones


class VolumeSignalDetector:
    """Detect trading signals from volume analysis."""
    
    @staticmethod
    def detect_accumulation(analyses: List[VolumeByTimeBar],
                          lookback: int = 10,
                          up_volume_ratio: float = 0.65) -> Optional[VolumePattern]:
        """
        Detect accumulation pattern (buy pressure building).
        
        Args:
            analyses: List of bar analyses
            lookback: Bars to analyze
            up_volume_ratio: Threshold for buy dominance
        
        Returns:
            VolumePattern if detected
        """
        if len(analyses) < lookback:
            return None
        
        recent = analyses[-lookback:]
        total_up = sum(a.current_up_volume for a in recent)
        total_down = sum(a.current_down_volume for a in recent)
        total = total_up + total_down
        
        if total == 0:
            return None
        
        up_ratio = total_up / total
        
        if up_ratio > up_volume_ratio:
            confidence = min(100, (up_ratio - up_volume_ratio) / (1 - up_volume_ratio) * 100)
            
            return VolumePattern(
                pattern_type='accumulation',
                time_slot=f"Recent {lookback} bars",
                confidence=confidence,
                description=f"Strong buying pressure: {up_ratio*100:.1f}% buy volume",
                trading_implication='Bullish bias - expect upside movement',
            )
        
        return None
    
    @staticmethod
    def detect_distribution(analyses: List[VolumeByTimeBar],
                           lookback: int = 10,
                           down_volume_ratio: float = 0.65) -> Optional[VolumePattern]:
        """
        Detect distribution pattern (sell pressure building).
        
        Args:
            analyses: List of bar analyses
            lookback: Bars to analyze
            down_volume_ratio: Threshold for sell dominance
        
        Returns:
            VolumePattern if detected
        """
        if len(analyses) < lookback:
            return None
        
        recent = analyses[-lookback:]
        total_up = sum(a.current_up_volume for a in recent)
        total_down = sum(a.current_down_volume for a in recent)
        total = total_up + total_down
        
        if total == 0:
            return None
        
        down_ratio = total_down / total
        
        if down_ratio > down_volume_ratio:
            confidence = min(100, (down_ratio - down_volume_ratio) / (1 - down_volume_ratio) * 100)
            
            return VolumePattern(
                pattern_type='distribution',
                time_slot=f"Recent {lookback} bars",
                confidence=confidence,
                description=f"Strong selling pressure: {down_ratio*100:.1f}% sell volume",
                trading_implication='Bearish bias - expect downside movement',
            )
        
        return None
    
    @staticmethod
    def detect_volume_breakout(analyses: List[VolumeByTimeBar],
                              std_threshold: float = 1.5) -> List[VolumePattern]:
        """
        Detect volume breakouts (unusual volume spikes).
        
        Args:
            analyses: List of bar analyses
            std_threshold: Standard deviation threshold for "unusual"
        
        Returns:
            List of detected breakout patterns
        """
        breakouts = []
        
        # Group by time slot
        time_slots = defaultdict(list)
        for analysis in analyses:
            time_key = analysis.time_slot.strftime('%H:%M')
            time_slots[time_key].append(analysis)
        
        # Check each time slot for outliers
        for time_key, bars in time_slots.items():
            if len(bars) < 2:
                continue
            
            volumes = [b.current_volume for b in bars]
            mean_vol = np.mean(volumes)
            std_vol = np.std(volumes)
            
            # Check if last bar is outlier
            if len(bars) > 0:
                last_vol = bars[-1].current_volume
                z_score = (last_vol - mean_vol) / std_vol if std_vol > 0 else 0
                
                if abs(z_score) > std_threshold:
                    breakouts.append(VolumePattern(
                        pattern_type='breakout',
                        time_slot=time_key,
                        confidence=min(100, abs(z_score) * 30),
                        description=f"Volume {abs(z_score):.1f}σ from average at {time_key}",
                        trading_implication='Unusual volume - potential setup emerging',
                    ))
        
        return breakouts
    
    @staticmethod
    def detect_volume_exhaustion(analyses: List[VolumeByTimeBar],
                                lookback: int = 5,
                                threshold_pct: float = 0.3) -> Optional[VolumePattern]:
        """
        Detect volume exhaustion (declining volume into move).
        
        Args:
            analyses: List of bar analyses
            lookback: Bars to analyze
            threshold_pct: Threshold for volume decline
        
        Returns:
            VolumePattern if detected
        """
        if len(analyses) < lookback:
            return None
        
        recent = analyses[-lookback:]
        volumes = [a.current_volume for a in recent]
        
        # Check if volumes are declining
        volume_trend = np.polyfit(range(len(volumes)), volumes, 1)[0]
        
        avg_vol = np.mean(volumes)
        current_vol = volumes[-1]
        volume_drop = (avg_vol - current_vol) / avg_vol if avg_vol > 0 else 0
        
        if volume_drop > threshold_pct and volume_trend < 0:
            return VolumePattern(
                pattern_type='exhaustion',
                time_slot=f"Last {lookback} bars",
                confidence=min(100, volume_drop * 100),
                description=f"Volume declining: {volume_drop*100:.1f}% below average",
                trading_implication='Move may be losing steam - reversal possible',
            )
        
        return None


class InstitutionalActivityDetector:
    """Detect institutional volume patterns."""
    
    @staticmethod
    def identify_moc_activity(analyses: List[VolumeByTimeBar],
                             hour: int = 15) -> Optional[Dict]:
        """
        Identify Market-on-Close (MOC) activity.
        Power hour typically shows institutional rebalancing.
        
        Args:
            analyses: List of bar analyses
            hour: Hour to identify as MOC (default 15 = 3PM)
        
        Returns:
            Dictionary with MOC analysis
        """
        moc_bars = [a for a in analyses if a.time_slot.hour == hour]
        
        if not moc_bars:
            return None
        
        total_vol = sum(a.current_volume for a in moc_bars)
        total_up = sum(a.current_up_volume for a in moc_bars)
        total_down = sum(a.current_down_volume for a in moc_bars)
        
        avg_vol_hist = np.mean([a.historical_average for a in moc_bars 
                               if not np.isnan(a.historical_average)])
        
        return {
            'moc_hour': hour,
            'total_volume': total_vol,
            'buy_volume': total_up,
            'sell_volume': total_down,
            'vs_historical': (total_vol - avg_vol_hist) / avg_vol_hist if avg_vol_hist > 0 else 0,
            'bias': 'bullish' if total_up > total_down else 'bearish',
        }
    
    @staticmethod
    def identify_institutional_hours(analyses: List[VolumeByTimeBar],
                                    top_n: int = 3) -> List[Dict]:
        """
        Identify top N institutional volume hours.
        
        Args:
            analyses: List of bar analyses
            top_n: Number of top hours to return
        
        Returns:
            List of hour dictionaries
        """
        hour_volumes = defaultdict(list)
        
        for analysis in analyses:
            hour = analysis.time_slot.hour
            hour_volumes[hour].append(analysis.current_volume)
        
        # Calculate average per hour
        hour_avgs = {h: np.mean(vols) for h, vols in hour_volumes.items()}
        
        # Sort and get top N
        top_hours = sorted(hour_avgs.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        return [
            {
                'hour': h,
                'hour_str': f"{h:02d}:00",
                'avg_volume': vol,
                'samples': len(hour_volumes[h]),
            }
            for h, vol in top_hours
        ]


class VolumeByTimeReporter:
    """Generate advanced volume by time reports."""
    
    @staticmethod
    def generate_pattern_report(patterns: List[VolumePattern]) -> str:
        """Generate report of detected patterns."""
        if not patterns:
            return "No patterns detected."
        
        report = """
╔════════════════════════════════════════════════════════════════╗
║            VOLUME BY TIME - PATTERN ANALYSIS                   ║
╚════════════════════════════════════════════════════════════════╝

"""
        for i, pattern in enumerate(patterns, 1):
            report += f"""
{i}. {pattern.pattern_type.upper()}
   Time: {pattern.time_slot}
   Confidence: {pattern.confidence:.0f}%
   Analysis: {pattern.description}
   Implication: {pattern.trading_implication}
"""
        
        return report
    
    @staticmethod
    def generate_institutional_report(moc: Optional[Dict],
                                     inst_hours: List[Dict]) -> str:
        """Generate institutional activity report."""
        report = """
╔════════════════════════════════════════════════════════════════╗
║         VOLUME BY TIME - INSTITUTIONAL ACTIVITY                ║
╚════════════════════════════════════════════════════════════════╝

"""
        
        if moc:
            report += f"""
📊 Market-on-Close (MOC) Activity ({moc['moc_hour']:02d}:00)
   Total Volume: {moc['total_volume']:,.0f}
   Buy Volume: {moc['buy_volume']:,.0f}
   Sell Volume: {moc['sell_volume']:,.0f}
   Bias: {moc['bias'].upper()}
   vs Historical: {moc['vs_historical']*100:+.1f}%

"""
        
        if inst_hours:
            report += """
⏰ Top Institutional Volume Hours:
"""
            for i, hour_data in enumerate(inst_hours, 1):
                report += f"   {i}. {hour_data['hour_str']}: {hour_data['avg_volume']:,.0f} (n={hour_data['samples']})\n"
        
        return report


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2023-12-01', periods=250, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(250) * 0.3)
    volumes = np.random.randint(50000, 500000, 250)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(250) * 0.2),
        'low': prices - np.abs(np.random.randn(250) * 0.2),
        'close': prices,
        'volume': volumes,
    }, index=dates)
    
    vbt = VolumeByTimeAnalyzer()
    df_result, analyses = vbt.analyze(df)
    
    # Pattern detection
    accum = VolumeSignalDetector.detect_accumulation(analyses)
    dist = VolumeSignalDetector.detect_distribution(analyses)
    exhaustion = VolumeSignalDetector.detect_volume_exhaustion(analyses)
    breakouts = VolumeSignalDetector.detect_volume_breakout(analyses)
    
    patterns = [p for p in [accum, dist, exhaustion] if p] + breakouts
    
    print("=" * 70)
    print("VOLUME BY TIME - ADVANCED ANALYSIS")
    print("=" * 70)
    
    reporter = VolumeByTimeReporter()
    print(reporter.generate_pattern_report(patterns))
    
    # Institutional activity
    moc = InstitutionalActivityDetector.identify_moc_activity(analyses, hour=15)
    inst_hours = InstitutionalActivityDetector.identify_institutional_hours(analyses)
    
    print(reporter.generate_institutional_report(moc, inst_hours))
    
    # Profile
    profile = VolumeProfileAnalyzer.create_time_volume_matrix(analyses)
    zones = VolumeProfileAnalyzer.identify_volume_zones(profile)
    print(f"\n✓ High volume times: {len(zones['high_volume'])}")
    print(f"✓ Normal volume times: {len(zones['normal_volume'])}")
    print(f"✓ Low volume times: {len(zones['low_volume'])}")
