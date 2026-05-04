"""
Unit Tests for UndoManager
BTCAAAAA-112 QA: Verify UndoManager and Undo button acceptance criteria

Tests cover:
- Class initialises correctly
- can_undo() returns False on empty stack, True after record_fix()
- undo_last_fix() restores config in-place and returns True
- undo_last_fix() returns False on empty stack
- Stack cap (MAX_HISTORY) drops oldest entry beyond limit
- peek_last_label() returns label without popping
- clear() empties history
- Snapshot isolation: mutations after record_fix do not corrupt snapshot
"""

import pytest
from copy import deepcopy
from unittest.mock import MagicMock

from src.strategy_builder.validation.undo_manager import UndoManager
from src.strategy_builder.core.strategy_config_engine import StrategyConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(name: str = "test", strategy_type: str = "Bullish") -> StrategyConfig:
    """Return a minimal StrategyConfig for snapshot tests."""
    config = StrategyConfig()
    config.name = name
    config.strategy_type = strategy_type
    config.blocks = []
    config.exit_conditions = []
    return config


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestUndoManagerInit:
    def test_initialises_with_empty_history(self):
        mgr = UndoManager()
        assert mgr._history == []

    def test_can_undo_is_false_on_init(self):
        mgr = UndoManager()
        assert mgr.can_undo() is False

    def test_max_history_is_20(self):
        assert UndoManager.MAX_HISTORY == 20


# ---------------------------------------------------------------------------
# record_fix / can_undo
# ---------------------------------------------------------------------------

class TestRecordFix:
    def test_can_undo_true_after_one_record(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="rule_A")
        assert mgr.can_undo() is True

    def test_stack_depth_increments(self):
        mgr = UndoManager()
        config = make_config()
        for i in range(3):
            mgr.record_fix(config, label=f"fix_{i}")
        assert len(mgr._history) == 3

    def test_label_stored_in_history(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="DIRECTION_001")
        assert mgr._history[-1]["label"] == "DIRECTION_001"

    def test_timestamp_stored_in_history(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="test")
        assert "timestamp" in mgr._history[-1]
        assert isinstance(mgr._history[-1]["timestamp"], str)

    def test_snapshot_is_deep_copy(self):
        """Mutating original config after record_fix must NOT affect stored snapshot."""
        mgr = UndoManager()
        config = make_config(name="before")
        mgr.record_fix(config, label="snap_test")
        # Mutate original
        config.name = "after"
        assert mgr._history[-1]["snapshot"].name == "before"

    def test_empty_label_accepted(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config)  # no label argument
        assert mgr._history[-1]["label"] == ""

    def test_stack_cap_evicts_oldest(self):
        """Recording MAX_HISTORY+1 entries must evict the oldest, not exceed cap."""
        mgr = UndoManager()
        config = make_config()
        for i in range(UndoManager.MAX_HISTORY + 1):
            mgr.record_fix(config, label=f"fix_{i}")
        assert len(mgr._history) == UndoManager.MAX_HISTORY
        # The oldest ("fix_0") should have been evicted
        assert mgr._history[0]["label"] == "fix_1"


# ---------------------------------------------------------------------------
# undo_last_fix
# ---------------------------------------------------------------------------

class TestUndoLastFix:
    def test_returns_false_on_empty_stack(self):
        mgr = UndoManager()
        config = make_config()
        result = mgr.undo_last_fix(config)
        assert result is False

    def test_returns_true_when_snapshot_available(self):
        mgr = UndoManager()
        original = make_config(name="original")
        snapshot = deepcopy(original)
        mgr.record_fix(snapshot, label="fix_A")
        live = make_config(name="mutated")
        result = mgr.undo_last_fix(live)
        assert result is True

    def test_restores_config_in_place(self):
        """undo_last_fix must update config.__dict__ to match the snapshot."""
        mgr = UndoManager()
        original = make_config(name="v1", strategy_type="Bullish")
        mgr.record_fix(original, label="fix_A")
        # Simulate a fix being applied to the live config
        live = make_config(name="v2", strategy_type="Bearish")
        mgr.undo_last_fix(live)
        assert live.name == "v1"
        assert live.strategy_type == "Bullish"

    def test_pops_entry_from_stack(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="fix_A")
        mgr.record_fix(config, label="fix_B")
        assert len(mgr._history) == 2
        mgr.undo_last_fix(config)
        assert len(mgr._history) == 1

    def test_can_undo_false_after_last_entry_popped(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="only_fix")
        mgr.undo_last_fix(config)
        assert mgr.can_undo() is False

    def test_lifo_order(self):
        """Most recent snapshot is restored first (LIFO)."""
        mgr = UndoManager()
        v1 = make_config(name="v1")
        v2 = make_config(name="v2")
        mgr.record_fix(v1, label="fix_v1_to_v2")
        mgr.record_fix(v2, label="fix_v2_to_v3")
        live = make_config(name="v3")
        # First undo should restore v2
        mgr.undo_last_fix(live)
        assert live.name == "v2"
        # Second undo should restore v1
        mgr.undo_last_fix(live)
        assert live.name == "v1"

    def test_restored_snapshot_is_independent_copy(self):
        """After undo, mutating config must not affect any remaining stack entries."""
        mgr = UndoManager()
        v1 = make_config(name="v1")
        v2 = make_config(name="v2")
        mgr.record_fix(v1, label="fix_A")  # stack: [v1]
        mgr.record_fix(v2, label="fix_B")  # stack: [v1, v2]
        live = make_config(name="v3")
        mgr.undo_last_fix(live)            # restores v2, pops it; stack: [v1]
        # Mutate live after restore
        live.name = "mutated_post_undo"
        # Remaining snapshot for v1 should be unaffected
        mgr.undo_last_fix(live)
        assert live.name == "v1"


# ---------------------------------------------------------------------------
# peek_last_label
# ---------------------------------------------------------------------------

class TestPeekLastLabel:
    def test_returns_none_on_empty_stack(self):
        mgr = UndoManager()
        assert mgr.peek_last_label() is None

    def test_returns_label_of_most_recent_fix(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="first")
        mgr.record_fix(config, label="second")
        assert mgr.peek_last_label() == "second"

    def test_does_not_pop_entry(self):
        mgr = UndoManager()
        config = make_config()
        mgr.record_fix(config, label="keep_me")
        mgr.peek_last_label()
        assert len(mgr._history) == 1


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

class TestClear:
    def test_clears_all_history(self):
        mgr = UndoManager()
        config = make_config()
        for _ in range(5):
            mgr.record_fix(config)
        mgr.clear()
        assert mgr._history == []
        assert mgr.can_undo() is False


# ---------------------------------------------------------------------------
# Integration-style: AutoFixSafety parity
# ---------------------------------------------------------------------------

class TestAutoFixSafetyParity:
    """
    Verify UndoManager's in-place restoration mirrors AutoFixSafety.rollback_if_needed().
    Both use config.__dict__.update(deepcopy(snapshot.__dict__)) semantics.
    """

    def test_in_place_update_preserves_object_identity(self):
        """
        The same config object reference must reflect the restored values
        after undo_last_fix — no new object is created.
        """
        mgr = UndoManager()
        original = make_config(name="original")
        mgr.record_fix(original, label="fix")
        live = make_config(name="mutated")
        original_id = id(live)
        mgr.undo_last_fix(live)
        assert id(live) == original_id, "undo_last_fix must restore in-place, not replace the object"
        assert live.name == "original"
