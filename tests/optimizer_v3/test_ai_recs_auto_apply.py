"""
Unit Tests for AutoApplyOrchestrator (Sprint 1.9.4 / BTCAAAAA-36744)
==================================================================

Coverage:
- classify() pure function: SAFE / DESTRUCTIVE / UNSUPPORTED
- dry_run: counts, opt-in preview, requires_any_opt_in
- run_apply_all: backup -> apply -> verify -> mark_applied lifecycle
- rollback on verify failure
- UNSUPPORTED skipped without failing the batch
- DESTRUCTIVE without opt-in skipped (not failed)
- progress callback receives (percent, stage_label) in 0..100
- manager.mark_applied called with (rec_id, version_id, applied_by)
- per-rec exception captured in failed, does not crash batch
- empty recs list returns clean empty ApplyResult
"""

from __future__ import annotations

import pytest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from src.optimizer_v3.ui.ai_recs_auto_apply import (
    AutoApplyOrchestrator,
    ApplyClassification,
    DryRunEntry,
    DryRunResult,
    AppliedEntry,
    ApplyResult,
    classify,
    FIX_STRATEGY_TYPE,
    REDUCE_RECHECK_DELAY,
    CONSOLIDATE_DUPLICATE_EXITS,
    REMOVE_DEAD_CODE,
    ADD_SIGNAL,
    ADD_BLOCK,
    ADJUST_PARAM,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeManager:
    """Records every mark_applied call; raise-on-demand."""

    def __init__(self, fail_for: Optional[List[str]] = None) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._fail_for = set(fail_for or [])

    def mark_applied(
        self,
        recommendation_id: str,
        applied_version_id: str,
        applied_by: Optional[str] = None,
    ) -> bool:
        if recommendation_id in self._fail_for:
            return False
        self.calls.append({
            "recommendation_id": recommendation_id,
            "applied_version_id": applied_version_id,
            "applied_by": applied_by,
        })
        return True


class FakeSafety:
    """Stub of AutoFixSafety: snapshot/verify/rollback are no-ops we can flip."""

    def __init__(self, verify_returns: bool = True) -> None:
        self.backup_called = False
        self.rollback_called = False
        self.verify_returns = verify_returns

    def backup_strategy(self, strategy) -> None:
        self.backup_called = True

    def verify_fix_result(self, config) -> bool:
        return self.verify_returns

    def rollback_if_needed(self, config) -> bool:
        self.rollback_called = True
        return True

    def log_fix_attempt(self, fix_type: str, success: bool, error: Optional[str] = None) -> None:
        pass


class FakeConfig:
    """Minimal stand-in for StrategyConfig -- just enough attrs for dispatcher."""

    def __init__(self, version_id: str = "v_test", blocks=None, exit_conditions=None) -> None:
        self.version_id = version_id
        self.blocks = blocks or []
        self.exit_conditions = exit_conditions or []
        self.tag = "after-apply"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rec_dict(rec_type: str, rec_id: Optional[str] = None, **extra) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "recommendation_id": rec_id or f"rec-{rec_type}",
        "type": rec_type,
        "reasoning": f"unit-test reasoning for {rec_type}",
    }
    d.update(extra)
    return d


def _rec_obj(rec_type: str, rec_id: Optional[str] = None, **extra) -> Any:
    ns = SimpleNamespace(
        recommendation_id=rec_id or f"rec-{rec_type}",
        type=rec_type,
        reasoning=f"unit-test reasoning for {rec_type}",
    )
    for k, v in extra.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# classify()
# ---------------------------------------------------------------------------

class TestClassify:

    @pytest.mark.parametrize("rec_type", [
        FIX_STRATEGY_TYPE, REDUCE_RECHECK_DELAY,
        CONSOLIDATE_DUPLICATE_EXITS, REMOVE_DEAD_CODE,
    ])
    def test_safe_types(self, rec_type):
        assert classify(_rec_dict(rec_type)) is ApplyClassification.SAFE

    @pytest.mark.parametrize("rec_type", [
        ADD_SIGNAL, ADD_BLOCK, ADJUST_PARAM,
    ])
    def test_destructive_types(self, rec_type):
        assert classify(_rec_dict(rec_type)) is ApplyClassification.DESTRUCTIVE

    def test_unknown_type_is_unsupported(self):
        assert classify(_rec_dict("CONFIGURE_SIGNAL_V999")) is ApplyClassification.UNSUPPORTED

    def test_missing_type_is_unsupported(self):
        assert classify({"recommendation_id": "x"}) is ApplyClassification.UNSUPPORTED

    def test_accepts_object_shaped_rec(self):
        rec = _rec_obj(FIX_STRATEGY_TYPE)
        assert classify(rec) is ApplyClassification.SAFE

    def test_accepts_object_shaped_destructive(self):
        rec = _rec_obj(ADD_BLOCK)
        assert classify(rec) is ApplyClassification.DESTRUCTIVE


# ---------------------------------------------------------------------------
# dry_run()
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_empty_recs_yields_empty_result(self):
        orch = AutoApplyOrchestrator()
        result = orch.dry_run([])
        assert result.entries == []
        assert result.safe_count == 0
        assert result.destructive_count == 0
        assert result.unsupported_count == 0
        assert result.requires_any_opt_in is False

    def test_counts_match_recs(self):
        orch = AutoApplyOrchestrator()
        recs = [
            _rec_dict(FIX_STRATEGY_TYPE, "r1"),
            _rec_dict(ADD_BLOCK, "r2"),
            _rec_dict("UNKNOWN_TYPE", "r3"),
        ]
        result = orch.dry_run(recs)
        assert result.safe_count == 1
        assert result.destructive_count == 1
        assert result.unsupported_count == 1
        assert len(result.entries) == 3

    def test_destructive_marks_requires_opt_in(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict(ADD_BLOCK, "r1")
        result = orch.dry_run([rec])
        entry = result.entries[0]
        assert entry.classification is ApplyClassification.DESTRUCTIVE
        assert entry.requires_opt_in is True
        assert entry.destructive_reason
        assert result.requires_any_opt_in is True

    def test_safe_does_not_require_opt_in(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1")
        result = orch.dry_run([rec])
        entry = result.entries[0]
        assert entry.requires_opt_in is False
        assert entry.destructive_reason is None
        assert result.requires_any_opt_in is False

    def test_unsupported_does_not_require_opt_in(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict("MYSTERY", "r1")
        result = orch.dry_run([rec])
        assert result.entries[0].requires_opt_in is False
        assert result.requires_any_opt_in is False

    def test_opt_in_ids_accepted_but_not_counted_as_safe(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict(ADD_BLOCK, "r1")
        result = orch.dry_run([rec], opt_in_destructive_ids=["r1"])
        assert result.destructive_count == 1
        assert result.requires_any_opt_in is True

    def test_target_label_built_from_block_and_signal(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict(ADD_SIGNAL, "r1", block_name="hod", signal_name="HOD_REJECTION")
        entry = orch.dry_run([rec]).entries[0]
        assert "block=hod" in entry.target
        assert "signal=HOD_REJECTION" in entry.target

    def test_target_label_falls_back_to_param(self):
        orch = AutoApplyOrchestrator()
        rec = _rec_dict(ADJUST_PARAM, "r1", parameter_name="stop_loss_pct")
        entry = orch.dry_run([rec]).entries[0]
        assert entry.target == "param=stop_loss_pct"

    def test_to_payload_shape(self):
        orch = AutoApplyOrchestrator()
        recs = [_rec_dict(FIX_STRATEGY_TYPE, "r1"), _rec_dict(ADD_BLOCK, "r2")]
        payload = orch.dry_run(recs).to_payload()
        assert "entries" in payload
        assert "safe_count" in payload
        assert "destructive_count" in payload
        assert "unsupported_count" in payload
        assert "requires_any_opt_in" in payload
        assert payload["safe_count"] == 1
        assert payload["destructive_count"] == 1
        assert payload["unsupported_count"] == 0


# ---------------------------------------------------------------------------
# run_apply_all() -- happy path
# ---------------------------------------------------------------------------

class TestRunApplyAllHappyPath:

    def test_empty_recs_returns_clean_empty_result(self):
        orch = AutoApplyOrchestrator()
        cfg = FakeConfig()
        result = orch.run_apply_all([], cfg)
        assert result.applied == []
        assert result.skipped == []
        assert result.failed == []
        assert result.rolled_back is False
        assert result.applied_count == 0
        assert result.failed_count == 0

    def test_fix_strategy_type_calls_auto_fix(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        called = {"n": 0, "suggested": None}

        def fake_auto_fix(cfg, suggested):
            called["n"] += 1
            called["suggested"] = suggested
            cfg.tag = "fixed"
            return True

        monkeypatch.setattr(mod, "auto_fix_strategy_type", fake_auto_fix)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert called["n"] == 1
        assert called["suggested"] == "Bullish"
        assert result.applied_count == 1
        assert result.failed_count == 0
        assert result.rolled_back is False

    def test_destructive_skipped_without_opt_in(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda *a, **k: True)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict(ADD_BLOCK, "r1")
        result = orch.run_apply_all([rec], FakeConfig())
        assert result.applied_count == 0
        assert len(result.skipped) == 1
        assert "did not opt in" in result.skipped[0].message
        assert result.skipped[0].rec_id == "r1"

    def test_destructive_with_opt_in_dispatches(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda *a, **k: True)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict(ADD_BLOCK, "r1")
        result = orch.run_apply_all(
            [rec], FakeConfig(), opt_in_destructive_ids=["r1"]
        )
        # Dispatcher hits the "destructive but no 1.9.3 algo yet" branch
        # and returns False. The rec should be in failed (not skipped),
        # because it passed the opt-in gate.
        assert len(result.applied) == 0
        assert len(result.skipped) == 0
        assert len(result.failed) == 1
        assert result.failed[0].rec_id == "r1"

    def test_unsupported_skipped(self):
        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict("MYSTERY_TYPE", "r1")
        result = orch.run_apply_all([rec], FakeConfig())
        assert result.applied_count == 0
        assert len(result.skipped) == 1
        assert "unsupported" in result.skipped[0].message

    def test_manager_mark_applied_called_with_correct_args(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        manager = FakeManager()
        orch = AutoApplyOrchestrator(manager=manager, safety=FakeSafety(), applied_by="unit_test")
        rec = _rec_dict(FIX_STRATEGY_TYPE, "rec-xyz", suggested_value="Bullish")
        orch.run_apply_all([rec], FakeConfig(version_id="v42"))
        assert len(manager.calls) == 1
        call = manager.calls[0]
        assert call["recommendation_id"] == "rec-xyz"
        assert call["applied_version_id"] == "v42"
        assert call["applied_by"] == "unit_test"

    def test_backup_called_once_before_apply(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        safety = FakeSafety()
        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=safety)
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        orch.run_apply_all([rec], FakeConfig())
        assert safety.backup_called is True
        assert safety.rollback_called is False

    def test_progress_callback_invoked_with_zero_to_hundred(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        events: List[tuple] = []

        def cb(percent, stage_label):
            events.append((percent, stage_label))

        orch = AutoApplyOrchestrator(
            manager=FakeManager(),
            safety=FakeSafety(),
            progress_cb=cb,
        )
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        orch.run_apply_all([rec], FakeConfig())
        assert len(events) >= 2
        # Last event must be the "Apply complete" terminal at 100%
        assert events[-1][0] == 100
        last_label = events[-1][1].lower()
        assert "complete" in last_label or "nothing" in last_label
        for pct, _ in events:
            assert 0 <= pct <= 100

    def test_set_progress_callback_after_construction(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        events: List[tuple] = []
        orch.set_progress_callback(lambda p, s: events.append((p, s)))
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        orch.run_apply_all([rec], FakeConfig())
        assert len(events) >= 2
        assert events[-1][0] == 100

    def test_progress_callback_exception_does_not_break_apply(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        def bad_cb(p, s):
            raise RuntimeError("UI is broken")

        orch = AutoApplyOrchestrator(
            manager=FakeManager(),
            safety=FakeSafety(),
            progress_cb=bad_cb,
        )
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert result.applied_count == 1

    def test_no_manager_still_applies(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        orch = AutoApplyOrchestrator(manager=None, safety=FakeSafety())
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert result.applied_count == 1
        assert result.failed_count == 0


# ---------------------------------------------------------------------------
# run_apply_all() -- rollback path
# ---------------------------------------------------------------------------

class TestRunApplyAllRollback:

    def test_rollback_on_verify_failure(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        safety = FakeSafety(verify_returns=False)
        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=safety)
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert safety.rollback_called is True
        assert result.rolled_back is True
        assert result.applied_count == 0
        assert len(result.failed) == 1
        assert "rolled back" in result.failed[0].message

    def test_partial_batch_rolled_back_on_late_failure(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        safety = FakeSafety(verify_returns=True)
        call_count = {"n": 0}

        def maybe_fail(cfg):
            call_count["n"] += 1
            return call_count["n"] < 2

        safety.verify_fix_result = maybe_fail  # type: ignore[assignment]

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=safety)
        rec1 = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        rec2 = _rec_dict(FIX_STRATEGY_TYPE, "r2", suggested_value="Bearish")
        result = orch.run_apply_all([rec1, rec2], FakeConfig())
        assert safety.rollback_called is True
        assert result.rolled_back is True
        assert result.applied_count == 0

    def test_dispatcher_exception_goes_to_failed_not_crashed(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod

        def boom(cfg, v):
            raise RuntimeError("disk full")

        monkeypatch.setattr(mod, "auto_fix_strategy_type", boom)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert len(result.failed) == 1
        assert "disk full" in result.failed[0].message
        assert result.rolled_back is False
        assert result.applied_count == 0

    def test_mixed_batch_safe_unsupported_destructive(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        recs = [
            _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish"),
            _rec_dict("MYSTERY", "r2"),
            _rec_dict(ADD_BLOCK, "r3"),
            _rec_dict(FIX_STRATEGY_TYPE, "r4", suggested_value="Bearish"),
        ]
        result = orch.run_apply_all(recs, FakeConfig())
        assert result.applied_count == 2
        assert len(result.skipped) == 2
        assert result.failed_count == 0
        assert result.rolled_back is False

    def test_mark_applied_failure_does_not_undo_already_applied_fix(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)

        class AuditFailManager:
            def __init__(self):
                self.calls = []
            def mark_applied(self, recommendation_id, applied_version_id, applied_by=None):
                self.calls.append(recommendation_id)
                return False

        manager = AuditFailManager()
        orch = AutoApplyOrchestrator(manager=manager, safety=FakeSafety())
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        result = orch.run_apply_all([rec], FakeConfig())
        assert len(result.failed) == 1
        assert "mark_applied" in result.failed[0].message
        assert manager.calls == ["r1"]


# ---------------------------------------------------------------------------
# Pure dispatcher tests (for the 4 Sprint 1.9.2 algorithms)
# ---------------------------------------------------------------------------

class TestDispatcherByAlgo:

    def test_reduce_recheck_delay_requires_block_signal_window(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        called = {"n": 0, "window": None, "buffer": None}
        monkeypatch.setattr(
            mod, "auto_fix_recheck_delay",
            lambda rc, w, buffer=0.75: called.update(n=called["n"] + 1, window=w, buffer=buffer) or True,
        )
        rec = _rec_dict(REDUCE_RECHECK_DELAY, "r1", block_name="hod", signal_name="S1", timing_window=10)
        block = SimpleNamespace(
            name="hod",
            signals=[SimpleNamespace(name="S1", recheck_config=SimpleNamespace(bar_delay=999))],
        )
        cfg = FakeConfig(blocks=[block])
        result = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety()).run_apply_all([rec], cfg)
        assert called["n"] == 1
        assert called["window"] == 10
        assert called["buffer"] == 0.75
        assert result.applied_count == 1

    def test_reduce_recheck_delay_block_not_found_is_silent_noop(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        called = {"n": 0}
        monkeypatch.setattr(mod, "auto_fix_recheck_delay", lambda *a, **k: (called.update(n=called["n"]+1) or True))
        rec = _rec_dict(REDUCE_RECHECK_DELAY, "r1", block_name="missing", signal_name="S1", timing_window=10)
        cfg = FakeConfig(blocks=[])
        result = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety()).run_apply_all([rec], cfg)
        assert called["n"] == 0
        assert result.applied_count == 0
        assert result.failed_count == 0

    def test_consolidate_duplicate_exits_replaces_attr(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(
            mod, "auto_fix_duplicate_exits",
            lambda exits, sig_name: ["merged"],
        )
        rec = _rec_dict(CONSOLIDATE_DUPLICATE_EXITS, "r1", signal_name="EXIT_X")
        cfg = FakeConfig(exit_conditions=["old1", "old2"])
        AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety()).run_apply_all([rec], cfg)
        assert cfg.exit_conditions == ["merged"]

    def test_remove_dead_code_with_dead_signal_names(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        called = {"n": 0, "names": None}
        monkeypatch.setattr(
            mod, "auto_fix_dead_code",
            lambda block, names, preserve_history=True: (
                called.update(n=called["n"] + 1, names=list(names)) or True
            ),
        )
        rec = _rec_dict(REMOVE_DEAD_CODE, "r1", block_name="hod", dead_signal_names=["S1", "S2"])
        block = SimpleNamespace(name="hod", signals=[SimpleNamespace(name="S1"), SimpleNamespace(name="S2")])
        cfg = FakeConfig(blocks=[block])
        result = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety()).run_apply_all([rec], cfg)
        assert called["n"] == 1
        assert called["names"] == ["S1", "S2"]
        assert result.applied_count == 1


# ---------------------------------------------------------------------------
# to_payload() / serialization
# ---------------------------------------------------------------------------

class TestResultSerialization:

    def test_dry_run_to_payload_round_trip(self):
        orch = AutoApplyOrchestrator()
        recs = [
            _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish"),
            _rec_dict(ADD_BLOCK, "r2", block_name="hod"),
        ]
        payload = orch.dry_run(recs).to_payload()
        import json
        json.dumps(payload)

    def test_apply_result_to_payload_round_trip(self, monkeypatch):
        from src.optimizer_v3.ui import ai_recs_auto_apply as mod
        monkeypatch.setattr(mod, "auto_fix_strategy_type", lambda cfg, v: True)
        orch = AutoApplyOrchestrator(manager=FakeManager(), safety=FakeSafety())
        rec = _rec_dict(FIX_STRATEGY_TYPE, "r1", suggested_value="Bullish")
        payload = orch.run_apply_all([rec], FakeConfig()).to_payload()
        import json
        json.dumps(payload)
        assert payload["applied_count"] == 1
        assert payload["failed_count"] == 0
        assert payload["rolled_back"] is False
