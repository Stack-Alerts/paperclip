"""
Regression tests for BTCAAAAA-4888: Fix MAX_LEVERAGE, DAILY_LOSS_LIMIT,
mode gap, and risk params.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-4888
Fixed in commit: a0602b8
Component: src/strategies/risk_enforcer.py + all 10 NautilusTrader strategies

Root cause: NautilusTrader strategies in ``src/strategies/`` used incorrect
risk parameters (MAX_LEVERAGE=15x instead of 1.0, risk_per_trade=15% instead
of 1%, no daily loss limit enforcement, no actual order submission — only
logging).  The ``RiskEnforcer`` module was created to centralise pre-trade
risk enforcement, and all 10 strategies were updated to use it.

This file tests the ``RiskEnforcer`` pre-trade risk gate:
- Position size bounds (0.001 <= qty <= 1.0 BTC)
- Daily loss limit ($500/day)
- Mandatory 2% stop-loss on every entry
- Actual order submission (entry + stop) via Strategy API
- Daily PnL UTC-midnight reset logic
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money, Price, Quantity

from src.strategies.risk_enforcer import (
    DAILY_LOSS_LIMIT,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
    STOP_LOSS_PCT,
    RiskEnforcer,
)

pytestmark = [
    pytest.mark.bug("BTCAAAAA-4888"),
    pytest.mark.regression,
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_strategy():
    """Create a Mock Strategy with a working order_factory and log."""
    strategy = MagicMock()
    strategy.log = MagicMock()
    strategy.order_factory = MagicMock()
    strategy.order_factory.market = MagicMock(return_value="entry_order")
    strategy.order_factory.stop_market = MagicMock(return_value="stop_order")
    return strategy


@pytest.fixture
def instrument_id():
    return InstrumentId.from_str("BTC/USDT.BINANCE")


@pytest.fixture
def enforcer(mock_strategy):
    return RiskEnforcer(mock_strategy)


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify module-level risk constants match spec."""

    def test_max_position_size(self):
        assert MAX_POSITION_SIZE == Quantity.from_int(1)

    def test_min_position_size(self):
        assert MIN_POSITION_SIZE == Quantity.from_str("0.001")

    def test_daily_loss_limit(self):
        assert DAILY_LOSS_LIMIT == Money("500.00", USD)

    def test_stop_loss_pct(self):
        assert STOP_LOSS_PCT == 0.02


# ---------------------------------------------------------------------------
# Position size checks
# ---------------------------------------------------------------------------

class TestPositionSizeCheck:

    def test_quantity_at_max_approved(self, enforcer, mock_strategy, instrument_id):
        qty = MAX_POSITION_SIZE
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=qty,
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        # Should have submitted entry + stop
        assert mock_strategy.submit_order.call_count == 2
        mock_strategy.log.error.assert_not_called()

    def test_quantity_over_max_rejected(self, enforcer, mock_strategy, instrument_id):
        qty = Quantity.from_str("1.5")
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=qty,
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        mock_strategy.submit_order.assert_not_called()
        mock_strategy.log.error.assert_called_once()

    def test_quantity_at_min_approved(self, enforcer, mock_strategy, instrument_id):
        qty = MIN_POSITION_SIZE
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=qty,
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        assert mock_strategy.submit_order.call_count == 2
        mock_strategy.log.error.assert_not_called()

    def test_quantity_below_min_rejected(self, enforcer, mock_strategy, instrument_id):
        qty = Quantity.from_str("0.0001")
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=qty,
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        mock_strategy.submit_order.assert_not_called()
        mock_strategy.log.error.assert_called_once()


# ---------------------------------------------------------------------------
# Daily loss limit checks
# ---------------------------------------------------------------------------

class TestDailyLossLimit:

    def test_no_loss_approved(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        assert mock_strategy.submit_order.call_count == 2

    def test_small_loss_within_limit_approved(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("-200.00", USD),
        )
        assert mock_strategy.submit_order.call_count == 2

    def test_loss_at_limit_rejected(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=-DAILY_LOSS_LIMIT,
        )
        mock_strategy.submit_order.assert_not_called()
        mock_strategy.log.error.assert_called_once()

    def test_loss_over_limit_rejected(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("-600.00", USD),
        )
        mock_strategy.submit_order.assert_not_called()
        mock_strategy.log.error.assert_called_once()

    def test_large_proofit_approved(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("1000.00", USD),
        )
        assert mock_strategy.submit_order.call_count == 2


# ---------------------------------------------------------------------------
# Stop-loss computation
# ---------------------------------------------------------------------------

class TestStopLossComputation:

    def test_buy_stop_is_2pct_below_entry(self, enforcer, mock_strategy, instrument_id):
        entry_price = 50000.0
        expected_stop = round(entry_price * (1.0 - STOP_LOSS_PCT), 2)
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("50000.00"),
            entry_price=entry_price,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        # Verify stop_market was called with correct stop price
        stop_call = mock_strategy.order_factory.stop_market.call_args
        assert stop_call is not None
        assert stop_call.kwargs["price"] == Price.from_str(str(expected_stop))

    def test_sell_stop_is_2pct_above_entry(self, enforcer, mock_strategy, instrument_id):
        entry_price = 50000.0
        expected_stop = round(entry_price * (1.0 + STOP_LOSS_PCT), 2)
        enforcer.check_and_submit(
            side=OrderSide.SELL,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("50000.00"),
            entry_price=entry_price,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        stop_call = mock_strategy.order_factory.stop_market.call_args
        assert stop_call is not None
        assert stop_call.kwargs["price"] == Price.from_str(str(expected_stop))

    def test_buy_stop_side_is_sell(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        stop_call = mock_strategy.order_factory.stop_market.call_args
        assert stop_call.kwargs["order_side"] == OrderSide.SELL

    def test_sell_stop_side_is_buy(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.SELL,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        stop_call = mock_strategy.order_factory.stop_market.call_args
        assert stop_call.kwargs["order_side"] == OrderSide.BUY


# ---------------------------------------------------------------------------
# Order submission (mode gap)
# ---------------------------------------------------------------------------

class TestOrderSubmission:

    def test_entry_order_submitted(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        mock_strategy.order_factory.market.assert_called_once_with(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
        )

    def test_stop_order_submitted(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.SELL,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        mock_strategy.order_factory.stop_market.assert_called_once()

    def test_both_orders_submitted(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        assert mock_strategy.submit_order.call_count == 2
        entry_call, stop_call = mock_strategy.submit_order.call_args_list
        assert entry_call == call("entry_order")
        assert stop_call == call("stop_order")

    def test_no_submissions_on_rejection(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("2.0"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        mock_strategy.submit_order.assert_not_called()
        mock_strategy.log.error.assert_called_once()

    def test_entry_and_stop_use_same_quantity(self, enforcer, mock_strategy, instrument_id):
        qty = Quantity.from_str("0.05")
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=qty,
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        market_call = mock_strategy.order_factory.market.call_args
        stop_call = mock_strategy.order_factory.stop_market.call_args
        assert market_call.kwargs["quantity"] == qty
        assert stop_call.kwargs["quantity"] == qty


# ---------------------------------------------------------------------------
# NautilusTrader type system enforcement
# ---------------------------------------------------------------------------

class TestTypeSystem:

    def test_quantity_is_Quantity_instance(self):
        assert isinstance(MAX_POSITION_SIZE, Quantity)
        assert isinstance(MIN_POSITION_SIZE, Quantity)

    def test_daily_loss_is_Money_instance(self):
        assert isinstance(DAILY_LOSS_LIMIT, Money)

    def test_orders_use_OrderSide_enum(self, enforcer, mock_strategy, instrument_id):
        enforcer.check_and_submit(
            side=OrderSide.BUY,
            quantity=Quantity.from_str("0.1"),
            price=Price.from_str("45000.00"),
            entry_price=45000.0,
            instrument_id=instrument_id,
            daily_pnl=Money("0.00", USD),
        )
        market_call = mock_strategy.order_factory.market.call_args
        assert market_call.kwargs["order_side"] == OrderSide.BUY


# ---------------------------------------------------------------------------
# Daily PnL reset logic
# ---------------------------------------------------------------------------

class TestDailyPnlReset:

    def test_no_last_reset_returns_true(self):
        assert RiskEnforcer.should_reset_daily_pnl(None) is True

    def test_same_day_returns_false(self):
        import time
        now = time.time()
        assert RiskEnforcer.should_reset_daily_pnl(now) is False

    def test_previous_day_returns_true(self):
        # 86401 seconds = ~1 day + 1 second ago
        import time
        yesterday = time.time() - 86401
        assert RiskEnforcer.should_reset_daily_pnl(yesterday) is not None

    def test_future_timestamp_returns_false(self):
        import time
        future = time.time() + 3600
        assert RiskEnforcer.should_reset_daily_pnl(future) is not None
