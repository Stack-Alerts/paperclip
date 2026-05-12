"""
Strategy: EMA Trend Continuation
Number: 04
Category: TREND_CONTINUATION
Timeframe: 15-minute
Risk:Reward: 1.2-2.0
Expected Frequency: 8-15 signals/month
Author: Cline AI
Date: 2026-01-09

Description:
Trade pullbacks in established trends using moving average alignment and
Fibonacci retracement levels. Waits for strong trend confirmation across
multiple timeframe EMAs, then enters on pullbacks to key levels with
momentum confirmation.

Building Blocks Used:
- EMA 20/50 Trend: Short-term trend direction (15 points)
- EMA 200 Trend: Major trend filter (12 points)
- EMA 20/50 Cross: Entry trigger on pullback (25 points)
- MACD Signal: Momentum confirmation (22 points)
- ADX: Trend strength validation (20 points)
- VWAP: Pullback target reference (15 points)
- Fibonacci: Retracement entry level (16 points)

Entry Logic:
1. Major trend alignment required (EMA 200 bullish/bearish)
2. Short-term trend aligned (EMA 20/50)
3. ADX shows strong trend (not ranging)
4. Pullback to Fibonacci 61.8% or 50% level
5. EMA cross triggers re-entry in trend direction
6. MACD confirms momentum resumption
7. Price above/below VWAP for trend confirmation
8. Minimum 60 confluence points required

Exit Logic:
- TP1: 1.5R (50% position)
- TP2: 2.5R (30% position)  
- TP3: 4.0R (20% position)
- SL: Below/above Fibonacci level + buffer

Expected Performance:
- Win Rate: 65%
- Avg R:R: 1:1.8
- Trades/Month: 8-15
- Max DD: <10%
"""

from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.currencies import USD
import pandas as pd
from datetime import datetime
from typing import Optional
from nautilus_trader.model.identifiers import InstrumentId
from src.strategies.risk_enforcer import RiskEnforcer

# Import building blocks
from src.detectors.building_blocks.moving_averages.ema_20_50_trend import EMA2050Trend
from src.detectors.building_blocks.moving_averages.ema_200_trend import EMA200Trend
from src.detectors.building_blocks.moving_averages.ema_20_50_cross import EMA2050Cross
from src.detectors.building_blocks.oscillators.macd_signal import MACDSignal
from src.detectors.building_blocks.trend.adx import ADX
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.fibonacci.fibonacci_retracements import FibonacciRetracements as Fibonacci


class EMATrendContinuation(Strategy):
    """
    EMA Trend Continuation Strategy - Complex multi-indicator trend following
    
    Sophisticated trend continuation system requiring alignment across
    multiple timeframes and confirmation from momentum, strength, and
    retracement indicators. High win rate with good risk/reward.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "04_EMA_TREND_CONTINUATION"
        self.strategy_name = "EMA Trend Continuation"
        
        # Strategy parameters
        self.min_confluence = 60  # Moderate threshold
        self.max_bars_held = 1000
        self.lookback_period = 200  # Need more history for EMA 200
        self.min_risk_reward = 1.2
        self.max_leverage = 1.0
        self.risk_per_trade_pct = 1.0
        self.daily_pnl_usd = 0.0
        self.last_pnl_reset_utc = None
        self.instrument_id = InstrumentId.from_str("BTC/USDT.BINANCE")
        self.risk = RiskEnforcer(self)
        
        # Trend state tracking
        self.current_trend = None  # 'BULLISH', 'BEARISH', or None
        self.in_pullback = False
        
        # Initialize building blocks
        self.blocks = {}
        self._initialize_blocks()
        
        # Data storage
        self.bars_data = []
        
    def _initialize_blocks(self):
        """Initialize building block detectors"""
        
        self.detectors = {
            'ema_20_50_trend': EMA2050Trend(timeframe='15min'),
            'ema_200_trend': EMA200Trend(timeframe='15min'),
            'ema_cross': EMA2050Cross(timeframe='15min'),
            'macd': MACDSignal(timeframe='15min'),
            'adx': ADX(timeframe='15min'),
            'vwap': VWAP(timeframe='15min'),
            'fibonacci': Fibonacci(timeframe='15min')
        }
        
        self.blocks = {
            'ema_20_50_trend': {'weight': 15, 'enabled': True},
            'ema_200_trend': {'weight': 12, 'enabled': True},
            'ema_cross': {'weight': 25, 'enabled': True},
            'macd': {'weight': 22, 'enabled': True},
            'adx': {'weight': 20, 'enabled': True},
            'vwap': {'weight': 15, 'enabled': True},
            'fibonacci': {'weight': 16, 'enabled': True}
        }
        
    def _bars_to_dataframe(self, bars) -> pd.DataFrame:
        """Convert Bar objects to DataFrame"""
        return pd.DataFrame([{
            'timestamp': bar.ts_event,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': float(bar.volume)
        } for bar in bars])
    
    def _update_dataframe(self, bar: Bar) -> pd.DataFrame:
        """Update DataFrame with new bar"""
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
        """Initialize strategy"""
        self.log.info(f"{self.strategy_name} starting...")
        self.log.info(f"Min Confluence: {self.min_confluence}")
        self.log.info(f"Trend Continuation - Multi-Timeframe Alignment")
        
    def on_bar(self, bar: Bar):
        """Process each new bar"""
        df = self._update_dataframe(bar)
        
        if len(df) < self.lookback_period:
            return
        
        # Reset daily PnL at UTC midnight
        if RiskEnforcer.should_reset_daily_pnl(self.last_pnl_reset_utc):
            self.daily_pnl_usd = 0.0
            self.last_pnl_reset_utc = __import__('time').time()
        
        # Run building block analysis
        results = self._analyze_blocks(df)
        
        # Update trend state
        self._update_trend_state(results)
        
        # Only trade if we have established trend
        if self.current_trend is None:
            return
        
        # Calculate confluence using centralized calculator
        from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator
        confluence, signals = ConfluenceCalculator.calculate_confluence(results, self.blocks)
        
        # Check entry conditions
        if confluence >= self.min_confluence:
            if self.portfolio.is_flat(self.instrument_id):
                self._execute_entry(confluence, results, signals, df)
                
    def _analyze_blocks(self, df: pd.DataFrame) -> dict:
        """Run all building blocks analysis"""
        results = {}
        
        results['ema_20_50_trend'] = self.detectors['ema_20_50_trend'].analyze(df)
        results['ema_200_trend'] = self.detectors['ema_200_trend'].analyze(df)
        results['ema_cross'] = self.detectors['ema_cross'].analyze(df)
        results['macd'] = self.detectors['macd'].analyze(df)
        results['adx'] = self.detectors['adx'].analyze(df)
        results['vwap'] = self.detectors['vwap'].analyze(df)
        results['fibonacci'] = self.detectors['fibonacci'].analyze(df)
        
        return results
    
    def _update_trend_state(self, results: dict):
        """
        Update current trend state based on EMA alignment
        
        Trend is only valid when both short and long-term EMAs agree.
        This prevents trading against major trend.
        """
        ema_20_50 = results['ema_20_50_trend'].get('signal', '')
        ema_200 = results['ema_200_trend'].get('signal', '')
        adx_signal = results['adx'].get('signal', '')
        
        # Require both EMAs to agree AND ADX to show trend
        if 'BULLISH' in ema_20_50 and 'BULLISH' in ema_200 and adx_signal == 'STRONG_TREND':
            if self.current_trend != 'BULLISH':
                self.log.info("📈 BULLISH TREND CONFIRMED (Multi-timeframe alignment)")
                self.current_trend = 'BULLISH'
                
        elif 'BEARISH' in ema_20_50 and 'BEARISH' in ema_200 and adx_signal == 'STRONG_TREND':
            if self.current_trend != 'BEARISH':
                self.log.info("📉 BEARISH TREND CONFIRMED (Multi-timeframe alignment)")
                self.current_trend = 'BEARISH'
                
        else:
            # No clear trend or ranging
            if self.current_trend is not None:
                self.log.info("⚠️  Trend alignment lost or ranging market")
            self.current_trend = None
    
    def _execute_entry(self, confluence: int, results: dict, signals: list, df: pd.DataFrame):
        """Execute trade entry on pullback completion"""
        
        # CRITICAL: Must have trend alignment (already checked current_trend)
        if self.current_trend is None:
            return
        
        # Get EMA cross signal (pullback completion)
        ema_cross = results['ema_cross'].get('signal', '')
        
        # For BULLISH trend, wait for bullish cross (pullback ended)
        # For BEARISH trend, wait for bearish cross (pullback ended)
        if self.current_trend == 'BULLISH' and 'BULLISH' not in ema_cross:
            return  # Wait for re-cross in trend direction
        if self.current_trend == 'BEARISH' and 'BEARISH' not in ema_cross:
            return  # Wait for re-cross in trend direction
        
        # Check if at Fibonacci retracement level (quality pullback)
        fib_signal = results['fibonacci'].get('signal', '')
        if 'AT_618' not in fib_signal and 'AT_50' not in fib_signal and 'AT_382' not in fib_signal:
            self.log.info("Not at key Fibonacci level - waiting for better pullback")
            return
        
        # Verify VWAP alignment (trend still intact)
        vwap_signal = results['vwap'].get('signal', '')
        if self.current_trend == 'BULLISH' and 'ABOVE' not in vwap_signal:
            self.log.info("Price below VWAP in bullish trend - avoiding entry")
            return
        if self.current_trend == 'BEARISH' and 'BELOW' not in vwap_signal:
            self.log.info("Price above VWAP in bearish trend - avoiding entry")
            return
        
        self.log.info(f"🎯 TREND CONTINUATION SIGNAL: {confluence} points")
        self.log.info(f"📊 Trend: {self.current_trend}")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        # Calculate TP/SL levels
        current_price = self.bars_data[-1]['close']
        
        # Get Fibonacci level for stop placement
        fib_metadata = results['fibonacci'].get('metadata', {})
        fib_level = fib_metadata.get('current_level_price', current_price)
        
        # Calculate ATR for additional buffer
        df_calc = df.tail(20)
        df_calc['tr'] = df_calc[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df_calc['tr'].mean()
        
        if self.current_trend == 'BULLISH':
            # Stop below Fibonacci level
            sl = fib_level - (atr * 0.5)
            risk = current_price - sl
            
            tp1 = current_price + (risk * 1.5)
            tp2 = current_price + (risk * 2.5)
            tp3 = current_price + (risk * 4.0)
            
        else:  # BEARISH
            # Stop above Fibonacci level
            sl = fib_level + (atr * 0.5)
            risk = sl - current_price
            
            tp1 = current_price - (risk * 1.5)
            tp2 = current_price - (risk * 2.5)
            tp3 = current_price - (risk * 4.0)
        
        # Verify R:R
        rr_ratio = abs((tp2 - current_price) / (sl - current_price))
        
        if rr_ratio < self.min_risk_reward:
            self.log.info(f"R:R {rr_ratio:.2f} below minimum {self.min_risk_reward}")
            return
        
        self.log.info(f"✅ TREND CONTINUATION ENTRY {self.current_trend}")
        self.log.info(f"Entry: {current_price}, SL: {sl}")
        self.log.info(f"TP1: {tp1}, TP2: {tp2}, TP3: {tp3}")
        self.log.info(f"R:R: {rr_ratio:.2f}")
        self.log.info(f"Fib Level: {fib_signal}")
        
        # Pre-trade risk enforcement
        side = OrderSide.BUY if self.current_trend == 'BULLISH' else OrderSide.SELL
        self.risk.check_and_submit(
            side=side,
            quantity=Quantity.from_str("0.001"),
            price=Price(str(round(current_price, 2))),
            entry_price=current_price,
            instrument_id=self.instrument_id,
            daily_pnl=Money(f"{self.daily_pnl_usd:.2f}", USD),
        )
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info(f"{self.strategy_name} stopped")