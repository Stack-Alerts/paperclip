"""
Integration test: Section G — Execution Engine & Order Lifecycle
=================================================================
Tests the full wiring: ExecutionEngine + OrderFactory + BracketManager
+ RiskGate (real, not mocked) + OrderStateMachine lifecycle.

All exchange I/O is mocked.  No real Binance calls.
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from src.itm.domain.entities import (
    Decision,
    DecisionAction,
    Instrument,
    OrderSide,
    Signal,
    SignalDirection,
)
from src.itm.engine.execution_engine import ExecutionEngine, ExecutionEngineConfig
from src.itm.engine.order_factory import OrderFactory
from src.itm.engine.order_state_machine import OrderState
from src.itm.engine.bracket_manager import BracketConfig
from src.itm.risk.risk_gate import RiskGate
from src.itm.risk.capital_governor import CapitalGovernor
from src.itm.risk.emergency_closeout import EmergencyCloseout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_real_risk_gate() -> RiskGate:
    """Create a real (non-mocked) risk gate with permissive capital limits."""
    from src.itm.risk.capital_governor import CapitalGovernorConfig
    from src.itm.risk.emergency_closeout import EmergencyCloseoutConfig
    governor = CapitalGovernor(
        config=CapitalGovernorConfig(
            base_capital=Decimal("100000"),
            max_position_pct=Decimal("0.50"),
            max_exposure_pct=Decimal("0.80"),
        )
    )
    closeout = EmergencyCloseout(
        config=EmergencyCloseoutConfig(
            base_capital=Decimal("100000"),
            daily_drawdown_limit_pct=Decimal("0.20"),
        )
    )
    return RiskGate(capital_governor=governor, closeout=closeout)


def _make_decision(
    action: DecisionAction = DecisionAction.ENTER_LONG,
    qty: str = "0.01",
    price: str = "45000",
) -> Decision:
    signal = Signal(
        direction=SignalDirection.LONG,
        strength=Decimal("0.8"),
        source_strategy="integration-strategy",
        instrument=Instrument.btc_usdt_perp(),
    )
    return Decision(
        action=action,
        confidence=Decimal("0.8"),
        contributing_signals=(signal,),
        risk_gated=False,
        instrument=Instrument.btc_usdt_perp(),
        metadata={
            "quantity": qty,
            "entry_price": price,
            "order_type": "limit",
        },
    )


@pytest.fixture
def mock_binance():
    client = MagicMock()
    client.place_order.return_value = "EX-INTEG-001"
    client.cancel_order.return_value = True
    return client


@pytest.fixture
def engine_real_gate(mock_binance):
    gate = _make_real_risk_gate()
    factory = OrderFactory(
        lot_size=Decimal("0.001"),
        tick_size=Decimal("0.10"),
        allow_market_orders=True,
    )
    config = ExecutionEngineConfig(
        order_ttl_secs=60.0,
        default_quantity=Decimal("0.01"),
        daily_loss_limit_usd=Decimal("500"),
        bracket_config=BracketConfig(
            tp_pct=Decimal("0.03"),
            sl_pct=Decimal("0.02"),
        ),
        use_testnet=True,
    )
    return ExecutionEngine(
        risk_gate=gate,
        binance_client=mock_binance,
        order_factory=factory,
        config=config,
    )


# ---------------------------------------------------------------------------
# Full lifecycle: entry → fill → bracket placement
# ---------------------------------------------------------------------------


class TestFullOrderLifecycle:
    def test_entry_fill_places_bracket(self, engine_real_gate, mock_binance):
        """
        End-to-end: ENTER_LONG decision → limit order submitted → fill via WS
        → bracket (TP + SL) placed.
        """
        decision = _make_decision(DecisionAction.ENTER_LONG, qty="0.01", price="45000")
        sms = engine_real_gate.handle_decision(decision)

        assert len(sms) == 1
        sm = sms[0]
        assert sm.state == OrderState.ACKNOWLEDGED

        # Simulate fill via WS executionReport
        cid = sm.spec.client_order_id
        mock_binance.place_order.reset_mock()
        engine_real_gate.handle_execution_report({
            "c": cid,
            "i": "EX-FILL-001",
            "X": "TRADE",
            "L": "45000",
            "l": "0.01",
            "n": "0",
            "q": "0.01",
            "z": "0.01",
        })

        assert sm.state == OrderState.FILLED
        # Bracket manager should have placed 2 orders (TP + SL)
        assert mock_binance.place_order.call_count == 2

    def test_entry_fill_sl_below_entry_by_2pct(self, engine_real_gate, mock_binance):
        """SL must be ≥ 2% below entry fill price."""
        decision = _make_decision(DecisionAction.ENTER_LONG, price="45000")
        sms = engine_real_gate.handle_decision(decision)
        cid = sms[0].spec.client_order_id

        mock_binance.place_order.reset_mock()
        engine_real_gate.handle_execution_report({
            "c": cid, "i": "EX-1", "X": "TRADE",
            "L": "45000", "l": "0.01", "n": "0",
            "q": "0.01", "z": "0.01",
        })

        # Second call is the SL order
        sl_spec = mock_binance.place_order.call_args_list[1][0][0]
        sl_price = sl_spec.stop_price
        assert sl_price is not None
        # SL ≤ 45000 * 0.98 = 44100
        assert sl_price <= Decimal("44100")

    def test_tp_fill_cancels_sl(self, engine_real_gate, mock_binance):
        """When TP fills, SL should be cancelled (OCO logic)."""
        decision = _make_decision(DecisionAction.ENTER_LONG)
        sms = engine_real_gate.handle_decision(decision)
        cid = sms[0].spec.client_order_id

        # Fill the entry
        mock_binance.place_order.return_value = "EX-BRACKET-INTEG"
        engine_real_gate.handle_execution_report({
            "c": cid, "i": "EX-1", "X": "TRADE",
            "L": "45000", "l": "0.01", "n": "0",
            "q": "0.01", "z": "0.01",
        })

        # Get the bracket record
        bracket = engine_real_gate._bracket_manager.get_bracket(cid)
        assert bracket is not None
        tp_cid = bracket.tp_client_id
        sl_cid = bracket.sl_client_id

        mock_binance.cancel_order.reset_mock()
        engine_real_gate.handle_execution_report({
            "c": tp_cid, "i": "EX-TP-1", "X": "TRADE",
            "L": "46350", "l": "0.01", "n": "0",
            "q": "0.01", "z": "0.01",
        })

        # SL should be cancelled
        mock_binance.cancel_order.assert_called_once_with(sl_cid)

    def test_risk_gate_rejects_over_limit_position(self, mock_binance):
        """Position > 1.0 BTC should be rejected by risk gate."""
        gate = _make_real_risk_gate()
        factory = OrderFactory(
            lot_size=Decimal("0.001"),
            tick_size=Decimal("0.10"),
        )
        eng = ExecutionEngine(
            risk_gate=gate,
            binance_client=mock_binance,
            order_factory=factory,
        )
        decision = _make_decision(
            DecisionAction.ENTER_LONG,
            qty="1.5",     # > MAX_POSITION_SIZE = 1.0
            price="45000",
        )
        sms = eng.handle_decision(decision)
        assert sms == []
        assert mock_binance.place_order.call_count == 0


# ---------------------------------------------------------------------------
# Timeout integration
# ---------------------------------------------------------------------------


class TestTimeoutIntegration:
    def test_timed_out_order_cancelled_on_watchdog(self, mock_binance):
        gate = _make_real_risk_gate()
        factory = OrderFactory(lot_size=Decimal("0.001"), tick_size=Decimal("0.10"))
        config = ExecutionEngineConfig(
            order_ttl_secs=0.001,  # 1ms
            bracket_config=BracketConfig(),
            use_testnet=True,
        )
        eng = ExecutionEngine(
            risk_gate=gate,
            binance_client=mock_binance,
            order_factory=factory,
            config=config,
        )
        decision = _make_decision(DecisionAction.ENTER_LONG)
        sms = eng.handle_decision(decision)

        import time
        time.sleep(0.05)

        mock_binance.cancel_order.reset_mock()
        cancelled = eng.check_order_timeouts()

        assert sms[0].spec.client_order_id in cancelled
        mock_binance.cancel_order.assert_called()


# ---------------------------------------------------------------------------
# clientOrderId deduplication integration
# ---------------------------------------------------------------------------


class TestDeduplicationIntegration:
    def test_duplicate_decision_same_cid(self, engine_real_gate, mock_binance):
        """Two identical decisions produce the same clientOrderId."""
        decision = _make_decision(DecisionAction.ENTER_LONG)
        engine_real_gate.handle_decision(decision)
        cid1 = mock_binance.place_order.call_args[0][0].client_order_id

        mock_binance.reset_mock()
        mock_binance.place_order.return_value = "EX-DUP-001"
        # New engine, same factory — should produce same CIDs
        gate2 = _make_real_risk_gate()
        factory2 = OrderFactory(lot_size=Decimal("0.001"), tick_size=Decimal("0.10"))
        eng2 = ExecutionEngine(
            risk_gate=gate2,
            binance_client=mock_binance,
            order_factory=factory2,
        )
        eng2.handle_decision(decision)
        cid2 = mock_binance.place_order.call_args[0][0].client_order_id

        assert cid1 == cid2
