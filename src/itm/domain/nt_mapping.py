"""
NautilusTrader Type Mapping Utilities
======================================
Bidirectional converters between ITM domain types and NautilusTrader (NT)
equivalents.

All NT imports are deferred (inside functions) so that this module can be
imported in environments where ``nautilus_trader`` is not installed — the
mapping functions raise ``ImportError`` at call time in that case.

Public API
----------
``NTTypeMapper``   — class with static mapping methods (enum round-trips,
                     Instrument → InstrumentId, NT event → ITM domain event)

Module-level function helpers
    itm_to_nt_order_side / nt_to_itm_order_side
    itm_to_nt_order_type / nt_to_itm_order_type
    nt_to_itm_order_status
    itm_to_nt_currency_pair / nt_to_itm_instrument
    apply_nt_fill_to_itm_order
    signal_from_strategy_builder / signal_to_strategy_builder
    itm_instrument_to_nt_id / nt_id_to_itm_kwargs
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from .entities import (
    ContractType,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionDirection,
    Signal,
    SignalDirection,
)
from .events import (
    TradeCancelled,
    TradeError,
    TradeFilled,
    TradePartialFill,
)


# ---------------------------------------------------------------------------
# Lazy NT import helper
# ---------------------------------------------------------------------------


def _require_nt() -> None:
    """Raise ImportError with a helpful message if nautilus_trader is missing."""
    try:
        import nautilus_trader  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "nautilus_trader is required for NT type mapping. "
            "Install it with: pip install nautilus_trader"
        ) from exc


# ---------------------------------------------------------------------------
# Precision helpers
# ---------------------------------------------------------------------------


def _decimal_precision(value: Decimal) -> int:
    """Return the number of decimal places in a Decimal value.

    Examples
    --------
    >>> _decimal_precision(Decimal("0.01"))
    2
    >>> _decimal_precision(Decimal("0.10"))
    1
    >>> _decimal_precision(Decimal("0.00001"))
    5
    """
    sign, digits, exponent = value.as_tuple()
    if exponent < 0:
        return -exponent
    return 0


# ---------------------------------------------------------------------------
# Instrument conversions
# ---------------------------------------------------------------------------


def itm_to_nt_currency_pair(instrument: Instrument):
    """Convert an ITM ``Instrument`` to a NautilusTrader ``CurrencyPair``.

    The CurrencyPair is constructed with the correct tick_size, lot_size,
    and inferred price/size precisions from the ITM instrument fields.

    Parameters
    ----------
    instrument : Instrument
        An ITM domain Instrument with symbol, exchange, tick_size, lot_size.

    Returns
    -------
    CurrencyPair
        A fully-constructed NautilusTrader CurrencyPair instrument.
    """
    _require_nt()
    from nautilus_trader.model.currencies import BTC, USDT
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.instruments import CurrencyPair
    from nautilus_trader.model.objects import Price, Quantity

    nt_symbol = instrument.symbol.replace("/", "")
    nt_venue = instrument.exchange.upper()
    instrument_id = InstrumentId(Symbol(nt_symbol), Venue(nt_venue))

    price_precision = _decimal_precision(instrument.tick_size)
    size_precision = _decimal_precision(instrument.lot_size)

    # Map base/quote currency to NT Currency objects
    _currency_map = {"BTC": BTC, "USDT": USDT}
    base_currency = _currency_map.get(instrument.base_currency, BTC)
    quote_currency = _currency_map.get(instrument.quote_currency, USDT)

    return CurrencyPair(
        instrument_id=instrument_id,
        raw_symbol=Symbol(nt_symbol),
        base_currency=base_currency,
        quote_currency=quote_currency,
        price_precision=price_precision,
        size_precision=size_precision,
        price_increment=Price(instrument.tick_size, price_precision),
        size_increment=Quantity(instrument.lot_size, size_precision),
        lot_size=None,
        max_quantity=None,
        min_quantity=None,
        max_notional=None,
        min_notional=None,
        max_price=None,
        min_price=None,
        margin_init=Decimal("0"),
        margin_maint=Decimal("0"),
        maker_fee=Decimal("0"),
        taker_fee=Decimal("0"),
        ts_event=0,
        ts_init=0,
    )


def nt_to_itm_instrument(
    nt_instrument,
    contract_type: ContractType = ContractType.SPOT,
) -> Instrument:
    """Convert a NautilusTrader instrument to an ITM ``Instrument``.

    Parameters
    ----------
    nt_instrument : CurrencyPair or similar
        A NautilusTrader instrument with id, price_increment, size_increment.
    contract_type : ContractType
        The contract type to assign (not available from NT instrument alone).

    Returns
    -------
    Instrument
    """
    raw_symbol = str(nt_instrument.id.symbol)
    venue = str(nt_instrument.id.venue).lower()

    # Reconstruct symbol with '/'
    if raw_symbol.endswith("USDT"):
        base = raw_symbol[:-4]
        symbol = f"{base}/USDT"
        quote = "USDT"
    elif raw_symbol.endswith("BTC"):
        base = raw_symbol[:-3]
        symbol = f"{base}/BTC"
        quote = "BTC"
    else:
        base = raw_symbol
        symbol = raw_symbol
        quote = ""

    tick_size = Decimal(str(nt_instrument.price_increment))
    lot_size = Decimal(str(nt_instrument.size_increment))

    return Instrument(
        symbol=symbol,
        exchange=venue,
        contract_type=contract_type,
        tick_size=tick_size,
        lot_size=lot_size,
        base_currency=base,
        quote_currency=quote,
    )


# ---------------------------------------------------------------------------
# OrderSide bridge
# ---------------------------------------------------------------------------


def itm_to_nt_order_side(side: OrderSide):
    """Convert ITM ``OrderSide`` → NT ``OrderSide``."""
    _require_nt()
    from nautilus_trader.model.enums import OrderSide as NTOrderSide

    mapping = {
        OrderSide.BUY: NTOrderSide.BUY,
        OrderSide.SELL: NTOrderSide.SELL,
    }
    return mapping[side]


def nt_to_itm_order_side(nt_side) -> OrderSide:
    """Convert NT ``OrderSide`` → ITM ``OrderSide``.

    Raises ValueError for NO_ORDER_SIDE and other unmapped values.
    """
    _require_nt()
    from nautilus_trader.model.enums import OrderSide as NTOrderSide

    mapping = {
        NTOrderSide.BUY: OrderSide.BUY,
        NTOrderSide.SELL: OrderSide.SELL,
    }
    try:
        return mapping[nt_side]
    except KeyError:
        raise ValueError(
            f"Cannot map NautilusTrader OrderSide {nt_side!r} to ITM OrderSide. "
            f"Valid values: {list(mapping.keys())}"
        ) from None


# ---------------------------------------------------------------------------
# OrderType bridge
# ---------------------------------------------------------------------------


def itm_to_nt_order_type(order_type: OrderType):
    """Convert ITM ``OrderType`` → NT ``OrderType``."""
    _require_nt()
    from nautilus_trader.model.enums import OrderType as NTOrderType

    mapping = {
        OrderType.MARKET: NTOrderType.MARKET,
        OrderType.LIMIT: NTOrderType.LIMIT,
        OrderType.STOP_MARKET: NTOrderType.STOP_MARKET,
        OrderType.STOP_LIMIT: NTOrderType.STOP_LIMIT,
        # NT does not have TAKE_PROFIT directly — map to LIMIT
        OrderType.TAKE_PROFIT: NTOrderType.LIMIT,
        OrderType.TAKE_PROFIT_LIMIT: NTOrderType.STOP_LIMIT,
    }
    return mapping[order_type]


def nt_to_itm_order_type(nt_type) -> OrderType:
    """Convert NT ``OrderType`` → ITM ``OrderType``."""
    _require_nt()
    from nautilus_trader.model.enums import OrderType as NTOrderType

    mapping = {
        NTOrderType.MARKET: OrderType.MARKET,
        NTOrderType.LIMIT: OrderType.LIMIT,
        NTOrderType.STOP_MARKET: OrderType.STOP_MARKET,
        NTOrderType.STOP_LIMIT: OrderType.STOP_LIMIT,
        NTOrderType.MARKET_TO_LIMIT: OrderType.LIMIT,
        NTOrderType.MARKET_IF_TOUCHED: OrderType.STOP_MARKET,
        NTOrderType.LIMIT_IF_TOUCHED: OrderType.STOP_LIMIT,
        NTOrderType.TRAILING_STOP_MARKET: OrderType.STOP_MARKET,
        NTOrderType.TRAILING_STOP_LIMIT: OrderType.STOP_LIMIT,
    }
    try:
        return mapping[nt_type]
    except KeyError:
        raise ValueError(
            f"Cannot map NautilusTrader OrderType {nt_type!r} to ITM OrderType"
        ) from None


# ---------------------------------------------------------------------------
# OrderStatus bridge
# ---------------------------------------------------------------------------


def nt_to_itm_order_status(nt_status) -> OrderStatus:
    """Convert NT ``OrderStatus`` → ITM ``OrderStatus``.

    NT has many more states than ITM; we collapse them to the ITM lifecycle.
    """
    _require_nt()
    from nautilus_trader.model.enums import OrderStatus as NTOrderStatus

    mapping = {
        NTOrderStatus.INITIALIZED: OrderStatus.PENDING,
        NTOrderStatus.SUBMITTED: OrderStatus.PENDING,
        NTOrderStatus.RELEASED: OrderStatus.PENDING,
        NTOrderStatus.EMULATED: OrderStatus.PENDING,
        NTOrderStatus.PENDING_UPDATE: OrderStatus.OPEN,
        NTOrderStatus.PENDING_CANCEL: OrderStatus.OPEN,
        NTOrderStatus.ACCEPTED: OrderStatus.OPEN,
        NTOrderStatus.TRIGGERED: OrderStatus.OPEN,
        NTOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIAL,
        NTOrderStatus.FILLED: OrderStatus.CLOSED,
        NTOrderStatus.CANCELED: OrderStatus.CANCELLED,
        NTOrderStatus.EXPIRED: OrderStatus.CANCELLED,
        NTOrderStatus.REJECTED: OrderStatus.ERROR,
        NTOrderStatus.DENIED: OrderStatus.ERROR,
    }
    return mapping.get(nt_status, OrderStatus.ERROR)


def itm_to_nt_order_status(status: OrderStatus):
    """Convert ITM ``OrderStatus`` → NT ``OrderStatus`` (nearest equivalent)."""
    _require_nt()
    from nautilus_trader.model.enums import OrderStatus as NTOrderStatus

    mapping = {
        OrderStatus.PENDING: NTOrderStatus.INITIALIZED,
        OrderStatus.OPEN: NTOrderStatus.ACCEPTED,
        OrderStatus.PARTIAL: NTOrderStatus.PARTIALLY_FILLED,
        OrderStatus.CLOSED: NTOrderStatus.FILLED,
        OrderStatus.CANCELLED: NTOrderStatus.CANCELED,
        OrderStatus.ERROR: NTOrderStatus.REJECTED,
    }
    return mapping[status]


# ---------------------------------------------------------------------------
# PositionSide bridge
# ---------------------------------------------------------------------------


def itm_to_nt_position_side(direction: PositionDirection):
    """Convert ITM ``PositionDirection`` → NT ``PositionSide``."""
    _require_nt()
    from nautilus_trader.model.enums import PositionSide as NTPositionSide

    mapping = {
        PositionDirection.LONG: NTPositionSide.LONG,
        PositionDirection.SHORT: NTPositionSide.SHORT,
        PositionDirection.FLAT: NTPositionSide.FLAT,
    }
    return mapping[direction]


def nt_to_itm_position_side(nt_side) -> PositionDirection:
    """Convert NT ``PositionSide`` → ITM ``PositionDirection``."""
    _require_nt()
    from nautilus_trader.model.enums import PositionSide as NTPositionSide

    mapping = {
        NTPositionSide.LONG: PositionDirection.LONG,
        NTPositionSide.SHORT: PositionDirection.SHORT,
        NTPositionSide.FLAT: PositionDirection.FLAT,
    }
    return mapping[nt_side]


# ---------------------------------------------------------------------------
# Instrument ID helpers
# ---------------------------------------------------------------------------


def itm_instrument_to_nt_id(instrument: Instrument):
    """Convert ITM Instrument → NT InstrumentId (``BTCUSDT.BINANCE`` style)."""
    _require_nt()
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

    nt_symbol = instrument.symbol.replace("/", "")
    nt_venue = instrument.exchange.upper()
    return InstrumentId(Symbol(nt_symbol), Venue(nt_venue))


def nt_id_to_itm_kwargs(nt_id) -> dict:
    """Return kwargs suitable for constructing an ``Instrument`` from NT id."""
    raw_symbol = str(nt_id.symbol)
    if raw_symbol.endswith("USDT"):
        base = raw_symbol[:-4]
        symbol = f"{base}/USDT"
        quote = "USDT"
    elif raw_symbol.endswith("BTC"):
        base = raw_symbol[:-3]
        symbol = f"{base}/BTC"
        quote = "BTC"
    else:
        base = raw_symbol
        symbol = raw_symbol
        quote = ""
    return {
        "symbol": symbol,
        "exchange": str(nt_id.venue).lower(),
        "base_currency": base,
        "quote_currency": quote,
    }


# ---------------------------------------------------------------------------
# Order fill helper
# ---------------------------------------------------------------------------


def apply_nt_fill_to_itm_order(order: Order, nt_fill) -> None:
    """Apply a NautilusTrader ``OrderFilled`` event to an ITM ``Order`` in-place.

    Updates: filled_quantity, average_fill_price (VWAP), exchange_order_id,
    and status (PARTIAL or CLOSED based on remaining quantity).

    Parameters
    ----------
    order   : ITM Order to update
    nt_fill : nautilus_trader.model.events.OrderFilled instance
    """
    fill_qty = Decimal(str(nt_fill.last_qty))
    fill_px = Decimal(str(nt_fill.last_px))

    # Compute new VWAP average fill price
    prev_filled = order.filled_quantity
    prev_avg = order.average_fill_price or Decimal("0")

    new_filled = prev_filled + fill_qty
    if prev_filled == Decimal("0"):
        new_avg = fill_px
    else:
        total_cost = prev_avg * prev_filled + fill_px * fill_qty
        new_avg = total_cost / new_filled

    order.filled_quantity = new_filled
    order.average_fill_price = new_avg

    # Set exchange order id from venue_order_id on first fill
    if order.exchange_order_id is None and hasattr(nt_fill, "venue_order_id"):
        order.exchange_order_id = str(nt_fill.venue_order_id)

    # Update status
    if new_filled >= order.quantity:
        order.status = OrderStatus.CLOSED
    else:
        order.status = OrderStatus.PARTIAL

    order.touch()


# ---------------------------------------------------------------------------
# Signal ↔ Strategy Builder dict converters
# ---------------------------------------------------------------------------


def signal_from_strategy_builder(
    payload: dict,
    instrument: Instrument,
) -> Signal:
    """Construct an ITM ``Signal`` from a Strategy Builder payload dict.

    Expected payload keys
    ---------------------
    strategy_id : str   (required)
    direction   : str   "long" | "short" | "exit" | "neutral" (case-insensitive)
    strength    : str   0.0 – 1.0 (optional, defaults to "1.0")
    metadata    : dict  (optional)

    Raises
    ------
    ValueError
        If direction is not a valid ``SignalDirection`` value.
    ValueError
        If strength cannot be parsed as a Decimal.
    """
    strategy_id = payload.get("strategy_id", "")
    direction_raw = payload.get("direction", "neutral").lower()
    strength_raw = str(payload.get("strength", "1.0"))
    metadata = payload.get("metadata", {})

    # Validate direction
    try:
        direction = SignalDirection(direction_raw)
    except ValueError:
        valid = [e.value for e in SignalDirection]
        raise ValueError(
            f"Signal has invalid direction {direction_raw!r}. "
            f"Valid values: {valid}"
        ) from None

    # Validate strength
    try:
        strength = Decimal(strength_raw)
    except InvalidOperation as exc:
        raise ValueError(
            f"Signal strength {strength_raw!r} cannot be parsed as a Decimal"
        ) from exc

    return Signal(
        direction=direction,
        strength=strength,
        source_strategy=strategy_id,
        instrument=instrument,
        metadata=dict(metadata),
    )


def signal_to_strategy_builder(signal: Signal) -> dict:
    """Serialise an ITM ``Signal`` to a Strategy Builder compatible dict.

    Returns
    -------
    dict with keys: signal_id, strategy_id, direction, strength,
                    instrument_symbol, instrument_exchange, created_at, metadata
    """
    return {
        "signal_id": signal.signal_id,
        "strategy_id": signal.source_strategy,
        "direction": signal.direction.value,
        "strength": str(signal.strength),
        "instrument_symbol": signal.instrument.symbol,
        "instrument_exchange": signal.instrument.exchange,
        "created_at": signal.created_at.isoformat(),
        "metadata": dict(signal.metadata),
    }


# Alias for backwards compat
signal_to_sb_dict = signal_to_strategy_builder


# ---------------------------------------------------------------------------
# NTTypeMapper class (primary OO public API)
# ---------------------------------------------------------------------------


class NTTypeMapper:
    """Bidirectional converter between ITM domain types and NautilusTrader types.

    All methods are static. Raises ``ImportError`` if ``nautilus_trader`` is
    not installed, ``KeyError`` / ``ValueError`` if a mapping is undefined.
    """

    @staticmethod
    def order_side_to_nt(side: OrderSide):
        return itm_to_nt_order_side(side)

    @staticmethod
    def nt_order_side_to_itm(nt_side) -> OrderSide:
        return nt_to_itm_order_side(nt_side)

    @staticmethod
    def order_type_to_nt(order_type: OrderType):
        return itm_to_nt_order_type(order_type)

    @staticmethod
    def nt_order_type_to_itm(nt_type) -> OrderType:
        return nt_to_itm_order_type(nt_type)

    @staticmethod
    def order_status_to_nt(status: OrderStatus):
        return itm_to_nt_order_status(status)

    @staticmethod
    def nt_order_status_to_itm(nt_status) -> OrderStatus:
        return nt_to_itm_order_status(nt_status)

    @staticmethod
    def position_direction_to_nt(direction: PositionDirection):
        return itm_to_nt_position_side(direction)

    @staticmethod
    def nt_position_side_to_itm(nt_side) -> PositionDirection:
        return nt_to_itm_position_side(nt_side)

    @staticmethod
    def instrument_to_nt_id(instrument: Instrument):
        return itm_instrument_to_nt_id(instrument)

    @staticmethod
    def nt_instrument_id_to_itm(nt_id, exchange: Optional[str] = None) -> dict:
        kwargs = nt_id_to_itm_kwargs(nt_id)
        if exchange:
            kwargs["exchange"] = exchange
        return kwargs

    @staticmethod
    def nt_order_filled_to_itm(nt_event: object, itm_order: Order) -> TradeFilled:
        _require_nt()
        from nautilus_trader.model.events import OrderFilled

        if not isinstance(nt_event, OrderFilled):
            raise TypeError(
                f"Expected nautilus_trader OrderFilled, got {type(nt_event).__name__}"
            )
        commission_val = Decimal("0")
        if hasattr(nt_event, "commission") and nt_event.commission is not None:
            commission_val = Decimal(str(nt_event.commission.as_double()))
        return TradeFilled(
            order=itm_order,
            fill_price=Decimal(str(nt_event.last_px)),
            fill_quantity=Decimal(str(nt_event.last_qty)),
            commission=commission_val,
        )

    @staticmethod
    def nt_order_partially_filled_to_itm(
        nt_event: object, itm_order: Order
    ) -> TradePartialFill:
        _require_nt()
        from nautilus_trader.model.events import OrderFilled

        if not isinstance(nt_event, OrderFilled):
            raise TypeError(
                f"Expected nautilus_trader OrderFilled, got {type(nt_event).__name__}"
            )
        remaining = itm_order.quantity - Decimal(str(nt_event.cum_qty))
        return TradePartialFill(
            order=itm_order,
            partial_price=Decimal(str(nt_event.last_px)),
            partial_quantity=Decimal(str(nt_event.last_qty)),
            remaining_quantity=max(Decimal("0"), remaining),
        )

    @staticmethod
    def nt_order_canceled_to_itm(
        nt_event: object, itm_order: Order
    ) -> TradeCancelled:
        _require_nt()
        from nautilus_trader.model.events import OrderCanceled

        if not isinstance(nt_event, OrderCanceled):
            raise TypeError(
                f"Expected nautilus_trader OrderCanceled, got {type(nt_event).__name__}"
            )
        return TradeCancelled(
            order=itm_order,
            reason="Order cancelled by exchange or user",
        )

    @staticmethod
    def nt_order_rejected_to_itm(
        nt_event: object, itm_order: Order
    ) -> TradeError:
        _require_nt()
        from nautilus_trader.model.events import OrderRejected

        if not isinstance(nt_event, OrderRejected):
            raise TypeError(
                f"Expected nautilus_trader OrderRejected, got {type(nt_event).__name__}"
            )
        return TradeError(
            order_id=itm_order.client_order_id,
            error_code="ORDER_REJECTED",
            message=str(nt_event.reason) if hasattr(nt_event, "reason") else "Rejected",
        )
