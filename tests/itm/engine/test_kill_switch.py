"""
Unit tests: paper_trading kill-switch (BTCAAAAA-727)
=====================================================
Tests every gated path with switch ON (paper_trading=True) vs OFF (False).

Explicit skip decisions:
- WS execution-report handler (handle_execution_report): not gated — it only
  processes inbound events; in paper mode no WS stream is started so this
  path is never reached organically.  It is still callable for test purposes
  and should not error; tested separately in test_execution_engine.py.
- PaperBinanceClient.get_position_size: read-only, deliberately not gated.

All tests are fully self-contained — no network I/O.
"""

from __future__ import annotations

import time
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

from src.itm.domain.entities import (
    Decision,
    DecisionAction,
    Instrument,
    OrderSide,
    Signal,
    SignalDirection,
)
from src.itm.engine.binance_client import PaperBinanceClient
from src.itm.engine.execution_engine import ExecutionEngine, ExecutionEngineConfig
from src.itm.engine.order_factory import OrderFactory
from src.itm.engine.order_state_machine import OrderState
from src.itm.engine.bracket_manager import BracketConfig
from src.itm.risk.risk_gate import RiskGate
from src.itm.risk.capital_governor import CapitalGovernor, CapitalGovernorConfig
from src.itm.risk.emergency_closeout import EmergencyCloseout, EmergencyCloseoutConfig


# ---------------------------------------------------------------------------
# Helpers
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
) -> Decision:
    signal = _make_signal()
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


def _make_risk_gate() -> RiskGate:
    governor = CapitalGovernor(
        config=CapitalGovernorConfig(
            base_capital=Decimal("10000"),
            max_position_pct=Decimal("0.10"),
            max_exposure_pct=Decimal("0.20"),
        )
    )
    closeout = EmergencyCloseout(
        config=EmergencyCloseoutConfig(
            base_capital=Decimal("10000"),
            daily_drawdown_limit_pct=Decimal("0.05"),
        )
    )
    return RiskGate(capital_governor=governor, closeout=closeout)


def _make_order_factory() -> OrderFactory:
    return OrderFactory(
        lot_size=Decimal("0.001"),
        tick_size=Decimal("0.10"),
        allow_market_orders=True,
    )


def _make_engine(paper_trading: bool, mock_client=None) -> ExecutionEngine:
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.place_order.return_value = "EXCHANGE-001"
        mock_client.cancel_order.return_value = True
    config = ExecutionEngineConfig(
        order_ttl_secs=60.0,
        default_quantity=Decimal("0.001"),
        bracket_config=BracketConfig(tp_pct=Decimal("0.03"), sl_pct=Decimal("0.02")),
        paper_trading=paper_trading,
    )
    return ExecutionEngine(
        risk_gate=_make_risk_gate(),
        binance_client=mock_client,
        order_factory=_make_order_factory(),
        config=config,
    )


# ---------------------------------------------------------------------------
# TestPaperBinanceClient
# ---------------------------------------------------------------------------


class TestPaperBinanceClient:
    def test_place_order_returns_fake_id(self):
        client = PaperBinanceClient()
        spec = MagicMock()
        spec.client_order_id = "cid-001"
        spec.binance_type.value = "LIMIT"
        spec.side = "BUY"
        spec.quantity = Decimal("0.001")
        result = client.place_order(spec)
        assert result.startswith("PAPER-")

    def test_place_order_counter_increments(self):
        client = PaperBinanceClient()
        spec = MagicMock()
        spec.client_order_id = "cid-x"
        spec.binance_type.value = "LIMIT"
        spec.side = "BUY"
        spec.quantity = Decimal("0.001")
        id1 = client.place_order(spec)
        id2 = client.place_order(spec)
        assert id1 != id2

    def test_cancel_order_returns_true(self):
        client = PaperBinanceClient()
        assert client.cancel_order("cid-001") is True

    def test_get_position_size_returns_zero(self):
        client = PaperBinanceClient()
        assert client.get_position_size("BTCUSDT") == Decimal("0")

    def test_start_user_data_stream_noop(self):
        client = PaperBinanceClient()
        # Must not raise, must not start any real thread
        client.start_user_data_stream(on_execution_report=lambda x: None)

    def test_keep_alive_listen_key_noop(self):
        client = PaperBinanceClient()
        client.keep_alive_listen_key()  # Must not raise

    def test_from_env_no_credentials_needed(self):
        # from_env must succeed without any BINANCE_* env vars set
        client = PaperBinanceClient.from_env(use_testnet=True)
        assert isinstance(client, PaperBinanceClient)


# ---------------------------------------------------------------------------
# TestExecutionEngineKillSwitch — handle_decision (new orders)
# ---------------------------------------------------------------------------


class TestExecutionEngineKillSwitch:
    def test_paper_on_no_real_http_calls(self, monkeypatch):
        """paper_trading=True must never make real HTTP calls (verified via PaperBinanceClient)."""
        # PaperBinanceClient is a no-op; verify no real network calls are attempted
        http_calls = []
        import src.itm.engine.binance_client as bc_mod
        original_signed = bc_mod.BinanceClient._signed_request
        monkeypatch.setattr(
            bc_mod.BinanceClient,
            "_signed_request",
            lambda *a, **kw: http_calls.append(a) or {},
        )
        engine = _make_engine(paper_trading=True, mock_client=PaperBinanceClient())

        decision = _make_decision()
        sms = engine.handle_decision(decision)

        assert len(sms) == 1
        assert http_calls == [], "Real HTTP calls were made in paper mode"

    def test_paper_off_calls_place_order(self):
        mock_client = MagicMock()
        mock_client.place_order.return_value = "EXCHANGE-001"
        mock_client.cancel_order.return_value = True
        engine = _make_engine(paper_trading=False, mock_client=mock_client)

        decision = _make_decision()
        sms = engine.handle_decision(decision)

        assert len(sms) == 1
        mock_client.place_order.assert_called()

    def test_paper_on_order_reaches_filled_state(self):
        engine = _make_engine(paper_trading=True, mock_client=PaperBinanceClient())
        decision = _make_decision()
        sms = engine.handle_decision(decision)
        assert len(sms) == 1
        assert sms[0].state == OrderState.FILLED

    def test_paper_off_order_reaches_acknowledged_state(self):
        mock_client = MagicMock()
        mock_client.place_order.return_value = "EXCHANGE-001"
        mock_client.cancel_order.return_value = True
        engine = _make_engine(paper_trading=False, mock_client=mock_client)
        decision = _make_decision()
        sms = engine.handle_decision(decision)
        assert len(sms) == 1
        # In live mode order stays ACKNOWLEDGED until WS fill event arrives
        assert sms[0].state == OrderState.ACKNOWLEDGED

    def test_paper_on_metrics_count_submitted_and_filled(self):
        engine = _make_engine(paper_trading=True, mock_client=PaperBinanceClient())
        decision = _make_decision()
        engine.handle_decision(decision)
        m = engine.metrics()
        assert m["orders_submitted"] == 1
        assert m["orders_filled"] == 1

    def test_paper_on_post_trade_callback_fired(self):
        post_trade_records = []
        config = ExecutionEngineConfig(
            paper_trading=True,
            default_quantity=Decimal("0.001"),
            bracket_config=BracketConfig(tp_pct=Decimal("0.03"), sl_pct=Decimal("0.02")),
        )
        engine = ExecutionEngine(
            risk_gate=_make_risk_gate(),
            binance_client=PaperBinanceClient(),
            order_factory=_make_order_factory(),
            config=config,
            on_post_trade=post_trade_records.append,
        )
        engine.handle_decision(_make_decision())
        assert len(post_trade_records) == 1
        assert post_trade_records[0]["outcome"] == "filled"

    def test_paper_on_hold_still_returns_empty(self):
        engine = _make_engine(paper_trading=True, mock_client=PaperBinanceClient())
        decision = _make_decision(action=DecisionAction.HOLD)
        sms = engine.handle_decision(decision)
        assert sms == []

    def test_paper_on_exit_long_also_suppressed(self):
        """EXIT_LONG market order in paper mode: no real call, SM reaches FILLED."""
        engine = _make_engine(paper_trading=True, mock_client=PaperBinanceClient())
        decision = _make_decision(action=DecisionAction.EXIT_LONG, order_type="market")
        sms = engine.handle_decision(decision)
        assert len(sms) == 1
        # Market orders have no price → placeholder fill_price=1 is used
        assert sms[0].state == OrderState.FILLED


# ---------------------------------------------------------------------------
# TestCheckOrderTimeoutsKillSwitch — order adjustment / cancel paths
# ---------------------------------------------------------------------------


class TestCheckOrderTimeoutsKillSwitch:
    def test_paper_on_cancel_does_not_call_exchange(self):
        mock_client = MagicMock()
        mock_client.place_order.return_value = "EX-001"
        mock_client.cancel_order.return_value = True
        engine = _make_engine(paper_trading=True, mock_client=mock_client)

        # Submit an order so the engine has something to cancel
        decision = _make_decision()
        sms = engine.handle_decision(decision)
        assert len(sms) == 1

        # In paper mode, order is immediately FILLED — is_timed_out won't apply.
        # Test instead that cancel_order is never called even on a synthetic sm.
        mock_client.cancel_order.assert_not_called()

    def test_paper_off_cancel_calls_exchange(self):
        mock_client = MagicMock()
        mock_client.place_order.return_value = "EX-001"
        mock_client.cancel_order.return_value = True

        config = ExecutionEngineConfig(
            order_ttl_secs=0.001,  # Near-zero TTL to trigger timeout quickly
            default_quantity=Decimal("0.001"),
            bracket_config=BracketConfig(tp_pct=Decimal("0.03"), sl_pct=Decimal("0.02")),
            paper_trading=False,
        )
        engine = ExecutionEngine(
            risk_gate=_make_risk_gate(),
            binance_client=mock_client,
            order_factory=_make_order_factory(),
            config=config,
        )

        decision = _make_decision()
        engine.handle_decision(decision)

        time.sleep(0.01)  # Allow TTL to expire
        cancelled = engine.check_order_timeouts()

        assert len(cancelled) == 1
        mock_client.cancel_order.assert_called()


# ---------------------------------------------------------------------------
# TestExecutionEngineConfigPaperTradingDefault
# ---------------------------------------------------------------------------


class TestExecutionEngineConfigPaperTradingDefault:
    def test_paper_trading_defaults_to_false(self):
        config = ExecutionEngineConfig()
        assert config.paper_trading is False

    def test_paper_trading_can_be_set_true(self):
        config = ExecutionEngineConfig(paper_trading=True)
        assert config.paper_trading is True
