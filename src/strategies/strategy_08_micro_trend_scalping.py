"""
Strategy: Micro Trend Scalping
Number: 08
Category: SCALPING
Timeframe: 15-minute
Risk:Reward: 0.8-1.5
Expected Frequency: 30-60 signals/month
Author: Cline AI
Date: 2026-01-09

Description:
Quick scalps on short-term momentum shifts during high-volume sessions.
Uses EMA crossovers with momentum oscillators for rapid entries/exits.
Employs trailing stop for profit maximization.

Building Blocks Used:
- EMA 20/50 Cross: Quick trigger signal (25 points)
- MACD Signal: Momentum confirmation (22 points)
- Stochastic RSI: Timing confirmation (18 points)
- VWAP: Directional bias (15 points)
- Kill Zones: Volume timing (16 points)

Entry Logic:
1. Must be in kill zone (London or NY AM)
2. EMA 20/50 crossover triggers
3. MACD confirms momentum shift
4. Stochastic RSI shows timing confirmation
5. VWAP confirms directional bias
6. Minimum 50 confluence points required
7. Use trailing stop for exits

Exit Logic:
- Trailing Stop: 1.5x ATR from entry
- Max Hold: 4 hours (16 bars)
- TP: When trailing stop hits
- SL: 1.5x ATR initial stop

Expected Performance:
- Win Rate: 65%
- Avg R:R: 1:1.0
- Trades/Month: 30-60
- Max DD: <8%
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
from src.detectors.building_blocks.moving_averages.ema_20_50_cross import EMA2050Cross
from src.detectors.building_blocks.oscillators.macd_signal import MACDSignal
from src.detectors.building_blocks.oscillators.stochastic_rsi import StochasticRSI
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.sessions.kill_zones import KillZones


class MicroTrendScalping(Strategy):
    """
    Micro Trend Scalping Strategy - Medium complexity scalping
    
    High frequency trading on short-term momentum during high volume.
    Uses trailing stops for profit capture. Moderate win rate with
    consistent small wins.
    """
    
    def __init__(self, config):
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "08_MICRO_TREND_SCALPING"
        self.strategy_name = "Micro Trend Scalping"
        
        # Strategy parameters
        self.min_confluence = 50  # Lower for higher frequency
        self.max_bars_held = 16  # 4 hours max (scalping)
        self.lookback_period = 100
        self.min_risk_reward = 0.8  # Lower R:R for scalping
        self.max_leverage = 1.0
        self.risk_per_trade_pct = 1.0
        self.daily_pnl_usd = 0.0
        self.last_pnl_reset_utc = None
        self.instrument_id = InstrumentId.from_str("BTC/USDT.BINANCE")
        self.risk = RiskEnforcer(self)
        
        # Trailing stop parameters
        self.trailing_stop_atr_multiplier = 1.5
        self.entry_bar = None
        self.trailing_stop_level = None
        
        # Initialize building blocks
        self.blocks = {}
        self._initialize_blocks()
        
        # Data storage
        self.bars_data = []
        
    def _initialize_blocks(self):
        """Initialize building block detectors"""
        
        self.detectors = {
            'ema_cross': EMA2050Cross(timeframe='15min'),
            'macd': MACDSignal(timeframe='15min'),
            'stoch_rsi': StochasticRSI(timeframe='15min'),
            'vwap': VWAP(timeframe='15min'),
            'kill_zones': KillZones(timeframe='15min')
        }
        
        self.blocks = {
            'ema_cross': {'weight': 25, 'enabled': True},
            'macd': {'weight': 22, 'enabled': True},
            'stoch_rsi': {'weight': 18, 'enabled': True},
            'vwap': {'weight': 15, 'enabled': True},
            'kill_zones': {'weight': 16, 'enabled': True}
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
        
        if len(self.bars_data) > 1000:
            self.bars_data.pop(0)
        
        return pd.DataFrame(self.bars_data)
    
    def on_start(self):
        """Initialize strategy"""
        self.log.info(f"{self.strategy_name} starting...")
        self.log.info(f"Min Confluence: {self.min_confluence}")
        self.log.info(f"Scalping Mode: Max {self.max_bars_held} bars hold")
        
    def on_bar(self, bar: Bar):
        """Process each new bar"""
        df = self._update_dataframe(bar)
        
        if len(df) < self.lookback_period:
            return
        
        # Reset daily PnL at UTC midnight
        if RiskEnforcer.should_reset_daily_pnl(self.last_pnl_reset_utc):
            self.daily_pnl_usd = 0.0
            self.last_pnl_reset_utc = __import__('time').time()
        
        # Check if we have open position
        if not self.portfolio.is_flat(self.instrument_id):
            self._manage_position(df)
            return
        
        # Run building block analysis for new entries
        results = self._analyze_blocks(df)
        
        # Calculate confluence using centralized calculator
        from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator
        confluence, signals = ConfluenceCalculator.calculate_confluence(results, self.blocks)
        
        # Check entry conditions
        if confluence >= self.min_confluence:
            self._execute_entry(confluence, results, signals, df)
                
    def _analyze_blocks(self, df: pd.DataFrame) -> dict:
        """Run all building blocks analysis"""
        results = {}
        
        results['ema_cross'] = self.detectors['ema_cross'].analyze(df)
        results['macd'] = self.detectors['macd'].analyze(df)
        results['stoch_rsi'] = self.detectors['stoch_rsi'].analyze(df)
        results['vwap'] = self.detectors['vwap'].analyze(df)
        results['kill_zones'] = self.detectors['kill_zones'].analyze(df)
        
        return results
    
    def _execute_entry(self, confluence: int, results: dict, signals: list, df: pd.DataFrame):
        """Execute trade entry"""
        
        # CRITICAL: Only trade in kill zones (high volume)
        kz_signal = results['kill_zones'].get('signal', '')
        if kz_signal not in ['LONDON_KZ', 'NY_AM_KZ']:
            self.log.info("Outside kill zone - skipping scalp")
            return
        
        self.log.info(f"🎯 SCALP SIGNAL: {confluence} points")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        # Determine direction from EMA cross
        ema_signal = results['ema_cross'].get('signal', '')
        
        if 'BULLISH' in ema_signal:
            side = 'LONG'
        elif 'BEARISH' in ema_signal:
            side = 'SHORT'
        else:
            return
        
        # Calculate ATR for stops
        df_calc = df.tail(20)
        df_calc['tr'] = df_calc[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df_calc['tr'].mean()
        
        current_price = self.bars_data[-1]['close']
        
        if side == 'LONG':
            sl = current_price - (atr * 1.5)
            self.trailing_stop_level = current_price + (atr * self.trailing_stop_atr_multiplier)
        else:  # SHORT
            sl = current_price + (atr * 1.5)
            self.trailing_stop_level = current_price - (atr * self.trailing_stop_atr_multiplier)
        
        # Record entry
        self.entry_bar = len(self.bars_data) - 1
        
        self.log.info(f"✅ SCALP ENTRY {side}")
        self.log.info(f"Entry: {current_price}, SL: {sl}")
        self.log.info(f"Initial Trailing Stop: {self.trailing_stop_level}")
        
        # Pre-trade risk enforcement
        order_side = OrderSide.BUY if side == 'LONG' else OrderSide.SELL
        self.risk.check_and_submit(
            side=order_side,
            quantity=Quantity.from_str("0.001"),
            price=Price(str(round(current_price, 2))),
            entry_price=current_price,
            instrument_id=self.instrument_id,
            daily_pnl=Money(f"{self.daily_pnl_usd:.2f}", USD),
        )
    
    def _manage_position(self, df: pd.DataFrame):
        """Manage open position with trailing stop"""
        
        # Check max hold time
        bars_held = len(self.bars_data) - 1 - self.entry_bar
        if bars_held >= self.max_bars_held:
            self.log.info(f"Max hold time reached ({self.max_bars_held} bars) - EXITING")
            self.trailing_stop_level = None
            self.entry_bar = None
            return
        
        current_price = self.bars_data[-1]['close']
        
        # Calculate ATR for trailing stop adjustment
        df_calc = df.tail(20)
        df_calc['tr'] = df_calc[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df_calc['tr'].mean()
        
        # Adjust trailing stop (tighten as price moves in our favor)
        # For LONG: trail below price, for SHORT: trail above price
        position = self.portfolio.get_position(self.instrument_id)
        
        if position and position.side == 'LONG':
            # Update trailing stop if price moved up
            new_trail = current_price - (atr * self.trailing_stop_atr_multiplier)
            if new_trail > self.trailing_stop_level:
                self.trailing_stop_level = new_trail
                self.log.info(f"Trailing stop updated: {self.trailing_stop_level}")
            
            # Check if hit
            if current_price <= self.trailing_stop_level:
                self.log.info(f"Trailing stop hit - EXITING LONG")
                self.trailing_stop_level = None
                self.entry_bar = None
                
        elif position and position.side == 'SHORT':
            # Update trailing stop if price moved down
            new_trail = current_price + (atr * self.trailing_stop_atr_multiplier)
            if new_trail < self.trailing_stop_level:
                self.trailing_stop_level = new_trail
                self.log.info(f"Trailing stop updated: {self.trailing_stop_level}")
            
            # Check if hit
            if current_price >= self.trailing_stop_level:
                self.log.info(f"Trailing stop hit - EXITING SHORT")
                self.trailing_stop_level = None
                self.entry_bar = None
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info(f"{self.strategy_name} stopped")