"""
Section D Integration Tests — MultiStrategyOrchestrator
=========================================================
Covers the acceptance criteria from BTCAAAAA-418:
- Two strategies run simultaneously without interference
- Strategy with excessive drawdown is auto-paused
- Signal from active strategy produces a Decision for execution engine
- SB-to-ITM import tested with a real SB export fixture
- All lifecycle events logged (tested via registry state checks)
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from src.itm.domain.entities import (
    Decision,
    Instrument,
    Signal,
    SignalDirection,
)
from src.itm.orchestrator import (
    CapitalAllocatorError,
    MultiStrategyOrchestrator,
    OrchestratorConfig,
    StrategyLifecycleState,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
)
from src.itm.orchestrator.sb_contract import SB_EXPORT_VERSION


# ---------------------------------------------------------------------------
# SB export fixture (realistic export from Strategy Builder)
# ---------------------------------------------------------------------------

REAL_SB_EXPORT = {
    "sb_export_version": SB_EXPORT_VERSION,
    "exported_at": "2026-05-08T09:00:00Z",
    "strategies": [
        {
            "id": "momentum-v1",
            "name": "BTC Momentum 15m",
            "instrument": {
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "contract_type": "perpetual",
            },
            "capital_allocation_pct": 0.4,
            "risk": {
                "max_drawdown_pct": 0.05,
                "max_position_qty": 0.5,
                "heat_limit": 5.0,
                "max_daily_loss": 400.0,
                "max_leverage": 1.0,
            },
            "signal_confidence_threshold": 0.65,
            "tags": ["momentum", "15m", "btc"],
            "metadata": {"author": "sb_user_01", "version": "1.0"},
        },
        {
            "id": "mean-reversion-v1",
            "name": "BTC Mean Reversion 1h",
            "instrument": {
                "symbol": "BTC/USDT",
                "exchange": "binance",
                "contract_type": "spot",
            },
            "capital_allocation_pct": 0.35,
            "risk": {
                "max_drawdown_pct": 0.07,
                "max_position_qty": 0.3,
                "heat_limit": 3.0,
                "max_daily_loss": 350.0,
                "max_leverage": 1.0,
            },
            "signal_confidence_threshold": 0.7,
            "tags": ["mean-reversion", "1h", "btc"],
            "metadata": {"author": "sb_user_02", "version": "2.0"},
        },
    ],
}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

BTC_USDT = Instrument.btc_usdt_spot()


def make_signal(strategy_id: str, direction=SignalDirection.LONG, strength="0.8"):
    return Signal(
        direction=direction,
        strength=Decimal(strength),
        source_strategy=strategy_id,
        instrument=BTC_USDT,
    )


def make_orchestrator(total_capital="50000", auto_activate=True, on_decision=None):
    config = OrchestratorConfig(
        total_capital=Decimal(total_capital),
        auto_activate_on_load=auto_activate,
    )
    return MultiStrategyOrchestrator(config=config, on_decision=on_decision)


# ---------------------------------------------------------------------------
# Test: SB export fixture import (acceptance criterion)
# ---------------------------------------------------------------------------

class TestSBExportFixtureImport:

    def test_import_real_sb_export_dict(self):
        """SB-to-ITM import with the real fixture passes validation."""
        orch = make_orchestrator()
        entries = orch.load_from_sb_dict(REAL_SB_EXPORT)
        assert len(entries) == 2

    def test_import_real_sb_export_json(self):
        """JSON-encoded SB export also imports cleanly."""
        json_str = json.dumps(REAL_SB_EXPORT)
        orch = make_orchestrator()
        entries = orch.load_from_sb_json(json_str)
        assert len(entries) == 2

    def test_imported_strategies_are_active(self):
        """auto_activate_on_load=True → strategies go ACTIVE immediately."""
        orch = make_orchestrator(auto_activate=True)
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        assert orch.active_strategy_count() == 2
        assert set(orch.active_strategy_ids()) == {"momentum-v1", "mean-reversion-v1"}

    def test_capital_slices_assigned_correctly(self):
        orch = make_orchestrator(total_capital="50000")
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        s1 = orch.capital.get_slice("momentum-v1")
        s2 = orch.capital.get_slice("mean-reversion-v1")
        assert s1.allocated_capital == Decimal("20000")   # 50000 * 0.4
        assert s2.allocated_capital == Decimal("17500")   # 50000 * 0.35

    def test_performance_monitor_registered_for_both(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        assert orch.get_strategy_metrics("momentum-v1") is not None
        assert orch.get_strategy_metrics("mean-reversion-v1") is not None


# ---------------------------------------------------------------------------
# Test: Two strategies run simultaneously without interference (AC)
# ---------------------------------------------------------------------------

class TestTwoStrategiesIndependence:

    def test_signals_from_two_strategies_independent(self):
        """Signals from two active strategies produce independent Decisions."""
        decisions = []
        orch = make_orchestrator(on_decision=lambda d: decisions.append(d))
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        sig1 = make_signal("momentum-v1", SignalDirection.LONG, "0.8")
        sig2 = make_signal("mean-reversion-v1", SignalDirection.SHORT, "0.75")

        d1 = orch.submit_signal(sig1)
        d2 = orch.submit_signal(sig2)

        assert d1 is not None
        assert d2 is not None
        assert d1.decision_id != d2.decision_id
        assert len(decisions) == 2

    def test_pausing_one_strategy_does_not_affect_other(self):
        """Pausing momentum-v1 doesn't stop mean-reversion-v1 signals."""
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        orch.pause_strategy("momentum-v1")

        # momentum signal should be dropped
        d1 = orch.submit_signal(make_signal("momentum-v1"))
        assert d1 is None

        # mean-reversion signal should be accepted
        d2 = orch.submit_signal(make_signal("mean-reversion-v1", strength="0.75"))
        assert d2 is not None

    def test_capital_use_is_isolated_per_strategy(self):
        """Recording capital use for s1 does not affect s2's available capital."""
        orch = make_orchestrator(total_capital="50000")
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        orch.record_capital_use("momentum-v1", Decimal("5000"))

        s1 = orch.capital.get_slice("momentum-v1")
        s2 = orch.capital.get_slice("mean-reversion-v1")

        assert s1.in_use == Decimal("5000")
        assert s2.in_use == Decimal("0")  # unaffected

    def test_pnl_tracking_isolated_per_strategy(self):
        """PnL recorded for s1 does not affect s2's metrics."""
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        orch.record_trade_pnl("momentum-v1", Decimal("200"), Decimal("10200"))

        m1 = orch.get_strategy_metrics("momentum-v1")
        m2 = orch.get_strategy_metrics("mean-reversion-v1")

        assert m1.realized_pnl == Decimal("200")
        assert m2.realized_pnl == Decimal("0")


# ---------------------------------------------------------------------------
# Test: Strategy with excessive drawdown is auto-paused (AC)
# ---------------------------------------------------------------------------

class TestAutoPauseOnDrawdown:

    def test_strategy_auto_paused_on_drawdown_breach(self):
        """Strategy should be auto-paused when drawdown >= threshold (5%)."""
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        # momentum-v1 has 5% drawdown threshold
        # Simulate: peak at 50000, then lose 3500 (7% drawdown)
        orch.record_trade_pnl("momentum-v1", Decimal("0"), Decimal("50000"))
        orch.record_trade_pnl("momentum-v1", Decimal("-3500"), Decimal("46500"))

        entry = orch.registry.get("momentum-v1")
        assert entry.is_paused, (
            f"Expected PAUSED after drawdown breach, got {entry.state.value}"
        )

    def test_other_strategy_stays_active_during_auto_pause(self):
        """mean-reversion-v1 stays ACTIVE when momentum-v1 is auto-paused."""
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        # Trigger drawdown auto-pause on momentum-v1
        orch.record_trade_pnl("momentum-v1", Decimal("0"), Decimal("50000"))
        orch.record_trade_pnl("momentum-v1", Decimal("-4000"), Decimal("46000"))

        entry_m = orch.registry.get("momentum-v1")
        entry_r = orch.registry.get("mean-reversion-v1")

        assert entry_m.is_paused
        assert entry_r.is_active

    def test_signal_from_auto_paused_strategy_dropped(self):
        """After auto-pause, signals from that strategy are dropped."""
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        # Trigger auto-pause
        orch.record_trade_pnl("momentum-v1", Decimal("0"), Decimal("50000"))
        orch.record_trade_pnl("momentum-v1", Decimal("-5000"), Decimal("45000"))

        # Signal from paused strategy should be dropped
        d = orch.submit_signal(make_signal("momentum-v1"))
        assert d is None


# ---------------------------------------------------------------------------
# Test: Signal from active strategy produces a Decision (AC)
# ---------------------------------------------------------------------------

class TestSignalToDecision:

    def test_signal_produces_decision(self):
        """Core acceptance criterion: active strategy signal → Decision."""
        decisions = []
        orch = make_orchestrator(on_decision=lambda d: decisions.append(d))
        orch.load_from_sb_dict(REAL_SB_EXPORT)

        sig = make_signal("momentum-v1", SignalDirection.LONG, "0.8")
        decision = orch.submit_signal(sig)

        assert decision is not None
        assert isinstance(decision, Decision)
        assert len(decisions) == 1

    def test_decision_instrument_matches_signal(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        sig = make_signal("momentum-v1")
        decision = orch.submit_signal(sig)
        assert decision.instrument == BTC_USDT


# ---------------------------------------------------------------------------
# Test: Pre-trade risk validation (institutional checklist)
# ---------------------------------------------------------------------------

class TestPreTradeValidation:

    def test_valid_order_passes_all_checks(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        allowed, reason = orch.validate_order("momentum-v1", Decimal("0.1"), Decimal("4000"))
        assert allowed is True
        assert reason is None

    def test_quantity_over_max_rejected(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        allowed, reason = orch.validate_order("momentum-v1", Decimal("1.5"), Decimal("1000"))
        assert allowed is False
        assert "MAX_POSITION_SIZE" in reason or "QUANTITY_TOO_LARGE" in reason

    def test_quantity_below_min_rejected(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        allowed, reason = orch.validate_order("momentum-v1", Decimal("0.0001"), Decimal("5"))
        assert allowed is False
        assert "MIN" in reason or "QUANTITY_TOO_SMALL" in reason

    def test_paused_strategy_rejected(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        orch.pause_strategy("momentum-v1")
        allowed, reason = orch.validate_order("momentum-v1", Decimal("0.1"), Decimal("4000"))
        assert allowed is False
        assert "not_active" in reason or "STRATEGY_NOT_ACTIVE" in reason

    def test_insufficient_capital_rejected(self):
        orch = make_orchestrator(total_capital="50000")
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        # momentum-v1 has 20000 allocated; request more than available
        allowed, reason = orch.validate_order(
            "momentum-v1", Decimal("0.5"), Decimal("25000")
        )
        assert allowed is False
        assert "capital" in reason.lower() or "INSUFFICIENT" in reason

    def test_leverage_over_one_rejected(self):
        orch = make_orchestrator()
        orch.load_from_sb_dict(REAL_SB_EXPORT)
        allowed, reason = orch.validate_order(
            "momentum-v1", Decimal("0.1"), Decimal("4000"), leverage=Decimal("2.0")
        )
        assert allowed is False
        assert "leverage" in reason.lower() or "LEVERAGE" in reason


# ---------------------------------------------------------------------------
# Test: Lifecycle logging (state checks as proxy for log events)
# ---------------------------------------------------------------------------

class TestLifecycleStateTransitions:

    def test_full_lifecycle_loading_active_paused_stopped(self):
        from src.itm.orchestrator.sb_contract import (
            StrategyConfig,
            StrategyInstrumentConfig,
            StrategyRiskConfig,
        )
        config = OrchestratorConfig(
            total_capital=Decimal("10000"),
            auto_activate_on_load=False,  # manual control
        )
        orch = MultiStrategyOrchestrator(config=config)

        sc = StrategyConfig(
            strategy_id="lifecycle-test",
            name="Lifecycle Test",
            instrument=StrategyInstrumentConfig(
                symbol="BTC/USDT", exchange="binance", contract_type="spot"
            ),
            capital_allocation_pct=Decimal("0.5"),
            risk=StrategyRiskConfig(
                max_drawdown_pct=Decimal("0.05"),
                max_position_qty=Decimal("0.5"),
                heat_limit=Decimal("5.0"),
                max_daily_loss=Decimal("400.0"),
                max_leverage=Decimal("1.0"),
            ),
            signal_confidence_threshold=Decimal("0.6"),
            tags=(),
            metadata={},
        )

        entry = orch.load_config(sc)
        assert entry.state == StrategyLifecycleState.LOADING

        orch.activate_strategy("lifecycle-test")
        assert orch.registry.get("lifecycle-test").is_active

        orch.pause_strategy("lifecycle-test", reason="test pause")
        assert orch.registry.get("lifecycle-test").is_paused

        orch.activate_strategy("lifecycle-test")
        assert orch.registry.get("lifecycle-test").is_active

        orch.stop_strategy("lifecycle-test")
        assert orch.registry.get("lifecycle-test").is_stopped
