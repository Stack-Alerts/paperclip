"""
Acceptance tests for FDR-850 / BTCAAAAA-850.

FDR: System MUST auto-pause an ACTIVE strategy when drawdown or daily loss
     exceeds configured thresholds under performance monitoring.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-850
Component: src/itm/orchestrator/performance_monitor.py

Each test in this module maps to exactly one acceptance criterion stated in the FDR.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.itm.orchestrator.performance_monitor import PerformanceMonitor
from src.itm.orchestrator.registry import StrategyRegistry
from src.itm.orchestrator.sb_contract import (
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
)

# Module-level markers bind every test here to FDR-850 and the acceptance suite.
pytestmark = [
    pytest.mark.fr("FDR-850"),
    pytest.mark.acceptance,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    strategy_id: str = "strat-850",
    max_drawdown_pct: str = "0.05",
    max_daily_loss: str = "500.0",
) -> StrategyConfig:
    return StrategyConfig(
        strategy_id=strategy_id,
        name="FDR-850 test strategy",
        instrument=StrategyInstrumentConfig(
            symbol="BTC/USDT", exchange="binance", contract_type="spot"
        ),
        capital_allocation_pct=Decimal("0.5"),
        risk=StrategyRiskConfig(
            max_drawdown_pct=Decimal(max_drawdown_pct),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal(max_daily_loss),
            max_leverage=Decimal("1.0"),
        ),
        signal_confidence_threshold=Decimal("0.6"),
        tags=(),
        metadata={},
    )


def _setup(config: StrategyConfig | None = None):
    config = config or _make_config()
    reg = StrategyRegistry()
    reg.load(config)
    reg.activate(config.strategy_id)
    monitor = PerformanceMonitor(registry=reg)
    monitor.register(config)
    return monitor, reg, config


# ---------------------------------------------------------------------------
# AC-1: auto-pause triggers when drawdown >= configured threshold
# ---------------------------------------------------------------------------

def test_ac1_auto_pause_on_drawdown_breach():
    """
    AC-1: An ACTIVE strategy that breaches its max_drawdown_pct threshold
    must transition to PAUSED with a reason that names 'drawdown'.
    """
    config = _make_config(max_drawdown_pct="0.05")  # 5% threshold
    monitor, reg, _ = _setup(config)

    monitor.record_pnl("strat-850", Decimal("0"), Decimal("10000"))       # set peak
    monitor.record_pnl("strat-850", Decimal("-1500"), Decimal("8500"))    # ~15% drawdown

    entry = reg.get("strat-850")
    assert entry.is_paused, (
        "Strategy must be PAUSED after drawdown exceeds 5% threshold "
        "(got is_paused=False — FDR-850 AC-1 violation)"
    )
    assert "drawdown" in entry.pause_reason.lower(), (
        f"pause_reason must mention 'drawdown'; got: {entry.pause_reason!r}"
    )


# ---------------------------------------------------------------------------
# AC-2: auto-pause triggers when daily loss >= configured threshold
# ---------------------------------------------------------------------------

def test_ac2_auto_pause_on_daily_loss_breach():
    """
    AC-2: An ACTIVE strategy that breaches its max_daily_loss threshold
    must transition to PAUSED with a reason that names 'daily_loss'.
    """
    config = _make_config(max_daily_loss="200.0")
    monitor, reg, _ = _setup(config)

    monitor.record_pnl("strat-850", Decimal("-250"), Decimal("9750"))  # $250 loss > $200 limit

    entry = reg.get("strat-850")
    assert entry.is_paused, (
        "Strategy must be PAUSED after daily loss exceeds $200 limit "
        "(got is_paused=False — FDR-850 AC-2 violation)"
    )
    assert "daily_loss" in entry.pause_reason.lower(), (
        f"pause_reason must mention 'daily_loss'; got: {entry.pause_reason!r}"
    )


# ---------------------------------------------------------------------------
# AC-3: no auto-pause when thresholds are not breached
# ---------------------------------------------------------------------------

def test_ac3_no_auto_pause_below_threshold():
    """
    AC-3: A strategy that stays within both thresholds must NOT be auto-paused.
    """
    config = _make_config(max_drawdown_pct="0.10", max_daily_loss="500.0")
    monitor, reg, _ = _setup(config)

    monitor.record_pnl("strat-850", Decimal("-20"), Decimal("9980"))  # well within limits

    entry = reg.get("strat-850")
    assert not entry.is_paused, (
        "Strategy must NOT be paused when within both thresholds "
        "(FDR-850 AC-3 violation)"
    )
