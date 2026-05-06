"""
Additional unit tests for ITM ↔ NautilusTrader type mapping (function-based API).
Complements test_nt_mapping.py which covers the NTTypeMapper class.
Covers: itm_instrument_to_nt_id, nt_id_to_itm_kwargs, signal_to_sb_dict,
        apply_nt_fill_to_itm_order, signal_from_strategy_builder.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.itm.domain.entities import (
    ContractType,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Signal,
    SignalDirection,
)
from src.itm.domain.nt_mapping import (
    apply_nt_fill_to_itm_order,
    itm_instrument_to_nt_id,
    nt_id_to_itm_kwargs,
    signal_from_strategy_builder,
    signal_to_sb_dict,
    signal_to_strategy_builder,
    NTTypeMapper,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def btc_spot() -> Instrument:
    return Instrument.btc_usdt_spot("binance")


@pytest.fixture
def btc_perp() -> Instrument:
    return Instrument.btc_usdt_perp("bybit")


# ---------------------------------------------------------------------------
# Instrument → NT InstrumentId (function helpers)
# ---------------------------------------------------------------------------


class TestInstrumentIdHelpers:
    def test_spot_symbol_no_slash(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        assert str(nt_id.symbol) == "BTCUSDT"

    def test_venue_uppercase(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        assert str(nt_id.venue) == "BINANCE"

    def test_perp_venue(self, btc_perp: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_perp)
        assert str(nt_id.venue) == "BYBIT"

    def test_nt_id_to_itm_kwargs_base_quote(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["symbol"] == "BTC/USDT"
        assert kwargs["exchange"] == "binance"
        assert kwargs["base_currency"] == "BTC"
        assert kwargs["quote_currency"] == "USDT"

    def test_nt_id_to_itm_kwargs_exchange_lowercase(self, btc_perp: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_perp)
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["exchange"] == "bybit"

    def test_nttype_mapper_instrument_to_nt_id(self, btc_spot: Instrument) -> None:
        nt_id = NTTypeMapper.instrument_to_nt_id(btc_spot)
        assert str(nt_id.symbol) == "BTCUSDT"

    def test_nttype_mapper_nt_id_to_itm(self, btc_spot: Instrument) -> None:
        nt_id = NTTypeMapper.instrument_to_nt_id(btc_spot)
        kwargs = NTTypeMapper.nt_instrument_id_to_itm(nt_id)
        assert kwargs["symbol"] == "BTC/USDT"

    def test_nt_id_to_itm_kwargs_btc_pair(self) -> None:
        """Test the elif raw_symbol.endswith('BTC') branch."""
        from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
        nt_id = InstrumentId(Symbol("ETHBTC"), Venue("BINANCE"))
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["symbol"] == "ETH/BTC"
        assert kwargs["base_currency"] == "ETH"
        assert kwargs["quote_currency"] == "BTC"

    def test_nt_id_to_itm_kwargs_unknown_pair(self) -> None:
        """Test the else branch for unknown symbol suffix."""
        from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
        nt_id = InstrumentId(Symbol("XYZUNKNOWN"), Venue("BINANCE"))
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["symbol"] == "XYZUNKNOWN"
        assert kwargs["base_currency"] == "XYZUNKNOWN"
        assert kwargs["quote_currency"] == ""


# ---------------------------------------------------------------------------
# signal_to_sb_dict tests
# ---------------------------------------------------------------------------


class TestSignalToSbDict:
    def test_round_trip_via_sb_dict(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.SHORT,
            strength=Decimal("0.65"),
            source_strategy="ema_cross_v2",
            instrument=btc_spot,
            metadata={"timeframe": "1h"},
        )
        d = signal_to_sb_dict(sig)
        assert d["strategy_id"] == "ema_cross_v2"
        assert d["direction"] == "short"
        assert d["strength"] == "0.65"
        assert d["metadata"]["timeframe"] == "1h"
        assert d["instrument_symbol"] == "BTC/USDT"
        assert d["instrument_exchange"] == "binance"
        assert "signal_id" in d
        assert "created_at" in d

    def test_created_at_is_isoformat(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.LONG,
            strength=Decimal("0.5"),
            source_strategy="s",
            instrument=btc_spot,
        )
        d = signal_to_sb_dict(sig)
        dt = datetime.fromisoformat(d["created_at"])
        assert dt.tzinfo is not None

    def test_empty_metadata_serializes_empty_dict(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.NEUTRAL,
            strength=Decimal("0"),
            source_strategy="s",
            instrument=btc_spot,
        )
        d = signal_to_sb_dict(sig)
        assert d["metadata"] == {}


# ---------------------------------------------------------------------------
# signal_from_strategy_builder standalone function tests
# ---------------------------------------------------------------------------


class TestSignalFromStrategyBuilder:
    def test_valid_long_signal(self, btc_spot: Instrument) -> None:
        payload = {
            "strategy_id": "rsi_momentum_v1",
            "direction": "long",
            "strength": "0.75",
        }
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.direction == SignalDirection.LONG
        assert sig.strength == Decimal("0.75")
        assert sig.source_strategy == "rsi_momentum_v1"

    def test_valid_short_signal(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "short", "strength": "0.5"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.direction == SignalDirection.SHORT

    def test_valid_exit_signal(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "exit", "strength": "1.0"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.direction == SignalDirection.EXIT

    def test_valid_neutral_signal(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "neutral", "strength": "0.0"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.direction == SignalDirection.NEUTRAL

    def test_direction_case_insensitive(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "LONG", "strength": "0.5"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.direction == SignalDirection.LONG

    def test_invalid_direction_raises(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "invalid", "strength": "0.5"}
        with pytest.raises(ValueError, match="invalid direction"):
            signal_from_strategy_builder(payload, btc_spot)

    def test_invalid_strength_raises(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "long", "strength": "not_a_number"}
        with pytest.raises(ValueError, match="strength"):
            signal_from_strategy_builder(payload, btc_spot)

    def test_metadata_preserved(self, btc_spot: Instrument) -> None:
        payload = {
            "strategy_id": "s1",
            "direction": "long",
            "strength": "0.9",
            "metadata": {"rsi": "72.3", "volume": "high"},
        }
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.metadata["rsi"] == "72.3"
        assert sig.metadata["volume"] == "high"

    def test_default_strength_when_missing(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "long"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.strength == Decimal("1.0")

    def test_instrument_set_correctly(self, btc_spot: Instrument) -> None:
        payload = {"strategy_id": "s1", "direction": "long", "strength": "0.5"}
        sig = signal_from_strategy_builder(payload, btc_spot)
        assert sig.instrument is btc_spot

    def test_signal_to_strategy_builder_alias(self, btc_spot: Instrument) -> None:
        # signal_to_strategy_builder is an alias of signal_to_sb_dict
        sig = Signal(
            direction=SignalDirection.LONG,
            strength=Decimal("0.5"),
            source_strategy="s",
            instrument=btc_spot,
        )
        d1 = signal_to_sb_dict(sig)
        d2 = signal_to_strategy_builder(sig)
        assert d1["signal_id"] == d2["signal_id"]
        assert d1["direction"] == d2["direction"]


# ---------------------------------------------------------------------------
# apply_nt_fill_to_itm_order standalone function tests
# ---------------------------------------------------------------------------


class TestApplyNTFillToITMOrder:
    def _make_fill_event(self, last_qty: str, last_px: str, venue_order_id: str = "VEN-1"):
        """Build a minimal NT OrderFilled event via the real NT constructor."""
        from nautilus_trader.model.events import OrderFilled
        from nautilus_trader.model.identifiers import (
            AccountId, ClientOrderId, InstrumentId, PositionId,
            Symbol, TradeId, Venue, VenueOrderId,
        )
        from nautilus_trader.model.identifiers import TraderId, StrategyId
        from nautilus_trader.model.objects import Money, Price, Quantity
        from nautilus_trader.model.currencies import USDT
        from nautilus_trader.model.enums import LiquiditySide, OrderSide as NTOrderSide, OrderType as NTOrderType
        from nautilus_trader.core.uuid import UUID4
        import time

        ts = int(time.time() * 1e9)
        return OrderFilled(
            trader_id=TraderId("TEST-001"),
            strategy_id=StrategyId("TEST-001"),
            instrument_id=InstrumentId(Symbol("BTC/USDT"), Venue("BINANCE")),
            client_order_id=ClientOrderId("coid-1"),
            venue_order_id=VenueOrderId(venue_order_id),
            account_id=AccountId("BINANCE-001"),
            trade_id=TradeId("TRADE-001"),
            position_id=None,
            order_side=NTOrderSide.BUY,
            order_type=NTOrderType.LIMIT,
            last_qty=Quantity.from_str(last_qty),
            last_px=Price.from_str(last_px),
            currency=USDT,
            commission=Money(0, USDT),
            liquidity_side=LiquiditySide.MAKER,
            event_id=UUID4(),
            ts_event=ts,
            ts_init=ts,
        )

    def test_first_fill_closed(self, btc_spot: Instrument) -> None:
        order = Order(
            instrument=btc_spot,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )
        fill = self._make_fill_event("0.1", "45000.00")
        apply_nt_fill_to_itm_order(order, fill)
        assert order.filled_quantity == Decimal("0.1")
        assert order.average_fill_price == Decimal("45000.00")
        assert order.status == OrderStatus.CLOSED

    def test_partial_fill(self, btc_spot: Instrument) -> None:
        order = Order(
            instrument=btc_spot,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.2"),
            price=Decimal("45000"),
        )
        fill = self._make_fill_event("0.1", "45000.00")
        apply_nt_fill_to_itm_order(order, fill)
        assert order.status == OrderStatus.PARTIAL
        assert order.filled_quantity == Decimal("0.1")

    def test_two_partial_fills_vwap(self, btc_spot: Instrument) -> None:
        order = Order(
            instrument=btc_spot,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.3"),
            price=Decimal("45000"),
        )
        fill1 = self._make_fill_event("0.1", "44000.00")
        fill2 = self._make_fill_event("0.2", "45000.00")
        apply_nt_fill_to_itm_order(order, fill1)
        apply_nt_fill_to_itm_order(order, fill2)
        expected = (Decimal("0.1") * Decimal("44000") + Decimal("0.2") * Decimal("45000")) / Decimal("0.3")
        assert abs(order.average_fill_price - expected) < Decimal("0.001")
        assert order.status == OrderStatus.CLOSED

    def test_exchange_order_id_set_on_first_fill(self, btc_spot: Instrument) -> None:
        order = Order(
            instrument=btc_spot,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )
        fill = self._make_fill_event("0.1", "45000.00", venue_order_id="VEN-42")
        apply_nt_fill_to_itm_order(order, fill)
        assert order.exchange_order_id == "VEN-42"
