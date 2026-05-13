"""
Regression tests for BTCAAAAA-7299: Add version_id to serialize_config_for_backtest output.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-7299
Fixed in commit: 4a27819d (cherry-picked as 5fa0a53e)
Component: src/strategy_builder/integration/strategy_builder_orchestrator.py

Root cause: serialize_config_for_backtest() built a config dict without including
the current_version_id, so downstream consumers (BacktestWorker, calibration gate)
had to separately read self.orchestrator.current_version_id rather than getting
it from the serialized config dict itself.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock

pytestmark = [
    pytest.mark.bug("BTCAAAAA-7299"),
    pytest.mark.regression,
]


class TestSerializeConfigForBacktestVersionId:
    """Verify serialize_config_for_backtest() includes version_id in its output."""

    def test_version_id_in_serialized_output(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.current_version_id = "test-version-uuid"

        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {"name": "Alpha", "logic": "AND", "signals": []})()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        assert "version_id" in result
        assert result["version_id"] == "test-version-uuid"

    def test_version_id_is_none_when_not_set(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.current_version_id = None

        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {"name": "Alpha", "logic": "AND", "signals": []})()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        assert "version_id" in result
        assert result["version_id"] is None

    def test_version_id_propagates_through_backtest_config_panel(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        orchestrator.current_version_id = "uuid-1234"

        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {"name": "Alpha", "logic": "AND", "signals": []})()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        assert result["version_id"] == orchestrator.current_version_id
