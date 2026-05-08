"""
Tests for StrategyRegistry (Section D — registry.py)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.itm.orchestrator.registry import (
    StrategyEntry,
    StrategyLifecycleState,
    StrategyRegistry,
    StrategyRegistryError,
)
from src.itm.orchestrator.sb_contract import (
    SBExportImporter,
    SB_EXPORT_VERSION,
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_config(
    strategy_id="strat-001",
    name="TestStrategy",
    capital_allocation_pct="0.5",
):
    instrument = StrategyInstrumentConfig(
        symbol="BTC/USDT", exchange="binance", contract_type="spot"
    )
    risk = StrategyRiskConfig(
        max_drawdown_pct=Decimal("0.05"),
        max_position_qty=Decimal("0.5"),
        heat_limit=Decimal("5.0"),
        max_daily_loss=Decimal("400.0"),
        max_leverage=Decimal("1.0"),
    )
    return StrategyConfig(
        strategy_id=strategy_id,
        name=name,
        instrument=instrument,
        capital_allocation_pct=Decimal(capital_allocation_pct),
        risk=risk,
        signal_confidence_threshold=Decimal("0.6"),
        tags=(),
        metadata={},
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestStrategyRegistryHappyPath:

    def test_load_single_strategy(self):
        reg = StrategyRegistry()
        config = make_config()
        entry = reg.load(config)
        assert entry.state == StrategyLifecycleState.LOADING
        assert entry.strategy_id == "strat-001"
        assert len(reg) == 1

    def test_activate_from_loading(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        entry = reg.activate(config.strategy_id)
        assert entry.state == StrategyLifecycleState.ACTIVE
        assert entry.is_active
        assert entry.activated_at is not None

    def test_pause_active_strategy(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        entry = reg.pause(config.strategy_id, reason="cooldown")
        assert entry.state == StrategyLifecycleState.PAUSED
        assert entry.pause_reason == "cooldown"
        assert entry.paused_at is not None

    def test_activate_from_paused(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        reg.pause(config.strategy_id)
        entry = reg.activate(config.strategy_id)
        assert entry.state == StrategyLifecycleState.ACTIVE

    def test_stop_active_strategy(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        entry = reg.stop(config.strategy_id, reason="end-of-day")
        assert entry.state == StrategyLifecycleState.STOPPED
        assert entry.is_stopped
        assert entry.stopped_at is not None

    def test_stop_paused_strategy(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        reg.pause(config.strategy_id)
        entry = reg.stop(config.strategy_id)
        assert entry.is_stopped

    def test_load_many(self):
        reg = StrategyRegistry()
        configs = [
            make_config("s1", capital_allocation_pct="0.3"),
            make_config("s2", capital_allocation_pct="0.3"),
        ]
        entries = reg.load_many(configs)
        assert len(entries) == 2
        assert reg.count() == 2

    def test_active_entries_filter(self):
        reg = StrategyRegistry()
        c1 = make_config("s1", capital_allocation_pct="0.3")
        c2 = make_config("s2", capital_allocation_pct="0.3")
        reg.load(c1)
        reg.load(c2)
        reg.activate("s1")
        # s2 stays in LOADING
        active = reg.active_entries()
        assert len(active) == 1
        assert active[0].strategy_id == "s1"

    def test_active_count(self):
        reg = StrategyRegistry()
        c1 = make_config("s1", capital_allocation_pct="0.3")
        c2 = make_config("s2", capital_allocation_pct="0.3")
        reg.load(c1)
        reg.load(c2)
        reg.activate("s1")
        reg.activate("s2")
        assert reg.active_count() == 2
        reg.pause("s1")
        assert reg.active_count() == 1

    def test_observer_callbacks_fired(self):
        activated = []
        paused = []
        stopped = []

        reg = StrategyRegistry(
            on_strategy_activated=lambda e: activated.append(e.strategy_id),
            on_strategy_paused=lambda e: paused.append(e.strategy_id),
            on_strategy_stopped=lambda e: stopped.append(e.strategy_id),
        )
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        reg.pause(config.strategy_id)
        reg.stop(config.strategy_id)

        assert activated == ["strat-001"]
        assert paused == ["strat-001"]
        assert stopped == ["strat-001"]

    def test_auto_pause(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        entry = reg.auto_pause(config.strategy_id, "drawdown exceeded")
        assert entry.state == StrategyLifecycleState.PAUSED
        assert "auto-pause" in entry.pause_reason

    def test_get_returns_none_for_unknown(self):
        reg = StrategyRegistry()
        assert reg.get("nonexistent") is None

    def test_iter_over_all_entries(self):
        reg = StrategyRegistry()
        c1 = make_config("s1", capital_allocation_pct="0.3")
        c2 = make_config("s2", capital_allocation_pct="0.4")
        reg.load(c1)
        reg.load(c2)
        ids = [e.strategy_id for e in reg]
        assert set(ids) == {"s1", "s2"}


# ---------------------------------------------------------------------------
# Error / constraint tests
# ---------------------------------------------------------------------------

class TestStrategyRegistryErrors:

    def test_load_duplicate_active_raises(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        with pytest.raises(StrategyRegistryError, match="already registered"):
            reg.load(config)

    def test_load_after_stop_succeeds(self):
        """Stopped strategies CAN be re-loaded (fresh start after terminal)."""
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.stop(config.strategy_id)
        # Should not raise
        entry = reg.load(config)
        assert entry.state == StrategyLifecycleState.LOADING

    def test_activate_stopped_raises(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.stop(config.strategy_id)
        with pytest.raises(StrategyRegistryError, match="Cannot activate stopped"):
            reg.activate(config.strategy_id)

    def test_pause_stopped_raises(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.stop(config.strategy_id)
        with pytest.raises(StrategyRegistryError, match="Cannot pause stopped"):
            reg.pause(config.strategy_id)

    def test_activate_unknown_raises(self):
        reg = StrategyRegistry()
        with pytest.raises(StrategyRegistryError, match="not registered"):
            reg.activate("ghost")

    def test_pause_unknown_raises(self):
        reg = StrategyRegistry()
        with pytest.raises(StrategyRegistryError, match="not registered"):
            reg.pause("ghost")

    def test_stop_unknown_raises(self):
        reg = StrategyRegistry()
        with pytest.raises(StrategyRegistryError, match="not registered"):
            reg.stop("ghost")

    def test_activate_already_active_is_idempotent(self):
        """Second activate on ACTIVE strategy should warn but not raise."""
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        entry = reg.activate(config.strategy_id)  # should not raise
        assert entry.is_active

    def test_pause_already_paused_is_idempotent(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.activate(config.strategy_id)
        reg.pause(config.strategy_id)
        entry = reg.pause(config.strategy_id)  # should not raise
        assert entry.is_paused

    def test_stop_already_stopped_is_idempotent(self):
        reg = StrategyRegistry()
        config = make_config()
        reg.load(config)
        reg.stop(config.strategy_id)
        entry = reg.stop(config.strategy_id)  # should not raise
        assert entry.is_stopped
