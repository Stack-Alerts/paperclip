"""
ITM Section G — Order Factory
===============================
Builds order payloads for Binance USDT-M Futures with deterministic
``clientOrderId`` derived from ``(strategy_id, signal_id, leg_index)``.

Order types supported
---------------------
* ``LIMIT``        — default for entries; requires price
* ``MARKET``       — emergency exit; guarded by ``allow_market`` flag
* ``STOP_MARKET``  — stop-loss bracket leg
* ``TAKE_PROFIT``  — take-profit bracket leg (LIMIT on opposite side)
* ``TRAILING_STOP_MARKET`` — trailing stop with configurable callback rate

TWAP and DCA helpers produce a *list* of child order specs.

clientOrderId deduplication
----------------------------
Every order carries a deterministic ID::

    cid = sha256(f"{strategy_id}:{signal_id}:{leg_index}")[:36]

Replaying the same (strategy_id, signal_id) will produce identical IDs,
so Binance will reject the duplicate rather than double-placing.

Design notes
------------
* All quantities/prices returned as ``Decimal`` — never float.
* No exchange I/O here; this module is pure order construction.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import List, Optional

from ..domain.entities import OrderSide, OrderType


# ---------------------------------------------------------------------------
# OrderSpec — portable exchange-agnostic order description
# ---------------------------------------------------------------------------


class BinanceOrderType(str, Enum):
    """Binance Futures order types (string values match the API)."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class BinanceTimeInForce(str, Enum):
    GTC = "GTC"   # Good Till Cancel
    IOC = "IOC"   # Immediate or Cancel
    FOK = "FOK"   # Fill or Kill
    GTX = "GTX"   # Good Till Crossing (post-only)


@dataclass
class OrderSpec:
    """Exchange-agnostic order specification produced by the factory.

    All prices/quantities are Decimal.  The ``binance_type`` field carries
    the exact string the Binance REST API expects.

    Parameters
    ----------
    client_order_id:  deterministic UUID-format string for deduplication
    side:             BUY or SELL (Binance string, e.g. ``"BUY"``)
    binance_type:     ``BinanceOrderType`` enum value
    quantity:         base-asset quantity (BTC), rounded to lot_size precision
    price:            limit price (None for MARKET / STOP_MARKET)
    stop_price:       trigger price for STOP_MARKET / TRAILING_STOP_MARKET
    callback_rate:    trailing stop callback rate in % (e.g. ``Decimal('1.5')``)
    time_in_force:    only meaningful for LIMIT orders
    reduce_only:      True for SL/TP orders that may only reduce the position
    strategy_id:      owning strategy (for logging)
    signal_id:        originating signal (for logging)
    leg_index:        leg within TWAP/DCA sequence (0 for single orders)
    """

    client_order_id: str
    side: str                         # "BUY" | "SELL"
    binance_type: BinanceOrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    callback_rate: Optional[Decimal] = None
    time_in_force: BinanceTimeInForce = BinanceTimeInForce.GTC
    reduce_only: bool = False
    strategy_id: str = ""
    signal_id: str = ""
    leg_index: int = 0

    def to_binance_params(self) -> dict:
        """Serialise to Binance REST API query parameters."""
        params: dict = {
            "symbol": "BTCUSDT",
            "side": self.side,
            "type": self.binance_type.value,
            "quantity": str(self.quantity),
            "newClientOrderId": self.client_order_id,
        }
        if self.price is not None:
            params["price"] = str(self.price)
            params["timeInForce"] = self.time_in_force.value
        if self.stop_price is not None:
            params["stopPrice"] = str(self.stop_price)
        if self.callback_rate is not None:
            params["callbackRate"] = str(self.callback_rate)
        if self.reduce_only:
            params["reduceOnly"] = "true"
        return params


# ---------------------------------------------------------------------------
# clientOrderId derivation
# ---------------------------------------------------------------------------


def derive_client_order_id(
    strategy_id: str,
    signal_id: str,
    leg_index: int = 0,
) -> str:
    """Produce a deterministic 36-char clientOrderId for deduplication.

    Parameters
    ----------
    strategy_id:  owning strategy identifier
    signal_id:    signal that triggered the order
    leg_index:    0 for single orders; 0…N-1 for TWAP/DCA slices

    Returns
    -------
    str
        A 36-character hex string (UUID-format, lowercase).
    """
    raw = f"{strategy_id}:{signal_id}:{leg_index}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    # Format as UUID-like string for Binance's 36-char limit
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


# ---------------------------------------------------------------------------
# Quantity helpers
# ---------------------------------------------------------------------------


def quantize_qty(quantity: Decimal, lot_size: Decimal) -> Decimal:
    """Round *quantity* down to the nearest *lot_size* multiple.

    BTC/USDT perpetual lot_size = 0.001 BTC.
    """
    if lot_size <= Decimal("0"):
        raise ValueError(f"lot_size must be positive, got {lot_size}")
    factor = Decimal("1") / lot_size
    return (quantity * factor).to_integral_value(rounding=ROUND_DOWN) / factor


def quantize_price(price: Decimal, tick_size: Decimal) -> Decimal:
    """Round *price* to the nearest *tick_size* multiple (round half-even)."""
    if tick_size <= Decimal("0"):
        raise ValueError(f"tick_size must be positive, got {tick_size}")
    factor = Decimal("1") / tick_size
    return (price * factor).to_integral_value() / factor


# ---------------------------------------------------------------------------
# OrderFactory
# ---------------------------------------------------------------------------


class OrderFactory:
    """Builds exchange order specs for every order type.

    Parameters
    ----------
    lot_size:   minimum BTC quantity increment (default 0.001 for BTCUSDT perp)
    tick_size:  minimum price increment (default 0.10 for BTCUSDT perp)
    allow_market_orders:
        Must be explicitly set to True to produce MARKET orders.
        Prevents accidental market-order submission.
    """

    LOT_SIZE_DEFAULT = Decimal("0.001")
    TICK_SIZE_DEFAULT = Decimal("0.10")

    def __init__(
        self,
        lot_size: Decimal = LOT_SIZE_DEFAULT,
        tick_size: Decimal = TICK_SIZE_DEFAULT,
        allow_market_orders: bool = False,
    ) -> None:
        self._lot_size = lot_size
        self._tick_size = tick_size
        self._allow_market = allow_market_orders

    # ------------------------------------------------------------------ #
    # LIMIT order                                                          #
    # ------------------------------------------------------------------ #

    def limit(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        strategy_id: str,
        signal_id: str,
        leg_index: int = 0,
        time_in_force: BinanceTimeInForce = BinanceTimeInForce.GTC,
    ) -> OrderSpec:
        """Build a LIMIT entry/exit order spec.

        Parameters
        ----------
        side:       ``OrderSide.BUY`` or ``OrderSide.SELL``
        quantity:   BTC quantity (will be quantized to lot_size)
        price:      limit price (will be quantized to tick_size)
        strategy_id, signal_id, leg_index: used to derive clientOrderId
        time_in_force: default GTC
        """
        qty = quantize_qty(quantity, self._lot_size)
        px = quantize_price(price, self._tick_size)
        cid = derive_client_order_id(strategy_id, signal_id, leg_index)
        return OrderSpec(
            client_order_id=cid,
            side=side.value.upper(),
            binance_type=BinanceOrderType.LIMIT,
            quantity=qty,
            price=px,
            time_in_force=time_in_force,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )

    # ------------------------------------------------------------------ #
    # MARKET order (emergency exit only)                                   #
    # ------------------------------------------------------------------ #

    def market(
        self,
        side: OrderSide,
        quantity: Decimal,
        strategy_id: str,
        signal_id: str,
        leg_index: int = 0,
        reduce_only: bool = True,
    ) -> OrderSpec:
        """Build a MARKET order spec.

        Only permitted when ``allow_market_orders=True`` on this factory.
        Typically used for emergency exits only.

        Parameters
        ----------
        reduce_only: defaults to True — market exits should be reduce-only
        """
        if not self._allow_market:
            raise ValueError(
                "MARKET orders are disabled on this OrderFactory.  "
                "Set allow_market_orders=True (emergency use only)."
            )
        qty = quantize_qty(quantity, self._lot_size)
        cid = derive_client_order_id(strategy_id, signal_id, leg_index)
        return OrderSpec(
            client_order_id=cid,
            side=side.value.upper(),
            binance_type=BinanceOrderType.MARKET,
            quantity=qty,
            reduce_only=reduce_only,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )

    # ------------------------------------------------------------------ #
    # STOP_MARKET (stop-loss bracket leg)                                  #
    # ------------------------------------------------------------------ #

    def stop_market(
        self,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        strategy_id: str,
        signal_id: str,
        leg_index: int = 90,  # convention: SL legs use indices 90+
    ) -> OrderSpec:
        """Build a STOP_MARKET stop-loss spec.

        Parameters
        ----------
        stop_price: trigger price; order fills at market once triggered
        leg_index:  90 by default to distinguish SL from entry legs
        """
        qty = quantize_qty(quantity, self._lot_size)
        sp = quantize_price(stop_price, self._tick_size)
        cid = derive_client_order_id(strategy_id, signal_id, leg_index)
        return OrderSpec(
            client_order_id=cid,
            side=side.value.upper(),
            binance_type=BinanceOrderType.STOP_MARKET,
            quantity=qty,
            stop_price=sp,
            reduce_only=True,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )

    # ------------------------------------------------------------------ #
    # TAKE_PROFIT (TP bracket leg, LIMIT on opposite side)                 #
    # ------------------------------------------------------------------ #

    def take_profit(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        stop_price: Decimal,
        strategy_id: str,
        signal_id: str,
        leg_index: int = 91,  # convention: TP legs use indices 91+
    ) -> OrderSpec:
        """Build a TAKE_PROFIT (limit-style) spec.

        For a LONG entry: side=SELL, price=TP, stop_price=TP trigger.
        Binance TAKE_PROFIT requires both ``price`` (limit) and
        ``stopPrice`` (trigger).
        """
        qty = quantize_qty(quantity, self._lot_size)
        px = quantize_price(price, self._tick_size)
        sp = quantize_price(stop_price, self._tick_size)
        cid = derive_client_order_id(strategy_id, signal_id, leg_index)
        return OrderSpec(
            client_order_id=cid,
            side=side.value.upper(),
            binance_type=BinanceOrderType.TAKE_PROFIT,
            quantity=qty,
            price=px,
            stop_price=sp,
            time_in_force=BinanceTimeInForce.GTC,
            reduce_only=True,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )

    # ------------------------------------------------------------------ #
    # TRAILING_STOP_MARKET                                                 #
    # ------------------------------------------------------------------ #

    def trailing_stop(
        self,
        side: OrderSide,
        quantity: Decimal,
        callback_rate: Decimal,
        strategy_id: str,
        signal_id: str,
        activation_price: Optional[Decimal] = None,
        leg_index: int = 92,  # convention: trailing stops use indices 92+
    ) -> OrderSpec:
        """Build a TRAILING_STOP_MARKET spec.

        Parameters
        ----------
        callback_rate:    Trailing callback percentage (e.g. Decimal('1.0')
                          for 1%).  Must be in [0.1, 5.0] per Binance rules.
        activation_price: Optional activation price; if None, Binance uses
                          current market price.
        """
        if callback_rate < Decimal("0.1") or callback_rate > Decimal("5.0"):
            raise ValueError(
                f"callback_rate must be in [0.1, 5.0], got {callback_rate}"
            )
        qty = quantize_qty(quantity, self._lot_size)
        cid = derive_client_order_id(strategy_id, signal_id, leg_index)
        spec = OrderSpec(
            client_order_id=cid,
            side=side.value.upper(),
            binance_type=BinanceOrderType.TRAILING_STOP_MARKET,
            quantity=qty,
            callback_rate=callback_rate,
            reduce_only=True,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )
        if activation_price is not None:
            spec.stop_price = quantize_price(activation_price, self._tick_size)
        return spec

    # ------------------------------------------------------------------ #
    # TWAP — time-weighted average price slices                            #
    # ------------------------------------------------------------------ #

    def twap(
        self,
        side: OrderSide,
        total_quantity: Decimal,
        price: Decimal,
        strategy_id: str,
        signal_id: str,
        num_slices: int = 5,
    ) -> List[OrderSpec]:
        """Split a large order into TWAP slices (all LIMIT).

        Parameters
        ----------
        total_quantity: total BTC to fill across all slices
        price:          limit price used for ALL slices (caller may update
                        each slice's price based on mid-market before submitting)
        num_slices:     number of time slices (default 5)

        Returns
        -------
        list[OrderSpec]
            Ordered list of slices (leg_index 0 … num_slices-1).
            The caller submits them sequentially at the configured interval.
        """
        if num_slices < 1:
            raise ValueError(f"num_slices must be >= 1, got {num_slices}")
        slice_qty = quantize_qty(total_quantity / num_slices, self._lot_size)
        if slice_qty <= Decimal("0"):
            raise ValueError(
                f"TWAP slice quantity is 0 after quantization: "
                f"total={total_quantity}, slices={num_slices}, lot={self._lot_size}"
            )
        slices = []
        for i in range(num_slices):
            spec = self.limit(
                side=side,
                quantity=slice_qty,
                price=price,
                strategy_id=strategy_id,
                signal_id=signal_id,
                leg_index=i,
            )
            slices.append(spec)
        return slices

    # ------------------------------------------------------------------ #
    # DCA — dollar-cost averaging legs                                     #
    # ------------------------------------------------------------------ #

    def dca(
        self,
        side: OrderSide,
        total_quantity: Decimal,
        base_price: Decimal,
        strategy_id: str,
        signal_id: str,
        num_legs: int = 4,
        price_step_pct: Decimal = Decimal("0.005"),  # 0.5% per leg
    ) -> List[OrderSpec]:
        """Build a DCA ladder of LIMIT orders.

        Parameters
        ----------
        total_quantity:  total BTC to accumulate across all legs
        base_price:      price for the first (most aggressive) leg
        num_legs:        number of DCA legs (default 4)
        price_step_pct:  price distance between legs as a fraction of
                         base_price (default 0.5%).
                         For BUY: each subsequent leg is further below.
                         For SELL: each subsequent leg is further above.

        Returns
        -------
        list[OrderSpec]
            Ordered list from leg 0 (base_price) to leg N-1 (deepest).
        """
        if num_legs < 1:
            raise ValueError(f"num_legs must be >= 1, got {num_legs}")
        if price_step_pct <= Decimal("0"):
            raise ValueError(f"price_step_pct must be positive, got {price_step_pct}")
        leg_qty = quantize_qty(total_quantity / num_legs, self._lot_size)
        if leg_qty <= Decimal("0"):
            raise ValueError(
                f"DCA leg quantity is 0 after quantization: "
                f"total={total_quantity}, legs={num_legs}, lot={self._lot_size}"
            )
        legs = []
        for i in range(num_legs):
            if side == OrderSide.BUY:
                # Each successive BUY leg is cheaper
                px = base_price * (Decimal("1") - price_step_pct * i)
            else:
                # Each successive SELL leg is more expensive
                px = base_price * (Decimal("1") + price_step_pct * i)
            spec = self.limit(
                side=side,
                quantity=leg_qty,
                price=px,
                strategy_id=strategy_id,
                signal_id=signal_id,
                leg_index=i,
            )
            legs.append(spec)
        return legs
