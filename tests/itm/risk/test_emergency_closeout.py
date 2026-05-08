"""
Tests — EmergencyCloseout (Section F)
=======================================
Covers:
- record_trade_pnl: single-position loss trigger
- record_trade_pnl: daily drawdown trigger
- trigger_global_closeout: fires callback, idempotent
- Callbacks are invoked correctly
- Daily PnL resets (simulated by date)
- Config validation
- get_daily_pnl and get_events queries
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.risk.emergency_closeout import (
    EmergencyCloseout,
    EmergencyCloseoutConfig,
    CloseoutEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(
    base_capital="25000",
    daily_pct="0.05",
    position_pct="0.02",
):
    return EmergencyCloseoutConfig(
        base_capital=Decimal(base_capital),
        daily_drawdown_limit_pct=Decimal(daily_pct),
        position_loss_limit_pct=Decimal(position_pct),
    )


def make_closeout(base_capital="25000", on_strategy=None, on_global=None):
    cfg = make_config(base_capital=base_capital)
    return EmergencyCloseout(
        config=cfg,
        on_strategy_closeout=on_strategy,
        on_global_closeout=on_global,
    )


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestEmergencyCloseoutConfig:

    def test_defaults_valid(self):
        cfg = EmergencyCloseoutConfig(base_capital=Decimal("25000"))
        assert cfg.daily_drawdown_limit_pct == Decimal("0.05")
        assert cfg.position_loss_limit_pct == Decimal("0.02")
        assert cfg.daily_drawdown_limit_usdt == Decimal("1250")
        assert cfg.position_loss_limit_usdt == Decimal("500")

    def test_zero_base_capital_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            EmergencyCloseoutConfig(base_capital=Decimal("0"))

    def test_zero_daily_pct_rejected(self):
        with pytest.raises(ValueError, match="daily_drawdown_limit_pct"):
            EmergencyCloseoutConfig(
                base_capital=Decimal("25000"),
                daily_drawdown_limit_pct=Decimal("0"),
            )

    def test_zero_position_pct_rejected(self):
        with pytest.raises(ValueError, match="position_loss_limit_pct"):
            EmergencyCloseoutConfig(
                base_capital=Decimal("25000"),
                position_loss_limit_pct=Decimal("0"),
            )


# ---------------------------------------------------------------------------
# Single-position loss trigger
# ---------------------------------------------------------------------------

class TestSinglePositionLossTrigger:

    def test_position_loss_at_limit_triggers_closeout(self):
        # base_capital=25000, position_pct=0.02 → limit=500 USDT
        strategy_closeouts = []
        closeout = make_closeout(
            base_capital="25000",
            on_strategy=lambda sid, r: strategy_closeouts.append((sid, r)),
        )
        event = closeout.record_trade_pnl("s1", Decimal("-500"))
        assert event is not None
        assert event.strategy_id == "s1"
        assert len(strategy_closeouts) == 1
        assert strategy_closeouts[0][0] == "s1"

    def test_position_loss_below_limit_no_trigger(self):
        closeout = make_closeout(base_capital="25000")
        event = closeout.record_trade_pnl("s1", Decimal("-499"))
        assert event is None

    def test_position_loss_above_limit_triggers(self):
        strategy_closeouts = []
        closeout = make_closeout(
            base_capital="25000",
            on_strategy=lambda sid, r: strategy_closeouts.append(sid),
        )
        event = closeout.record_trade_pnl("s1", Decimal("-600"))
        assert event is not None
        assert len(strategy_closeouts) == 1

    def test_win_does_not_trigger_closeout(self):
        closeout = make_closeout(base_capital="25000")
        event = closeout.record_trade_pnl("s1", Decimal("1000"))
        assert event is None


# ---------------------------------------------------------------------------
# Daily drawdown trigger
# ---------------------------------------------------------------------------

class TestDailyDrawdownTrigger:

    def test_daily_drawdown_trigger(self):
        # base_capital=25000, daily_pct=0.05 → limit=1250 USDT
        strategy_closeouts = []
        closeout = make_closeout(
            base_capital="25000",
            on_strategy=lambda sid, r: strategy_closeouts.append(sid),
        )
        # Two losses that sum to the limit
        closeout.record_trade_pnl("s1", Decimal("-400"))
        closeout.record_trade_pnl("s1", Decimal("-400"))
        event = closeout.record_trade_pnl("s1", Decimal("-450"))  # total=1250 → trigger
        assert event is not None
        assert len(strategy_closeouts) == 1

    def test_daily_drawdown_below_limit_no_trigger(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-400"))
        closeout.record_trade_pnl("s1", Decimal("-400"))
        event = closeout.record_trade_pnl("s1", Decimal("-449"))  # total=1249 → no trigger
        assert event is None

    def test_get_daily_pnl(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-100"))
        closeout.record_trade_pnl("s1", Decimal("50"))
        assert closeout.get_daily_pnl("s1") == Decimal("-50")

    def test_daily_pnl_isolated_per_strategy(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-200"))
        closeout.record_trade_pnl("s2", Decimal("-300"))
        assert closeout.get_daily_pnl("s1") == Decimal("-200")
        assert closeout.get_daily_pnl("s2") == Decimal("-300")

    def test_reset_daily_pnl_single_strategy(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-200"))
        closeout.reset_daily_pnl("s1")
        assert closeout.get_daily_pnl("s1") == Decimal("0")

    def test_reset_daily_pnl_all_strategies(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-100"))
        closeout.record_trade_pnl("s2", Decimal("-200"))
        closeout.reset_daily_pnl()
        assert closeout.get_daily_pnl("s1") == Decimal("0")
        assert closeout.get_daily_pnl("s2") == Decimal("0")


# ---------------------------------------------------------------------------
# Global closeout
# ---------------------------------------------------------------------------

class TestGlobalCloseout:

    def test_global_closeout_fires_callback(self):
        global_calls = []
        closeout = make_closeout(
            on_global=lambda r: global_calls.append(r),
        )
        event = closeout.trigger_global_closeout("test: extreme event")
        assert event.is_global is True
        assert len(global_calls) == 1
        assert "extreme event" in global_calls[0]

    def test_global_closeout_is_idempotent(self):
        global_calls = []
        closeout = make_closeout(
            on_global=lambda r: global_calls.append(r),
        )
        e1 = closeout.trigger_global_closeout("first")
        e2 = closeout.trigger_global_closeout("second")  # idempotent
        assert len(global_calls) == 1
        assert e1.reason == e2.reason

    def test_global_closeout_blocks_further_strategy_triggers(self):
        strategy_calls = []
        closeout = make_closeout(
            base_capital="25000",
            on_strategy=lambda sid, r: strategy_calls.append(sid),
        )
        closeout.trigger_global_closeout("global emergency")
        # After global, per-strategy records are ignored
        event = closeout.record_trade_pnl("s1", Decimal("-10000"))
        assert event is None
        assert len(strategy_calls) == 0  # callback not fired

    def test_global_closeout_flag_reset(self):
        closeout = make_closeout()
        closeout.trigger_global_closeout("test")
        assert closeout.global_closeout_triggered is True
        closeout.reset_global_closeout()
        assert closeout.global_closeout_triggered is False


# ---------------------------------------------------------------------------
# get_events
# ---------------------------------------------------------------------------

class TestGetEvents:

    def test_no_events_initially(self):
        closeout = make_closeout()
        assert closeout.get_events() == []

    def test_events_recorded_on_trigger(self):
        closeout = make_closeout(base_capital="25000")
        closeout.record_trade_pnl("s1", Decimal("-600"))  # over position limit
        events = closeout.get_events()
        assert len(events) == 1
        assert isinstance(events[0], CloseoutEvent)
