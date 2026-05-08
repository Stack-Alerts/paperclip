"""
Tests — CapitalGovernor (Section F)
=====================================
Covers:
- Fixed-Notional capital model and configuration validation
- Per-position and total exposure caps
- Account heat computation and level transitions (GREEN/YELLOW/RED)
- Heat transition callbacks
- open_position, close_position, close_all_for_strategy
- adjusted_notional under each heat level
- can_open_position query
- Snapshot correctness
- update_base_capital
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.risk.capital_governor import (
    CapitalGovernor,
    CapitalGovernorConfig,
    CapitalGovernorError,
    HeatLevel,
    HEAT_YELLOW_THRESHOLD,
    HEAT_RED_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_governor(
    base_capital="25000",
    max_position_pct="0.10",
    max_exposure_pct="0.40",
    on_transition=None,
):
    config = CapitalGovernorConfig(
        base_capital=Decimal(base_capital),
        max_position_pct=Decimal(max_position_pct),
        max_exposure_pct=Decimal(max_exposure_pct),
    )
    return CapitalGovernor(config=config, on_heat_transition=on_transition)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestCapitalGovernorConfig:

    def test_defaults_are_valid(self):
        cfg = CapitalGovernorConfig()
        assert cfg.base_capital == Decimal("25000.00")
        assert cfg.max_position_pct == Decimal("0.10")
        assert cfg.max_exposure_pct == Decimal("0.40")

    def test_max_position_notional(self):
        cfg = CapitalGovernorConfig(
            base_capital=Decimal("20000"),
            max_position_pct=Decimal("0.10"),
            max_exposure_pct=Decimal("0.40"),
        )
        assert cfg.max_position_notional == Decimal("2000")

    def test_max_exposure_notional(self):
        cfg = CapitalGovernorConfig(
            base_capital=Decimal("25000"),
            max_position_pct=Decimal("0.10"),
            max_exposure_pct=Decimal("0.40"),
        )
        assert cfg.max_exposure_notional == Decimal("10000")

    def test_negative_capital_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            CapitalGovernorConfig(base_capital=Decimal("-1"))

    def test_invalid_position_pct_rejected(self):
        with pytest.raises(ValueError, match="max_position_pct"):
            CapitalGovernorConfig(
                base_capital=Decimal("25000"),
                max_position_pct=Decimal("1.5"),
                max_exposure_pct=Decimal("0.40"),
            )

    def test_invalid_exposure_pct_rejected(self):
        with pytest.raises(ValueError, match="max_exposure_pct"):
            CapitalGovernorConfig(
                base_capital=Decimal("25000"),
                max_position_pct=Decimal("0.10"),
                max_exposure_pct=Decimal("0"),
            )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestCapitalGovernorInitial:

    def test_initial_heat_is_green(self):
        g = make_governor()
        assert g.heat_level == HeatLevel.GREEN

    def test_initial_heat_pct_is_zero(self):
        g = make_governor()
        assert g.heat_pct == Decimal("0")

    def test_initial_open_exposure_is_zero(self):
        g = make_governor()
        assert g.open_exposure == Decimal("0")

    def test_can_open_position_initially(self):
        g = make_governor()
        assert g.can_open_position("s1", Decimal("1000")) is True


# ---------------------------------------------------------------------------
# open_position
# ---------------------------------------------------------------------------

class TestOpenPosition:

    def test_open_valid_position(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        # Max position = 2500; max exposure = 10000
        g.open_position("s1", Decimal("2000"))
        assert g.open_exposure == Decimal("2000")
        assert g.get_strategy_exposure("s1") == Decimal("2000")

    def test_open_position_exceeds_per_trade_cap(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        # Max position = 2500
        with pytest.raises(CapitalGovernorError, match="per-position cap"):
            g.open_position("s1", Decimal("3000"))

    def test_open_position_zero_rejected(self):
        g = make_governor()
        with pytest.raises(CapitalGovernorError, match="positive"):
            g.open_position("s1", Decimal("0"))

    def test_open_position_exceeds_total_exposure(self):
        # max_exposure = 10000; open two positions of 2500 each = 5000; third 6000 → breach
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        g.open_position("s1", Decimal("2500"))
        g.open_position("s2", Decimal("2500"))
        g.open_position("s3", Decimal("2500"))
        g.open_position("s4", Decimal("2500"))
        # Now exposure = 10000 (at limit); next should fail
        with pytest.raises(CapitalGovernorError):
            g.open_position("s5", Decimal("100"))

    def test_open_position_blocked_when_red(self):
        # max_exposure = 2500; open 2100 → heat = 84% → RED
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.10")
        # max_exposure = 2500; max_position = 2500
        g.open_position("s1", Decimal("2100"))
        assert g.heat_level == HeatLevel.RED
        with pytest.raises(CapitalGovernorError, match="RED"):
            g.open_position("s2", Decimal("100"))


# ---------------------------------------------------------------------------
# close_position
# ---------------------------------------------------------------------------

class TestClosePosition:

    def test_close_position_reduces_exposure(self):
        g = make_governor()
        g.open_position("s1", Decimal("1000"))
        g.close_position("s1", Decimal("500"))
        assert g.get_strategy_exposure("s1") == Decimal("500")
        assert g.open_exposure == Decimal("500")

    def test_close_more_than_open_clamped(self):
        g = make_governor()
        g.open_position("s1", Decimal("1000"))
        g.close_position("s1", Decimal("5000"))  # should clamp to 1000
        assert g.get_strategy_exposure("s1") == Decimal("0")

    def test_close_position_reduces_heat(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.10")
        # max_exposure = 2500
        g.open_position("s1", Decimal("2100"))  # → RED
        assert g.heat_level == HeatLevel.RED
        g.close_position("s1", Decimal("1000"))
        # exposure = 1100; heat = 44% → GREEN
        assert g.heat_level == HeatLevel.GREEN

    def test_close_all_for_strategy(self):
        g = make_governor()
        g.open_position("s1", Decimal("1000"))
        g.open_position("s1", Decimal("500"))
        released = g.close_all_for_strategy("s1")
        assert released == Decimal("1500")
        assert g.get_strategy_exposure("s1") == Decimal("0")


# ---------------------------------------------------------------------------
# Heat computation
# ---------------------------------------------------------------------------

class TestHeatComputation:

    def test_green_below_50_pct(self):
        # max_exposure = 10000; open 4999 → 49.99%
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        g.open_position("s1", Decimal("2499"))
        g.open_position("s2", Decimal("2499"))  # total 4998 < 5000 → GREEN
        assert g.heat_level == HeatLevel.GREEN

    def test_yellow_at_50_pct(self):
        g = make_governor(base_capital="10000", max_position_pct="0.60", max_exposure_pct="0.40")
        # max_exposure = 4000; max_position = 6000 (won't be limiting)
        g.open_position("s1", Decimal("2000"))  # 50% → YELLOW
        assert g.heat_level == HeatLevel.YELLOW

    def test_red_at_80_pct(self):
        g = make_governor(base_capital="10000", max_position_pct="0.90", max_exposure_pct="0.40")
        # max_exposure = 4000
        g.open_position("s1", Decimal("3200"))  # 80% → RED
        assert g.heat_level == HeatLevel.RED

    def test_heat_transition_callback_fires(self):
        transitions = []
        g = make_governor(
            base_capital="10000",
            max_position_pct="0.90",
            max_exposure_pct="0.40",
            on_transition=lambda old, new: transitions.append((old, new)),
        )
        # max_exposure = 4000
        g.open_position("s1", Decimal("2000"))  # GREEN → YELLOW
        g.open_position("s2", Decimal("1200"))  # YELLOW → RED (3200/4000 = 80%)
        assert len(transitions) == 2
        assert transitions[0] == (HeatLevel.GREEN, HeatLevel.YELLOW)
        assert transitions[1] == (HeatLevel.YELLOW, HeatLevel.RED)


# ---------------------------------------------------------------------------
# adjusted_notional
# ---------------------------------------------------------------------------

class TestAdjustedNotional:

    def test_green_returns_full_notional(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        adj = g.adjusted_notional(Decimal("1500"))
        assert adj == Decimal("1500")  # within cap of 2500

    def test_green_caps_at_per_position_limit(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        # max_position = 2500; request 5000
        adj = g.adjusted_notional(Decimal("5000"))
        assert adj == Decimal("2500")

    def test_yellow_halves_notional(self):
        g = make_governor(base_capital="10000", max_position_pct="0.90", max_exposure_pct="0.40")
        # max_exposure = 4000
        g.open_position("s1", Decimal("2000"))  # → YELLOW
        # Request 2000 → halved → 1000 (within per-position cap of 9000)
        adj = g.adjusted_notional(Decimal("2000"))
        assert adj == Decimal("1000")

    def test_red_returns_zero(self):
        g = make_governor(base_capital="10000", max_position_pct="0.90", max_exposure_pct="0.40")
        g.open_position("s1", Decimal("3200"))  # → RED
        adj = g.adjusted_notional(Decimal("1000"))
        assert adj == Decimal("0")


# ---------------------------------------------------------------------------
# update_base_capital
# ---------------------------------------------------------------------------

class TestUpdateBaseCapital:

    def test_update_increases_limits(self):
        g = make_governor(base_capital="10000", max_position_pct="0.10", max_exposure_pct="0.40")
        # max_position = 1000 initially; try to open 1500 → should fail
        with pytest.raises(CapitalGovernorError):
            g.open_position("s1", Decimal("1500"))

        g.update_base_capital(Decimal("20000"))  # max_position = 2000 now
        g.open_position("s1", Decimal("1500"))   # now OK
        assert g.open_exposure == Decimal("1500")

    def test_update_rejects_zero(self):
        g = make_governor()
        with pytest.raises(CapitalGovernorError, match="positive"):
            g.update_base_capital(Decimal("0"))


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:

    def test_snapshot_reflects_current_state(self):
        g = make_governor(base_capital="25000", max_position_pct="0.10", max_exposure_pct="0.40")
        g.open_position("s1", Decimal("1000"))
        snap = g.snapshot()
        assert snap.base_capital == Decimal("25000")
        assert snap.open_exposure == Decimal("1000")
        assert snap.heat_level == HeatLevel.GREEN
        assert "s1" in snap.per_strategy_exposure
        assert snap.per_strategy_exposure["s1"] == Decimal("1000")
