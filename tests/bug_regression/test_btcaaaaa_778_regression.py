"""
Regression tests for BTCAAAAA-778: None exit conditions crash in hasattr-guard.

Root cause: _get_required_exit_signals and _organize_exit_conditions crashed
when exit_conditions was None or lacked expected dict structure.

This file re-exports the existing integration test unchanged.
The canonical logic is in tests/integration/ so it cannot drift from
the original fix verification.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-778"),
    pytest.mark.regression,
]

from tests.integration.test_btcaaaaa_778_none_exit_conditions import (  # noqa: E402, F401
    TestSignalExistsInConfigNoneExitConditions,
    TestLiquiditySweepExitConditionsAttribute,
)
