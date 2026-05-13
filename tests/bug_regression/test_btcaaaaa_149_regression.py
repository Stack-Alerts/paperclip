"""
Regression tests for BTCAAAAA-149: Config Discovery Engine — permutation
generation, metrics aggregation, and nested config delta helpers.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-149
Components: src/strategy_builder/ui/config_permutation_engine.py
            src/strategy_builder/ui/config_discovery_results_dialog.py

This file re-exports the existing Config Discovery unit tests from
tests/strategy_builder/integration/test_config_discovery_engine.py so
the Impact Gate runner can discover them by bug ID.  The canonical
tests live in tests/strategy_builder/integration/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-149"),
    pytest.mark.regression,
]

from tests.strategy_builder.integration.test_config_discovery_engine import (  # noqa: E402, F401
    TestParameterRange,
    TestSetNested,
    TestGenerateSingleAxisPermutations,
    TestConfigPermutationEngineFacade,
    TestDefaultParameterRanges,
    TestAggregateMetrics,
    TestDiscoveryResultSortability,
    two_value_ranges,
    adaptive_sl_ranges,
    base_config,
    sample_trades,
    sample_scenario,
)
