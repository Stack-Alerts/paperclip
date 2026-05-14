"""Unit tests for budget-threshold switching logic in provider_monitor."""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
SCRIPTS_DIR = os.path.abspath(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)
spec = importlib.util.spec_from_file_location(
    "provider_monitor", os.path.join(SCRIPTS_DIR, "provider_monitor.py")
)
pm = importlib.util.module_from_spec(spec)
sys.modules["provider_monitor"] = pm
spec.loader.exec_module(pm)


def _make_snapshot(**overrides) -> pm.UsageSnapshot:
    defaults = {
        "deepseek_balance_usd": 100.0,
        "deepseek_pct_remaining": 80.0,
        "openrouter_total": 100.0,
        "openrouter_used": 20.0,
        "openrouter_remaining": 80.0,
        "openrouter_pct_remaining": 80.0,
        "claude_4hr_pct": 10.0,
        "claude_7day_pct": 20.0,
        "claude_available": True,
        "month_spend_cents": 1000,
        "month_budget_cents": 5000,
        "budget_pct": 20.0,
    }
    defaults.update(overrides)
    return pm.UsageSnapshot(**defaults)


def _make_state(**overrides) -> pm.MonitorState:
    defaults = {
        "current_provider_state": "normal",
        "pro_model": pm.PRO_MODEL_NORMAL,
        "standard_model": pm.STANDARD_MODEL_NORMAL,
    }
    defaults.update(overrides)
    return pm.MonitorState(**defaults)


class TestBudgetB1Alert:
    def test_b1_triggers_alert_only(self):
        snap = _make_snapshot(budget_pct=85.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "alert_budget"
        assert decision.alert_only is True
        assert "80%" in decision.reason

    def test_b1_alert_not_resent(self):
        snap = _make_snapshot(budget_pct=85.0)
        state = _make_state(budget_alert_sent=True)
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"

    def test_b1_below_threshold_no_alert(self):
        snap = _make_snapshot(budget_pct=75.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action != "alert_budget"

    def test_b1_clears_alert_flag_when_below(self):
        snap = _make_snapshot(budget_pct=60.0)
        state = _make_state(budget_alert_sent=True)
        decision = pm.evaluate_triggers(snap, state)
        assert state.budget_alert_sent is False
        assert decision.action == "noop"


class TestBudgetB2Degrade:
    def test_b2_degrades_standard_tier(self):
        snap = _make_snapshot(budget_pct=92.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_budget_b2"
        assert decision.pro_model == pm.PRO_MODEL_NORMAL
        assert decision.standard_model == pm.STANDARD_MODEL_DEGRADED

    def test_b2_noop_when_already_b3(self):
        snap = _make_snapshot(budget_pct=92.0)
        state = _make_state(budget_degraded_level="b3")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"

    def test_b2_noop_when_already_b2(self):
        snap = _make_snapshot(budget_pct=92.0)
        state = _make_state(budget_degraded_level="b2")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"

    def test_b2_skips_when_claude_degraded(self):
        snap = _make_snapshot(budget_pct=92.0, claude_4hr_pct=97.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_c1"


class TestBudgetB3Degrade:
    def test_b3_degrades_all_tiers(self):
        snap = _make_snapshot(budget_pct=97.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_budget_b3"
        assert decision.pro_model == pm.STANDARD_MODEL_DEGRADED
        assert decision.standard_model == pm.STANDARD_MODEL_DEGRADED

    def test_b3_noop_when_already_b3(self):
        snap = _make_snapshot(budget_pct=97.0)
        state = _make_state(budget_degraded_level="b3")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"

    def test_b3_blocks_when_already_b2(self):
        snap = _make_snapshot(budget_pct=97.0)
        state = _make_state(budget_degraded_level="b2")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"


class TestBudgetRecovery:
    def test_recovery_when_below_threshold(self):
        snap = _make_snapshot(budget_pct=50.0)
        state = _make_state(budget_degraded_level="b3")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "upgrade_budget"
        assert decision.pro_model == pm.PRO_MODEL_NORMAL
        assert decision.standard_model == pm.STANDARD_MODEL_NORMAL

    def test_recovery_not_triggered_above_threshold(self):
        snap = _make_snapshot(budget_pct=85.0)
        state = _make_state(budget_degraded_level="b2")
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"


class TestBudgetHysteresis:
    def test_b3_degrade_blocked_by_cooldown(self):
        snap = _make_snapshot(budget_pct=97.0)
        now = datetime.now(timezone.utc).isoformat()
        state = _make_state(
            last_switch_direction="budget_degrade",
            last_budget_switch_at=now,
        )
        decision = pm.evaluate_triggers(snap, state)
        assert decision.blocked_by_hysteresis is True

    def test_b2_degrade_blocked_by_cooldown(self):
        snap = _make_snapshot(budget_pct=92.0)
        now = datetime.now(timezone.utc).isoformat()
        state = _make_state(
            last_switch_direction="budget_degrade",
            last_budget_switch_at=now,
        )
        decision = pm.evaluate_triggers(snap, state)
        assert decision.blocked_by_hysteresis is True

    def test_budget_upgrade_blocked_by_cooldown(self):
        snap = _make_snapshot(budget_pct=50.0)
        now = datetime.now(timezone.utc).isoformat()
        state = _make_state(
            budget_degraded_level="b3",
            last_switch_direction="budget_upgrade",
            last_budget_switch_at=now,
        )
        decision = pm.evaluate_triggers(snap, state)
        assert decision.blocked_by_hysteresis is True


class TestClaudePrioOverBudget:
    def test_c1_wins_over_b3(self):
        snap = _make_snapshot(budget_pct=97.0, claude_4hr_pct=97.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_c1"

    def test_c2_wins_over_b2(self):
        snap = _make_snapshot(budget_pct=92.0, claude_7day_pct=97.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_c2"

    def test_c1c2_wins_over_b3(self):
        snap = _make_snapshot(
            budget_pct=97.0, claude_4hr_pct=97.0, claude_7day_pct=97.0
        )
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_c1c2"


class TestNoBudgetData:
    def test_null_budget_pct_no_budget_triggers(self):
        snap = _make_snapshot(budget_pct=None)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "noop"
        assert "All conditions nominal" in decision.reason

    def test_null_budget_with_claude_degraded_still_works(self):
        snap = _make_snapshot(budget_pct=None, claude_4hr_pct=97.0)
        state = _make_state()
        decision = pm.evaluate_triggers(snap, state)
        assert decision.action == "degrade_c1"


class TestBudgetSnapshot:
    def test_create_and_serialize(self):
        snap = pm.BudgetSnapshot(
            month_spend_cents=5000, month_budget_cents=10000, budget_pct=50.0,
        )
        d = snap.to_dict()
        assert d["month_spend_cents"] == 5000
        assert d["month_budget_cents"] == 10000
        assert d["budget_pct"] == 50.0
        assert d["dashboard_error"] is None


class TestFetchBudgetData:
    @patch("provider_monitor._paperclip_session")
    def test_successful_fetch(self, mock_session_fn):
        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "costs": {"monthSpendCents": 35000, "monthBudgetCents": 50000}
        }
        mock_sess.get.return_value = mock_resp
        mock_session_fn.return_value.__enter__.return_value = mock_sess
        spend, budget, pct, err = pm.fetch_budget_data()
        assert spend == 35000
        assert budget == 50000
        assert pct == 70.0
        assert err is None

    @patch("provider_monitor._paperclip_session")
    def test_missing_budget(self, mock_session_fn):
        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"costs": {"monthSpendCents": 1000}}
        mock_sess.get.return_value = mock_resp
        mock_session_fn.return_value.__enter__.return_value = mock_sess
        spend, budget, pct, err = pm.fetch_budget_data()
        assert spend == 1000
        assert budget is None
        assert pct is None
        assert err is None

    @patch("provider_monitor._paperclip_session")
    def test_api_error(self, mock_session_fn):
        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_sess.get.return_value = mock_resp
        mock_session_fn.return_value.__enter__.return_value = mock_sess
        spend, budget, pct, err = pm.fetch_budget_data()
        assert spend is None
        assert budget is None
        assert pct is None
        assert "500" in err


class TestApplySwitchBudgetState:
    @patch("provider_monitor.patch_agent_model", return_value=True)
    @patch("provider_monitor.save_state")
    def test_b3_sets_budget_state(self, mock_save, mock_patch):
        state = pm.MonitorState()
        decision = pm.SwitchingDecision(
            action="degrade_budget_b3",
            pro_model=pm.STANDARD_MODEL_DEGRADED,
            standard_model=pm.STANDARD_MODEL_DEGRADED,
            reason="test",
        )
        pm.apply_switch(decision, state, dry_run=False)
        assert state.budget_degraded_level == "b3"
        assert state.last_switch_direction == "budget_degrade"
        assert state.last_budget_switch_at is not None
        mock_save.assert_called_once()

    @patch("provider_monitor.patch_agent_model", return_value=True)
    @patch("provider_monitor.save_state")
    def test_b2_sets_budget_state(self, mock_save, mock_patch):
        state = pm.MonitorState()
        decision = pm.SwitchingDecision(
            action="degrade_budget_b2",
            pro_model=pm.PRO_MODEL_NORMAL,
            standard_model=pm.STANDARD_MODEL_DEGRADED,
            reason="test",
        )
        pm.apply_switch(decision, state, dry_run=False)
        assert state.budget_degraded_level == "b2"

    @patch("provider_monitor.patch_agent_model", return_value=True)
    @patch("provider_monitor.save_state")
    def test_upgrade_clears_budget_state(self, mock_save, mock_patch):
        state = pm.MonitorState(budget_degraded_level="b3")
        decision = pm.SwitchingDecision(
            action="upgrade_budget",
            pro_model=pm.PRO_MODEL_NORMAL,
            standard_model=pm.STANDARD_MODEL_NORMAL,
            reason="test",
        )
        pm.apply_switch(decision, state, dry_run=False)
        assert state.budget_degraded_level is None
        assert state.last_switch_direction == "budget_upgrade"


class TestMonitorStateBudget:
    def test_roundtrip_budget_fields(self):
        state = pm.MonitorState(
            budget_degraded_level="b3",
            last_budget_switch_at="2026-05-14T12:00:00Z",
            budget_alert_sent=True,
        )
        d = state.to_dict()
        loaded = pm.MonitorState.from_dict(d)
        assert loaded.budget_degraded_level == "b3"
        assert loaded.last_budget_switch_at == "2026-05-14T12:00:00Z"
        assert loaded.budget_alert_sent is True

    def test_from_dict_missing_budget_fields_defaults(self):
        loaded = pm.MonitorState.from_dict({})
        assert loaded.budget_degraded_level is None
        assert loaded.last_budget_switch_at is None
        assert loaded.budget_alert_sent is False
