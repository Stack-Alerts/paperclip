"""
Unit tests: ExecutionEngine (Section G)
=========================================
Tests the full execution engine: risk gate integration, order submission,
WebSocket execution report processing, timeout watchdog, clientOrderId
deduplication, and post-trade reporting.

All exchange calls are mocked — no real network I/O.
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

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
from src.itm.risk.risk_gate import RiskDecision, RiskGate
from src.itm.risk.capital_governor import CapitalGovernor
from src.itm.risk.emergency_closeout import EmergencyCloseout


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_instrument() -> Instrument:
    return Instrument.btc_usdt_perp()


def _make_signal(strategy_id: str = "strat-1", signal_id: str = "sig-001") -> Signal:
    return Signal(
        direction=SignalDirection.LONG,
        strength=Decimal("0.8"),
        source_strategy=strategy_id,
        instrument=_make_instrument(),
    )


def _make_decision(
    action: DecisionAction = DecisionAction.ENTER_LONG,
    quantity: str = "0.01",
    entry_price: str = "45000",
    order_type: str = "limit",
    strategy_id: str = "strat-1",
) -> Decision:
    signal = _make_signal(strategy_id=strategy_id)
    return Decision(
        action=action,
        confidence=Decimal("0.8"),
        contributing_signals=(signal,),
        risk_gated=False,
        instrument=_make_instrument(),
        metadata={
            "quantity": quantity,
            "entry_price": entry_price,
            "order_type": order_type,
        },
    )


@pytest.fixture
def mock_binance_client():
    client = MagicMock()
    client.place_order.return_value = "EXCHANGE-ID-001"
    client.cancel_order.return_value = True
    return client


@pytest.fixture
def mock_risk_gate():
    gate = MagicMock()
    gate.approve.return_value = RiskDecision(
        approved=True,
        adjusted_quantity=Decimal("0.01"),
        stop_loss_price=Decimal("44100"),
        reason="approved",
    )
    return gate


@pytest.fixture
def factory():
    return OrderFactory(
        lot_size=Decimal("0.001"),
        tick_size=Decimal("0.10"),
        allow_market_orders=True,
    )


@pytest.fixture
def config():
    return ExecutionEngineConfig(
        order_ttl_secs=60.0,
        default_quantity=Decimal("0.01"),
        daily_loss_limit_usd=Decimal("500"),
        bracket_config=BracketConfig(
            tp_pct=Decimal("0.03"),
            sl_pct=Decimal("0.02"),
        ),
        use_testnet=True,
    )


@pytest.fixture
def engine(mock_risk_gate, mock_binance_client, factory, config):
    return ExecutionEngine(
        risk_gate=mock_risk_gate,
        binance_client=mock_binance_client,
        order_factory=factory,
        config=config,
    )


# ---------------------------------------------------------------------------
# handle_decision — basic cases
# ---------------------------------------------------------------------------


class TestHandleDecisionBasic:
    def test_enter_long_submits_limit_order(self, engine, mock_binance_client):
        decision = _make_decision(
            action=DecisionAction.ENTER_LONG,
            quantity="0.01",
            entry_price="45000",
        )
        sms = engine.handle_decision(decision)

        assert len(sms) == 1
        assert sms[0].state == OrderState.ACKNOWLEDGED
        assert mock_binance_client.place_order.called

    def test_hold_returns_empty_list(self, engine):
        decision = _make_decision(action=DecisionAction.HOLD)
        sms = engine.handle_decision(decision)
        assert sms == []

    def test_pre_rejected_returns_empty_list(self, engine):
        decision = _make_decision(action=DecisionAction.REJECT)
        sms = engine.handle_decision(decision)
        assert sms == []

    def test_missing_entry_price_returns_empty(self, engine):
        decision = Decision(
            action=DecisionAction.ENTER_LONG,
            confidence=Decimal("0.8"),
            contributing_signals=(_make_signal(),),
            risk_gated=False,
            instrument=_make_instrument(),
            metadata={"quantity": "0.01"},  # no entry_price
        )
        sms = engine.handle_decision(decision)
        assert sms == []


# ---------------------------------------------------------------------------
# Risk gate integration
# ---------------------------------------------------------------------------


class TestRiskGateIntegration:
    def test_risk_gate_called_for_entry(self, engine, mock_risk_gate):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        engine.handle_decision(decision)
        assert mock_risk_gate.approve.called

    def test_risk_gate_rejection_stops_submission(
        self, engine, mock_risk_gate, mock_binance_client
    ):
        mock_risk_gate.approve.return_value = RiskDecision(
            approved=False,
            adjusted_quantity=Decimal("0"),
            stop_loss_price=Decimal("44100"),
            reason="daily_loss_limit_reached",
            rejection_code=None,
        )
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = engine.handle_decision(decision)

        assert sms == []
        assert mock_binance_client.place_order.call_count == 0

    def test_risk_gate_increments_rejection_counter(self, engine, mock_risk_gate):
        from src.itm.risk.risk_gate import RejectionCode
        mock_risk_gate.approve.return_value = RiskDecision(
            approved=False,
            adjusted_quantity=Decimal("0"),
            stop_loss_price=Decimal("44100"),
            reason="test rejection",
            rejection_code=RejectionCode.DAILY_LOSS_LIMIT,
        )
        engine.handle_decision(_make_decision(action=DecisionAction.ENTER_LONG))
        engine.handle_decision(_make_decision(action=DecisionAction.ENTER_LONG))
        assert engine.metrics()["risk_rejections"] == 2

    def test_risk_gate_not_called_for_exit(self, engine, mock_risk_gate):
        """Exit orders bypass the risk gate."""
        decision = _make_decision(
            action=DecisionAction.EXIT_LONG,
            entry_price="46000",
        )
        engine.handle_decision(decision)
        assert not mock_risk_gate.approve.called

    def test_risk_gate_adjusted_quantity_used(
        self, engine, mock_risk_gate, mock_binance_client
    ):
        mock_risk_gate.approve.return_value = RiskDecision(
            approved=True,
            adjusted_quantity=Decimal("0.005"),  # reduced by heat
            stop_loss_price=Decimal("44100"),
            reason="approved with heat reduction",
        )
        decision = _make_decision(action=DecisionAction.ENTER_LONG, quantity="0.01")
        engine.handle_decision(decision)

        # The submitted spec should use 0.005, not 0.01
        submitted_spec = mock_binance_client.place_order.call_args[0][0]
        assert submitted_spec.quantity == Decimal("0.005")


# ---------------------------------------------------------------------------
# Order type dispatch
# ---------------------------------------------------------------------------


class TestOrderTypeDispatch:
    def test_twap_submits_multiple_slices(
        self, mock_risk_gate, mock_binance_client, factory, config
    ):
        cfg = ExecutionEngineConfig(
            twap_num_slices=3,
            bracket_config=BracketConfig(),
            use_testnet=True,
        )
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=cfg,
        )
        decision = _make_decision(
            order_type="twap",
            quantity="0.3",
            entry_price="45000",
        )
        mock_binance_client.place_order.return_value = "EX-TWAP-001"
        sms = eng.handle_decision(decision)
        assert len(sms) == 3

    def test_dca_submits_multiple_legs(
        self, mock_risk_gate, mock_binance_client, factory
    ):
        cfg = ExecutionEngineConfig(
            dca_num_legs=4,
            bracket_config=BracketConfig(),
            use_testnet=True,
        )
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=cfg,
        )
        decision = _make_decision(
            order_type="dca",
            quantity="0.4",
            entry_price="45000",
        )
        sms = eng.handle_decision(decision)
        assert len(sms) == 4

    def test_market_order_uses_market_type(
        self, mock_risk_gate, mock_binance_client, factory, config
    ):
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=config,
        )
        decision = _make_decision(
            action=DecisionAction.EXIT_LONG,
            order_type="market",
            entry_price="46000",
            quantity="0.01",
        )
        sms = eng.handle_decision(decision)
        assert len(sms) == 1
        submitted = mock_binance_client.place_order.call_args[0][0]
        from src.itm.engine.order_factory import BinanceOrderType
        assert submitted.binance_type == BinanceOrderType.MARKET


# ---------------------------------------------------------------------------
# clientOrderId deduplication
# ---------------------------------------------------------------------------


class TestClientOrderIdDeduplication:
    def test_same_signal_same_cid(self, factory):
        from src.itm.engine.order_factory import derive_client_order_id
        cid1 = derive_client_order_id("strat-1", "sig-001", 0)
        cid2 = derive_client_order_id("strat-1", "sig-001", 0)
        assert cid1 == cid2

    def test_replaying_decision_produces_same_cid(
        self, engine, mock_binance_client, mock_risk_gate
    ):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        engine.handle_decision(decision)
        first_cid = mock_binance_client.place_order.call_args[0][0].client_order_id

        # Simulate replaying the same decision
        mock_binance_client.reset_mock()
        mock_binance_client.place_order.return_value = "EX-ID-002"
        # Create new engine to clear state (same factory → same CIDs)
        engine2 = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=engine._factory,
            config=engine._config,
        )
        engine2.handle_decision(decision)
        second_cid = mock_binance_client.place_order.call_args[0][0].client_order_id

        assert first_cid == second_cid


# ---------------------------------------------------------------------------
# handle_execution_report — WebSocket events
# ---------------------------------------------------------------------------


class TestHandleExecutionReport:
    def test_new_event_acknowledges_order(self, engine, mock_binance_client):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = engine.handle_decision(decision)
        sm = sms[0]
        # Already acknowledged by place_order flow; simulate a second ACK via WS
        # In real flow the WS ACK is the primary ack — but we test the report handler
        # directly by creating a new SM
        cid = sm.spec.client_order_id
        # State already ACKNOWLEDGED; simulate fill via WS
        report = {
            "c": cid,
            "i": "EX-WS-001",
            "X": "TRADE",
            "L": "45001",
            "l": "0.01",
            "n": "0.001",
            "q": "0.01",
            "z": "0.01",  # cumulative filled qty == order qty → FILLED
        }
        engine.handle_execution_report(report)
        assert sm.state == OrderState.FILLED

    def test_cancelled_event_transitions_to_cancelled(self, engine):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = engine.handle_decision(decision)
        sm = sms[0]
        cid = sm.spec.client_order_id

        report = {"c": cid, "i": "EX-WS-001", "X": "CANCELED"}
        engine.handle_execution_report(report)
        assert sm.state == OrderState.CANCELLED

    def test_rejected_event_transitions_to_rejected(self, engine):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = engine.handle_decision(decision)
        sm = sms[0]
        cid = sm.spec.client_order_id

        report = {"c": cid, "i": "EX-WS-001", "X": "REJECTED", "r": "insufficient_margin"}
        engine.handle_execution_report(report)
        assert sm.state == OrderState.REJECTED

    def test_partial_fill_then_final_fill(self, engine, mock_binance_client):
        decision = _make_decision(action=DecisionAction.ENTER_LONG, quantity="0.1")
        sms = engine.handle_decision(decision)
        sm = sms[0]
        cid = sm.spec.client_order_id

        # Partial fill (50%)
        engine.handle_execution_report({
            "c": cid, "i": "EX-WS-001", "X": "PARTIALLY_FILLED",
            "L": "45000", "l": "0.05", "n": "0.001",
            "q": "0.1", "z": "0.05",  # 50% filled
        })
        assert sm.state == OrderState.PARTIALLY_FILLED
        assert sm.filled_quantity == Decimal("0.05")

        # Final fill (remaining 50%)
        engine.handle_execution_report({
            "c": cid, "i": "EX-WS-001", "X": "TRADE",
            "L": "45001", "l": "0.05", "n": "0.001",
            "q": "0.1", "z": "0.1",  # 100% filled
        })
        assert sm.state == OrderState.FILLED

    def test_unknown_client_id_does_not_raise(self, engine):
        report = {"c": "UNKNOWN-CID", "i": "EX-UNKNOWN", "X": "NEW"}
        # Should not raise
        engine.handle_execution_report(report)


# ---------------------------------------------------------------------------
# Timeout watchdog
# ---------------------------------------------------------------------------


class TestTimeoutWatchdog:
    def test_timeout_order_cancelled(
        self, mock_risk_gate, mock_binance_client, factory
    ):
        config = ExecutionEngineConfig(
            order_ttl_secs=0.001,  # 1ms TTL
            bracket_config=BracketConfig(),
            use_testnet=True,
        )
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=config,
        )
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = eng.handle_decision(decision)
        sm = sms[0]

        import time
        time.sleep(0.05)  # wait past 1ms TTL

        mock_binance_client.cancel_order.reset_mock()
        cancelled = eng.check_order_timeouts()

        assert sm.spec.client_order_id in cancelled
        mock_binance_client.cancel_order.assert_called_once_with(
            sm.spec.client_order_id
        )

    def test_no_timeout_within_ttl(self, engine):
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        engine.handle_decision(decision)
        cancelled = engine.check_order_timeouts()
        assert cancelled == []


# ---------------------------------------------------------------------------
# Post-trade reporting
# ---------------------------------------------------------------------------


class TestPostTradeReporting:
    def test_post_trade_callback_called_on_fill(
        self, mock_risk_gate, mock_binance_client, factory, config
    ):
        records = []
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=config,
            on_post_trade=records.append,
        )
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = eng.handle_decision(decision)
        cid = sms[0].spec.client_order_id

        eng.handle_execution_report({
            "c": cid, "i": "EX-1", "X": "TRADE",
            "L": "45000", "l": "0.01", "n": "0",
            "q": "0.01", "z": "0.01",
        })

        assert len(records) == 1
        record = records[0]
        assert record["outcome"] == "filled"
        assert record["client_order_id"] == cid
        assert record["event"] == "post_trade"

    def test_post_trade_callback_called_on_cancel(
        self, mock_risk_gate, mock_binance_client, factory, config
    ):
        records = []
        eng = ExecutionEngine(
            risk_gate=mock_risk_gate,
            binance_client=mock_binance_client,
            order_factory=factory,
            config=config,
            on_post_trade=records.append,
        )
        decision = _make_decision(action=DecisionAction.ENTER_LONG)
        sms = eng.handle_decision(decision)
        cid = sms[0].spec.client_order_id

        eng.handle_execution_report({"c": cid, "i": "EX-1", "X": "CANCELED"})

        assert len(records) == 1
        assert records[0]["outcome"] == "cancelled"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_metrics_counts_submitted(self, engine):
        engine.handle_decision(_make_decision(action=DecisionAction.ENTER_LONG))
        m = engine.metrics()
        assert m["orders_submitted"] == 1

    def test_metrics_counts_risk_rejections(self, engine, mock_risk_gate):
        from src.itm.risk.risk_gate import RejectionCode
        mock_risk_gate.approve.return_value = RiskDecision(
            approved=False,
            adjusted_quantity=Decimal("0"),
            stop_loss_price=Decimal("44100"),
            reason="rejected",
            rejection_code=RejectionCode.DAILY_LOSS_LIMIT,
        )
        engine.handle_decision(_make_decision(action=DecisionAction.ENTER_LONG))
        assert engine.metrics()["risk_rejections"] == 1
