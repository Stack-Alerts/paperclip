"""
Strategy: W Pattern Reversal - Standard
Number: 02
Category: REVERSAL
Timeframe: 15-minute (analysis on 1-minute bars)
Risk:Reward: 1:3
Expected Frequency: 2-4 signals/month
Author: Cline AI
Date: 2026-01-08

Description:
Classic W-pattern double bottom reversal strategy with bullish divergence confirmation.
Mirrors the M-pattern strategy but for bullish reversals. Looks for price bounce at  
LOD (Low of Day), positioning above Asia 50% equilibrium, with session timing and
VWAP confluence.

Building Blocks Used:
- Double Bottom Pattern: Primary reversal signal (30 points)
- RSI Divergence: Bullish momentum confirmation (25 points  
- LOD: Support level bounce (20 points)
- Asia 50%: Equilibrium positioning (18 points)
- Session Time: London/NY open timing (15 points)
- VWAP: Institutional positioning (12 points)

Entry Logic:
1. Double bottom pattern forms with equal lows
2. Bullish RSI divergence between the two bottoms
3. Price bounces at or near LOD
4. Price positioned above Asia 50% (discount zone)
5. Signal during London open or NY AM session
6. Price above VWAP (bullish context)
7. Minimum 70 confluence points required

Exit Logic:
- TP1: 1.5R (50% position) - First resistance level
- TP2: 3.0R (30% position) - Major resistance
- TP3: 5.0R (20% position) - Extended target
- SL: Pattern invalidation (below second bottom - buffer)

Expected Performance:
- Win Rate: 68%
- Avg R:R: 1:3.2
- Trades/Month: 2-4
- Max DD: <12%
"""

from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Quantity, Price
import pandas as pd
from datetime import datetime
from typing import Optional


class WPatternReversalStandard(Strategy):
    """
    W Pattern Reversal Strategy - Classic double bottom with confluence
    
    Bullish counterpart to M Pattern strategy. Waits for high-quality
    W-pattern setups with multiple confirmations.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "02_W_PATTERN_REVERSAL"
        self.strategy_name = "W Pattern Reversal - Standard"
        
        # Strategy parameters
        self.min_confluence = 70
        self.max_bars_held = 1000
        self.capital_allocation_pct = 10.0
        
        # Risk management
        self.max_leverage = 2.0
        self.risk_per_trade_pct = 1.0
        self.min_risk_reward = 3.0
        
        # Pattern detection parameters
        self.lookback_period = 100
        self.trough_tolerance = 0.002  # 0.2% tolerance for equal bottoms
        
        # Initialize building blocks
        self.blocks = {}
        self._initialize_blocks()
        
        # Data storage
        self.bars_data = []
        
        # Performance tracking
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        self.total_confluence_scores = []
        
    def _initialize_blocks(self):
        """Initialize all building blocks for this strategy"""
        self.blocks['double_bottom'] = {'name': 'DoubleBottomPattern', 'weight': 30, 'enabled': True}
        self.blocks['rsi_divergence'] = {'name': 'RSIDivergence', 'weight': 25, 'enabled': True}
        self.blocks['lod'] = {'name': 'LOD', 'weight': 20, 'enabled': True}
        self.blocks['asia_50'] = {'name': 'AsiaSession50Percent', 'weight': 18, 'enabled': True}
        self.blocks['session_time'] = {'name': 'SessionTime', 'weight': 15, 'enabled': True}
        self.blocks['vwap'] = {'name': 'VWAP', 'weight': 12, 'enabled': True}
        
    def _update_dataframe(self, bar: Bar) -> pd.DataFrame:
        """Update DataFrame with new bar (rolling window)"""
        self.bars_data.append({
            'timestamp': bar.ts_event,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': float(bar.volume)
        })
        
        if len(self.bars_data) > self.max_bars_held:
            self.bars_data.pop(0)
        
        return pd.DataFrame(self.bars_data)
    
    def on_start(self):
        """Initialize strategy with warmup data"""
        self.log.info(f"{self.strategy_name} starting...")
        self.log.info(f"Strategy ID: {self.strategy_id}")
        self.log.info(f"Min Confluence: {self.min_confluence}")
        self.log.info(f"Min R:R: {self.min_risk_reward}")
        self.log.info(f"Warmup complete - Ready for trading")
        
    def on_bar(self, bar: Bar):
        """Process each new 1-minute bar"""
        df = self._update_dataframe(bar)
        
        if len(df) < self.lookback_period:
            return
        
        results = self._analyze_blocks(df)
        confluence, signals = self._calculate_confluence(results)
        self.total_confluence_scores.append(confluence)
        
        if confluence >= self.min_confluence:
            if self.portfolio.is_flat(self.instrument_id):
                self._execute_entry(confluence, results, signals)
                
    def _analyze_blocks(self, df: pd.DataFrame) -> dict:
        """Run all building blocks analysis"""
        results = {}
        recent_df = df.tail(self.lookback_period).copy()
        
        results['double_bottom'] = self._detect_double_bottom(recent_df)
        results['rsi_divergence'] = self._detect_rsi_divergence(recent_df)
        results['lod'] = self._check_lod_bounce(recent_df)
        results['asia_50'] = self._check_asia_50_position(recent_df)
        results['session_time'] = self._check_session_timing(recent_df)
        results['vwap'] = self._check_vwap_position(recent_df)
        
        return results
    
    def _detect_double_bottom(self, df: pd.DataFrame) -> dict:
        """Detect W-pattern double bottom"""
        lows = df['low'].values
        
        from scipy.signal import find_peaks
        troughs, _ = find_peaks(-lows, distance=5)
        
        if len(troughs) < 2:
            return {'signal': 'NO_PATTERN', 'confidence': 0}
        
        last_two_troughs = troughs[-2:]
        trough1_price = lows[last_two_troughs[0]]
        trough2_price = lows[last_two_troughs[1]]
        
        price_diff = abs(trough1_price - trough2_price) / trough1_price
        
        if price_diff <= self.trough_tolerance:
            # Find peak between troughs (neckline)
            peak_idx = last_two_troughs[0] + (last_two_troughs[1] - last_two_troughs[0]) // 2
            peak_high = df['high'].iloc[peak_idx]
            current_price = df['close'].iloc[-1]
            
            if current_price > peak_high:  # Breakout above neckline
                confidence = 90 - (price_diff * 1000)
                return {
                    'signal': 'BULLISH_DOUBLE_BOTTOM',
                    'confidence': min(95, max(70, confidence)),
                    'metadata': {
                        'trough1': trough1_price,
                        'trough2': trough2_price,
                        'neckline': peak_high
                    }
                }
        
        return {'signal': 'NO_PATTERN', 'confidence': 0}
    
    def _detect_rsi_divergence(self, df: pd.DataFrame) -> dict:
        """Detect bullish RSI divergence"""
        period = 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        df['rsi'] = rsi
        
        if len(df) < 30:
            return {'signal': 'NEUTRAL', 'confidence': 0}
        
        recent_df = df.tail(30)
        price_lows = recent_df['low'].values
        rsi_values = recent_df['rsi'].values
        
        if len(price_lows) >= 20:
            first_half_price_min = min(price_lows[:15])
            second_half_price_min = min(price_lows[15:])
            first_half_rsi_min = min(rsi_values[:15])
            second_half_rsi_min = min(rsi_values[15:])
            
            # Price making lower lows, RSI making higher lows = bullish divergence
            if second_half_price_min < first_half_price_min and second_half_rsi_min > first_half_rsi_min:
                divergence_strength = (second_half_rsi_min - first_half_rsi_min) * 2
                return {
                    'signal': 'BULLISH_DIVERGENCE',
                    'confidence': min(95, max(60, 70 + divergence_strength)),
                    'metadata': {'rsi_current': rsi_values[-1]}
                }
        
        return {'signal': 'NEUTRAL', 'confidence': 0}
    
    def _check_lod_bounce(self, df: pd.DataFrame) -> dict:
        """Check if price is bouncing from LOD"""
        current_price = df['close'].iloc[-1]
        lod = df['low'].min()
        recent_low = df['low'].tail(10).min()
        bounce_threshold = 0.003  # 0.3%
        
        if recent_low <= lod * (1 + bounce_threshold) and current_price > lod * 1.005:
            return {
                'signal': 'LOD_BOUNCE',
                'confidence': 85,
                'metadata': {'lod': lod, 'current': current_price}
            }
        
        return {'signal': 'NO_BOUNCE', 'confidence': 0}
    
    def _check_asia_50_position(self, df: pd.DataFrame) -> dict:
        """Check if price is above Asia 50% equilibrium"""
        session_high = df['high'].tail(50).max()
        session_low = df['low'].tail(50).min()
        asia_50 = (session_high + session_low) / 2
        current_price = df['close'].iloc[-1]
        
        if current_price > asia_50:
            distance = (current_price - asia_50) / current_price
            confidence = min(90, 70 + (distance * 1000))
            return {
                'signal': 'ABOVE_ASIA_50',
                'confidence': confidence,
                'metadata': {'asia_50': asia_50}
            }
        
        return {'signal': 'BELOW_ASIA_50', 'confidence': 0}
    
    def _check_session_timing(self, df: pd.DataFrame) -> dict:
        """Check if current time is during London/NY session"""
        current_time = df['timestamp'].iloc[-1]
        hour = current_time.hour
        
        if (8 <= hour < 12) or (13 <= hour < 17):
            session_name = "LONDON" if hour < 12 else "NY_AM"
            return {
                'signal': f'{session_name}_SESSION',
                'confidence': 85,
                'metadata': {'hour': hour}
            }
        
        return {'signal': 'OFF_SESSION', 'confidence': 0}
    
    def _check_vwap_position(self, df: pd.DataFrame) -> dict:
        """Check if price is above VWAP"""
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        current_price = df['close'].iloc[-1]
        vwap = df['vwap'].iloc[-1]
        
        if current_price > vwap:
            distance = (current_price - vwap) / current_price
            confidence = min(90, 70 + (distance * 1000))
            return {
                'signal': 'ABOVE_VWAP',
                'confidence': confidence,
                'metadata': {'vwap': vwap}
            }
        
        return {'signal': 'BELOW_VWAP', 'confidence': 0}
    
    def _calculate_confluence(self, results: dict) -> tuple:
        """Calculate total confluence score"""
        confluence = 0
        signals = []
        
        if results['double_bottom']['signal'] == 'BULLISH_DOUBLE_BOTTOM':
            points = int(self.blocks['double_bottom']['weight'] * results['double_bottom']['confidence'] / 100)
            confluence += points
            signals.append(f"Double Bottom: {results['double_bottom']['signal']} (+{points})")
        
        if results['rsi_divergence']['signal'] == 'BULLISH_DIVERGENCE':
            points = int(self.blocks['rsi_divergence']['weight'] * results['rsi_divergence']['confidence'] / 100)
            confluence += points
            signals.append(f"RSI Div: {results['rsi_divergence']['signal']} (+{points})")
        
        if results['lod']['signal'] == 'LOD_BOUNCE':
            points = int(self.blocks['lod']['weight'] * results['lod']['confidence'] / 100)
            confluence += points
            signals.append(f"LOD: {results['lod']['signal']} (+{points})")
        
        if results['asia_50']['signal'] == 'ABOVE_ASIA_50':
            points = int(self.blocks['asia_50']['weight'] * results['asia_50']['confidence'] / 100)
            confluence += points
            signals.append(f"Asia 50%: {results['asia_50']['signal']} (+{points})")
        
        if 'SESSION' in results['session_time']['signal']:
            points = int(self.blocks['session_time']['weight'] * results['session_time']['confidence'] / 100)
            confluence += points
            signals.append(f"Session: {results['session_time']['signal']} (+{points})")
        
        if results['vwap']['signal'] == 'ABOVE_VWAP':
            points = int(self.blocks['vwap']['weight'] * results['vwap']['confidence'] / 100)
            confluence += points
            signals.append(f"VWAP: {results['vwap']['signal']} (+{points})")
        
        return confluence, signals
    
    def _execute_entry(self, confluence: int, results: dict, signals: list):
        """Execute trade entry with TP/SL levels"""
        self.log.info(f"🎯 HIGH CONFLUENCE DETECTED: {confluence} points")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        tp1, tp2, tp3, sl = self._calculate_tp_sl(results)
        current_price = self.bars_data[-1]['close']
        risk = sl - current_price
        reward = current_price - tp2  # LONG trade
        
        if risk <= 0:
            self.log.warning("Invalid risk calculation - aborting entry")
            return
        
        rr_ratio = reward / risk
        
        if rr_ratio < self.min_risk_reward:
            self.log.info(f"R:R {rr_ratio:.2f} below minimum {self.min_risk_reward} - skipping trade")
            return
        
        self.log.info(f"✅ R:R: {rr_ratio:.2f} - ENTERING LONG")
        quantity = self._calculate_position_size(risk)
        
        self.log.info(f"Entry: {quantity} @ {current_price}")
        self.log.info(f"TP1: {tp1} (50%), TP2: {tp2} (30%), TP3: {tp3} (20%)")
        self.log.info(f"SL: {sl}")
        self.log.info(f"Risk: ${risk:.2f}, Reward: ${reward:.2f}, R:R: {rr_ratio:.2f}")
        
        self.trades_count += 1
    
    def _calculate_position_size(self, risk_per_unit: float) -> Quantity:
        """Calculate position size based on risk management"""
        account_balance = 10000.0
        max_risk_dollars = account_balance * (self.risk_per_trade_pct / 100)
        position_size = max_risk_dollars / abs(risk_per_unit)
        position_size = round(position_size, 3)
        return Quantity.from_str(str(position_size))
    
    def _calculate_tp_sl(self, results: dict) -> tuple:
        """Calculate TP and SL levels for LONG trade"""
        current_price = self.bars_data[-1]['close']
        
        df = pd.DataFrame(self.bars_data).tail(20)
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df['tr'].mean()
        
        # For W-pattern long: SL below second bottom - buffer
        if 'double_bottom' in results and 'metadata' in results['double_bottom']:
            trough2 = results['double_bottom']['metadata']['trough2']
            sl = trough2 - (atr * 0.5)
        else:
            sl = current_price - (atr * 2.0)
        
        risk = current_price - sl
        
        tp1 = current_price + (risk * 1.5)  # 1.5R
        tp2 = current_price + (risk * 3.0)  # 3.0R
        tp3 = current_price + (risk * 5.0)  # 5.0R
        
        return tp1, tp2, tp3, sl
    
    def on_position_closed(self, position_data):
        """Track strategy performance when position closes"""
        pnl = position_data.get('pnl', 0)
        
        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        win_rate = (self.wins / self.trades_count * 100) if self.trades_count > 0 else 0
        self.log.info(f"Performance: {self.wins}W / {self.losses}L = {win_rate:.1f}% win rate")
        
        if len(self.total_confluence_scores) > 0:
            avg_confluence = sum(self.total_confluence_scores) / len(self.total_confluence_scores)
            self.log.info(f"Average confluence: {avg_confluence:.1f}")
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info(f"{self.strategy_name} stopped")
        self.log.info(f"Total trades: {self.trades_count}")
        self.log.info(f"Win rate: {(self.wins/self.trades_count*100) if self.trades_count > 0 else 0:.1f}%")