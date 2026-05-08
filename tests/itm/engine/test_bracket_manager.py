"""
Unit tests: BracketManager (Section G)
========================================
Tests TP/SL bracket attachment, trailing stop attachment, OCO-style
cancel-surviving-leg logic, partial fill policy, and bracket cancellation.
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, call

from src.itm.domain.entities import OrderSide
from src.itm.engine.bracket_manager import BracketConfig, BracketManager
from src.itm.engine.order_factory import OrderFactory
from src.itm.engine.order_state_machine import OrderState, OrderStateMachine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def factory():
    return OrderFactory(lot_size=Decimal("0.001"), tick_size=Decimal("0.10"))


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.place_order.return_value = "EX-BRACKET-001"
    client.cancel_order.return_value = True
    return client


@pytest.fixture
def bracket_manager(factory, mock_client):
    config = BracketConfig(
        tp_pct=Decimal("0.03"),
        sl_pct=Decimal("0.02"),
        min_fill_ratio=Decimal("0.5"),
    )
    return BracketManager(
        order_factory=factory,
        exchange_client=mock_client,
        config=config,
    )


def _make_filled_sm(factory, side_str: str = "BUY", qty: str = "0.1", price: str = "45000"):
    """Helper: create a state machine that is already FILLED."""
    spec = factory.limit(
        side=OrderSide.BUY if side_str == "BUY" else OrderSide.SELL,
        quantity=Decimal(qty),
        price=Decimal(price),
        strategy_id="test-strat",
        signal_id="sig-123",
    )
    # Manually set side string to match
    spec.side = side_str

    sm = OrderStateMachine(spec=spec, ttl_secs=60.0)
    sm.acknowledge("EX-ENTRY-001")
    sm.fill(Decimal(price), Decimal(qty))
    return sm


# ---------------------------------------------------------------------------
# on_entry_filled — normal cases
# ---------------------------------------------------------------------------


class TestOnEntryFilled:
    def test_places_tp_and_sl_on_fill(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)

        assert record is not None
        # place_order called twice: once for TP, once for SL
        assert mock_client.place_order.call_count == 2

    def test_bracket_record_stored(self, bracket_manager, factory):
        sm = _make_filled_sm(factory)
        bracket_manager.on_entry_filled(sm)
        record = bracket_manager.get_bracket(sm.spec.client_order_id)
        assert record is not None
        assert record.entry_client_id == sm.spec.client_order_id

    def test_bracket_record_has_tp_and_sl_ids(self, bracket_manager, factory):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)
        assert record.tp_client_id is not None
        assert record.sl_client_id is not None

    def test_tp_above_entry_for_long(self, bracket_manager, factory, mock_client):
        """TP price must be > fill price for a LONG (BUY) entry."""
        sm = _make_filled_sm(factory, side_str="BUY", price="45000")
        bracket_manager.on_entry_filled(sm)
        # First place_order call should be for TP
        tp_spec = mock_client.place_order.call_args_list[0][0][0]
        # TP price = 45000 * 1.03 = 46350
        assert tp_spec.price > Decimal("45000")

    def test_sl_below_entry_for_long(self, bracket_manager, factory, mock_client):
        """SL price must be < fill price for a LONG (BUY) entry."""
        sm = _make_filled_sm(factory, side_str="BUY", price="45000")
        bracket_manager.on_entry_filled(sm)
        # Second place_order call should be for SL
        sl_spec = mock_client.place_order.call_args_list[1][0][0]
        # SL price = 45000 * 0.98 = 44100
        assert sl_spec.stop_price < Decimal("45000")

    def test_sl_at_least_2pct_from_entry(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory, side_str="BUY", price="45000")
        bracket_manager.on_entry_filled(sm)
        sl_spec = mock_client.place_order.call_args_list[1][0][0]
        sl_pct = (Decimal("45000") - sl_spec.stop_price) / Decimal("45000")
        assert sl_pct >= Decimal("0.02")

    def test_ignored_if_not_filled_state(self, bracket_manager, factory):
        """on_entry_filled should return None if order not FILLED."""
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        sm = OrderStateMachine(spec=spec, ttl_secs=60.0)
        sm.acknowledge("EX-1")  # only acknowledged, not filled
        result = bracket_manager.on_entry_filled(sm)
        assert result is None

    def test_no_bracket_if_fills_none(self, bracket_manager, factory):
        """Edge case: FILLED state but no fills recorded (defensive)."""
        sm = _make_filled_sm(factory)
        # Corrupt fills list
        sm.fills.clear()
        result = bracket_manager.on_entry_filled(sm)
        assert result is None


# ---------------------------------------------------------------------------
# Partial fill policy
# ---------------------------------------------------------------------------


class TestPartialFillPolicy:
    def test_bracket_placed_above_min_fill_ratio(self, factory, mock_client):
        config = BracketConfig(min_fill_ratio=Decimal("0.5"))
        mgr = BracketManager(
            order_factory=factory, exchange_client=mock_client, config=config
        )
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        sm = OrderStateMachine(spec=spec, ttl_secs=60.0)
        sm.acknowledge("EX-1")
        # Partial fill of 60% then cancel
        sm.partial_fill(Decimal("45000"), Decimal("0.06"))
        sm.cancel("timeout")

        record = mgr.on_partial_entry_cancelled(sm)
        assert record is not None  # 60% >= 50% threshold

    def test_no_bracket_below_min_fill_ratio(self, factory, mock_client):
        config = BracketConfig(min_fill_ratio=Decimal("0.5"))
        mgr = BracketManager(
            order_factory=factory, exchange_client=mock_client, config=config
        )
        spec = factory.limit(
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            strategy_id="s1",
            signal_id="sig1",
        )
        sm = OrderStateMachine(spec=spec, ttl_secs=60.0)
        sm.acknowledge("EX-1")
        # Partial fill of only 20% then cancel
        sm.partial_fill(Decimal("45000"), Decimal("0.02"))
        sm.cancel("timeout")

        mock_client.place_order.reset_mock()
        record = mgr.on_partial_entry_cancelled(sm)
        assert record is None
        assert mock_client.place_order.call_count == 0


# ---------------------------------------------------------------------------
# OCO-style management: TP fills → cancel SL
# ---------------------------------------------------------------------------


class TestOcoManagement:
    def test_tp_fill_cancels_sl(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)
        tp_cid = record.tp_client_id
        sl_cid = record.sl_client_id

        mock_client.cancel_order.reset_mock()
        bracket_manager.on_bracket_leg_filled(tp_cid)

        assert record.tp_filled is True
        # SL should be cancelled
        mock_client.cancel_order.assert_called_once_with(sl_cid)

    def test_sl_fill_cancels_tp(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)
        tp_cid = record.tp_client_id
        sl_cid = record.sl_client_id

        mock_client.cancel_order.reset_mock()
        bracket_manager.on_bracket_leg_filled(sl_cid)

        assert record.sl_filled is True
        mock_client.cancel_order.assert_called_once_with(tp_cid)

    def test_unknown_cid_does_not_raise(self, bracket_manager):
        # Should log a warning but not raise
        bracket_manager.on_bracket_leg_filled("UNKNOWN-CID")


# ---------------------------------------------------------------------------
# cancel_bracket
# ---------------------------------------------------------------------------


class TestCancelBracket:
    def test_cancel_bracket_cancels_both_legs(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)
        tp_cid = record.tp_client_id
        sl_cid = record.sl_client_id

        mock_client.cancel_order.reset_mock()
        bracket_manager.cancel_bracket(sm.spec.client_order_id, reason="strategy_stop")

        cancelled_cids = {c.args[0] for c in mock_client.cancel_order.call_args_list}
        assert tp_cid in cancelled_cids
        assert sl_cid in cancelled_cids
        assert record.cancelled is True

    def test_cancel_already_resolved_bracket_noop(self, bracket_manager, factory, mock_client):
        sm = _make_filled_sm(factory)
        record = bracket_manager.on_entry_filled(sm)

        # Resolve via TP fill
        bracket_manager.on_bracket_leg_filled(record.tp_client_id)
        mock_client.cancel_order.reset_mock()

        # Now calling cancel_bracket should be a no-op
        bracket_manager.cancel_bracket(sm.spec.client_order_id)
        assert mock_client.cancel_order.call_count == 0

    def test_cancel_nonexistent_bracket_noop(self, bracket_manager, mock_client):
        mock_client.cancel_order.reset_mock()
        bracket_manager.cancel_bracket("nonexistent-entry-id")
        assert mock_client.cancel_order.call_count == 0


# ---------------------------------------------------------------------------
# Trailing stop bracket
# ---------------------------------------------------------------------------


class TestTrailingStopBracket:
    def test_trailing_stop_placed_instead_of_fixed_sl(self, factory, mock_client):
        config = BracketConfig(
            tp_pct=Decimal("0.03"),
            sl_pct=Decimal("0.02"),
            trailing_stop_callback_rate=Decimal("1.0"),
        )
        mgr = BracketManager(
            order_factory=factory, exchange_client=mock_client, config=config
        )
        sm = _make_filled_sm(factory)
        record = mgr.on_entry_filled(sm)
        assert record is not None
        # Should still have both tp and sl client IDs placed
        assert record.tp_client_id is not None
        assert record.sl_client_id is not None
        # SL leg should be a trailing stop (no fixed stop_price in params)
        sl_spec = mock_client.place_order.call_args_list[1][0][0]
        from src.itm.engine.order_factory import BinanceOrderType
        assert sl_spec.binance_type == BinanceOrderType.TRAILING_STOP_MARKET


# ---------------------------------------------------------------------------
# BracketConfig validation
# ---------------------------------------------------------------------------


class TestBracketConfig:
    def test_sl_below_2pct_raises(self):
        with pytest.raises(ValueError, match="sl_pct"):
            BracketConfig(sl_pct=Decimal("0.01"))

    def test_invalid_trailing_rate_raises(self):
        with pytest.raises(ValueError, match="trailing"):
            BracketConfig(trailing_stop_callback_rate=Decimal("6.0"))

    def test_invalid_min_fill_ratio_raises(self):
        with pytest.raises(ValueError, match="min_fill_ratio"):
            BracketConfig(min_fill_ratio=Decimal("0"))
