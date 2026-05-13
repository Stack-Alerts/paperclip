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
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-33"),
    pytest.mark.regression,
]


class TestOrchestratorStrategyId:
    """Verify orchestrator tracks strategy_id and version_id."""

    def test_orchestrator_has_strategy_id_attribute(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        assert hasattr(orchestrator, "current_strategy_id")
        assert hasattr(orchestrator, "current_version_id")

    def test_strategy_id_defaults_to_none(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        assert orchestrator.current_strategy_id is None
        assert orchestrator.current_version_id is None

    def test_orchestrator_serialize_includes_version_id(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.current_version_id = "ver-uuid"
        orchestrator.current_strategy_id = "strat-uuid"

        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {"name": "Alpha", "logic": "AND", "signals": []})()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        assert result.get("version_id") == "ver-uuid"
