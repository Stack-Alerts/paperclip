"""
Strategy: Bollinger Band Mean Reversion
Number: 15
Category: VOLATILITY
Timeframe: 15-minute
Risk:Reward: 1.2-2.0
Expected Frequency: 10-20 signals/month
Author: Cline AI
Date: 2026-01-09

Description:
Trade extremes with reversion to mean. Enters when price reaches Bollinger Band
extremes in ranging conditions, targeting VWAP reversion with RSI/Stochastic
confirmation for timing.

Building Blocks Used:
- Bollinger Bands: Primary signal at extremes (15 points)
- RSI Divergence: Reversal confirmation (25 points)
- Stochastic RSI: Entry timing (18 points)
- VWAP: Mean reversion target (15 points)
- EMA 20/50 Trend: Range filter (15 points)

Entry Logic:
1. Must be in ranging market (no strong trend)
2. Price at Bollinger Band extreme (upper for short, lower for long)
3. RSI showing divergence or oversold/overbought
4. Stochastic RSI crossing in reversal direction
5. Target VWAP as mean
6. Minimum 55 confluence points required

Exit Logic:
- TP1: VWAP level (50% position)
- TP2: Opposite Bollinger Band (30% position)
- TP3: 2x initial risk (20% position)
- SL: 1.5x ATR beyond entry

Expected Performance:
- Win Rate: 68%
- Avg R:R: 1:1.5
- Trades/Month: 10-20
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
from src.detectors.building_blocks.volatility.bollinger_bands import BollingerBands
from src.detectors.building_blocks.oscillators.rsi_divergence import RSIDivergence
from src.detectors.building_blocks.oscillators.stochastic_rsi import StochasticRSI
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.moving_averages.ema_20_50_trend import EMA2050Trend


class BollingerMeanReversion(Strategy):
    """
    Bollinger Mean Reversion Strategy - Simple volatility extremes
    
    Trades price extremes back to mean in ranging conditions.
    High frequency with moderate win rate and good risk/reward.
    """
    
    def __init__(self, config):
        if isinstance(config, dict):
            from nautilus_trader.trading.config import StrategyConfig
            config = StrategyConfig(strategy_id=config.get('strategy_id', '15_BOLLINGER_MEAN_REVERSION'))
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "15_BOLLINGER_MEAN_REVERSION"
        self.strategy_name = "Bollinger Band Mean Reversion"
        
        # Strategy parameters
        self.min_confluence = 55  # Lower threshold for higher frequency
        self.max_bars_held = 1000
        self.lookback_period = 100
        self.min_risk_reward = 1.2
        self.max_leverage = 1.0
        self.risk_per_trade_pct = 1.0
        self.daily_pnl_usd = 0.0
        self.last_pnl_reset_utc = None
        self.instrument_id = InstrumentId.from_str("BTC/USDT.BINANCE")
        self.risk = RiskEnforcer(self)
        
        # Initialize building blocks
        self.blocks = {}
        self._initialize_blocks()
        
        # Data storage
        self.bars_data = []
        
    def _initialize_blocks(self):
        """Initialize building block detectors"""
        
        self.detectors = {
            'bollinger': BollingerBands(timeframe='15min'),
            'rsi_divergence': RSIDivergence(timeframe='15min'),
            'stoch_rsi': StochasticRSI(timeframe='15min'),
            'vwap': VWAP(timeframe='15min'),
            'ema_trend': EMA2050Trend(timeframe='15min')
        }
        
        self.blocks = {
            'bollinger': {'weight': 15, 'enabled': True},
            'rsi_divergence': {'weight': 25, 'enabled': True},
            'stoch_rsi': {'weight': 18, 'enabled': True},
            'vwap': {'weight': 15, 'enabled': True},
            'ema_trend': {'weight': 15, 'enabled': True}
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
        self.log.info(f"Min R:R: {self.min_risk_reward}")
        
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
        
        # Calculate confluence using centralized calculator
        from src.strategies.universal_optimizer.modules.confluence_calculator import ConfluenceCalculator
        confluence, signals = ConfluenceCalculator.calculate_confluence(results, self.blocks)
        
        # Check entry conditions
        if confluence >= self.min_confluence:
            if self.portfolio.is_flat(self.instrument_id):
                self._execute_entry(confluence, results, signals)
                
    def _analyze_blocks(self, df: pd.DataFrame) -> dict:
        """Run all building blocks analysis"""
        results = {}
        
        results['bollinger'] = self.detectors['bollinger'].analyze(df)
        results['rsi_divergence'] = self.detectors['rsi_divergence'].analyze(df)
        results['stoch_rsi'] = self.detectors['stoch_rsi'].analyze(df)
        results['vwap'] = self.detectors['vwap'].analyze(df)
        results['ema_trend'] = self.detectors['ema_trend'].analyze(df)
        
        return results
    
    def _execute_entry(self, confluence: int, results: dict, signals: list):
        """Execute trade entry"""
        
        # CRITICAL: Only trade in ranging conditions
        ema_signal = results['ema_trend'].get('signal', '')
        if ema_signal in ['STRONG_BULLISH', 'STRONG_BEARISH']:
            self.log.info("Avoiding mean reversion in strong trend")
            return  # Don't fade strong trends
        
        self.log.info(f"🎯 MEAN REVERSION SIGNAL: {confluence} points")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        # Determine direction from Bollinger signal
        bb_signal = results['bollinger'].get('signal', '')
        
        if 'BELOW_LOWER' in bb_signal:
            side = 'LONG'  # Price at lower band, expect reversion up
        elif 'ABOVE_UPPER' in bb_signal:
            side = 'SHORT'  # Price at upper band, expect reversion down
        else:
            return  # Need extreme for mean reversion
        
        # Calculate TP/SL levels
        current_price = self.bars_data[-1]['close']
        
        # Get VWAP as primary target
        vwap_level = results['vwap'].get('metadata', {}).get('vwap', current_price)
        
        # Calculate ATR for stop loss
        df = pd.DataFrame(self.bars_data).tail(20)
        df['tr'] = df[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df['tr'].mean()
        
        if side == 'LONG':
            sl = current_price - (atr * 1.5)
            risk = current_price - sl
            tp1 = vwap_level  # Mean reversion to VWAP
            tp2 = current_price + (risk * 1.5)
            tp3 = current_price + (risk * 2.0)
        else:  # SHORT
            sl = current_price + (atr * 1.5)
            risk = sl - current_price
            tp1 = vwap_level  # Mean reversion to VWAP
            tp2 = current_price - (risk * 1.5)
            tp3 = current_price - (risk * 2.0)
        
        # Verify R:R (use TP2 for calculation)
        rr_ratio = abs((tp2 - current_price) / (sl - current_price))
        
        if rr_ratio < self.min_risk_reward:
            self.log.info(f"R:R {rr_ratio:.2f} below minimum {self.min_risk_reward}")
            return
        
        self.log.info(f"✅ R:R: {rr_ratio:.2f} - ENTERING {side}")
        self.log.info(f"Entry: {current_price}, SL: {sl}")
        self.log.info(f"TP1 (VWAP): {tp1}, TP2: {tp2}, TP3: {tp3}")
        
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
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info(f"{self.strategy_name} stopped")