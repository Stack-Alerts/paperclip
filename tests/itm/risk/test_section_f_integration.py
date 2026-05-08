"""
Section F Integration Tests — Risk, Capital & Account Heat Management
=======================================================================
Covers the acceptance criteria from BTCAAAAA-433:

1. Orders exceeding capital limits are rejected by RiskGate
2. Account heat correctly computed; thresholds trigger correct actions
3. Emergency closeout fires correctly in simulation
4. Capital metrics computed correctly against known test data
5. Full pipeline: capital governor → risk gate → closeout interaction
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.domain.entities import OrderSide
from src.itm.risk import (
    CapitalGovernor,
    CapitalGovernorConfig,
    EmergencyCloseout,
    EmergencyCloseoutConfig,
    RiskGate,
    OrderRequest,
    RejectionCode,
    HeatLevel,
    CapitalMetrics,
    PositionSizer,
    PositionSizerConfig,
    SizingMode,
)


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------

def make_standard_system(base_capital="25000"):
    """Create a standard governor + closeout + gate with realistic limits."""
    gov_config = CapitalGovernorConfig(
        base_capital=Decimal(base_capital),
        max_position_pct=Decimal("0.10"),  # 10% per trade
        max_exposure_pct=Decimal("0.40"),  # 40% total
    )
    governor = CapitalGovernor(config=gov_config)
    cls_config = EmergencyCloseoutConfig(
        base_capital=Decimal(base_capital),
        daily_drawdown_limit_pct=Decimal("0.05"),
        position_loss_limit_pct=Decimal("0.02"),
    )
    closeout = EmergencyCloseout(config=cls_config)
    gate = RiskGate(capital_governor=governor, closeout=closeout)
    return gate, governor, closeout


def make_order(
    strategy_id="s1",
    qty="0.05",
    entry_price="45000",
    daily_pnl="0",
    max_daily_loss="500",
    leverage="1.0",
    side=OrderSide.BUY,
):
    return OrderRequest(
        strategy_id=strategy_id,
        side=side,
        quantity=Decimal(qty),
        entry_price=Decimal(entry_price),
        daily_pnl=Decimal(daily_pnl),
        max_daily_loss=Decimal(max_daily_loss),
        leverage=Decimal(leverage),
    )


# ---------------------------------------------------------------------------
# AC 1: Orders exceeding capital limits are rejected by RiskGate
# ---------------------------------------------------------------------------

class TestCapitalLimitEnforcement:

    def test_order_within_limit_approved(self):
        """0.05 BTC @ 45000 = 2250 USDT (< 2500 cap) → approved."""
        gate, gov, _ = make_standard_system()
        order = make_order(qty="0.05", entry_price="45000")
        decision = gate.approve(order)
        assert decision.approved, f"Expected approval, got: {decision.reason}"

    def test_order_exceeds_per_position_cap_rejected(self):
        """0.1 BTC @ 45000 = 4500 USDT (> 2500 cap) → rejected."""
        gate, gov, _ = make_standard_system(base_capital="25000")
        # max_position = 25000 * 0.10 = 2500; 4500 > 2500
        order = make_order(qty="0.1", entry_price="45000")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.CAPITAL_LIMIT

    def test_total_exposure_cap_enforced(self):
        """After multiple positions, total exposure capped at 40%."""
        gate, gov, _ = make_standard_system(base_capital="25000")
        # max_exposure = 25000 * 0.40 = 10000 USDT
        # Fill up exposure with 4 × 2000 = 8000 USDT
        for i in range(4):
            gov.open_position(f"s{i}", Decimal("2000"))
        # Remaining capacity = 10000 - 8000 = 2000
        # 0.05 BTC @ 45000 = 2250 > 2000 → rejected
        order = make_order(qty="0.05", entry_price="45000")
        decision = gate.approve(order)
        assert decision.approved is False

    def test_leverage_over_one_always_rejected(self):
        gate, _, _ = make_standard_system()
        order = make_order(leverage="3.0")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.LEVERAGE_EXCEEDED

    def test_quantity_over_1_btc_rejected(self):
        gate, _, _ = make_standard_system()
        order = make_order(qty="1.5")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.QUANTITY_TOO_LARGE


# ---------------------------------------------------------------------------
# AC 2: Account heat correctly computed; thresholds trigger correct actions
# ---------------------------------------------------------------------------

class TestAccountHeatThresholds:

    def test_green_heat_below_50pct(self):
        # max_exposure = 10000; open 4000 → 40% → GREEN
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("25000"),
            max_position_pct=Decimal("0.20"),
            max_exposure_pct=Decimal("0.40"),
        )
        gov = CapitalGovernor(config=gov_config)
        gov.open_position("s1", Decimal("4000"))
        assert gov.heat_level == HeatLevel.GREEN
        assert gov.heat_pct < Decimal("50")

    def test_yellow_heat_between_50_and_80pct(self):
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("25000"),
            max_position_pct=Decimal("0.30"),
            max_exposure_pct=Decimal("0.40"),
        )
        gov = CapitalGovernor(config=gov_config)
        # max_exposure = 10000; open 6000 → 60% → YELLOW
        gov.open_position("s1", Decimal("6000"))
        assert gov.heat_level == HeatLevel.YELLOW
        assert Decimal("50") <= gov.heat_pct < Decimal("80")

    def test_yellow_heat_reduces_new_position_size(self):
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("25000"),
            max_position_pct=Decimal("0.30"),
            max_exposure_pct=Decimal("0.40"),
        )
        gov = CapitalGovernor(config=gov_config)
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(base_capital=Decimal("25000"))
        )
        gate = RiskGate(capital_governor=gov, closeout=closeout)

        gov.open_position("s1", Decimal("6000"))  # → YELLOW
        order = make_order(qty="0.04", entry_price="10000")  # 400 USDT
        decision = gate.approve(order)
        assert decision.approved
        assert decision.adjusted_quantity <= Decimal("0.02")  # halved

    def test_red_heat_above_80pct_blocks_orders(self):
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("25000"),
            max_position_pct=Decimal("0.40"),
            max_exposure_pct=Decimal("0.40"),
        )
        gov = CapitalGovernor(config=gov_config)
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(base_capital=Decimal("25000"))
        )
        gate = RiskGate(capital_governor=gov, closeout=closeout)

        gov.open_position("s1", Decimal("8500"))  # 85% → RED
        assert gov.heat_level == HeatLevel.RED

        order = make_order(qty="0.001", entry_price="45000")
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.HEAT_RED

    def test_heat_transitions_on_close(self):
        gov_config = CapitalGovernorConfig(
            base_capital=Decimal("10000"),
            max_position_pct=Decimal("0.90"),
            max_exposure_pct=Decimal("0.40"),
        )
        gov = CapitalGovernor(config=gov_config)
        gov.open_position("s1", Decimal("3300"))  # 82.5% → RED
        assert gov.heat_level == HeatLevel.RED
        # Close enough to drop below RED (80%)
        gov.close_position("s1", Decimal("300"))  # now 3000/4000 = 75% → YELLOW
        assert gov.heat_level == HeatLevel.YELLOW


# ---------------------------------------------------------------------------
# AC 3: Emergency closeout fires correctly in simulation
# ---------------------------------------------------------------------------

class TestEmergencyCloseoutSimulation:

    def test_strategy_closeout_on_daily_drawdown(self):
        """Daily drawdown >= 5% (1250 USDT on 25k base) triggers strategy closeout."""
        strategy_closeouts = []
        gate, gov, closeout = make_standard_system()
        closeout._on_strategy_closeout = lambda sid, r: strategy_closeouts.append(sid)

        # Accumulate 1250 USDT in daily losses
        closeout.record_trade_pnl("s1", Decimal("-500"))
        closeout.record_trade_pnl("s1", Decimal("-500"))
        event = closeout.record_trade_pnl("s1", Decimal("-250"))  # total = 1250 → trigger

        assert event is not None
        assert event.strategy_id == "s1"
        assert "s1" in strategy_closeouts

    def test_strategy_closeout_on_position_loss(self):
        """Single position loss >= 2% (500 USDT on 25k base) triggers strategy closeout."""
        strategy_closeouts = []
        gate, gov, closeout = make_standard_system()
        closeout._on_strategy_closeout = lambda sid, r: strategy_closeouts.append(sid)

        event = closeout.record_trade_pnl("s1", Decimal("-500"))

        assert event is not None
        assert len(strategy_closeouts) == 1

    def test_global_closeout_blocks_all_orders(self):
        """Global closeout fires and blocks all subsequent orders."""
        global_calls = []
        gate, gov, closeout = make_standard_system()
        closeout._on_global_closeout = lambda r: global_calls.append(r)

        closeout.trigger_global_closeout("extreme market event")
        assert len(global_calls) == 1

        # All orders now rejected
        order = make_order()
        decision = gate.approve(order)
        assert decision.approved is False
        assert decision.rejection_code == RejectionCode.EMERGENCY_CLOSEOUT_ACTIVE

    def test_closeout_only_affects_triggered_strategy(self):
        """Strategy closeout does not affect other strategies (independence)."""
        strategy_closeouts = []
        gate, gov, closeout = make_standard_system()
        closeout._on_strategy_closeout = lambda sid, r: strategy_closeouts.append(sid)

        # Trigger closeout for s1 only
        closeout.record_trade_pnl("s1", Decimal("-600"))

        assert "s1" in strategy_closeouts
        # s2 unaffected
        assert "s2" not in strategy_closeouts


# ---------------------------------------------------------------------------
# AC 4: Capital metrics computed correctly against known test data
# ---------------------------------------------------------------------------

class TestCapitalMetricsKnownData:

    def test_win_rate_known_data(self):
        """3 wins / 5 trades = 60% win rate."""
        m = CapitalMetrics(initial_capital=Decimal("25000"))
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        m.record_trade(Decimal("200"), Decimal("25250"))
        m.record_trade(Decimal("-30"), Decimal("25220"))
        m.record_trade(Decimal("80"), Decimal("25300"))
        assert m.win_rate == Decimal("3") / Decimal("5")

    def test_profit_factor_known_data(self):
        """Gross profit = 380 USDT; gross loss = 80 USDT → PF = 4.75."""
        m = CapitalMetrics(initial_capital=Decimal("25000"))
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        m.record_trade(Decimal("200"), Decimal("25250"))
        m.record_trade(Decimal("-30"), Decimal("25220"))
        m.record_trade(Decimal("80"), Decimal("25300"))
        # Gross profit = 100+200+80 = 380; Gross loss = 50+30 = 80
        expected_pf = Decimal("380") / Decimal("80")
        assert m.profit_factor == expected_pf

    def test_max_drawdown_known_data(self):
        """Peak 26000, trough 24700 → drawdown = 1300/26000 = 5%."""
        m = CapitalMetrics(initial_capital=Decimal("25000"))
        m.record_trade(Decimal("1000"), Decimal("26000"))   # peak = 26000
        m.record_trade(Decimal("-1300"), Decimal("24700"))  # trough
        m.record_trade(Decimal("500"), Decimal("25200"))    # partial recovery

        expected_drawdown = Decimal("1300") / Decimal("26000")
        assert m.max_drawdown == expected_drawdown

    def test_total_pnl_known_data(self):
        m = CapitalMetrics()
        m.record_trade(Decimal("100"), Decimal("25100"))
        m.record_trade(Decimal("-50"), Decimal("25050"))
        m.record_trade(Decimal("200"), Decimal("25250"))
        assert m.total_pnl == Decimal("250")


# ---------------------------------------------------------------------------
# AC 5: Position sizing with known test data
# ---------------------------------------------------------------------------

class TestPositionSizingIntegration:

    def test_fixed_fraction_known_result(self):
        """
        capital=25000, risk=1%, stop_dist=900 USDT (2% of 45000)
        qty = (25000 * 0.01) / 900 = 250/900 ≈ 0.2778 BTC
        """
        sizer = PositionSizer(PositionSizerConfig(
            mode=SizingMode.FIXED_FRACTION,
            risk_fraction=Decimal("0.01"),
            default_stop_pct=Decimal("0.02"),
        ))
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
        )
        # stop_dist = 45000 * 0.02 = 900
        assert result.stop_distance == Decimal("900")
        expected_qty = Decimal("250") / Decimal("900")
        assert result.quantity == expected_qty

    def test_atr_based_stop_known_result(self):
        """
        capital=25000, risk=1%, ATR=600, multiplier=1.5 → stop=900
        qty = 250/900 ≈ 0.2778 BTC
        """
        sizer = PositionSizer(PositionSizerConfig(
            mode=SizingMode.FIXED_FRACTION,
            risk_fraction=Decimal("0.01"),
            atr_multiplier=Decimal("1.5"),
        ))
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
            atr=Decimal("600"),
        )
        assert result.stop_distance == Decimal("900")

    def test_position_size_respects_risk_gate_limits(self):
        """Sized quantity must pass the risk gate (≤ MAX_POSITION_SIZE)."""
        from src.itm.risk.risk_gate import MAX_POSITION_SIZE
        sizer = PositionSizer()
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
            stop_distance_usdt=Decimal("900"),
        )
        assert result.quantity <= MAX_POSITION_SIZE
