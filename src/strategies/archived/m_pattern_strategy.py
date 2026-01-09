#!/usr/bin/env python3
"""
BTC_Engine_v3 - M-Pattern Strategy
Day 4: NautilusTrader strategy using M-pattern detector

This strategy:
1. Detects M-patterns using PatternAdapter
2. Enters SHORT positions on confirmed M-patterns
3. Manages risk with stop loss and take profit levels
4. Follows institutional-grade risk management
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.objects import Price, Quantity

from src.indicators.pattern_adapter import PatternAdapter, PatternSignal


class MPatternStrategyConfig:
    """Configuration for M-Pattern strategy"""
    
    # Pattern detection
    lookback: int = 50
    min_confidence: float = 0.70  # Minimum 70% confidence to trade
    
    # Position sizing
    position_size_btc: float = 0.01  # 0.01 BTC per trade
    max_positions: int = 5  # Allow up to 5 concurrent positions
    
    # Risk management (from .clinerules)
    max_position_size_btc: float = 1.0  # Absolute maximum
    min_position_size_btc: float = 0.001  # Absolute minimum
    max_daily_loss_usd: float = 500.0  # Daily loss limit
    
    # Trade management
    use_take_profit: bool = True
    use_stop_loss: bool = True
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class MPatternStrategy(Strategy):
    """
    M-Pattern trading strategy for NautilusTrader
    
    Detects M-patterns and enters SHORT positions when:
    - M-pattern detected with sufficient confidence
    - No existing position
    - Risk limits not exceeded
    """
    
    def __init__(self, config: Optional[MPatternStrategyConfig] = None):
        """
        Initialize M-pattern strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__()
        
        # Configuration (use strategy_config to avoid conflict with base class)
        self.strategy_config = config or MPatternStrategyConfig()
        
        # Pattern detector
        self.pattern_adapter = PatternAdapter(
            pattern_type='m_pattern',
            lookback=self.strategy_config.lookback
        )
        
        # Strategy state
        self.instrument_id = None
        self.bar_count = 0
        self.trade_count = 0
        self.daily_pnl = 0.0
        self.last_signal: Optional[PatternSignal] = None
        
        # Track signals per order (key: order_id, value: signal)
        self.order_signals = {}
        
        # Performance tracking
        self.patterns_detected = 0
        self.patterns_traded = 0
        self.patterns_skipped = 0
        
    def on_start(self):
        """Called when strategy starts"""
        self.log.info("=" * 70)
        self.log.info("M-PATTERN STRATEGY STARTING")
        self.log.info("=" * 70)
        self.log.info(f"Configuration:")
        self.log.info(f"  Lookback: {self.strategy_config.lookback} bars")
        self.log.info(f"  Min Confidence: {self.strategy_config.min_confidence:.0%}")
        self.log.info(f"  Position Size: {self.strategy_config.position_size_btc} BTC")
        self.log.info(f"  Max Daily Loss: ${self.strategy_config.max_daily_loss_usd}")
        self.log.info("=" * 70)
        
    def on_bar(self, bar: Bar):
        """
        Called on each new bar
        
        Args:
            bar: New bar data
        """
        self.bar_count += 1
        
        # Set instrument ID from first bar
        if self.instrument_id is None:
            self.instrument_id = bar.bar_type.instrument_id
            self.log.info(f"Trading instrument: {self.instrument_id}")
        
        # Add bar to pattern adapter
        self.pattern_adapter.add_bar(bar)
        
        # Log periodically
        if self.bar_count % 100 == 0:
            self.log.info(f"Processed {self.bar_count} bars | "
                         f"Patterns: {self.patterns_detected} detected, "
                         f"{self.patterns_traded} traded, "
                         f"{self.patterns_skipped} skipped")
        
        # Detect pattern
        signal = self.pattern_adapter.detect_pattern()
        
        # Check if M-pattern detected
        if signal.pattern_type == 'M':
            self.patterns_detected += 1
            self.last_signal = signal
            
            self.log.info("=" * 70)
            self.log.info(f"M-PATTERN DETECTED (#{self.patterns_detected})")
            self.log.info(f"  Bar: {self.bar_count}")
            self.log.info(f"  Confidence: {signal.confidence:.1%}")
            self.log.info(f"  Entry: ${signal.entry_price:.2f}")
            self.log.info(f"  Stop Loss: ${signal.stop_loss:.2f}")
            self.log.info(f"  Take Profit 1: ${signal.take_profit_1:.2f}")
            
            if signal.metadata:
                self.log.info(f"  Peak 1: ${signal.metadata.get('peak1_price', 0):.2f}")
                self.log.info(f"  Peak 2: ${signal.metadata.get('peak2_price', 0):.2f}")
                self.log.info(f"  Neckline: ${signal.metadata.get('neckline', 0):.2f}")
                rr = signal.metadata.get('risk_reward', 0)
                self.log.info(f"  Risk/Reward: {rr:.2f}x")
            
            # Evaluate trading decision
            self._evaluate_trade(signal, bar)
            
    def _evaluate_trade(self, signal: PatternSignal, bar: Bar):
        """
        Evaluate whether to execute trade
        
        Args:
            signal: Pattern signal
            bar: Current bar
        """
        # Check confidence threshold
        if signal.confidence < self.strategy_config.min_confidence:
            self.log.info(f"  ❌ SKIPPED: Confidence {signal.confidence:.1%} < {self.strategy_config.min_confidence:.1%}")
            self.patterns_skipped += 1
            return
        
        # Check if we have room for another position
        # net_position returns a Decimal quantity (negative for SHORT)
        # Allow multiple SHORT positions up to max_positions limit
        position_qty = self.portfolio.net_position(self.instrument_id)
        current_short_size = abs(float(position_qty)) if position_qty < 0 else 0.0
        max_total_size = self.strategy_config.max_positions * self.strategy_config.position_size_btc
        
        if current_short_size >= max_total_size:
            self.log.info(f"  ❌ SKIPPED: Max position limit reached ({current_short_size:.6f}/{max_total_size:.6f} BTC)")
            self.patterns_skipped += 1
            return
        
        # Check daily loss limit
        if self.daily_pnl < -self.strategy_config.max_daily_loss_usd:
            self.log.info(f"  ❌ SKIPPED: Daily loss limit hit (${self.daily_pnl:.2f})")
            self.patterns_skipped += 1
            return
        
        # Check position size limits
        if self.strategy_config.position_size_btc > self.strategy_config.max_position_size_btc:
            self.log.error(f"  ❌ INVALID: Position {self.strategy_config.position_size_btc} > max {self.strategy_config.max_position_size_btc}")
            self.patterns_skipped += 1
            return
        
        if self.strategy_config.position_size_btc < self.strategy_config.min_position_size_btc:
            self.log.error(f"  ❌ INVALID: Position {self.strategy_config.position_size_btc} < min {self.strategy_config.min_position_size_btc}")
            self.patterns_skipped += 1
            return
        
        # All checks passed - execute trade
        self._execute_short_entry(signal, bar)
        
    def _execute_short_entry(self, signal: PatternSignal, bar: Bar):
        """
        Execute SHORT entry based on M-pattern signal
        
        Args:
            signal: Pattern signal
            bar: Current bar
        """
        try:
            # Create market order for SHORT entry
            # Use 6 decimal precision to match instrument size_precision
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.SELL,
                quantity=Quantity.from_str(f"{self.strategy_config.position_size_btc:.6f}"),
            )
            
            # Submit order
            self.submit_order(order)
            
            # Store signal for this order
            self.order_signals[str(order.client_order_id)] = signal
            
            self.trade_count += 1
            self.patterns_traded += 1
            
            self.log.info(f"  ✅ ORDER SUBMITTED (Trade #{self.trade_count})")
            self.log.info(f"     Order ID: {order.client_order_id}")
            self.log.info(f"     Side: {order.side}")
            self.log.info(f"     Quantity: {order.quantity} BTC")
            self.log.info(f"     Expected Entry: ${signal.entry_price:.2f}")
            self.log.info("=" * 70)
            
        except Exception as e:
            self.log.error(f"  ❌ ORDER FAILED: {e}")
            self.patterns_skipped += 1
    
    def on_order_filled(self, event):
        """
        Called when order is filled
        
        Args:
            event: Order filled event
        """
        self.log.info("=" * 70)
        self.log.info(f"ORDER FILLED")
        self.log.info(f"  Order ID: {event.client_order_id}")
        self.log.info(f"  Instrument: {event.instrument_id}")
        self.log.info(f"  Side: {event.order_side}")
        self.log.info(f"  Quantity: {event.last_qty}")
        self.log.info(f"  Price: ${event.last_px}")
        self.log.info(f"  Commission: {event.commission if hasattr(event, 'commission') else 'N/A'}")
        self.log.info("=" * 70)
        
        # Only submit exit orders for ENTRY fills (not exit fills!)
        # Entry fills for SHORT = SELL side
        # Exit fills for SHORT = BUY side
        if event.order_side == OrderSide.SELL:
            # This is an entry fill - submit exit orders
            order_id_str = str(event.client_order_id)
            if order_id_str in self.order_signals:
                signal = self.order_signals[order_id_str]
                position_qty = self.portfolio.net_position(self.instrument_id)
                if position_qty != 0:
                    self.log.info(f"Position: {position_qty} BTC")
                    self._submit_exit_orders(event, signal)
        else:
            # This is an exit fill (BUY side for closing SHORT)
            self.log.info("  ✅ POSITION CLOSED")
    
    def _submit_exit_orders(self, fill_event, signal: PatternSignal):
        """
        Submit stop loss and take profit orders after entry fill
        
        Args:
            fill_event: Order filled event
            signal: Pattern signal for this trade
        """
        if not signal:
            return
        
        try:
            from nautilus_trader.model.enums import OrderSide, TriggerType
            from nautilus_trader.model.orders import StopMarketOrder
            
            # Get current position
            position_qty = self.portfolio.net_position(self.instrument_id)
            if position_qty == 0:
                return
            
            # For SHORT positions (negative qty), we need BUY orders to close
            exit_side = OrderSide.BUY if position_qty < 0 else OrderSide.SELL
            qty = abs(float(position_qty))
            
            # Stop Loss Order (if price goes against us)
            if self.strategy_config.use_stop_loss:
                sl_order = self.order_factory.stop_market(
                    instrument_id=self.instrument_id,
                    order_side=exit_side,
                    quantity=Quantity.from_str(f"{qty:.6f}"),
                    trigger_price=Price.from_str(f"{signal.stop_loss:.2f}"),
                )
                self.submit_order(sl_order)
                self.log.info(f"  📍 STOP LOSS: ${signal.stop_loss:.2f}")
            
            # Take Profit Order (if price moves in our favor)
            if self.strategy_config.use_take_profit:
                tp_order = self.order_factory.stop_market(
                    instrument_id=self.instrument_id,
                    order_side=exit_side,
                    quantity=Quantity.from_str(f"{qty:.6f}"),
                    trigger_price=Price.from_str(f"{signal.take_profit_1:.2f}"),
                )
                self.submit_order(tp_order)
                self.log.info(f"  🎯 TAKE PROFIT: ${signal.take_profit_1:.2f}")
                
        except Exception as e:
            self.log.error(f"  ❌ EXIT ORDER FAILED: {e}")
    
    def on_order_rejected(self, event):
        """
        Called when order is rejected
        
        Args:
            event: Order rejected event
        """
        self.log.error("=" * 70)
        self.log.error(f"ORDER REJECTED")
        self.log.error(f"  Order ID: {event.client_order_id}")
        self.log.error(f"  Reason: {event.reason}")
        self.log.error("=" * 70)
    
    def on_stop(self):
        """Called when strategy stops"""
        self.log.info("=" * 70)
        self.log.info("M-PATTERN STRATEGY STOPPING")
        self.log.info("=" * 70)
        self.log.info(f"Performance Summary:")
        self.log.info(f"  Total Bars: {self.bar_count}")
        self.log.info(f"  Patterns Detected: {self.patterns_detected}")
        self.log.info(f"  Patterns Traded: {self.patterns_traded}")
        self.log.info(f"  Patterns Skipped: {self.patterns_skipped}")
        self.log.info(f"  Total Trades: {self.trade_count}")
        
        if self.patterns_detected > 0:
            trade_rate = (self.patterns_traded / self.patterns_detected) * 100
            self.log.info(f"  Trade Rate: {trade_rate:.1f}%")
        
        self.log.info("=" * 70)


# Factory function
def create_m_pattern_strategy(config: Optional[MPatternStrategyConfig] = None) -> MPatternStrategy:
    """
    Create M-pattern strategy instance
    
    Args:
        config: Strategy configuration
        
    Returns:
        MPatternStrategy instance
    """
    return MPatternStrategy(config)
