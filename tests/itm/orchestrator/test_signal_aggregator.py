"""
Tests for SignalAggregator (Section D — signal_aggregator.py)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.itm.domain.entities import (
    ContractType,
    Decision,
    DecisionAction,
    Instrument,
    Signal,
    SignalDirection,
)
from src.itm.orchestrator.registry import StrategyRegistry
from src.itm.orchestrator.sb_contract import (
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
)
from src.itm.orchestrator.signal_aggregator import (
    AggregationMode,
    AggregationStats,
    SignalAggregator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BTC_USDT = Instrument.btc_usdt_spot()


def make_config(
    strategy_id="strat-001",
    capital_allocation_pct="0.5",
    signal_confidence_threshold="0.6",
):
    return StrategyConfig(
        strategy_id=strategy_id,
        name="Test",
        instrument=StrategyInstrumentConfig(
            symbol="BTC/USDT", exchange="binance", contract_type="spot"
        ),
        capital_allocation_pct=Decimal(capital_allocation_pct),
        risk=StrategyRiskConfig(
            max_drawdown_pct=Decimal("0.05"),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal("400.0"),
            max_leverage=Decimal("1.0"),
        ),
        signal_confidence_threshold=Decimal(signal_confidence_threshold),
        tags=(),
        metadata={},
    )


def make_signal(
    strategy_id="strat-001",
    direction=SignalDirection.LONG,
    strength="0.8",
    expiry=None,
):
    return Signal(
        direction=direction,
        strength=Decimal(strength),
        source_strategy=strategy_id,
        instrument=BTC_USDT,
        expiry=expiry,
    )


def setup_active_registry(strategy_id="strat-001"):
    reg = StrategyRegistry()
    config = make_config(strategy_id)
    reg.load(config)
    reg.activate(strategy_id)
    return reg, config


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestSignalAggregatorHappyPath:

    def test_long_signal_produces_enter_long_decision(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        signal = make_signal(direction=SignalDirection.LONG, strength="0.8")
        decision = agg.submit_signal(signal)
        assert decision is not None
        assert decision.action == DecisionAction.ENTER_LONG
        assert decision.confidence == Decimal("0.8")
        assert len(decision.contributing_signals) == 1

    def test_short_signal_produces_enter_short_decision(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        signal = make_signal(direction=SignalDirection.SHORT)
        decision = agg.submit_signal(signal)
        assert decision.action == DecisionAction.ENTER_SHORT

    def test_exit_signal_produces_exit_long_decision(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        signal = make_signal(direction=SignalDirection.EXIT)
        decision = agg.submit_signal(signal)
        assert decision.action == DecisionAction.EXIT_LONG

    def test_neutral_signal_produces_hold_decision(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        signal = make_signal(direction=SignalDirection.NEUTRAL)
        decision = agg.submit_signal(signal)
        assert decision.action == DecisionAction.HOLD

    def test_on_decision_callback_fired(self):
        reg, _ = setup_active_registry()
        received = []
        agg = SignalAggregator(registry=reg, on_decision=lambda d: received.append(d))
        signal = make_signal()
        agg.submit_signal(signal)
        assert len(received) == 1
        assert isinstance(received[0], Decision)

    def test_stats_tracking(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        agg.submit_signal(make_signal())  # accepted
        agg.submit_signal(make_signal(strength="0.3"))  # below threshold
        stats = agg.stats
        assert stats.signals_received == 2
        assert stats.decisions_produced == 1
        assert stats.signals_dropped_low_confidence == 1

    def test_signal_at_exact_threshold_is_accepted(self):
        reg, _ = setup_active_registry()  # threshold=0.6
        agg = SignalAggregator(registry=reg)
        signal = make_signal(strength="0.6")  # exactly at threshold
        decision = agg.submit_signal(signal)
        assert decision is not None

    def test_risk_gated_false_on_passthrough(self):
        """Passthrough mode: risk_gated should be False (gate applied by exec engine)."""
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        decision = agg.submit_signal(make_signal())
        assert decision.risk_gated is False

    def test_reset_stats(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        agg.submit_signal(make_signal())
        agg.reset_stats()
        assert agg.stats.signals_received == 0
        assert agg.stats.decisions_produced == 0


# ---------------------------------------------------------------------------
# Drop / filter tests
# ---------------------------------------------------------------------------

class TestSignalAggregatorDrops:

    def test_stale_signal_dropped(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        signal = make_signal(expiry=past)
        decision = agg.submit_signal(signal)
        assert decision is None
        assert agg.stats.signals_dropped_stale == 1

    def test_signal_below_threshold_dropped(self):
        reg, _ = setup_active_registry()
        agg = SignalAggregator(registry=reg)
        signal = make_signal(strength="0.4")  # below threshold of 0.6
        decision = agg.submit_signal(signal)
        assert decision is None
        assert agg.stats.signals_dropped_low_confidence == 1

    def test_signal_from_paused_strategy_dropped(self):
        reg, _ = setup_active_registry()
        reg.pause("strat-001")
        agg = SignalAggregator(registry=reg)
        decision = agg.submit_signal(make_signal())
        assert decision is None
        assert agg.stats.signals_dropped_inactive_strategy == 1

    def test_signal_from_stopped_strategy_dropped(self):
        reg, _ = setup_active_registry()
        reg.stop("strat-001")
        agg = SignalAggregator(registry=reg)
        decision = agg.submit_signal(make_signal())
        assert decision is None

    def test_signal_from_unregistered_strategy_dropped(self):
        reg = StrategyRegistry()  # empty
        agg = SignalAggregator(registry=reg)
        decision = agg.submit_signal(make_signal(strategy_id="ghost"))
        assert decision is None

    def test_signal_from_loading_state_dropped(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)  # LOADING — never activated
        agg = SignalAggregator(registry=reg)
        decision = agg.submit_signal(make_signal())
        assert decision is None

    def test_two_strategies_signals_independent(self):
        """Signal from inactive strategy dropped; active strategy's signal accepted."""
        reg = StrategyRegistry()
        c1 = make_config("s1", capital_allocation_pct="0.4")
        c2 = make_config("s2", capital_allocation_pct="0.4")
        reg.load(c1)
        reg.load(c2)
        reg.activate("s1")
        # s2 stays LOADING

        agg = SignalAggregator(registry=reg)
        d1 = agg.submit_signal(make_signal(strategy_id="s1"))
        d2 = agg.submit_signal(make_signal(strategy_id="s2"))

        assert d1 is not None  # s1 is ACTIVE
        assert d2 is None      # s2 is LOADING
