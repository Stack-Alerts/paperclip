"""
Risk Enforcer - shared pre-trade risk enforcement for NautilusTrader strategies.

Every strategy must call check_and_submit() instead of directly submitting
orders.  The enforcer validates all AGENTS.md institutional risk rules before
allowing any order to reach the exchange.
"""

from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.currencies import USD
from nautilus_trader.trading.strategy import Strategy

MAX_POSITION_SIZE = Quantity.from_int(1)
MIN_POSITION_SIZE = Quantity.from_str("0.001")
DAILY_LOSS_LIMIT = Money("500.00", USD)
STOP_LOSS_PCT = 0.02


class RiskEnforcer:
    """Pre-trade risk enforcement for NautilusTrader strategies."""

    def __init__(self, strategy: Strategy) -> None:
        self._strategy = strategy

    def check_and_submit(
        self,
        side: OrderSide,
        quantity: Quantity,
        price: Price,
        entry_price: float,
        instrument_id: InstrumentId,
        daily_pnl: Money,
    ) -> None:
        log = self._strategy.log

        if quantity > MAX_POSITION_SIZE:
            log.error(f"Order rejected: quantity {quantity} exceeds MAX_POSITION_SIZE {MAX_POSITION_SIZE}")
            return

        if quantity < MIN_POSITION_SIZE:
            log.error(f"Order rejected: quantity {quantity} below MIN_POSITION_SIZE {MIN_POSITION_SIZE}")
            return

        if daily_pnl <= -DAILY_LOSS_LIMIT:
            log.error(f"Order rejected: daily loss limit reached (pnl={daily_pnl}, limit={-DAILY_LOSS_LIMIT})")
            return

        if side == OrderSide.BUY:
            stop_price_value = round(entry_price * (1.0 - STOP_LOSS_PCT), 2)
        else:
            stop_price_value = round(entry_price * (1.0 + STOP_LOSS_PCT), 2)

        stop_price = Price.from_str(str(stop_price_value))

        if self._strategy.order_factory is None:
            log.info(f"Dry run: {side} {quantity} @ {price}, stop @ {stop_price}")
            return

        entry_order = self._strategy.order_factory.market(
            instrument_id=instrument_id,
            order_side=side,
            quantity=quantity,
        )
        self._strategy.submit_order(entry_order)

        stop_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        stop_order = self._strategy.order_factory.stop_market(
            instrument_id=instrument_id,
            order_side=stop_side,
            quantity=quantity,
            price=stop_price,
        )
        self._strategy.submit_order(stop_order)

        log.info(f"Order submitted: {side} {quantity} @ {price}, stop @ {stop_price}")

    @staticmethod
    def should_reset_daily_pnl(last_reset_utc: float | None) -> bool:
        import time
        from datetime import datetime, timezone
        now = time.time()
        if last_reset_utc is None:
            return True
        last_day = datetime.fromtimestamp(last_reset_utc, tz=timezone.utc).timetuple().tm_yday
        current_day = datetime.fromtimestamp(now, tz=timezone.utc).timetuple().tm_yday
        return current_day != last_day
