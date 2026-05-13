"""
Regression tests for BTCAAAAA-33: fix test result persistence — parent_window lookup
fails in BacktestConfigPanel.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-33
Fixed in commit: 6b2fad56
Component: src/strategy_builder/integration/strategy_builder_orchestrator.py

Root cause: BacktestConfigPanel._populate_tabs_with_results() read strategy_id
and version_id from self.parent_window (BacktestConfigDialog) which had no
current_strategy_id, so every DB persist was silently skipped. Fix added
current_strategy_id to StrategyBuilderOrchestrator alongside current_version_id.

Acceptance criteria tested here:
  AC1  StrategyBuilderOrchestrator has current_strategy_id attribute.
  AC2  StrategyBuilderOrchestrator has current_version_id attribute.
  AC3  current_strategy_id defaults to None on fresh instance.
  AC4  current_version_id defaults to None on fresh instance.
  AC5  loaded_strategy_path attribute still exists (regression safety).
  AC6  strategy_id can be set independently of version_id.
  AC7  version_id can be set independently of strategy_id.
  AC8  version_id is included in serialize_config_for_backtest output.
  AC9  strategy_id is NOT included in serialize_config_for_backtest output.
  AC10 serialize_config_for_backtest raises ValueError when config has no name.
  AC11 serialize_config_for_backtest raises ValueError when config has no blocks.
  AC12 create_strategy preserves existing current_strategy_id and current_version_id.
  AC13 Multiple orchestrator instances maintain independent ID state.
  AC14 Serialize does not mutate orchestrator ID attributes.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-33"),
    pytest.mark.regression,
]


def _make_orchestrator():
    from src.strategy_builder.integration.strategy_builder_orchestrator import (
        StrategyBuilderOrchestrator,
    )

    return StrategyBuilderOrchestrator()


def _make_minimal_config(orchestrator):
    """Set up minimal config so serialize_config_for_backtest does not raise."""
    config = orchestrator.config_engine.config
    config.name = "TestStrategy"
    block = type("Block", (), {"name": "Alpha", "logic": "AND", "signals": []})()
    config.blocks.append(block)
    return config


class TestOrchestratorAttributes:
    """AC1-AC5: Verify orchestrator tracking attributes."""

    def test_orchestrator_has_strategy_id_attribute(self):
        orchestrator = _make_orchestrator()
        assert hasattr(orchestrator, "current_strategy_id")

    def test_orchestrator_has_version_id_attribute(self):
        orchestrator = _make_orchestrator()
        assert hasattr(orchestrator, "current_version_id")

    def test_strategy_id_defaults_to_none(self):
        orchestrator = _make_orchestrator()
        assert orchestrator.current_strategy_id is None

    def test_version_id_defaults_to_none(self):
        orchestrator = _make_orchestrator()
        assert orchestrator.current_version_id is None

    def test_loaded_strategy_path_preserved(self):
        orchestrator = _make_orchestrator()
        assert hasattr(orchestrator, "loaded_strategy_path")
        assert orchestrator.loaded_strategy_path is None


class TestOrchestratorIdAssignment:
    """AC6-AC7: Verify IDs can be set independently."""

    def test_strategy_id_set_independently(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "strat-abc"
        assert orchestrator.current_strategy_id == "strat-abc"
        assert orchestrator.current_version_id is None

    def test_version_id_set_independently(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_version_id = "ver-xyz"
        assert orchestrator.current_version_id == "ver-xyz"
        assert orchestrator.current_strategy_id is None

    def test_both_ids_set_simultaneously(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "strat-abc"
        orchestrator.current_version_id = "ver-xyz"
        assert orchestrator.current_strategy_id == "strat-abc"
        assert orchestrator.current_version_id == "ver-xyz"

    def test_ids_can_be_reset_to_none(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "sid"
        orchestrator.current_version_id = "vid"
        orchestrator.current_strategy_id = None
        orchestrator.current_version_id = None
        assert orchestrator.current_strategy_id is None
        assert orchestrator.current_version_id is None


class TestSerialization:
    """AC8-AC11: Verify serialize_config_for_backtest behavior."""

    def test_serialize_includes_version_id(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_version_id = "ver-uuid"
        orchestrator.current_strategy_id = "strat-uuid"
        _make_minimal_config(orchestrator)
        result = orchestrator.serialize_config_for_backtest()
        assert result.get("version_id") == "ver-uuid"

    def test_serialize_does_not_include_strategy_id(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "strat-uuid"
        orchestrator.current_version_id = "ver-uuid"
        _make_minimal_config(orchestrator)
        result = orchestrator.serialize_config_for_backtest()
        assert "strategy_id" not in result

    def test_serialize_raises_without_name(self):
        orchestrator = _make_orchestrator()
        config = orchestrator.config_engine.config
        config.name = ""
        block = type("Block", (), {"name": "A", "logic": "AND", "signals": []})()
        config.blocks.append(block)
        with pytest.raises(ValueError, match="No strategy configured"):
            orchestrator.serialize_config_for_backtest()

    def test_serialize_raises_without_blocks(self):
        orchestrator = _make_orchestrator()
        orchestrator.config_engine.config.name = "Orphan"
        with pytest.raises(ValueError, match="has no blocks"):
            orchestrator.serialize_config_for_backtest()


class TestIdPersistence:
    """AC12-AC14: Verify IDs persist across operations."""

    def test_create_strategy_preserves_ids(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "preserved-sid"
        orchestrator.current_version_id = "preserved-vid"
        orchestrator.create_strategy("NewName")
        assert orchestrator.current_strategy_id == "preserved-sid"
        assert orchestrator.current_version_id == "preserved-vid"

    def test_multiple_instances_independent(self):
        o1 = _make_orchestrator()
        o2 = _make_orchestrator()
        o1.current_strategy_id = "o1-sid"
        o1.current_version_id = "o1-vid"
        assert o2.current_strategy_id is None
        assert o2.current_version_id is None
        o2.current_strategy_id = "o2-sid"
        assert o1.current_strategy_id == "o1-sid"
        assert o2.current_strategy_id == "o2-sid"

    def test_serialize_does_not_mutate_ids(self):
        orchestrator = _make_orchestrator()
        orchestrator.current_strategy_id = "stable-sid"
        orchestrator.current_version_id = "stable-vid"
        _make_minimal_config(orchestrator)
        orchestrator.serialize_config_for_backtest()
        assert orchestrator.current_strategy_id == "stable-sid"
        assert orchestrator.current_version_id == "stable-vid"


# ======================================================================
# Impact Gate Meta-Tests
# ======================================================================


class TestFileMetadata:
    """Validate file structure expected by the Impact Gate runner."""

    def test_file_docstring_contains_issue_number(self):
        assert "BTCAAAAA-33" in (__doc__ or "")

    def test_bug_marker_has_correct_id(self):
        marker_ids = [
            m.args[0] for m in pytestmark
            if hasattr(m, "args") and m.args
        ]
        assert "BTCAAAAA-33" in marker_ids
