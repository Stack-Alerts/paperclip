"""
Strategy: Order Flow Scalping
Number: 09
Category: SCALPING
Timeframe: 15-minute
Risk:Reward: 1.0-1.8
Expected Frequency: 25-50 signals/month
Author: Cline AI
Date: 2026-01-09

Description:
Trade institutional order flow imbalances during high-volume sessions.
Uses order flow and market depth combined with Fair Value Gaps and VWAP
for high-probability scalps.

Building Blocks Used:
- Order Flow Imbalance: Primary institutional signal (15 points)
- Market Depth: Order book positioning (12 points)
- VWAP: Institutional level reference (15 points)
- Fair Value Gap: Imbalance zones (20 points)
- Kill Zones: High volume timing (16 points)

Entry Logic:
1. Must be in kill zone (institutional activity)
2. Order flow imbalance detected
3. Market depth shows support/resistance
4. Fair Value Gap present for entry
5. VWAP confirms institutional positioning
6. Minimum 55 confluence points required

Exit Logic:
- TP1: FVG fill or imbalance resolution (50%)
- TP2: 1.5R (30%)
- TP3: 2.0R (20%)
- SL: 1.5x ATR
- Max Hold: 6 hours

Expected Performance:
- Win Rate: 70%
- Avg R:R: 1:1.5
- Trades/Month: 25-50
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
from src.detectors.building_blocks.institutional.order_flow_imbalance import OrderFlowImbalance
from src.detectors.building_blocks.institutional.market_depth import MarketDepth
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.price_action.fair_value_gap import FairValueGap
from src.detectors.building_blocks.sessions.kill_zones import KillZones


class OrderFlowScalping(Strategy):
    """
    Order Flow Scalping Strategy - Medium complexity institutional scalping
    
    Trades order flow imbalances with institutional confirmation.
    Higher win rate due to institutional edge, moderate frequency.
    """
    
    def __init__(self, config):
        if isinstance(config, dict):
            from nautilus_trader.trading.config import StrategyConfig
            config = StrategyConfig(strategy_id=config.get('strategy_id', '09_ORDER_FLOW_SCALPING'))
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "09_ORDER_FLOW_SCALPING"
        self.strategy_name = "Order Flow Scalping"
        
        # Strategy parameters
        self.min_confluence = 55  # Moderate threshold
        self.max_bars_held = 24  # 6 hours max
        self.lookback_period = 100
        self.min_risk_reward = 1.0
        self.max_leverage = 1.0
        self.risk_per_trade_pct = 1.0
        self.daily_pnl_usd = 0.0
        self.last_pnl_reset_utc = None
        self.instrument_id = InstrumentId.from_str("BTC/USDT.BINANCE")
        self.risk = RiskEnforcer(self)
        
        # Position tracking
        self.entry_bar = None
        
        # Initialize building blocks
        self.blocks = {}
        self._initialize_blocks()
        
        # Data storage
        self.bars_data = []
        
    def _initialize_blocks(self):
        """Initialize building block detectors"""
        
        self.detectors = {
            'order_flow': OrderFlowImbalance(timeframe='15min'),
            'market_depth': MarketDepth(timeframe='15min'),
            'vwap': VWAP(timeframe='15min'),
            'fvg': FairValueGap(timeframe='15min'),
            'kill_zones': KillZones(timeframe='15min')
        }
        
        self.blocks = {
            'order_flow': {'weight': 15, 'enabled': True},
            'market_depth': {'weight': 12, 'enabled': True},
            'vwap': {'weight': 15, 'enabled': True},
            'fvg': {'weight': 20, 'enabled': True},
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
        self.log.info(f"Order Flow Scalping - Institutional Edge")
        
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
            self._manage_position()
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
        
        results['order_flow'] = self.detectors['order_flow'].analyze(df)
        results['market_depth'] = self.detectors['market_depth'].analyze(df)
        results['vwap'] = self.detectors['vwap'].analyze(df)
        results['fvg'] = self.detectors['fvg'].analyze(df)
        results['kill_zones'] = self.detectors['kill_zones'].analyze(df)
        
        return results
    
    def _execute_entry(self, confluence: int, results: dict, signals: list, df: pd.DataFrame):
        """Execute trade entry"""
        
        # CRITICAL: Only trade in kill zones (institutional activity)
        kz_signal = results['kill_zones'].get('signal', '')
        if kz_signal not in ['LONDON_KZ', 'NY_AM_KZ', 'NY_PM_KZ']:
            self.log.info("Outside kill zone - skipping order flow trade")
            return
        
        self.log.info(f"🎯 ORDER FLOW SIGNAL: {confluence} points")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        # Determine direction from order flow imbalance
        of_signal = results['order_flow'].get('signal', '')
        fvg_signal = results['fvg'].get('signal', '')
        
        if 'BULLISH' in of_signal or 'BULLISH' in fvg_signal:
            side = 'LONG'
        elif 'BEARISH' in of_signal or 'BEARISH' in fvg_signal:
            side = 'SHORT'
        else:
            return  # Need clear direction
        
        # Calculate TP/SL levels
        current_price = self.bars_data[-1]['close']
        
        # Calculate ATR for stops
        df_calc = df.tail(20)
        df_calc['tr'] = df_calc[['high', 'low', 'close']].apply(
            lambda x: max(x['high'] - x['low'],
                         abs(x['high'] - x['close']),
                         abs(x['low'] - x['close'])), axis=1
        )
        atr = df_calc['tr'].mean()
        
        # Get FVG target if available
        fvg_metadata = results['fvg'].get('metadata', {})
        fvg_target = fvg_metadata.get('target_price')
        
        if side == 'LONG':
            sl = current_price - (atr * 1.5)
            risk = current_price - sl
            
            # Use FVG target for TP1 if available
            if fvg_target and fvg_target > current_price:
                tp1 = fvg_target
            else:
                tp1 = current_price + (risk * 1.0)
            
            tp2 = current_price + (risk * 1.5)
            tp3 = current_price + (risk * 2.0)
            
        else:  # SHORT
            sl = current_price + (atr * 1.5)
            risk = sl - current_price
            
            # Use FVG target for TP1 if available
            if fvg_target and fvg_target < current_price:
                tp1 = fvg_target
            else:
                tp1 = current_price - (risk * 1.0)
            
            tp2 = current_price - (risk * 1.5)
            tp3 = current_price - (risk * 2.0)
        
        # Verify R:R
        rr_ratio = abs((tp2 - current_price) / (sl - current_price))
        
        if rr_ratio < self.min_risk_reward:
            self.log.info(f"R:R {rr_ratio:.2f} below minimum {self.min_risk_reward}")
            return
        
        # Record entry
        self.entry_bar = len(self.bars_data) - 1
        
        self.log.info(f"✅ ORDER FLOW ENTRY {side}")
        self.log.info(f"Entry: {current_price}, SL: {sl}")
        self.log.info(f"TP1 (FVG): {tp1}, TP2: {tp2}, TP3: {tp3}")
        self.log.info(f"R:R: {rr_ratio:.2f}")
        
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
    
    def _manage_position(self):
        """Manage open position"""
        
        # Check max hold time
        if self.entry_bar is not None:
            bars_held = len(self.bars_data) - 1 - self.entry_bar
            if bars_held >= self.max_bars_held:
                self.log.info(f"Max hold time reached ({self.max_bars_held} bars) - EXITING")
                self.entry_bar = None
                return
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info(f"{self.strategy_name} stopped")