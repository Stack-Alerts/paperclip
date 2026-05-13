"""
Regression tests for BTCAAAAA-685: Zero-trades root cause (reference/reference_signal key).

Root cause: _get_timing_constraint_for_signal reads 'reference_signal' from the
timing_constraint dict, but current_strategy.json uses the key 'reference'.
This means the timing constraint for BELOW_ASIA_50 is never injected.

This file re-exports the existing integration test unchanged.
The canonical logic is in tests/integration/ so it cannot drift from
the original fix verification.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-685"),
    pytest.mark.regression,
]

from tests.integration.test_btcaaaaa_685_timing_chain import (  # noqa: E402, F401
    TestTimingConstraintKeyParsing,
    TestAsiaRejectionTimingChain,
)
