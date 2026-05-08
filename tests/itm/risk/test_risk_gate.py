"""
Tests — RiskGate (Section F)
===============================
Covers:
- Leverage check (must be 1.0)
- Minimum position size check (>= 0.001 BTC)
- Maximum position size check (<= 1.0 BTC)
- Emergency closeout blocks new orders
- Account heat RED blocks new orders
- Account heat YELLOW reduces quantity
- Capital governor limit check
- Daily loss limit check
- Stop-loss price computation (2% rule for BUY and SELL)
- Approved order returns correct fields
- Integration: full approval pipeline passes
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.domain.entities import OrderSide
from src.itm.risk.capital_governor import (
    CapitalGovernor,
    CapitalGovernorConfig,
    HeatLevel,
)
from src.itm.risk.emergency_closeout import EmergencyCloseout, EmergencyCloseoutConfig
from src.itm.risk.risk_gate import (
    RiskGate,
    OrderRequest,
    RiskDecision,
    RejectionCode,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
    STOP_LOSS_PCT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_gate(
    base_capital="25000",
    max_position_pct="0.20",  # allow up to 5000 USDT per position
    max_exposure_pct="0.80",  # allow up to 20000 USDT exposure
    global_closeout=False,
):
    gov_config = CapitalGovernorConfig(
        base_capital=Decimal(base_capital),
        max_position_pct=Decimal(max_position_pct),
        max_exposure_pct=Decimal(max_exposure_pct),
    )
    governor = CapitalGovernor(config=gov_config)
    cls_config = EmergencyCloseoutConfig(base_capital=Decimal(base_capital))
    closeout = EmergencyCloseout(config=cls_config)
    if global_closeout:
        closeout.trigger_global_closeout("test setup")
    gate = RiskGate(capital_governor=governor, closeout=closeout)
    return gate, governor, closeout


def make_order(
    strategy_id="s1",
    side=OrderSide.BUY,
    quantity="0.1",
    entry_price="45000",
    daily_pnl="0",
    max_daily_loss="500",
    leverage="1.0",
    stop_loss_price=None,
):
    return OrderRequest(
        strategy_id=strategy_id,
        side=side,
        quantity=Decimal(quantity),
        entry_price=Decimal(entry_price),
        daily_pnl=Decimal(daily_pnl),
        max_daily_loss=Decimal(max_daily_loss),
        leverage=Decimal(leverage),
        stop_loss_price=Decimal(stop_loss_price) if stop_loss_price else None,
    )


# ---------------------------------------------------------------------------
# Stop-loss computation
# ---------------------------------------------------------------------------

class TestStopLossComputation:

    def test_buy_stop_loss_2pct_below_entry(self):
        gate, _, _ = make_gate()
        order = make_order(entry_price="50000", side=OrderSide.BUY)
        decision = gate.approve(order)
        expected_stop = Decimal("50000") * (Decimal("1") - STOP_LOSS_PCT)
        assert decision.stop_loss_price == expected_stop

    def test_sell_stop_loss_2pct_above_entry(self):
        gate, _, _ = make_gate()
        order = make_order(entry_price="50000", side=OrderSide.SELL)
        decision = gate.approve(order)
        expected_stop = Decimal("50000") * (Decimal("1") + STOP_LOSS_PCT)
        assert decision.stop_loss_price == expected_stop

    def test_caller_tighter_stop_respected_for_buy(self):
        gate, _, _ = make_gate()
        # Caller suggests a tighter stop: 43800 (2.7% below entry 45000)
        # Required 2% stop = 44100; 43800 < 44100 → TIGHTER → use caller's
        order = make_order(
            entry_price="45000", side=OrderSide.BUY,
            stop_loss_price="43800",  # tighter than the 2% rule (44100)
        )
        decision = gate.approve(order)
        # Gate should use the caller's tighter stop (min for BUY)
        assert decision.stop_loss_price == Decimal("43800")

    def test_caller_looser_stop_overridden_for_buy(self):
        gate, _, _ = make_gate()
        # Caller suggests 0.5% stop at 44775 — LOOSER than 2% (44100)
        # 44775 is only 0.5% below entry, which is less protective than 2%
        order = make_order(
            entry_price="45000", side=OrderSide.BUY,
            stop_loss_price="44775",  # looser: 0.5% below, above the 2% stop of 44100
        )
        decision = gate.approve(order)
        # Gate enforces the 2% rule: 45000 * 0.98 = 44100
        assert decision.stop_loss_price == Decimal("45000") * Decimal("0.98")


# ---------------------------------------------------------------------------
# Leverage check
# ---------------------------------------------------------------------------

class TestLeverageCheck:

    def test_leverage_1_approved(self):
        gate, _, _ = make_gate()
        order = make_order(leverage="1.0")
        decision = gate.approve(order)
        assert decision.approved

    def test_leverage_over_one_rejected(self):
        gate, _, _ = make_gate()
        order = make_order(leverage="2.0")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.LEVERAGE_EXCEEDED

    def test_leverage_less_than_one_approved(self):
        gate, _, _ = make_gate()
        order = make_order(leverage="0.5")
        decision = gate.approve(order)
        assert decision.approved


# ---------------------------------------------------------------------------
# Minimum position size
# ---------------------------------------------------------------------------

class TestMinPositionSize:

    def test_at_minimum_approved(self):
        gate, _, _ = make_gate()
        order = make_order(quantity=str(MIN_POSITION_SIZE))
        decision = gate.approve(order)
        assert decision.approved

    def test_below_minimum_rejected(self):
        gate, _, _ = make_gate()
        order = make_order(quantity="0.0001")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.QUANTITY_TOO_SMALL


# ---------------------------------------------------------------------------
# Maximum position size
# ---------------------------------------------------------------------------

class TestMaxPositionSize:

    def test_at_maximum_approved(self):
        gate, _, _ = make_gate(
            base_capital="200000",   # large enough to allow 1.0 BTC notional
            max_position_pct="0.30",
            max_exposure_pct="0.80",
        )
        order = make_order(quantity=str(MAX_POSITION_SIZE), entry_price="40000")
        decision = gate.approve(order)
        assert decision.approved

    def test_over_maximum_rejected(self):
        gate, _, _ = make_gate()
        order = make_order(quantity="1.5")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.QUANTITY_TOO_LARGE


# ---------------------------------------------------------------------------
# Emergency closeout
# ---------------------------------------------------------------------------

class TestEmergencyCloseout:

    def test_global_closeout_blocks_all_orders(self):
        gate, _, _ = make_gate(global_closeout=True)
        order = make_order()
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.EMERGENCY_CLOSEOUT_ACTIVE


# ---------------------------------------------------------------------------
# Account heat
# ---------------------------------------------------------------------------

class TestAccountHeat:

    def test_red_heat_blocks_new_orders(self):
        # Set up: base_capital=10000, max_exposure_pct=0.40 → max_exposure=4000
        # max_position_pct=0.90 → per-position cap=9000 (not limiting)
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("10000"),
            max_position_pct=Decimal("0.90"),
            max_exposure_pct=Decimal("0.40"),
        )
        governor = CapitalGovernor(config=gov_config)
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(base_capital=Decimal("10000"))
        )
        gate = RiskGate(capital_governor=governor, closeout=closeout)

        # Open a position to push heat to RED (>80%)
        governor.open_position("s1", Decimal("3300"))   # 82.5%
        assert governor.heat_level == HeatLevel.RED

        order = make_order(quantity="0.01", entry_price="10000")  # small order
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.HEAT_RED

    def test_yellow_heat_reduces_quantity(self):
        # base_capital=10000, max_exposure=4000, max_position=9000
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("10000"),
            max_position_pct=Decimal("0.90"),
            max_exposure_pct=Decimal("0.40"),
        )
        governor = CapitalGovernor(config=gov_config)
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(base_capital=Decimal("10000"))
        )
        gate = RiskGate(capital_governor=governor, closeout=closeout)

        # Push to YELLOW: 50% = 2000/4000
        governor.open_position("s1", Decimal("2000"))
        assert governor.heat_level == HeatLevel.YELLOW

        # Request 0.04 BTC @ 10000 = 400 USDT notional
        order = make_order(
            quantity="0.04",  # 400 USDT @ 10k
            entry_price="10000",
            max_daily_loss="500",
        )
        decision = gate.approve(order)
        # Should be approved with halved quantity
        # adjusted_notional = 400 * 0.5 = 200; qty = 200/10000 = 0.02
        assert decision.approved
        assert decision.adjusted_quantity < Decimal("0.04")


# ---------------------------------------------------------------------------
# Capital governor limit
# ---------------------------------------------------------------------------

class TestCapitalGovernorLimit:

    def test_position_over_per_trade_cap_rejected(self):
        # base_capital=10000, max_position_pct=0.10 → cap=1000 USDT
        # Request: 0.1 BTC @ 15000 = 1500 USDT → exceeds cap
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("10000"),
            max_position_pct=Decimal("0.10"),
            max_exposure_pct=Decimal("0.80"),
        )
        governor = CapitalGovernor(config=gov_config)
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(base_capital=Decimal("10000"))
        )
        gate = RiskGate(capital_governor=governor, closeout=closeout)
        order = make_order(quantity="0.1", entry_price="15000")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.CAPITAL_LIMIT


# ---------------------------------------------------------------------------
# Daily loss limit
# ---------------------------------------------------------------------------

class TestDailyLossLimit:

    def test_daily_loss_at_limit_rejected(self):
        gate, _, _ = make_gate()
        order = make_order(
            daily_pnl="-500",   # lost exactly $500
            max_daily_loss="500",  # limit is $500
        )
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.DAILY_LOSS_LIMIT

    def test_daily_loss_below_limit_approved(self):
        gate, _, _ = make_gate()
        order = make_order(
            daily_pnl="-499",
            max_daily_loss="500",
        )
        decision = gate.approve(order)
        assert decision.approved

    def test_daily_profit_not_blocking(self):
        gate, _, _ = make_gate()
        order = make_order(daily_pnl="200", max_daily_loss="500")
        decision = gate.approve(order)
        assert decision.approved


# ---------------------------------------------------------------------------
# Full approval pipeline
# ---------------------------------------------------------------------------

class TestFullApprovalPipeline:

    def test_valid_order_approved(self):
        gate, _, _ = make_gate(
            base_capital="50000",
            max_position_pct="0.10",
            max_exposure_pct="0.80",
        )
        # 0.1 BTC @ 45000 = 4500 USDT; cap = 5000 → OK
        order = make_order(
            quantity="0.1",
            entry_price="45000",
            daily_pnl="0",
            max_daily_loss="500",
            leverage="1.0",
        )
        decision = gate.approve(order)
        assert decision.approved is True
        assert decision.rejection_code is None
        assert decision.adjusted_quantity == Decimal("0.1")
        # Stop loss should be 2% below entry
        assert decision.stop_loss_price == Decimal("45000") * Decimal("0.98")

    def test_approved_decision_has_reason(self):
        gate, _, _ = make_gate()
        order = make_order()
        decision = gate.approve(order)
        if decision.approved:
            assert decision.reason is not None
            assert len(decision.reason) > 0

    def test_rejected_decision_has_reason(self):
        gate, _, _ = make_gate()
        order = make_order(quantity="1.5")  # over max
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.reason is not None
