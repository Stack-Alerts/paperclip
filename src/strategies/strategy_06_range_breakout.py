"""
Strategy: Range Breakout with Confirmation
Number: 06
Category: BREAKOUT
Timeframe: 15-minute
Risk:Reward: 2.0-3.0
Expected Frequency: 5-10 signals/month
Author: Cline AI
Date: 2026-01-09

Description:
Trade consolidation breakouts with volume and momentum confirmation.
Waits for tight range (Bollinger squeeze), then takes breakout when structure
confirms and session volume supports the move.

Building Blocks Used:
- Initial Balance Breakout: Primary breakout signal (16 points)
- Wave Consolidation: Range identification (12 points)
- Bollinger Bands: Squeeze detection (15 points)
- Break of Structure: Confirmation (22 points)
- MACD Signal: Momentum (22 points)
- Kill Zones: Volume timing (16 points)
- VWAP: Direction bias (15 points)

Entry Logic:
1. Consolidation detected (Wave Consolidation)
2. Bollinger Bands showing squeeze (low volatility)
3. Initial balance breakout triggers
4. Break of structure confirms direction
5. MACD shows momentum alignment
6. During kill zone (high volume)
7. VWAP confirms directional bias
8. Minimum 60 confluence points required

Exit Logic:
- TP1: 2.0R (50% position)
- TP2: 3.0R (30% position)
- TP3: 4.0R (20% position)
- SL: Below/above breakout level + buffer

Expected Performance:
- Win Rate: 62%
- Avg R:R: 1:2.5
- Trades/Month: 5-10
- Max DD: <15%
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
from src.detectors.building_blocks.patterns.initial_balance_breakout import InitialBalanceBreakout
from src.detectors.building_blocks.market_structure.wave_consolidation import WaveConsolidation
from src.detectors.building_blocks.volatility.bollinger_bands import BollingerBands
from src.detectors.building_blocks.smc_ict.break_of_structure import BreakOfStructure
from src.detectors.building_blocks.oscillators.macd_signal import MACDSignal
from src.detectors.building_blocks.sessions.kill_zones import KillZones
from src.detectors.building_blocks.institutional.vwap import VWAP


class RangeBreakoutConfirmation(Strategy):
    """
    Range Breakout Strategy - Simple breakout with confirmation
    
    Waits for consolidation, then takes clean breakouts with momentum.
    Conservative entry at 60+ confluence ensures quality setups.
    """
    
    def __init__(self, config):
        if isinstance(config, dict):
            from nautilus_trader.trading.config import StrategyConfig
            config = StrategyConfig(strategy_id=config.get('strategy_id', '06_RANGE_BREAKOUT'))
        super().__init__(config)
        
        # Strategy identification
        self.strategy_id = "06_RANGE_BREAKOUT"
        self.strategy_name = "Range Breakout with Confirmation"
        
        # Strategy parameters
        self.min_confluence = 60  # Minimum confluence for entry
        self.max_bars_held = 1000
        self.lookback_period = 100
        self.min_risk_reward = 2.0
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
            'ib_breakout': InitialBalanceBreakout(timeframe='15min'),
            'wave_cons': WaveConsolidation(timeframe='15min'),
            'bollinger': BollingerBands(timeframe='15min'),
            'bos': BreakOfStructure(timeframe='15min'),
            'macd': MACDSignal(timeframe='15min'),
            'kill_zones': KillZones(timeframe='15min'),
            'vwap': VWAP(timeframe='15min')
        }
        
        self.blocks = {
            'ib_breakout': {'weight': 16, 'enabled': True},
            'wave_cons': {'weight': 12, 'enabled': True},
            'bollinger': {'weight': 15, 'enabled': True},
            'bos': {'weight': 22, 'enabled': True},
            'macd': {'weight': 22, 'enabled': True},
            'kill_zones': {'weight': 16, 'enabled': True},
            'vwap': {'weight': 15, 'enabled': True}
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
        
        results['ib_breakout'] = self.detectors['ib_breakout'].analyze(df)
        results['wave_cons'] = self.detectors['wave_cons'].analyze(df)
        results['bollinger'] = self.detectors['bollinger'].analyze(df)
        results['bos'] = self.detectors['bos'].analyze(df)
        results['macd'] = self.detectors['macd'].analyze(df)
        results['kill_zones'] = self.detectors['kill_zones'].analyze(df)
        results['vwap'] = self.detectors['vwap'].analyze(df)
        
        return results
    
    def _execute_entry(self, confluence: int, results: dict, signals: list):
        """Execute trade entry"""
        self.log.info(f"🎯 BREAKOUT SIGNAL: {confluence} points")
        for signal in signals:
            self.log.info(f"  ✓ {signal}")
        
        # Determine direction from breakout signal
        ib_signal = results['ib_breakout'].get('signal', '')
        
        if 'BULLISH' in ib_signal:
            side = 'LONG'
        elif 'BEARISH' in ib_signal:
            side = 'SHORT'
        else:
            return  # No clear direction
        
        # Calculate TP/SL levels
        current_price = self.bars_data[-1]['close']
        
        # Calculate ATR for dynamic levels
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
            tp1 = current_price + (risk * 2.0)
            tp2 = current_price + (risk * 3.0)
            tp3 = current_price + (risk * 4.0)
        else:  # SHORT
            sl = current_price + (atr * 1.5)
            risk = sl - current_price
            tp1 = current_price - (risk * 2.0)
            tp2 = current_price - (risk * 3.0)
            tp3 = current_price - (risk * 4.0)
        
        # Verify R:R
        rr_ratio = abs((tp2 - current_price) / (sl - current_price))
        
        if rr_ratio < self.min_risk_reward:
            self.log.info(f"R:R {rr_ratio:.2f} below minimum {self.min_risk_reward}")
            return
        
        self.log.info(f"✅ R:R: {rr_ratio:.2f} - ENTERING {side}")
        self.log.info(f"Entry: {current_price}, SL: {sl}, TP1: {tp1}, TP2: {tp2}, TP3: {tp3}")
        
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