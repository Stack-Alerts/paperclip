"""
Unit tests: OrderFactory (Section G)
=====================================
Tests order construction, clientOrderId determinism, TWAP/DCA splitting,
quantity/price quantization, and error conditions.
"""

from __future__ import annotations

import pytest
from decimal import Decimal

from src.itm.domain.entities import OrderSide
from src.itm.engine.order_factory import (
    BinanceOrderType,
    BinanceTimeInForce,
    OrderFactory,
    OrderSpec,
    derive_client_order_id,
    quantize_price,
    quantize_qty,
)


# ---------------------------------------------------------------------------
# derive_client_order_id
# ---------------------------------------------------------------------------


class TestDeriveClientOrderId:
    def test_deterministic(self):
        cid1 = derive_client_order_id("strat-1", "sig-abc", 0)
        cid2 = derive_client_order_id("strat-1", "sig-abc", 0)
        assert cid1 == cid2

    def test_different_leg_different_id(self):
        cid0 = derive_client_order_id("strat-1", "sig-abc", 0)
        cid1 = derive_client_order_id("strat-1", "sig-abc", 1)
        assert cid0 != cid1

    def test_different_signal_different_id(self):
        cid_a = derive_client_order_id("strat-1", "sig-A", 0)
        cid_b = derive_client_order_id("strat-1", "sig-B", 0)
        assert cid_a != cid_b

    def test_format_is_uuid_like(self):
        cid = derive_client_order_id("strat-1", "sig-abc", 0)
        parts = cid.split("-")
        assert len(parts) == 5
        assert len(cid) == 36


# ---------------------------------------------------------------------------
# quantize helpers
# ---------------------------------------------------------------------------


class TestQuantizeHelpers:
    def test_quantize_qty_rounds_down(self):
        # lot_size=0.001 → 0.0019 → 0.001
        result = quantize_qty(Decimal("0.0019"), Decimal("0.001"))
        assert result == Decimal("0.001")

    def test_quantize_qty_exact(self):
        result = quantize_qty(Decimal("0.123"), Decimal("0.001"))
        assert result == Decimal("0.123")

    def test_quantize_price_rounds(self):
        result = quantize_price(Decimal("45000.34"), Decimal("0.10"))
        assert result % Decimal("0.10") == Decimal("0")

    def test_quantize_qty_zero_lot_raises(self):
        with pytest.raises(ValueError):
            quantize_qty(Decimal("1.0"), Decimal("0"))


# ---------------------------------------------------------------------------
# OrderFactory — LIMIT
# ---------------------------------------------------------------------------


class TestOrderFactoryLimit:
    @pytest.fixture
    def factory(self):
        return OrderFactory(
            lot_size=Decimal("0.001"),
            tick_size=Decimal("0.10"),
        )

    def test_limit_buy_basic(self, factory):
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec.side == "BUY"
        assert spec.binance_type == BinanceOrderType.LIMIT
        assert spec.quantity == Decimal("0.1")
        assert spec.price == Decimal("45000.0")
        assert spec.time_in_force == BinanceTimeInForce.GTC
        assert spec.reduce_only is False

    def test_limit_sell_basic(self, factory):
        spec = factory.limit(
            side=OrderSide.SELL,
            quantity=Decimal("0.5"),
            price=Decimal("50000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec.side == "SELL"
        assert spec.binance_type == BinanceOrderType.LIMIT

    def test_limit_client_id_deterministic(self, factory):
        spec1 = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        spec2 = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec1.client_order_id == spec2.client_order_id

    def test_limit_to_binance_params_has_required_keys(self, factory):
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        params = spec.to_binance_params()
        assert "symbol" in params
        assert "side" in params
        assert "type" in params
        assert "quantity" in params
        assert "price" in params
        assert "timeInForce" in params
        assert "newClientOrderId" in params

    def test_limit_quantity_quantized(self, factory):
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.0019"),   # below lot_size precision
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        # 0.0019 / 0.001 = 1.9 → floor → 1 → 0.001
        assert spec.quantity == Decimal("0.001")


# ---------------------------------------------------------------------------
# OrderFactory — MARKET
# ---------------------------------------------------------------------------


class TestOrderFactoryMarket:
    def test_market_blocked_by_default(self):
        factory = OrderFactory()
        with pytest.raises(ValueError, match="disabled"):
            factory.market(
                side=OrderSide.SELL,
                quantity=Decimal("0.1"),
                strategy_id="s1",
                signal_id="sig1",
            )

    def test_market_allowed_with_flag(self):
        factory = OrderFactory(allow_market_orders=True)
        spec = factory.market(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            strategy_id="s1",
            signal_id="sig1",
            reduce_only=True,
        )
        assert spec.binance_type == BinanceOrderType.MARKET
        assert spec.reduce_only is True
        assert spec.price is None

    def test_market_params_no_price_no_tif(self):
        factory = OrderFactory(allow_market_orders=True)
        spec = factory.market(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            strategy_id="s1",
            signal_id="sig1",
        )
        params = spec.to_binance_params()
        assert "price" not in params
        assert "timeInForce" not in params


# ---------------------------------------------------------------------------
# OrderFactory — STOP_MARKET
# ---------------------------------------------------------------------------


class TestOrderFactoryStopMarket:
    @pytest.fixture
    def factory(self):
        return OrderFactory()

    def test_stop_market_spec(self, factory):
        spec = factory.stop_market(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            stop_price=Decimal("44100"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec.binance_type == BinanceOrderType.STOP_MARKET
        assert spec.stop_price is not None
        assert spec.reduce_only is True
        assert spec.price is None

    def test_stop_market_params_has_stop_price(self, factory):
        spec = factory.stop_market(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            stop_price=Decimal("44100"),
            strategy_id="s1",
            signal_id="sig1",
        )
        params = spec.to_binance_params()
        assert "stopPrice" in params
        assert params["stopPrice"] == str(spec.stop_price)


# ---------------------------------------------------------------------------
# OrderFactory — TAKE_PROFIT
# ---------------------------------------------------------------------------


class TestOrderFactoryTakeProfit:
    @pytest.fixture
    def factory(self):
        return OrderFactory()

    def test_take_profit_spec(self, factory):
        spec = factory.take_profit(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            price=Decimal("46350.0"),
            stop_price=Decimal("46350.0"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec.binance_type == BinanceOrderType.TAKE_PROFIT
        assert spec.price is not None
        assert spec.stop_price is not None
        assert spec.reduce_only is True


# ---------------------------------------------------------------------------
# OrderFactory — TRAILING_STOP
# ---------------------------------------------------------------------------


class TestOrderFactoryTrailingStop:
    @pytest.fixture
    def factory(self):
        return OrderFactory()

    def test_trailing_stop_spec(self, factory):
        spec = factory.trailing_stop(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            callback_rate=Decimal("1.0"),
            strategy_id="s1",
            signal_id="sig1",
        )
        assert spec.binance_type == BinanceOrderType.TRAILING_STOP_MARKET
        assert spec.callback_rate == Decimal("1.0")
        assert spec.reduce_only is True

    def test_trailing_stop_invalid_rate_raises(self, factory):
        with pytest.raises(ValueError, match="callback_rate"):
            factory.trailing_stop(
                side=OrderSide.SELL,
                quantity=Decimal("0.1"),
                callback_rate=Decimal("0.05"),  # too small
                strategy_id="s1",
                signal_id="sig1",
            )

    def test_trailing_stop_with_activation_price(self, factory):
        spec = factory.trailing_stop(
            side=OrderSide.SELL,
            quantity=Decimal("0.1"),
            callback_rate=Decimal("1.5"),
            strategy_id="s1",
            signal_id="sig1",
            activation_price=Decimal("46000"),
        )
        assert spec.stop_price is not None


# ---------------------------------------------------------------------------
# OrderFactory — TWAP
# ---------------------------------------------------------------------------


class TestOrderFactoryTwap:
    @pytest.fixture
    def factory(self):
        return OrderFactory()

    def test_twap_produces_correct_slice_count(self, factory):
        slices = factory.twap(
            side=OrderSide.BUY,
            total_quantity=Decimal("0.5"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
            num_slices=5,
        )
        assert len(slices) == 5

    def test_twap_slices_have_unique_cids(self, factory):
        slices = factory.twap(
            side=OrderSide.BUY,
            total_quantity=Decimal("0.5"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
            num_slices=4,
        )
        cids = [s.client_order_id for s in slices]
        assert len(set(cids)) == 4, "All slice CIDs must be unique"

    def test_twap_slices_all_limit(self, factory):
        slices = factory.twap(
            side=OrderSide.BUY,
            total_quantity=Decimal("0.5"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        for spec in slices:
            assert spec.binance_type == BinanceOrderType.LIMIT

    def test_twap_zero_slices_raises(self, factory):
        with pytest.raises(ValueError):
            factory.twap(
                side=OrderSide.BUY,
                total_quantity=Decimal("0.5"),
                price=Decimal("45000"),
                strategy_id="s1",
                signal_id="sig1",
                num_slices=0,
            )


# ---------------------------------------------------------------------------
# OrderFactory — DCA
# ---------------------------------------------------------------------------


class TestOrderFactoryDca:
    @pytest.fixture
    def factory(self):
        return OrderFactory()

    def test_dca_buy_legs_decreasing_price(self, factory):
        legs = factory.dca(
            side=OrderSide.BUY,
            total_quantity=Decimal("0.4"),
            base_price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
            num_legs=4,
            price_step_pct=Decimal("0.005"),
        )
        assert len(legs) == 4
        prices = [leg.price for leg in legs]
        for i in range(1, len(prices)):
            assert prices[i] < prices[i - 1], "BUY DCA prices should decrease each leg"

    def test_dca_sell_legs_increasing_price(self, factory):
        legs = factory.dca(
            side=OrderSide.SELL,
            total_quantity=Decimal("0.4"),
            base_price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
            num_legs=4,
            price_step_pct=Decimal("0.005"),
        )
        prices = [leg.price for leg in legs]
        for i in range(1, len(prices)):
            assert prices[i] > prices[i - 1], "SELL DCA prices should increase each leg"

    def test_dca_legs_have_unique_cids(self, factory):
        legs = factory.dca(
            side=OrderSide.BUY,
            total_quantity=Decimal("0.4"),
            base_price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
            num_legs=4,
        )
        cids = [leg.client_order_id for leg in legs]
        assert len(set(cids)) == 4
