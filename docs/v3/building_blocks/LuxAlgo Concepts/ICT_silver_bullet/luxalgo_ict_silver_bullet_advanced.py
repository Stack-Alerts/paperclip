"""
LuxAlgo ICT Silver Bullet - Advanced Analysis
==============================================

Advanced utilities for ICT Silver Bullet analysis including market structure
detection, liquidity analysis, and trading signal generation.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from luxalgo_ict_silver_bullet import (
    SilverBulletIndicator,
    SessionType,
    TrendDirection,
    FVGMode,
    SilverBulletSession,
)


@dataclass
class LiquidityPool:
    """Detected liquidity pool for targeting."""
    level: float
    pool_type: str  # 'buy_side', 'sell_side'
    strength: int  # Number of times touched
    last_touched: pd.Timestamp


class MarketStructureAnalyzer:
    """Analyze market structure and identify key levels."""
    
    @staticmethod
    def identify_buy_side_liquidity(df: pd.DataFrame, fvgs: List[Dict],
                                   lookback: int = 50) -> List[LiquidityPool]:
        """
        Identify buy-side liquidity (swing lows, support levels).
        
        Args:
            df: OHLCV DataFrame
            fvgs: List of FVGs
            lookback: Lookback period for swing analysis
        
        Returns:
            List of liquidity pools
        """
        pools = []
        
        # Find swing lows
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback//2:i+lookback//2]
            if df.iloc[i]['low'] == window['low'].min():
                level = df.iloc[i]['low']
                
                # Count times this level was touched
                touches = sum(1 for bar in df.iloc[i:] 
                            if abs(bar['low'] - level) < (level * 0.001))
                
                pools.append(LiquidityPool(
                    level=level,
                    pool_type='buy_side',
                    strength=touches,
                    last_touched=df.index[i],
                ))
        
        return pools
    
    @staticmethod
    def identify_sell_side_liquidity(df: pd.DataFrame, fvgs: List[Dict],
                                    lookback: int = 50) -> List[LiquidityPool]:
        """
        Identify sell-side liquidity (swing highs, resistance levels).
        
        Args:
            df: OHLCV DataFrame
            fvgs: List of FVGs
            lookback: Lookback period for swing analysis
        
        Returns:
            List of liquidity pools
        """
        pools = []
        
        # Find swing highs
        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback//2:i+lookback//2]
            if df.iloc[i]['high'] == window['high'].max():
                level = df.iloc[i]['high']
                
                # Count times this level was touched
                touches = sum(1 for bar in df.iloc[i:] 
                            if abs(bar['high'] - level) < (level * 0.001))
                
                pools.append(LiquidityPool(
                    level=level,
                    pool_type='sell_side',
                    strength=touches,
                    last_touched=df.index[i],
                ))
        
        return pools


class TradingSignalGenerator:
    """Generate trading signals from Silver Bullet analysis."""
    
    @staticmethod
    def detect_bullish_setup(fvgs: List[Dict], sr_lines: List[Dict],
                            trend: str, current_price: float) -> Optional[Dict]:
        """
        Detect bullish Silver Bullet setup.
        
        Requirements:
        - Bullish FVG detected
        - Trend is bullish
        - FVG not yet retested
        - Price near support
        
        Args:
            fvgs: List of FVGs
            sr_lines: List of S/R lines
            trend: Current trend
            current_price: Current price
        
        Returns:
            Setup dictionary if detected
        """
        if trend != 'bullish':
            return None
        
        # Find bullish FVGs
        bullish_fvgs = [f for f in fvgs if f['type'] == 'bullish' 
                       and not f.get('retested', False)]
        
        if not bullish_fvgs:
            return None
        
        # Get nearest support
        fvg = bullish_fvgs[-1]  # Most recent
        support_level = fvg['low']
        
        # Check if price is near support (within 0.5%)
        if abs(current_price - support_level) < (support_level * 0.005):
            return {
                'type': 'bullish',
                'entry_zone': support_level,
                'stop_loss': fvg['low'] * 0.99,  # Below FVG
                'target': fvg['high'] * 1.02,  # Above FVG
                'confidence': 'high' if fvg['trend_aligned'] else 'medium',
            }
        
        return None
    
    @staticmethod
    def detect_bearish_setup(fvgs: List[Dict], sr_lines: List[Dict],
                            trend: str, current_price: float) -> Optional[Dict]:
        """
        Detect bearish Silver Bullet setup.
        
        Requirements:
        - Bearish FVG detected
        - Trend is bearish
        - FVG not yet retested
        - Price near resistance
        
        Args:
            fvgs: List of FVGs
            sr_lines: List of S/R lines
            trend: Current trend
            current_price: Current price
        
        Returns:
            Setup dictionary if detected
        """
        if trend != 'bearish':
            return None
        
        # Find bearish FVGs
        bearish_fvgs = [f for f in fvgs if f['type'] == 'bearish'
                       and not f.get('retested', False)]
        
        if not bearish_fvgs:
            return None
        
        # Get nearest resistance
        fvg = bearish_fvgs[-1]  # Most recent
        resistance_level = fvg['high']
        
        # Check if price is near resistance (within 0.5%)
        if abs(current_price - resistance_level) < (resistance_level * 0.005):
            return {
                'type': 'bearish',
                'entry_zone': resistance_level,
                'stop_loss': fvg['high'] * 1.01,  # Above FVG
                'target': fvg['low'] * 0.98,  # Below FVG
                'confidence': 'high' if fvg['trend_aligned'] else 'medium',
            }
        
        return None
    
    @staticmethod
    def detect_fvg_break_and_retest(fvgs: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """
        Detect FVGs being retested (potential entry signals).
        
        Args:
            fvgs: List of FVGs
            df: OHLCV DataFrame
        
        Returns:
            List of retest setups
        """
        retests = []
        
        for fvg in fvgs:
            if fvg.get('retested'):
                retest_time = fvg.get('retest_bar')
                if retest_time and retest_time in df.index:
                    idx = df.index.get_loc(retest_time)
                    
                    # Check for candle pattern at retest
                    retest_bar = df.iloc[idx]
                    
                    if fvg['type'] == 'bullish':
                        # Bullish candle at FVG = strong bounce
                        if retest_bar['close'] > retest_bar['open']:
                            retests.append({
                                'fvg_type': 'bullish',
                                'fvg_level': fvg['low'],
                                'retest_time': retest_time,
                                'signal_strength': 'strong',
                                'setup': 'Buy at support',
                            })
                    else:
                        # Bearish candle at FVG = strong bounce
                        if retest_bar['close'] < retest_bar['open']:
                            retests.append({
                                'fvg_type': 'bearish',
                                'fvg_level': fvg['high'],
                                'retest_time': retest_time,
                                'signal_strength': 'strong',
                                'setup': 'Sell at resistance',
                            })
        
        return retests


class SessionPerformanceAnalyzer:
    """Analyze performance of each Silver Bullet session."""
    
    @staticmethod
    def analyze_session_moves(df: pd.DataFrame,
                            session_type: SessionType) -> Dict:
        """
        Analyze price movements during a specific session.
        
        Args:
            df: OHLCV DataFrame
            session_type: Session to analyze
        
        Returns:
            Performance statistics
        """
        session_bars = []
        
        for idx, row in df.iterrows():
            if SilverBulletSession.get_session_type(idx) == session_type:
                session_bars.append(row)
        
        if not session_bars:
            return {'bars': 0}
        
        session_df = pd.DataFrame(session_bars)
        
        return {
            'session': SilverBulletSession.get_session_name(session_type),
            'bars': len(session_df),
            'avg_range': (session_df['high'] - session_df['low']).mean(),
            'avg_move': abs(session_df['close'].iloc[-1] - session_df['close'].iloc[0]),
            'volatility': session_df['close'].std(),
            'open': session_df['close'].iloc[0],
            'close': session_df['close'].iloc[-1],
            'direction': 'up' if session_df['close'].iloc[-1] > session_df['close'].iloc[0] else 'down',
        }
    
    @staticmethod
    def compare_sessions(df: pd.DataFrame) -> Dict:
        """Compare all three Silver Bullet sessions."""
        results = {}
        
        for session_type in [SessionType.LONDON_OPEN, SessionType.AM_SESSION, SessionType.PM_SESSION]:
            results[session_type.value] = SessionPerformanceAnalyzer.analyze_session_moves(
                df, session_type
            )
        
        return results


class SilverBulletReporter:
    """Generate Silver Bullet analysis reports."""
    
    @staticmethod
    def generate_session_report(results: Dict) -> str:
        """Generate report of Silver Bullet sessions."""
        
        report = """
╔════════════════════════════════════════════════════════════════╗
║         ICT SILVER BULLET - SESSION ANALYSIS REPORT            ║
╚════════════════════════════════════════════════════════════════╝

📊 Market Structure
   Trend: {trend}
   FVGs Detected: {fvg_count}
   S/R Lines Generated: {sr_count}

""".format(
            trend=results.get('trend', 'unknown').upper(),
            fvg_count=len(results.get('fvgs', [])),
            sr_count=len(results.get('sr_lines', [])),
        )
        
        # Session breakdown
        report += "\n⏰ Silver Bullet Sessions:\n"
        for session_type, data in results.get('sessions', {}).items():
            report += f"   {SilverBulletSession.get_session_name(session_type)}\n"
            report += f"      FVGs: {len(data.get('fvgs', []))}\n"
            report += f"      S/R Lines: {len(data.get('sr_lines', []))}\n"
        
        return report
    
    @staticmethod
    def generate_fvg_report(fvgs: List[Dict]) -> str:
        """Generate FVG detailed report."""
        
        report = """
╔════════════════════════════════════════════════════════════════╗
║            ICT SILVER BULLET - FVG ANALYSIS                    ║
╚════════════════════════════════════════════════════════════════╝

"""
        
        bullish_fvgs = [f for f in fvgs if f['type'] == 'bullish']
        bearish_fvgs = [f for f in fvgs if f['type'] == 'bearish']
        
        report += f"📈 Bullish FVGs: {len(bullish_fvgs)}\n"
        for fvg in bullish_fvgs[:3]:
            report += f"   Low: {fvg['low']:.4f}, High: {fvg['high']:.4f}\n"
            report += f"   Retested: {'Yes' if fvg.get('retested') else 'No'}\n"
        
        report += f"\n📉 Bearish FVGs: {len(bearish_fvgs)}\n"
        for fvg in bearish_fvgs[:3]:
            report += f"   Low: {fvg['low']:.4f}, High: {fvg['high']:.4f}\n"
            report += f"   Retested: {'Yes' if fvg.get('retested') else 'No'}\n"
        
        return report
    
    @staticmethod
    def generate_setup_report(setup: Optional[Dict]) -> str:
        """Generate trading setup report."""
        
        if not setup:
            return "No valid setup detected at this time."
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║             ICT SILVER BULLET - TRADING SETUP                  ║
╚════════════════════════════════════════════════════════════════╝

🎯 Setup Type: {setup['type'].upper()}
   Confidence: {setup['confidence'].upper()}

📍 Entry Zone: {setup['entry_zone']:.4f}
   Stop Loss: {setup['stop_loss']:.4f}
   Target: {setup['target']:.4f}

⚡ Risk/Reward: 1:{(abs(setup['target'] - setup['entry_zone']) / abs(setup['entry_zone'] - setup['stop_loss'])):.2f}
"""
        
        return report


if __name__ == "__main__":
    import numpy as np
    
    dates = pd.date_range('2024-01-01', periods=500, freq='3min')
    prices = 100 + np.cumsum(np.random.randn(500) * 0.1)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(500) * 0.05,
        'high': prices + np.abs(np.random.randn(500) * 0.1),
        'low': prices - np.abs(np.random.randn(500) * 0.1),
        'close': prices,
        'volume': np.random.randint(1000, 100000, 500),
    }, index=dates)
    
    sb = SilverBulletIndicator(fvg_mode=FVGMode.TREND_ALIGNED)
    df_result, results = sb.analyze(df)
    
    print("=" * 70)
    print("ICT SILVER BULLET - ADVANCED ANALYSIS")
    print("=" * 70)
    
    reporter = SilverBulletReporter()
    print(reporter.generate_session_report(results))
    print(reporter.generate_fvg_report(results['fvgs']))
    
    # Trading signals
    current_price = df['close'].iloc[-1]
    bullish_setup = TradingSignalGenerator.detect_bullish_setup(
        results['fvgs'], results['sr_lines'], results['trend'], current_price
    )
    
    if bullish_setup:
        print(reporter.generate_setup_report(bullish_setup))
    
    # Session performance
    perf = SessionPerformanceAnalyzer.compare_sessions(df)
    print("\n✓ Session Performance:")
    for session, data in perf.items():
        if data.get('bars', 0) > 0:
            print(f"  {session}: {data['bars']} bars")
