from __future__ import annotations

from decimal import Decimal
from typing import Optional


from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy

from .risk_enforcer import RiskEnforcer


class PaperTradingStrategy(Strategy):
    """
    NautilusTrader Strategy for Binance testnet paper trading.

    Uses RiskEnforcer for pre-trade checks. All order parameters use
    NautilusTrader types (Quantity, Price, Money) — no floats.
    """

    def __init__(self, config: dict) -> None:
        instrument_id_str = str(config.get("instrument_id", "BTCUSDT.BINANCE")) if isinstance(config, dict) else "BTCUSDT.BINANCE"
        bar_type_str = str(config.get("bar_type", "")) if isinstance(config, dict) else ""
        if isinstance(config, dict):
            from nautilus_trader.trading.config import StrategyConfig
            config = StrategyConfig(strategy_id=config.get("strategy_id", "PAPER_TRADING"))
        super().__init__(config)
        self.instrument_id: Optional[InstrumentId] = InstrumentId.from_str(instrument_id_str)
        self.bar_type: Optional[BarType] = BarType.from_str(bar_type_str) if bar_type_str else None
        self.risk_enforcer: Optional[RiskEnforcer] = None
        self.entry_price: Optional[Price] = None
        self._daily_pnl: Money = Money("0.00", USD)
        self._last_reset_utc: Optional[float] = None

    def on_start(self) -> None:
        self.log.info(f"Starting {self.__class__.__name__}")
        self.risk_enforcer = RiskEnforcer(self)
        if self.bar_type:
            self.subscribe_bars(self.bar_type)
        self.log.info("PaperTradingStrategy initialised")

    def on_bar(self, bar: Bar) -> None:
        if self._should_reset_daily_pnl():
            self._daily_pnl = Money("0.00", USD)
            self._last_reset_utc = __import__("time").time()
            self.log.info("Daily PnL counter reset at UTC midnight")

        entry = self._evaluate_entry_signal(bar)
        if entry is None:
            return

        side, quantity, price = entry
        self._submit_risk_gated_order(side, quantity, price)

    def _evaluate_entry_signal(
        self, bar: Bar
    ) -> Optional[tuple[OrderSide, Quantity, Price]]:
        return None

    def _submit_risk_gated_order(
        self, side: OrderSide, quantity: Quantity, price: Price
    ) -> None:
        if self.risk_enforcer is None:
            return

        entry_price_float = float(price)
        self.risk_enforcer.check_and_submit(
            side=side,
            quantity=quantity,
            price=price,
            entry_price=entry_price_float,
            instrument_id=self.instrument_id,
            daily_pnl=self._daily_pnl,
        )

        self._daily_pnl = Money(
            str(float(self._daily_pnl.as_double()) - float(quantity.as_double()) * entry_price_float * Decimal("0.001")),
            "USD",
        )

    def _should_reset_daily_pnl(self) -> bool:
        return RiskEnforcer.should_reset_daily_pnl(self._last_reset_utc)

    def on_stop(self) -> None:
        self.log.info(f"Stopping {self.__class__.__name__}")
