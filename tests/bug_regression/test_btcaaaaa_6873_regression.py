"""
Regression tests for BTCAAAAA-6873: add parameters field to BlockConfig +
serialize metadata/indented/parameters + pass params to block instantiation.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-6873
Fixed in commit: abf16db3
Component: src/strategy_builder/core/strategy_config_engine.py,
          src/strategy_builder/integration/strategy_builder_orchestrator.py,
          src/strategy_builder/persistence/strategy_persistence.py

Root cause: BlockConfig was missing a parameters field, and the serialization
in serialize_config_for_backtest() omitted metadata, indented, and parameters.
Block instantiation received no tunable params. Fix added the field, included
all 3 fields in serialize_config_for_backtest(), and passed params as kwargs
to BlockRegistry.instantiate().
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-6873"),
    pytest.mark.regression,
]

from tests.strategy_builder.persistence.test_strategy_persistence import (  # noqa: E402, F401
    TestParametersMetadataIndented,
)


class TestSerializeConfigFields:
    """Verify serialize_config_for_backtest() includes metadata/indented/parameters."""

    def test_serialize_includes_metadata(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {
            "name": "Alpha", "logic": "AND", "signals": [],
            "metadata": {"source": "test"},
            "indented": True,
            "parameters": {"lookback": 14},
        })()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        block_out = result["blocks"][0]
        assert block_out["metadata"] == {"source": "test"}
        assert block_out["indented"] is True
        assert block_out["parameters"] == {"lookback": 14}

    def test_serialize_defaults_when_attrs_missing(self):
        from src.strategy_builder.integration.strategy_builder_orchestrator import (
            StrategyBuilderOrchestrator,
        )

        orchestrator = StrategyBuilderOrchestrator()
        config = orchestrator.config_engine.config
        config.name = "TestStrategy"
        block = type("Block", (), {
            "name": "Alpha", "logic": "AND", "signals": [],
        })()
        config.blocks.append(block)

        result = orchestrator.serialize_config_for_backtest()
        block_out = result["blocks"][0]
        assert block_out.get("metadata") is None
        assert block_out.get("indented") is False
        assert block_out.get("parameters") == {}
