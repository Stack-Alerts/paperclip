"""
Unit tests for itm.domain.nt_mapping — NTTypeMapper
"""

import pytest
from decimal import Decimal

from src.itm.domain.entities import (
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionEntry,
    PositionDirection,
)
from src.itm.domain.nt_mapping import NTTypeMapper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def instrument():
    return Instrument.btc_usdt_spot()


@pytest.fixture
def buy_order(instrument):
    return Order(
        instrument=instrument,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.5"),
        price=None,
    )


# ---------------------------------------------------------------------------
# OrderSide mapping
# ---------------------------------------------------------------------------


class TestOrderSideMapping:
    def test_buy_round_trip(self):
        nt_side = NTTypeMapper.order_side_to_nt(OrderSide.BUY)
        itm_side = NTTypeMapper.nt_order_side_to_itm(nt_side)
        assert itm_side == OrderSide.BUY

    def test_sell_round_trip(self):
        nt_side = NTTypeMapper.order_side_to_nt(OrderSide.SELL)
        itm_side = NTTypeMapper.nt_order_side_to_itm(nt_side)
        assert itm_side == OrderSide.SELL

    def test_nt_buy_value(self):
        from nautilus_trader.model.enums import OrderSide as NTOrderSide

        nt_side = NTTypeMapper.order_side_to_nt(OrderSide.BUY)
        assert nt_side == NTOrderSide.BUY

    def test_nt_sell_value(self):
        from nautilus_trader.model.enums import OrderSide as NTOrderSide

        nt_side = NTTypeMapper.order_side_to_nt(OrderSide.SELL)
        assert nt_side == NTOrderSide.SELL


# ---------------------------------------------------------------------------
# OrderType mapping
# ---------------------------------------------------------------------------


class TestOrderTypeMapping:
    def test_market_round_trip(self):
        nt_type = NTTypeMapper.order_type_to_nt(OrderType.MARKET)
        itm_type = NTTypeMapper.nt_order_type_to_itm(nt_type)
        assert itm_type == OrderType.MARKET

    def test_limit_round_trip(self):
        nt_type = NTTypeMapper.order_type_to_nt(OrderType.LIMIT)
        itm_type = NTTypeMapper.nt_order_type_to_itm(nt_type)
        assert itm_type == OrderType.LIMIT

    def test_stop_market_round_trip(self):
        nt_type = NTTypeMapper.order_type_to_nt(OrderType.STOP_MARKET)
        itm_type = NTTypeMapper.nt_order_type_to_itm(nt_type)
        assert itm_type == OrderType.STOP_MARKET

    def test_stop_limit_round_trip(self):
        nt_type = NTTypeMapper.order_type_to_nt(OrderType.STOP_LIMIT)
        itm_type = NTTypeMapper.nt_order_type_to_itm(nt_type)
        assert itm_type == OrderType.STOP_LIMIT


# ---------------------------------------------------------------------------
# OrderStatus mapping
# ---------------------------------------------------------------------------


class TestOrderStatusMapping:
    @pytest.mark.parametrize("itm_status", [
        OrderStatus.PENDING,
        OrderStatus.OPEN,
        OrderStatus.PARTIAL,
        OrderStatus.CLOSED,
        OrderStatus.CANCELLED,
    ])
    def test_round_trip(self, itm_status):
        nt_status = NTTypeMapper.order_status_to_nt(itm_status)
        result = NTTypeMapper.nt_order_status_to_itm(nt_status)
        assert result == itm_status


# ---------------------------------------------------------------------------
# PositionDirection mapping
# ---------------------------------------------------------------------------


class TestPositionDirectionMapping:
    def test_long_round_trip(self):
        nt_side = NTTypeMapper.position_direction_to_nt(PositionDirection.LONG)
        itm_dir = NTTypeMapper.nt_position_side_to_itm(nt_side)
        assert itm_dir == PositionDirection.LONG

    def test_short_round_trip(self):
        nt_side = NTTypeMapper.position_direction_to_nt(PositionDirection.SHORT)
        itm_dir = NTTypeMapper.nt_position_side_to_itm(nt_side)
        assert itm_dir == PositionDirection.SHORT

    def test_flat_round_trip(self):
        nt_side = NTTypeMapper.position_direction_to_nt(PositionDirection.FLAT)
        itm_dir = NTTypeMapper.nt_position_side_to_itm(nt_side)
        assert itm_dir == PositionDirection.FLAT


# ---------------------------------------------------------------------------
# Instrument → NT InstrumentId
# ---------------------------------------------------------------------------


class TestInstrumentMapping:
    def test_btc_usdt_spot(self, instrument):
        nt_id = NTTypeMapper.instrument_to_nt_id(instrument)
        assert str(nt_id.symbol) == "BTCUSDT"
        assert str(nt_id.venue) == "BINANCE"

    def test_bybit_instrument(self):
        inst = Instrument.btc_usdt_perp(exchange="bybit")
        nt_id = NTTypeMapper.instrument_to_nt_id(inst)
        assert str(nt_id.venue) == "BYBIT"

    def test_nt_id_to_itm_kwargs(self, instrument):
        nt_id = NTTypeMapper.instrument_to_nt_id(instrument)
        kwargs = NTTypeMapper.nt_instrument_id_to_itm(nt_id)
        assert kwargs["symbol"] == "BTC/USDT"
        assert kwargs["exchange"] == "binance"
        assert kwargs["base_currency"] == "BTC"
        assert kwargs["quote_currency"] == "USDT"


# ---------------------------------------------------------------------------
# NT event → ITM event converters (integration with NT mock events)
# ---------------------------------------------------------------------------


class TestNTEventConverters:
    """These tests construct mock NT event objects to verify converter output."""

    def _make_nt_filled_event(self, last_px, last_qty, cum_qty, commission=None):
        """Minimal mock of nautilus_trader OrderFilled."""
        from unittest.mock import MagicMock
        from nautilus_trader.model.events import OrderFilled

        mock_event = MagicMock(spec=OrderFilled)
        mock_event.last_px = last_px
        mock_event.last_qty = last_qty
        mock_event.cum_qty = cum_qty
        mock_event.commission = commission
        return mock_event

    def _make_nt_canceled_event(self):
        from unittest.mock import MagicMock
        from nautilus_trader.model.events import OrderCanceled

        return MagicMock(spec=OrderCanceled)

    def _make_nt_rejected_event(self):
        from unittest.mock import MagicMock
        from nautilus_trader.model.events import OrderRejected

        mock = MagicMock(spec=OrderRejected)
        mock.reason = "INSUFFICIENT_BALANCE"
        return mock

    def test_nt_order_filled_to_itm(self, buy_order):
        from src.itm.domain.events import TradeFilled
        from nautilus_trader.model.objects import Price, Quantity

        nt_event = self._make_nt_filled_event(
            last_px=Price(41000.0, 2),
            last_qty=Quantity(0.5, 3),
            cum_qty=Quantity(0.5, 3),
            commission=None,
        )
        result = NTTypeMapper.nt_order_filled_to_itm(nt_event, buy_order)
        assert isinstance(result, TradeFilled)
        assert result.fill_price == Decimal("41000.00")
        assert result.fill_quantity == Decimal("0.500")

    def test_nt_order_filled_wrong_type_raises(self, buy_order):
        with pytest.raises(TypeError, match="OrderFilled"):
            NTTypeMapper.nt_order_filled_to_itm(object(), buy_order)

    def test_nt_partial_fill_to_itm(self, buy_order):
        from src.itm.domain.events import TradePartialFill
        from nautilus_trader.model.objects import Price, Quantity

        nt_event = self._make_nt_filled_event(
            last_px=Price(40500.0, 2),
            last_qty=Quantity(0.2, 3),
            cum_qty=Quantity(0.2, 3),
        )
        result = NTTypeMapper.nt_order_partially_filled_to_itm(nt_event, buy_order)
        assert isinstance(result, TradePartialFill)
        assert result.partial_price == Decimal("40500.00")
        assert result.partial_quantity == Decimal("0.200")
        # remaining = 0.5 - 0.2 = 0.3
        assert result.remaining_quantity == Decimal("0.300")

    def test_nt_order_canceled_to_itm(self, buy_order):
        from src.itm.domain.events import TradeCancelled

        nt_event = self._make_nt_canceled_event()
        result = NTTypeMapper.nt_order_canceled_to_itm(nt_event, buy_order)
        assert isinstance(result, TradeCancelled)
        assert result.order is buy_order

    def test_nt_order_rejected_to_itm(self, buy_order):
        from src.itm.domain.events import TradeError

        nt_event = self._make_nt_rejected_event()
        result = NTTypeMapper.nt_order_rejected_to_itm(nt_event, buy_order)
        assert isinstance(result, TradeError)
        assert result.order_id == buy_order.client_order_id
        assert result.error_code == "ORDER_REJECTED"

    def test_nt_order_canceled_wrong_type_raises(self, buy_order):
        with pytest.raises(TypeError, match="OrderCanceled"):
            NTTypeMapper.nt_order_canceled_to_itm(object(), buy_order)

    def test_nt_order_rejected_wrong_type_raises(self, buy_order):
        with pytest.raises(TypeError, match="OrderRejected"):
            NTTypeMapper.nt_order_rejected_to_itm(object(), buy_order)
